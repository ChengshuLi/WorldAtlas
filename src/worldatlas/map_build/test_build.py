"""Runner contracts, measured parallelism, and actual raw-to-component chaining."""

import json
from contextlib import redirect_stderr
import os
import signal
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, nullcontext
import gzip
import hashlib
import io
from pathlib import Path
import zipfile
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

import numpy as np
from osgeo import ogr
import pyarrow as pa
import pyarrow.parquet as pq

from worldatlas.map_build import build as pipeline
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.execution.runtime import elapsed_union
from worldatlas.map_build.land.connected import build_components
from worldatlas.map_build.physical import build as physical_build
from worldatlas.map_build.test_support import selection
from worldatlas.shared.files import (
    json_bytes,
    pin_file,
    read_json,
    sha256_file,
    write_json,
)


class TimingTests(unittest.TestCase):
    def test_reused_physical_outputs_count_current_verification_only(self):
        with tempfile.TemporaryDirectory() as td:
            timer = pipeline.Timing(Path(td) / "events.jsonl")
            self.addCleanup(timer.close)
            receipt = {
                "status": "reused",
                "source_run": "/source/run",
                "processing_elapsed_seconds": 12345,
                "source_download_elapsed_seconds": 54321,
            }
            with timer.measure("physical", "verify-reused"):
                pass
            timer.mark_complete("physical", physical_report=receipt)
            result = timer.summary(receipt)["physical"]
            self.assertTrue(result["complete"])
            self.assertLess(result["processing_elapsed_seconds"], 1)
            self.assertEqual(result["source_download_elapsed_seconds"], 0)
            self.assertEqual(result["reused_from"], "/source/run")
            self.assertIsNone(result["producer_processing_elapsed_seconds"])

    def test_selected_configuration_has_portable_sources(self):
        path = Path(pipeline.__file__).parent / "config.json"
        cfg = read_json(path)
        self.assertNotIn("/workspace/", path.read_text())
        self.assertNotIn("/tmp/", path.read_text())
        self.assertNotIn("input_root", cfg)
        self.assertEqual(len(cfg["sources"]["inland_water"]["files"]), 32)
        self.assertNotIn("decision_revisions", cfg)
        self.assertEqual(
            set(cfg["sources"]), {"land_config", "inland_water"}
        )

    def test_interval_union_excludes_idle_gaps_and_parallel_double_count(self):
        self.assertEqual(elapsed_union([(1, 5), (2, 4), (8, 9), (4, 7)]), 7)
        self.assertEqual(elapsed_union([]), 0)
        with self.assertRaises(ValueError):
            elapsed_union([(2, 1)])

    def test_completed_intervals_survive_and_failures_remain_incomplete(self):
        with tempfile.TemporaryDirectory() as td:
            timer = pipeline.Timing(Path(td) / "events.jsonl")
            with patch.object(
                pipeline.time, "monotonic", side_effect=[10, 13, 20, 21, 40, 40, 65, 65]
            ):
                with timer.measure("water", "basin"):
                    pass
                with self.assertRaises(RuntimeError):
                    with timer.measure("water", "coast"):
                        raise RuntimeError("interrupted")
                with timer.measure("physical", "stage-total"):
                    with timer.measure("physical", "physical", kind="command"):
                        pass
            timer.completed_groups.add("physical")
            doc = timer.summary(
                {
                    "status": "candidate-only",
                    "processing_elapsed_seconds": 5,
                    "source_download_elapsed_seconds": 20,
                }
            )
            self.assertEqual(doc["water"]["processing_elapsed_seconds"], 4)
            self.assertFalse(doc["water"]["complete"])
            self.assertEqual(doc["physical"]["processing_elapsed_seconds"], 5)
            self.assertEqual(doc["physical"]["source_download_elapsed_seconds"], 20)
            records = [json.loads(line) for line in timer.path.read_text().splitlines()]
            self.assertEqual(
                [r["event"] for r in records if r["event"] != "attempt"],
                [
                    "start",
                    "complete",
                    "start",
                    "failed",
                    "start",
                    "start",
                    "complete",
                    "complete",
                ],
            )

    def test_invalid_acquisition_timing_cannot_be_a_complete_stage(self):
        with tempfile.TemporaryDirectory() as td:
            timer = pipeline.Timing(Path(td) / "events.jsonl")
            with patch.object(pipeline.time, "monotonic", side_effect=[1, 3]):
                with timer.measure("physical", "stage-total"):
                    pass
            timer.completed_groups.add("physical")
            summary = timer.summary(
                {"status": "candidate-only", "source_download_elapsed_seconds": 4}
            )["physical"]
            self.assertFalse(summary["complete"])
            self.assertIsNone(summary["processing_elapsed_seconds"])
            self.assertIsNotNone(summary["timing_error"])

    def test_parallel_jobs_are_measured_as_union_not_sum(self):
        with tempfile.TemporaryDirectory() as td:
            timer = pipeline.Timing(Path(td) / "events.jsonl")
            entered = threading.Barrier(3)

            def job(name):
                with timer.measure("water", name):
                    entered.wait()

            threads = [
                threading.Thread(target=job, args=(name,)) for name in ("sea", "coast")
            ]
            for thread in threads:
                thread.start()
            entered.wait()
            for thread in threads:
                thread.join()
            timer.completed_groups.add("water")
            summary = timer.summary(None)["water"]
            self.assertTrue(summary["complete"])
            completed = [r for r in timer.records if r["event"] == "complete"]
            intervals = [
                (r["start_monotonic_seconds"], r["monotonic_seconds"])
                for r in completed
            ]
            self.assertEqual(
                summary["processing_elapsed_seconds"], elapsed_union(intervals)
            )
            self.assertLess(
                summary["processing_elapsed_seconds"],
                sum(end - start for start, end in intervals),
            )


class CommandTests(unittest.TestCase):
    def test_build_requires_proj_offline(self):
        with (
            patch.object(pipeline, "set_network_enabled") as disable,
            patch.object(pipeline, "is_network_enabled", return_value=True),
            patch.dict(os.environ),
        ):
            with self.assertRaisesRegex(ValueError, "PROJ network must be disabled"):
                pipeline.validate_runtime()
            disable.assert_called_once_with(False)
            self.assertEqual(os.environ["PROJ_NETWORK"], "OFF")

    def test_build_requires_an_explicit_output(self):
        for options in ([], ["--resume"]):
            args = ["worldatlas-build", "config.json", *options]
            with (
                self.subTest(options=options),
                patch("sys.argv", args),
                patch.object(pipeline, "Pipeline") as builder,
                redirect_stderr(io.StringIO()) as error,
            ):
                with self.assertRaises(SystemExit) as stop:
                    pipeline.main()
                self.assertEqual(stop.exception.code, 2)
                self.assertIn("the following arguments are required: output", error.getvalue())
                builder.assert_not_called()

    def test_recompute_requires_a_prior_run(self):
        args = ["worldatlas-build", "config.json", "run", "--recompute-division"]
        with patch("sys.argv", args), redirect_stderr(io.StringIO()) as error:
            with self.assertRaises(SystemExit) as stop:
                pipeline.main()
        self.assertEqual(stop.exception.code, 2)
        self.assertIn("--recompute-division requires --reuse-from", error.getvalue())

    def test_stop_signals_cancel_the_active_builder(self):
        for signum in (signal.SIGTERM, signal.SIGINT):
            with self.subTest(signum=signum):
                install = Mock()
                runner = Mock()

                def interrupt_running_build():
                    handlers = dict(call.args for call in install.call_args_list)
                    handlers[signum](signum, None)

                runner.run.side_effect = interrupt_running_build
                with (
                    patch("sys.argv", ["worldatlas-build", "config.json", "run"]),
                    patch.object(pipeline, "Pipeline", return_value=runner),
                    patch.object(pipeline.signal, "signal", install),
                ):
                    with self.assertRaisesRegex(KeyboardInterrupt, str(signum)):
                        pipeline.main()
                runner.cancel.assert_called_once_with()


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.frozen = selection()
        for mocking in (
            patch.dict("os.environ", {"NEON_DATABASE_URL": "fixture"}),
            patch(
                "psycopg.connect", side_effect=lambda *a, **kw: nullcontext(object())
            ),
            patch.object(
                pipeline,
                "read_selection",
                side_effect=lambda *a, **kw: json.loads(json.dumps(self.frozen)),
            ),
        ):
            mocking.start()
            self.addCleanup(mocking.stop)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        self.cfg = {
            "schema": "worldatlas-end-to-end-pipeline-v3",
            "selection_notes": "Synthetic processor integration fixture",
            "input_root": str(self.root),
            "sources": {
                "land_config": {"land": []},
                "inland_water": {"rasterization": {}, "files": []},
            },
            "grid": dict(width=36, height=18, step=10),
        }

    def make(self):
        config = write_json(self.inputs / "request.json", self.cfg)
        runner = pipeline.Pipeline(config, self.root / "run")
        self.addCleanup(runner.close)
        return runner

    def test_parallel_builds_can_publish_the_same_generated_input(self):
        first = self.make()
        second = pipeline.Pipeline(first.config_path, self.root / "other-run")
        self.addCleanup(second.close)
        document = {"source": "shared"}
        data = json_bytes(document)
        name = hashlib.sha256(data).hexdigest() + ".json"
        opening = threading.Barrier(2)
        original = Path.open

        def synchronized(path, mode="r", *args, **kwargs):
            if mode == "xb" and name in path.name:
                opening.wait(timeout=10)
            return original(path, mode, *args, **kwargs)

        with (
            patch.object(Path, "open", synchronized),
            ThreadPoolExecutor(max_workers=2) as workers,
        ):
            futures = [
                workers.submit(runner.save_source_document, document)
                for runner in (first, second)
            ]
            paths = [future.result(timeout=10) for future in futures]
        self.assertEqual(paths[0], paths[1])
        self.assertEqual(paths[0].read_bytes(), data)
        self.assertIn(pin_file(paths[0]), first.source_pins)
        self.assertIn(pin_file(paths[0]), second.source_pins)

    def test_interrupted_generated_input_is_not_published_and_can_be_retried(self):
        runner = self.make()
        document = {"source": "interrupted"}
        data = json_bytes(document)
        path = self.inputs / (hashlib.sha256(data).hexdigest() + ".json")
        original = Path.open

        @contextmanager
        def interrupted(target, mode="r", *args, **kwargs):
            with original(target, mode, *args, **kwargs) as stream:
                if mode == "xb" and path.name in target.name:

                    def partial(value):
                        stream.write(value[:4])
                        stream.flush()
                        raise KeyboardInterrupt("interrupted write")

                    yield Mock(write=partial)
                else:
                    yield stream

        with (
            patch.object(Path, "open", interrupted),
            self.assertRaises(KeyboardInterrupt),
        ):
            runner.save_source_document(document)
        self.assertFalse(path.exists())
        self.assertEqual(runner.save_source_document(document), path)
        self.assertEqual(path.read_bytes(), data)
        path.write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "generated input changed"):
            runner.save_source_document(document)
        self.assertEqual(path.read_bytes(), b"corrupt")

    def test_invalid_source_fails_before_any_processing(self):
        local = write_json(self.inputs / "coast.geojson", {})
        self.select_coastline(
            str(local), files=[dict(pin_file(local), sha256="0" * 64)]
        )
        with self.assertRaisesRegex(ValueError, "selected source file differs"):
            self.make()
        self.assertFalse((self.root / "run").exists())

    def test_physical_settings_require_inline_values(self):
        path = write_json(self.inputs / "settings.json", {})
        for name in ("land_config", "inland_water"):
            with self.subTest(name=name):
                sources = dict(self.cfg["sources"], **{name: pin_file(path)})
                config = write_json(
                    self.inputs / f"{name}-request.json",
                    dict(self.cfg, sources=sources),
                )
                with self.assertRaisesRegex(ValueError, f"{name} .* inline"):
                    pipeline.Pipeline(config, self.root / "run")

    def test_rejects_invalid_run_options_before_creating_output(self):
        config = self.inputs / "build.json"
        output = self.root / "run"
        cases = [
            (dict(self.cfg, schema="unknown"), {}, "unsupported end-to-end configuration"),
            (dict(self.cfg, sources=[]), {}, "sources must be a JSON object"),
            (dict(self.cfg, sources={}), {}, "sources is missing inland_water, land_config"),
            (
                dict(self.cfg, sources=dict(self.cfg["sources"], inland_watre={})),
                {},
                "sources has unexpected keys inland_watre",
            ),
            (
                {key: value for key, value in self.cfg.items() if key != "input_root"},
                {},
                "choose a local input/run directory",
            ),
            (self.cfg, {"output": self.root.parent / "elsewhere"}, "new output inside input_root"),
            (self.cfg, {"recompute_division": True}, "requires --reuse-from"),
        ]
        for definition, options, error in cases:
            with self.subTest(error=error):
                config.write_text(json.dumps(definition))
                with self.assertRaisesRegex(ValueError, error):
                    pipeline.Pipeline(config, **({"output": output} | options))
                self.assertFalse(output.exists())

        config.write_text(json.dumps(self.cfg))
        output.mkdir()
        with self.assertRaisesRegex(ValueError, "no supported checkpoint identity"):
            pipeline.Pipeline(config, output, resume=True)

    def test_fresh_run_requires_a_working_database_or_selection(self):
        config = write_json(self.inputs / "build.json", self.cfg)
        with patch.dict(os.environ, {"NEON_DATABASE_URL": ""}):
            with self.assertRaisesRegex(ValueError, "supply --selection"):
                pipeline.Pipeline(config, self.root / "run")
        self.assertFalse((self.root / "run").exists())

    def test_compare_requires_two_streams_and_a_single_reference_source(self):
        reference = self.inputs / "rows.u32le"
        reference.write_bytes(b"fixture rows")
        config = self.inputs / "comparison.json"
        self.cfg["sources"]["reference_rows"] = {
            "path": reference.name, "sha256": sha256_file(reference),
        }
        config.write_text(json.dumps(self.cfg))
        for options, message in (
            ({}, "both reference stream pins are required"),
            ({"compare_release": "v9.0"}, "choose a published comparison release or local"),
        ):
            with self.subTest(options=options):
                with self.assertRaisesRegex(ValueError, message):
                    pipeline.Pipeline(config, self.root / "run", **options)

    def test_source_pin_requires_a_file(self):
        with self.assertRaisesRegex(ValueError, "not a file"):
            pin_file(self.inputs)

    def test_compare_can_load_pinned_streams_from_one_zip(self):
        packed = io.BytesIO()
        streams = {"rows": b"row offsets", "runs": b"cell runs"}
        with zipfile.ZipFile(packed, "w") as archive:
            for kind, data in streams.items():
                archive.writestr(kind + ".u32le", data)
        archive = self.cloud(packed.getvalue(), "sources/map.zip")
        for kind, data in streams.items():
            self.cfg["sources"]["reference_" + kind] = dict(
                archive=archive, member=kind + ".u32le", size_bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
            )
        with self.fake_r2({"sources/map.zip": packed.getvalue()}, []) as download:
            runner = self.make()
        rows, runs = (runner.sources["reference_" + kind] for kind in ("rows", "runs"))
        self.assertEqual(rows.parent, runs.parent)
        self.assertEqual((rows.read_bytes(), runs.read_bytes()), tuple(streams.values()))
        download.assert_called_once()

    def test_invalid_reference_pin_has_a_clear_error(self):
        self.cfg["sources"]["reference_rows"] = "rows.u32le"
        config = write_json(self.inputs / "build.json", self.cfg)
        with self.assertRaisesRegex(ValueError, "explicit path/SHA-256 pins"):
            pipeline.Pipeline(config, self.root / "run")

    def test_local_comparison_requires_both_named_streams_in_one_directory(self):
        second = self.inputs / "unrelated"
        second.mkdir()
        rows = self.inputs / "rows.u32le"
        runs = second / "runs.u32le"
        rows.write_bytes(b"first reference")
        runs.write_bytes(b"other reference")
        self.cfg["sources"].update(reference_rows=pin_file(rows), reference_runs=pin_file(runs))
        runner = self.make()
        with self.assertRaisesRegex(ValueError, "reference must use .* in one directory"):
            runner.compare(runner.out / "final", runner.out / "physical")

    def test_invalid_catalog_selector_fails_before_file_acquisition(self):
        for spec, message in (
            (dict(r2_source={"source_id": "absent"}), "missing selected sources"),
            (dict(r2_source="id"), "invalid raw catalog reference"),
            (dict(r2_source={"source_id": " "}), "invalid raw catalog reference"),
            (
                dict(r2_source={"source_id": "fixture"}, r2_bucket="test"),
                "invalid raw catalog reference",
            ),
        ):
            with self.subTest(spec=spec):
                self.select_coastline(spec)
                config = self.inputs / "catalog.json"
                config.write_text(json.dumps(self.cfg))
                with self.fake_r2({}, []) as download:
                    with self.assertRaisesRegex(ValueError, message):
                        pipeline.Pipeline(config, self.root / "run")
                download.assert_not_called()

    def test_saved_complete_selection_is_used_for_initialization_and_resume(self):
        selected = selection()
        config = write_json(self.inputs / "request.json", self.cfg)
        selection_path = write_json(self.inputs / "selection.json", selected)
        with patch.object(
            pipeline,
            "read_selection",
            side_effect=AssertionError("unexpected live database read"),
        ):
            runner = pipeline.Pipeline(config, self.root / "run", selection=selection_path)
            original = runner.identity["input_selection_sha256"]
            self.assertEqual(
                read_json(runner.out / "input-selection.json"), selected
            )
            runner.close()
            resumed = pipeline.Pipeline(config, runner.out, resume=True)
            self.assertEqual(resumed.identity["input_selection_sha256"], original)
            resumed.close()

    def test_resume_requires_the_same_frozen_selection(self):
        runner = self.make()
        runner.close()
        saved = runner.out / "input-selection.json"
        changed = read_json(saved)
        changed["geography"]["entities"][0]["name"] = "Different world"
        alternative = write_json(self.inputs / "alternate-selection.json", changed)
        with patch.object(pipeline, "read_selection", side_effect=AssertionError("unexpected live read")):
            with self.assertRaisesRegex(ValueError, "different saved geographic selection"):
                pipeline.Pipeline(runner.config_path, runner.out, resume=True, selection=alternative)
            saved.unlink()
            with self.assertRaises(FileNotFoundError) as error:
                pipeline.Pipeline(runner.config_path, runner.out, resume=True)
            self.assertEqual(Path(error.exception.filename), saved)

    def test_release_comparison_downloads_and_verifies_streams_and_config(self):
        raw_endpoint = "https://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.r2.cloudflarestorage.com"
        release_endpoint = "https://bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.r2.cloudflarestorage.com"
        raw_key = "sources/coast.geojson"
        self.select_coastline(self.cloud(b"{}", raw_key))
        self.cfg["physical_controls"] = {"source_staging": {"endpoint_url": raw_endpoint}}
        config = write_json(self.inputs / "request.json", self.cfg)
        digest = lambda data: hashlib.sha256(data).hexdigest()
        decoded = {name: name.encode() for name in ("rows", "runs")}
        stored = {
            f"review/{name}.u32le.gz": gzip.compress(data)
            for name, data in decoded.items()
        }
        catalog = [
            (name, "worldatlas", key, len(data), digest(data), digest(decoded[name]))
            for name, (key, data) in zip(decoded, stored.items())
        ]
        release_config = b'{"categories":[]}'
        config_asset = self.cloud(release_config, "review/config.json")
        stored[config_asset["r2_key"]] = release_config
        calls = []
        with (
            patch.object(
                pipeline, "read_release_assets", return_value=(catalog, config_asset)
            ) as release_lookup,
            patch.object(pipeline, "release_endpoint", return_value=release_endpoint),
            self.fake_r2(stored | {raw_key: b"{}"}, calls),
        ):
            runner = pipeline.Pipeline(config, self.root / "run", compare_release="v8.0")
            try:
                for name, data in decoded.items():
                    self.assertEqual(
                        runner.sources["reference_" + name].read_bytes(), data
                    )
                self.assertEqual(runner.sources["reference_config"].read_bytes(), release_config)
            finally:
                runner.close()
            release_lookup.side_effect = AssertionError("preview is no longer cataloged")
            for _, _, key, _, checksum, _ in catalog:
                (self.inputs / checksum / Path(key).name).unlink()
            resumed = pipeline.Pipeline(config, runner.out, resume=True)
            try:
                self.assertEqual(resumed.identity["compare_release"], "v8.0")
                self.assertEqual(resumed.sources, runner.sources)
            finally:
                resumed.close()
            with self.assertRaisesRegex(ValueError, "different --compare-release"):
                pipeline.Pipeline(config, runner.out, compare_release="v8.1", resume=True)
            runner.sources["reference_rows"].write_bytes(b"changed comparison")
            with self.assertRaisesRegex(ValueError, "source pin mismatch"):
                pipeline.Pipeline(config, runner.out, resume=True)
            identity_path = runner.out / "run-identity.json"
            identity = read_json(identity_path)
            identity.pop("comparison_inputs")
            identity_path.write_text(json.dumps(identity))
            with self.assertRaisesRegex(ValueError, "resume is missing saved comparison files"):
                pipeline.Pipeline(config, runner.out, resume=True)
            self.assertEqual(
                [call.args[0] for call in physical_build.make_r2_client.call_args_list],
                [raw_endpoint] + [release_endpoint] * len(stored),
            )
        self.assertEqual(calls, [raw_key, *stored])

    def test_release_comparison_reuses_decoded_stream_without_a_viewer_config(self):
        runner = self.make()
        decoded = b"map bytes"
        packed = gzip.compress(decoded)
        stored_hash = hashlib.sha256(packed).hexdigest()
        decoded_hash = hashlib.sha256(decoded).hexdigest()
        key = "releases/fixture/rows.u32le.gz"
        good = ("rows", "worldatlas", key, len(packed), stored_hash, decoded_hash)
        bad = (*good[:-1], "0" * 64)
        directory = self.inputs / ("release-" + hashlib.sha256(json_bytes([good])).hexdigest())
        directory.symlink_to(runner.out, target_is_directory=True)
        link = os.link

        def publish_together(source, destination):
            if destination.name == "rows.u32le":
                destination.write_bytes(decoded)
            return link(source, destination)

        with (
            patch.object(
                pipeline, "read_release_assets",
                side_effect=[([good], None), ([bad], None), ([good], None), ([good], None)],
            ),
            patch.object(pipeline, "release_endpoint", return_value="unused"),
            self.fake_r2({key: packed}, []) as download,
        ):
            with self.assertRaisesRegex(ValueError, "release reference overlaps output"):
                runner.release_reference("fixture")
            directory.unlink()
            with self.assertRaisesRegex(ValueError, "decoded reference stream hash mismatch"):
                runner.release_reference("fixture")
            with patch.object(os, "link", side_effect=publish_together):
                expected = runner.release_reference("fixture")
            self.assertEqual(list(expected), ["reference_rows"])
            self.assertEqual(expected["reference_rows"].read_bytes(), decoded)
            self.assertEqual(runner.release_reference("fixture"), expected)
            download.assert_called_once()

    def cloud(self, payload, key="sources/input.json"):
        return {
            "r2_bucket": "worldatlas",
            "r2_key": key,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }

    def select_coastline(self, dataset, *, files=None):
        self.cfg["sources"]["land_config"]["land"] = [
            {"dataset": dataset, "files": [dataset] if files is None else files}
        ]

    @contextmanager
    def fake_r2(self, payloads, calls):
        def download(endpoint, entry, destination):
            calls.append(entry["r2_key"])
            destination.write_bytes(payloads[entry["r2_key"]])

        def retrieve(*, Bucket, Key):
            calls.append(Key)
            data = payloads[Key]
            return {"Body": io.BytesIO(data), "ContentLength": len(data)}

        client = Mock()
        client.get_object.side_effect = retrieve
        with (
            patch.object(physical_build, "download_r2", side_effect=download),
            patch.object(physical_build, "make_r2_client", return_value=client),
        ):
            yield client.get_object

    def test_catalog_resolves_exact_versions_before_r2_acquisition(self):
        payload = b"{}"
        raw = self.cloud(payload)
        identity = {"source_id": "fixture", "version": "v1"}
        reference = {"r2_source": identity}
        self.frozen["raw_sources"] = [
            dict(source_id="fixture", version="v1", **raw),
            dict(source_id="fixture", version="v2", **self.cloud(b"other")),
        ]
        self.select_coastline(reference)
        self.cfg["sources"]["inland_water"]["files"] = [
            {"path": "raw/fixture", **reference}
        ]
        calls = []
        with self.fake_r2({raw["r2_key"]: payload}, calls):
            runner = self.make()
        self.assertEqual(calls, [raw["r2_key"]])
        land = read_json(runner.sources["land_config"])["land"][0]
        self.assertEqual(Path(land["dataset"]).read_bytes(), payload)
        manifest = read_json(runner.sources["raw_manifest"])
        size = raw.pop("size_bytes")
        self.assertEqual(
            manifest["files"],
            [
                {
                    "path": "raw/fixture",
                    "size": size,
                    "source_id": identity["source_id"],
                    **raw,
                }
            ],
        )

    def test_coastline_download_uses_each_builds_work_directory(self):
        payload = b"{}"
        self.select_coastline(self.cloud(payload))
        self.cfg["input_root"] = "/not-this-computer"
        config = write_json(self.inputs / "cloud-config.json", self.cfg)
        calls, results = [], []
        with self.fake_r2({"sources/input.json": payload}, calls):
            for name in ("computer-one", "computer-two"):
                root = self.root / name
                runner = pipeline.Pipeline(config, root / "run", work_dir=root)
                try:
                    self.assertEqual(runner.out, root / "run")
                    layer = read_json(runner.sources["land_config"])["land"][0]
                    source = Path(layer["dataset"])
                    self.assertIn(pin_file(source), runner.source_pins)
                    self.assertTrue(source.is_relative_to(root))
                    self.assertEqual(source.read_bytes(), payload)
                    self.assertEqual(len(runner.acquisition_intervals), 1)
                    results.append(sha256_file(source))
                finally:
                    runner.close()
        self.assertEqual(calls, ["sources/input.json", "sources/input.json"])
        self.assertEqual(results[0], results[1])

    def test_inline_physical_documents_share_verified_cloud_sources(self):
        payload = b"raw source bytes"
        source = self.cloud(payload, "sources/land.geojson")
        self.select_coastline(source)
        calls = []
        with self.fake_r2({"sources/land.geojson": payload}, calls):
            runner = self.make()
        land = read_json(runner.sources["land_config"])["land"][0]
        self.assertEqual(land["dataset"], land["files"][0]["path"])
        self.assertEqual(land["files"][0]["size_bytes"], len(payload))
        self.assertEqual(calls, ["sources/land.geojson"])

    def test_cloud_zip_members_are_individually_pinned_and_keep_sidecars_together(self):
        buffer = io.BytesIO()
        members = {"land/land.shp": b"geometry", "land/land.dbf": b"attributes"}
        with zipfile.ZipFile(buffer, "w") as packed:
            for name, value in members.items():
                packed.writestr(name, value)
        archive = self.cloud(buffer.getvalue(), "sources/land.zip")
        files = [
            {
                "archive": archive,
                "member": name,
                "sha256": hashlib.sha256(value).hexdigest(),
                "size_bytes": len(value),
            }
            for name, value in members.items()
        ]
        self.select_coastline(files[0], files=files)
        calls = []
        with self.fake_r2({"sources/land.zip": buffer.getvalue()}, calls):
            runner = self.make()
        land = read_json(runner.sources["land_config"])["land"][0]
        self.assertEqual(calls, ["sources/land.zip"])
        self.assertEqual(
            Path(land["files"][0]["path"]).parent, Path(land["files"][1]["path"]).parent
        )
        self.assertEqual(len({item["path"] for item in runner.source_pins}), 6)

    def test_invalid_zip_members_are_never_published_to_cache(self):
        runner = self.make()
        packed = io.BytesIO()
        payload = b"geometry"
        with zipfile.ZipFile(packed, "w") as archive:
            archive.writestr("data.shp", payload)
        archive = self.cloud(packed.getvalue(), "sources/archive.zip")
        output = self.inputs / archive["sha256"] / "data.shp"
        pin = dict(archive=archive, member="data.shp", size_bytes=len(payload),
                   sha256=hashlib.sha256(payload).hexdigest())
        with self.fake_r2({"sources/archive.zip": packed.getvalue()}, []) as download:
            for changes, reason in (
                ({"member": 1}, "unsafe ZIP member"),
                ({"member": "missing.shp"}, "must be one regular file"),
                ({"sha256": "0" * 64}, "size/SHA-256 mismatch"),
            ):
                with self.subTest(changes=changes):
                    with self.assertRaisesRegex(ValueError, reason):
                        runner.cloud_file(dict(pin, **changes))
                    self.assertFalse(output.exists())
                    self.assertEqual(list(output.parent.glob("*.partial")), [])
            self.assertEqual(runner.cloud_file(pin).read_bytes(), payload)
            self.assertEqual(download.call_count, 1)

    def test_zip_cache_publication_checks_a_concurrent_writers_bytes(self):
        runner = self.make()
        packed = io.BytesIO()
        payload = b"geometry"
        with zipfile.ZipFile(packed, "w") as archive:
            archive.writestr("one.shp", payload)
            archive.writestr("two.shp", payload)
        archive = self.cloud(packed.getvalue(), "sources/archive.zip")

        link = os.link
        for member, content in (("one.shp", payload), ("two.shp", b"corrupt!")):
            with self.subTest(member=member):
                output = self.inputs / archive["sha256"] / member

                def race(source, destination):
                    if destination == output:
                        output.write_bytes(content)
                    return link(source, destination)

                pin = dict(archive=archive, member=member, size_bytes=len(payload),
                           sha256=hashlib.sha256(payload).hexdigest())
                with (
                    self.fake_r2({"sources/archive.zip": packed.getvalue()}, []),
                    patch.object(os, "link", side_effect=race),
                ):
                    if content == payload:
                        self.assertEqual(runner.cloud_file(pin).read_bytes(), payload)
                    else:
                        with self.assertRaisesRegex(ValueError, "concurrent cloud input changed"):
                            runner.cloud_file(pin)
                self.assertEqual(output.read_bytes(), content)
                self.assertEqual(list(output.parent.glob("*.partial")), [])

    def test_raw_manifest_keeps_shards_deferred_to_existing_physical_stage(self):
        raw = {
            "file_count": 1,
            "files": [
                {
                    "path": "raw/part.parquet",
                    "sha256": "a" * 64,
                    "r2_bucket": "worldatlas",
                    "r2_key": "raw/part.parquet",
                    "size": 123,
                }
            ],
        }
        self.cfg["sources"]["inland_water"].update(raw)
        with self.fake_r2({}, []) as download:
            runner = self.make()
        download.assert_not_called()
        self.assertEqual(read_json(runner.sources["raw_manifest"]), raw)

    def test_changed_cloud_cache_or_wrong_download_fails_before_run_creation(self):
        payload = b"{}"
        self.select_coastline(self.cloud(payload))
        calls = []
        with self.fake_r2({"sources/input.json": b"wrong"}, calls):
            with self.assertRaisesRegex(
                ValueError, "cloud input size/SHA-256 mismatch"
            ):
                self.make()
        self.assertFalse((self.root / "run").exists())
        self.assertEqual(len(list((self.root / "inputs").rglob("download-*"))), 0)

    def test_invalid_cloud_pin_or_escaped_cache_path_is_rejected(self):
        runner = self.make()
        spec = self.cloud(b"source", "raw/list.json")
        for changes, message in (
            ({"size_bytes": None}, "explicit SHA-256 and byte size"),
            ({"r2_key": "raw/../list.json"}, "invalid pinned R2 location"),
        ):
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ValueError, message):
                    runner.cloud_file(dict(spec, **changes))
        outside = self.root / "run"
        cached = self.inputs / spec["sha256"]
        cached.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "cloud input overlaps output"):
            runner.cloud_file(spec)

    def test_cache_reuses_same_bytes_without_duplicate_file_pins(self):
        runner = self.make()
        payload = b"archive byte sequence"
        first = self.cloud(payload, "folder1/shared.bin")
        second = self.cloud(payload, "folder2/shared.bin")
        count = len(runner.source_pins)
        with self.fake_r2({first["r2_key"]: payload}, []) as download:
            self.assertEqual(runner.cloud_file(first), runner.cloud_file(second))
            download.assert_called_once()
        self.assertEqual(len(runner.source_pins), count + 1)
        saved_count = len(runner.source_pins)
        first = runner.save_source_document({"key": "value"})
        self.assertEqual(runner.save_source_document({"key": "value"}), first)
        self.assertEqual(len(runner.source_pins), saved_count + 1)

    def test_generated_input_respects_the_run_directory_boundary(self):
        runner = self.make()
        document = {"unexpected": "configuration"}
        hashed_name = hashlib.sha256(json_bytes(document)).hexdigest() + ".json"
        link = self.inputs / hashed_name
        link.symlink_to(runner.out / "forbidden.json")
        with self.assertRaisesRegex(ValueError, "generated input overlaps output"):
            runner.save_source_document(document)
        self.assertFalse((runner.out / "forbidden.json").exists())

    def test_resume_rejects_changed_build_configuration(self):
        first = self.make()
        config = read_json(first.config_path)
        first.close()
        config["selection_notes"] = "changed after starting"
        first.config_path.write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, "resume request, input selection or output identity changed"):
            pipeline.Pipeline(first.config_path, first.out, resume=True)

    def test_physical_timing_reads_only_complete_records(self):
        runner = self.make()
        directory = runner.out / "physical"
        directory.mkdir()
        journal = directory / "processing-events.jsonl"
        event = {"event": "attempt_start", "attempt": "fixture"}
        start = json.dumps(event).encode() + b"\n"
        for tail in (b'{"event":', b'invalid-json\n'):
            with self.subTest(tail=tail):
                journal.write_bytes(start + tail)
                self.assertEqual(runner.physical_attempts(), [event])
        end = {
            "event": "attempt_end", "attempt": "fixture",
            "processing_elapsed_seconds": 8, "source_download_elapsed_seconds": 3,
        }
        journal.write_bytes(start + json.dumps(end).encode() + b"\n")
        with self.assertRaisesRegex(ValueError, "invalid physical invocation timing"):
            runner.record_physical_invocation(
                {"monotonic_seconds": 0, "end_monotonic_seconds": 10}, [],
            )
        journal.write_bytes(start)
        runner.record_physical_invocation(
            {"monotonic_seconds": 0, "end_monotonic_seconds": 10}, [],
        )
        self.assertFalse(
            any(event["event"] == "physical-invocation-processing" for event in runner.timing.records)
        )

    def test_failure_to_open_the_physical_timer_does_not_create_an_invocation(self):
        runner = self.make()

        @contextmanager
        def unavailable(*_, **__):
            raise OSError("cannot write the timing journal")
            yield

        with (
            patch.object(runner.timing, "measure", new=unavailable),
            patch.object(runner, "record_physical_invocation") as report,
        ):
            with self.assertRaisesRegex(OSError, "cannot write the timing journal"):
                runner.physical()
        report.assert_not_called()

    def test_import_cache_is_reused_without_network_or_download_time(self):
        payload = b"{}"
        source = self.cloud(payload)
        cached = self.inputs / source["sha256"] / "input.json"
        cached.parent.mkdir()
        cached.write_bytes(payload)
        self.select_coastline(source)
        with self.fake_r2({}, []) as download:
            runner = self.make()
        download.assert_not_called()
        land = read_json(runner.sources["land_config"])["land"][0]
        self.assertEqual(Path(land["dataset"]), cached)
        self.assertEqual(runner.acquisition_intervals, [])

    def test_relative_input_root_is_relative_to_the_configuration(self):
        self.cfg["input_root"] = ".."
        runner = self.make()
        self.assertEqual(runner.root, self.root)

    def test_cached_cloud_corruption_and_zip_path_escapes_fail_closed(self):
        payload = b"{}"
        spec = self.cloud(payload)
        cached = self.root / "inputs" / spec["sha256"] / "input.json"
        cached.parent.mkdir(parents=True)
        cached.write_bytes(b"xx")
        self.select_coastline(spec)
        with self.fake_r2({}, []) as download:
            with self.assertRaisesRegex(
                ValueError, "cached cloud input size/SHA-256 mismatch"
            ):
                self.make()
        download.assert_not_called()
        cached.write_bytes(payload)
        self.select_coastline(
            {
                "archive": spec,
                "member": "../outside",
                "sha256": "a" * 64,
                "size_bytes": 1,
            }
        )
        config = write_json(self.inputs / "request2.json", self.cfg)
        with self.assertRaisesRegex(ValueError, "unsafe ZIP member"):
            pipeline.Pipeline(config, self.root / "run")

    def test_failure_report_is_not_a_completed_stage(self):
        runner = self.make()

        def interrupted():
            with runner.timing.measure("division", "prepare"):
                pass
            raise RuntimeError("fixture failure")

        runner.selection = {"domains": {}}
        with patch.object(runner, "physical", side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError, "fixture failure"):
                runner.run()
        self.assertFalse((runner.out / "report.json").exists())
        failure = read_json(runner.out / "failure.json")
        self.assertFalse(failure["stages"]["division"]["complete"])
        self.assertFalse(failure["stages"]["package"]["complete"])

    def test_corrupt_physical_report_cannot_hide_the_original_failure(self):
        runner = self.make()
        report = runner.out / "physical" / "report.json"
        report.parent.mkdir()
        report.write_text('{"malformed":')
        with patch.object(runner, "physical", side_effect=RuntimeError("fixture stage failed")):
            with self.assertRaisesRegex(RuntimeError, "fixture stage failed"):
                runner.run()
        self.assertFalse((runner.out / "report.json").exists())
        self.assertEqual(read_json(runner.out / "failure.json")["status"], "incomplete")

    def test_actual_raw_sources_to_fresh_components_in_process(self):
        grid = {"width": 8, "height": 4, "west": -180, "north": 90, "step": 45}
        raw = self.inputs / "raw"
        raw.mkdir()
        land_file = write_json(
            raw / "land.geojson",
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [[-180, 90], [-45, 90], [-45, 0], [-180, 0], [-180, 90]]
                            ],
                        },
                    }
                ],
            },
        )
        land = {
            "schema": "land-raster-candidate-v1",
            "selection_notes": "synthetic",
            "strip_rows": 2,
            "minimum_free_bytes": 0,
            "land": [
                {
                    "dataset": str(land_file),
                    "where": None,
                    "files": [pin_file(land_file)],
                }
            ],
        }
        water = {
            "schema": "water-shard-candidate-v2",
            "tile_size": 4,
            "minimum_free_bytes": 0,
            "selection_notes": "synthetic",
            "policy": {"method": "overture-inland-subtype-v1"},
        }
        geometry = bytes(
            ogr.CreateGeometryFromWkt(
                "POLYGON ((-180 90,-135 90,-135 45,-180 45,-180 90))"
            ).ExportToWkb()
        )
        table = pa.Table.from_pylist(
            [
                {
                    "id": "lake",
                    "subtype": "lake",
                    "class": "lake",
                    "sources": [{"property": "", "dataset": "OpenStreetMap"}],
                    "geometry": geometry,
                }
            ]
        )
        table = table.replace_schema_metadata(
            {
                b"geo": json.dumps(
                    {
                        "primary_column": "geometry",
                        "columns": {"geometry": {"encoding": "WKB"}},
                    }
                ).encode()
            }
        )
        shard = raw / "water.parquet"
        pq.write_table(table, shard)
        self.cfg["grid"] = grid
        self.cfg["sources"] = dict(
            land_config=land,
            inland_water=dict(
                rasterization=water,
                file_count=1,
                files=[{"path": "raw/water.parquet", "sha256": sha256_file(shard)}],
            ),
        )
        self.cfg["physical_controls"] = {
            "minimum_free_bytes": 0,
            "max_parallel_shards": 1,
        }
        runner = self.make()
        physical = runner.physical()
        config_path = runner.out / "physical-build-config.json"
        original_config = config_path.read_bytes()
        self.assertEqual(
            read_json(config_path)["land_config"],
            pin_file(runner.sources["land_config"]),
        )
        config_path.write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "saved physical build configuration changed"):
            runner.physical()
        config_path.write_bytes(original_config)
        reused = pipeline.Pipeline(
            runner.config_path, self.root / "reused", reuse_from=runner.out
        )
        self.addCleanup(reused.close)
        producer_report = (physical / "report.json").read_bytes()
        with patch.object(
            physical_build,
            "run",
            side_effect=AssertionError("physical outputs must be reused"),
        ):
            self.assertEqual(reused.physical(), physical)
        self.assertEqual(
            reused.identity["physical_reuse"]["source_run"], str(runner.out)
        )
        self.assertEqual(
            pipeline.physical_reference(reused.out, runner.sources)["source_run"],
            str(runner.out),
        )
        self.assertEqual((physical / "report.json").read_bytes(), producer_report)
        notes = dict(land, grid=grid)
        notes["selection_notes"] = "Reworded description of the same selected sources"
        descriptive = write_json(self.inputs / "same-land-new-notes.json", notes)
        self.assertEqual(
            pipeline.physical_reference(
                runner.out, {**runner.sources, "land_config": descriptive}
            )["status"],
            "reused",
        )
        changed = write_json(
            self.inputs / "different-land.json", {"grid": grid, "different": True}
        )
        with self.assertRaisesRegex(ValueError, "physical input differs"):
            pipeline.physical_reference(
                runner.out, {**runner.sources, "land_config": changed}
            )
        shorter_grid = {**grid, "height": grid["height"] - 1}
        shorter_sources = dict(runner.sources)
        for key in ("land_config", "water_config"):
            shorter_sources[key] = write_json(
                self.inputs / f"shorter-{key}.json",
                {**read_json(runner.sources[key]), "grid": shorter_grid},
            )
        with self.assertRaisesRegex(ValueError, "physical reuse requires the same grid"):
            pipeline.physical_reference(runner.out, shorter_sources)
        mask = physical / "physical-dry.tif"
        original = mask.read_bytes()
        mask.write_bytes(original + b"changed")
        with self.assertRaisesRegex(ValueError, "checkpoint/input hash mismatch"):
            reused.physical()
        mask.write_bytes(original)
        components = runner.out / "components"
        result = build_components(Grid(**grid), physical, components)
        self.assertEqual(result["land_cells"], 5)
        self.assertEqual(
            result["output_sha256"]["runs.u32le"],
            sha256_file(components / "runs.u32le"),
        )
        np.testing.assert_array_equal(
            np.fromfile(physical / "rows.u32le", dtype="<u4"), [0, 3, 5, 6, 7]
        )
        self.assertEqual(
            read_json(runner.out / "physical/report.json")[
                "source_download_elapsed_seconds"
            ],
            0,
        )

    def test_single_cloud_configuration_matches_local_raw_and_component_streams_in_another_root(
        self,
    ):
        self.test_actual_raw_sources_to_fresh_components_in_process()
        payloads = {
            "sources/land.geojson": (self.inputs / "raw/land.geojson").read_bytes(),
            "sources/water.parquet": (self.inputs / "raw/water.parquet").read_bytes(),
        }
        land_source = self.cloud(
            payloads["sources/land.geojson"], "sources/land.geojson"
        )
        land = dict(self.cfg["sources"]["land_config"])
        land["land"] = [{"dataset": land_source, "where": None, "files": [land_source]}]
        water_source = self.cloud(
            payloads["sources/water.parquet"], "sources/water.parquet"
        )
        manifest = {
            "file_count": 1,
            "files": [
                {
                    "path": "raw/water.parquet",
                    "sha256": water_source["sha256"],
                    "size": water_source["size_bytes"],
                    "r2_bucket": water_source["r2_bucket"],
                    "r2_key": water_source["r2_key"],
                }
            ],
        }
        cfg = {
            **self.cfg,
            "input_root": "./unused-on-another-computer",
            "sources": dict(
                land_config=land,
                inland_water=dict(
                    rasterization=self.cfg["sources"]["inland_water"]["rasterization"],
                    **manifest,
                ),
            ),
            "physical_controls": {
                **self.cfg["physical_controls"],
                "source_staging": {
                    "mode": "r2-s3",
                    "endpoint_url": "https://" + "0" * 32 + ".r2.cloudflarestorage.com",
                },
            },
        }
        config = write_json(self.inputs / "single-cloud-config.json", cfg)
        calls = []
        with self.fake_r2(payloads, calls):
            other = self.root / "another-computer"
            runner = pipeline.Pipeline(config, other / "run", work_dir=other)
            self.addCleanup(runner.close)
            physical = runner.physical()
        components = runner.out / "components"
        build_components(Grid(**cfg["grid"]), physical, components)
        for local, cloud in [
            (self.root / "run/physical/physical", physical),
            (self.root / "run/components", components),
        ]:
            for name in ("rows.u32le", "runs.u32le"):
                self.assertEqual(sha256_file(local / name), sha256_file(cloud / name))
        self.assertEqual(calls, ["sources/land.geojson", "sources/water.parquet"])


if __name__ == "__main__":
    unittest.main()
