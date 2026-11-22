"""Runner contracts, measured parallelism, and actual raw-to-component chaining."""

import json
from contextlib import redirect_stderr
import os
import signal
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
from worldatlas.shared import r2
from worldatlas.shared.r2 import R2Client
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
    def test_build_requires_an_explicit_workspace_and_output(self):
        for options, missing in (
            (["--work-dir", "workspace"], "output"),
            (["--work-dir", "workspace", "--resume"], "output"),
            (["run"], "--work-dir"),
        ):
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
                self.assertIn(f"the following arguments are required: {missing}", error.getvalue())
                builder.assert_not_called()

    def test_recompute_requires_a_prior_run(self):
        args = [
            "worldatlas-build", "config.json", "run",
            "--work-dir", "workspace", "--recompute-division",
        ]
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
                    patch(
                        "sys.argv",
                        ["worldatlas-build", "config.json", "run", "--work-dir", "workspace"],
                    ),
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
            "sources": {
                "land_config": {"land": []},
                "inland_water": {"files": []},
            },
            "grid": dict(width=36, height=18, step=10),
        }

    def make(self):
        config = write_json(self.inputs / "request.json", self.cfg)
        runner = pipeline.Pipeline(config, self.root / "run", work_dir=self.root)
        self.addCleanup(runner.close)
        return runner

    def test_physical_settings_require_inline_values(self):
        path = write_json(self.inputs / "settings.json", {})
        for name in ("land_config", "inland_water"):
            with self.subTest(name=name):
                sources = dict(self.cfg["sources"], **{name: pin_file(path)})
                config = write_json(
                    self.inputs / f"{name}-request.json",
                    dict(self.cfg, sources=sources),
                )
                with self.assertRaisesRegex(ValueError, rf"sources\.{name}\."):
                    pipeline.Pipeline(config, self.root / "run", work_dir=self.root)

    def test_rejects_invalid_run_options_before_creating_output(self):
        config = self.inputs / "build.json"
        output = self.root / "run"
        existing = self.root / "existing"
        existing.mkdir()
        cases = [
            (dict(self.cfg, schema="unknown"), {}, "literal_error"),
            (dict(self.cfg, sources=[]), {}, "dict_type"),
            (dict(self.cfg, sources={}), {}, r"sources\.land_config"),
            (
                dict(self.cfg, sources=dict(
                    self.cfg["sources"], land_config={"land": [], "strip_rows": "512"}
                )),
                {},
                r"sources\.land_config\.strip_rows",
            ),
            (
                dict(self.cfg, sources=dict(self.cfg["sources"], inland_watre={})),
                {},
                r"sources\.inland_watre",
            ),
            (self.cfg, {"output": self.root / "missing" / "run"}, "parent directory must exist"),
            (self.cfg, {"output": existing}, "fresh build requires a new output"),
            (self.cfg, {"resume": True}, "resume requires an existing output directory"),
            (self.cfg, {"output": self.root.parent / "elsewhere"}, "output must be inside --work-dir"),
            (self.cfg, {"output": self.inputs / "run"}, "input cache must use separate directories"),
            (self.cfg, {"output": self.root}, "input cache must use separate directories"),
            (self.cfg, {"recompute_division": True}, "requires --reuse-from"),
        ]
        for definition, options, error in cases:
            with self.subTest(error=error):
                config.write_text(json.dumps(definition))
                with self.assertRaisesRegex(ValueError, error):
                    pipeline.Pipeline(config, work_dir=self.root, **({"output": output} | options))
                self.assertFalse(output.exists())

        config.write_text(json.dumps(self.cfg))
        output.mkdir()
        with self.assertRaisesRegex(ValueError, "no supported checkpoint identity"):
            pipeline.Pipeline(config, output, work_dir=self.root, resume=True)

    def test_fresh_run_requires_a_working_database_or_selection(self):
        config = write_json(self.inputs / "build.json", self.cfg)
        with patch.dict(os.environ, {"NEON_DATABASE_URL": ""}):
            with self.assertRaisesRegex(ValueError, "supply --selection"):
                pipeline.Pipeline(config, self.root / "run", work_dir=self.root)
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
                    pipeline.Pipeline(
                        config,
                        self.root / "run",
                        work_dir=self.root,
                        **options,
                    )

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
        rows, runs = (runner.comparison_files["reference_" + kind] for kind in ("rows", "runs"))
        self.assertEqual(rows.parent, runs.parent)
        self.assertEqual((rows.read_bytes(), runs.read_bytes()), tuple(streams.values()))
        download.assert_called_once()

    def test_invalid_reference_pin_has_a_clear_error(self):
        self.cfg["sources"]["reference_rows"] = "rows.u32le"
        config = write_json(self.inputs / "build.json", self.cfg)
        with self.assertRaisesRegex(ValueError, r"sources\.reference_rows"):
            pipeline.Pipeline(config, self.root / "run", work_dir=self.root)

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
            (dict(r2_source="absent"), "missing selected sources"),
            (dict(r2_source=" "), "r2_source must be a nonblank Neon source ID"),
            (dict(r2_source={"source_id": "fixture"}), "r2_source must be a nonblank Neon source ID"),
            (
                dict(r2_source="fixture", r2_bucket="test"),
                "invalid raw catalog reference",
            ),
        ):
            with self.subTest(spec=spec):
                self.select_coastline("fixture", [spec])
                config = self.inputs / "catalog.json"
                config.write_text(json.dumps(self.cfg))
                with self.fake_r2({}, []) as download:
                    with self.assertRaisesRegex(ValueError, message):
                        pipeline.Pipeline(config, self.root / "run", work_dir=self.root)
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
            runner = pipeline.Pipeline(
                config,
                self.root / "run",
                work_dir=self.root,
                selection=selection_path,
            )
            original = runner.identity["input_selection_sha256"]
            self.assertEqual(
                read_json(runner.out / "input-selection.json"), selected
            )
            runner.close()
            resumed = pipeline.Pipeline(
                config,
                runner.out,
                work_dir=self.root,
                resume=True,
            )
            self.assertEqual(resumed.identity["input_selection_sha256"], original)
            resumed.close()

    def test_resume_uses_only_the_run_selection(self):
        runner = self.make()
        runner.close()
        saved = runner.out / "input-selection.json"
        with patch.object(pipeline, "read_selection", side_effect=AssertionError("unexpected live read")):
            with self.assertRaisesRegex(ValueError, "Omit --selection"):
                pipeline.Pipeline(
                    runner.config_path,
                    runner.out,
                    work_dir=self.root,
                    resume=True,
                    selection=saved,
                )
            saved.unlink()
            with self.assertRaises(FileNotFoundError) as error:
                pipeline.Pipeline(
                    runner.config_path,
                    runner.out,
                    work_dir=self.root,
                    resume=True,
                )
            self.assertEqual(Path(error.exception.filename), saved)

    def test_release_comparison_downloads_and_verifies_streams_and_config(self):
        raw_endpoint = "https://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.r2.cloudflarestorage.com"
        release_endpoint = r2.DEFAULT_R2_ENDPOINT
        raw_key = "sources/coast.geojson"
        self.select_coastline(raw_key, [self.cloud(b"{}", raw_key)])
        self.cfg["r2_endpoint"] = raw_endpoint
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
            self.fake_r2(stored | {raw_key: b"{}"}, calls),
        ):
            runner = pipeline.Pipeline(
                config,
                self.root / "run",
                work_dir=self.root,
                compare_release="v8.0",
            )
            try:
                for name, data in decoded.items():
                    self.assertEqual(
                        runner.comparison_files["reference_" + name].read_bytes(), data
                    )
                self.assertEqual(runner.comparison_files["reference_config"].read_bytes(), release_config)
            finally:
                runner.close()
            release_lookup.side_effect = AssertionError("preview is no longer cataloged")
            for _, _, key, _, checksum, _ in catalog:
                (self.inputs / checksum / Path(key).name).unlink()
            resumed = pipeline.Pipeline(
                config,
                runner.out,
                work_dir=self.root,
                resume=True,
            )
            try:
                self.assertEqual(resumed.identity["compare_release"], "v8.0")
                self.assertEqual(resumed.comparison_files, runner.comparison_files)
            finally:
                resumed.close()
            with self.assertRaisesRegex(ValueError, "--resume uses saved options"):
                pipeline.Pipeline(
                    config,
                    runner.out,
                    work_dir=self.root,
                    compare_release="v8.0",
                    resume=True,
                )
            runner.comparison_files["reference_rows"].write_bytes(b"changed comparison")
            with self.assertRaisesRegex(ValueError, "source pin mismatch"):
                pipeline.Pipeline(config, runner.out, work_dir=self.root, resume=True)
            identity_path = runner.out / "run-identity.json"
            identity = read_json(identity_path)
            identity.pop("comparison_inputs")
            identity_path.write_text(json.dumps(identity))
            with self.assertRaisesRegex(ValueError, "resume is missing saved comparison files"):
                pipeline.Pipeline(config, runner.out, work_dir=self.root, resume=True)
            self.assertEqual(
                [call.args[0] for call in r2.make_r2_client.call_args_list],
                [release_endpoint] * len(stored),
            )
        self.assertEqual(calls, list(stored))

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

    def select_coastline(self, dataset, files):
        self.cfg["sources"]["land_config"]["land"] = [
            {"dataset": dataset, "files": files}
        ]

    @contextmanager
    def fake_r2(self, payloads, calls):
        def retrieve(*, Bucket, Key):
            calls.append(Key)
            data = payloads[Key]
            return {"Body": io.BytesIO(data), "ContentLength": len(data)}

        client = Mock()
        client.get_object.side_effect = retrieve
        with patch.object(r2, "make_r2_client", return_value=R2Client(client)):
            yield client.get_object

    def test_catalog_resolves_source_ids_before_r2_acquisition(self):
        payload = b"{}"
        raw = self.cloud(payload)
        source_id = "fixture"
        reference = {"r2_source": source_id}
        self.frozen["raw_sources"] = [
            dict(source_id="fixture", **raw),
            dict(source_id="unrelated", **self.cloud(b"other")),
        ]
        self.select_coastline(source_id, [reference])
        self.cfg["sources"]["inland_water"]["files"] = [
            {"path": "raw/fixture", **reference}
        ]
        with (
            self.fake_r2({}, []) as download,
            patch.object(
                pipeline, "catalog_references", wraps=pipeline.catalog_references
            ) as scan,
        ):
            runner = self.make()
        scan.assert_called_once()
        self.assertEqual(
            pipeline.read_selection.call_args.kwargs["raw_sources"], {source_id}
        )
        self.assertEqual(runner.cfg["sources"], self.cfg["sources"])
        download.assert_not_called()
        resolved = {"source_id": source_id, **raw}
        land = runner.physical_config["land_config"]["land"][0]
        self.assertEqual(land["dataset"], source_id)
        self.assertEqual(land["files"], [resolved])
        planned, requests = physical_build.plan_land_inputs(
            runner.physical_config["land_config"], runner.r2_inputs
        )
        self.assertEqual(requests, [resolved])
        self.assertEqual(planned["land"][0]["dataset"], str(runner.r2_inputs.path(resolved)))
        self.assertEqual(
            runner.physical_config["inland_water"]["files"],
            [{"path": "raw/fixture", **resolved}],
        )

    def test_coastline_download_uses_each_builds_work_directory(self):
        payload = b"{}"
        source = self.cloud(payload)
        self.select_coastline(source["r2_key"], [source])
        config = write_json(self.inputs / "cloud-config.json", self.cfg)
        calls, results = [], []
        with self.fake_r2({"sources/input.json": payload}, calls):
            for name in ("computer-one", "computer-two"):
                root = self.root / name
                runner = pipeline.Pipeline(config, root / "run", work_dir=root)
                try:
                    self.assertEqual(runner.out, root / "run")
                    planned, (pin,) = physical_build.plan_land_inputs(
                        runner.physical_config["land_config"], runner.r2_inputs
                    )
                    source = runner.r2_inputs.acquire(pin)
                    self.assertEqual(planned["land"][0]["dataset"], str(source))
                    self.assertIn(pin_file(source), runner.source_pins)
                    self.assertTrue(source.is_relative_to(root))
                    self.assertEqual(source.read_bytes(), payload)
                    self.assertEqual(len(runner.r2_inputs.download_intervals), 1)
                    results.append(sha256_file(source))
                finally:
                    runner.close()
        self.assertEqual(calls, ["sources/input.json", "sources/input.json"])
        self.assertEqual(results[0], results[1])

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
        self.select_coastline("land/land.shp", list(reversed(files)))
        calls = []
        with self.fake_r2({"sources/land.zip": buffer.getvalue()}, calls):
            runner = self.make()
            planned, requests = physical_build.plan_land_inputs(
                runner.physical_config["land_config"], runner.r2_inputs
            )
            self.assertEqual(calls, [])
            for request in requests:
                runner.r2_inputs.acquire(request)
        land = planned["land"][0]
        self.assertEqual(calls, ["sources/land.zip"])
        self.assertEqual(len(requests), 2)
        self.assertEqual(land["dataset"], land["files"][1]["path"])
        self.assertEqual(Path(land["dataset"]).read_bytes(), b"geometry")
        self.assertEqual(
            Path(land["files"][0]["path"]).parent, Path(land["files"][1]["path"]).parent
        )
        self.assertEqual(len({item["path"] for item in runner.source_pins}), 3)

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
                ({"sha256": "0" * 64}, "size or hash mismatch"),
            ):
                with self.subTest(changes=changes):
                    with self.assertRaisesRegex(ValueError, reason):
                        runner.r2_inputs.acquire(dict(pin, **changes))
                    self.assertFalse(output.exists())
                    self.assertEqual(list(output.parent.glob("*.partial")), [])
            self.assertEqual(runner.r2_inputs.acquire(pin).read_bytes(), payload)
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
                        self.assertEqual(runner.r2_inputs.acquire(pin).read_bytes(), payload)
                    else:
                        with self.assertRaisesRegex(ValueError, "size or hash mismatch"):
                            runner.r2_inputs.acquire(pin)
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
                    "size_bytes": 123,
                }
            ],
        }
        self.cfg["sources"]["inland_water"].update(raw)
        with self.fake_r2({}, []) as download:
            runner = self.make()
        download.assert_not_called()
        self.assertEqual(runner.physical_config["inland_water"], raw)

    def test_wrong_download_is_never_published(self):
        runner = self.make()
        spec = self.cloud(b"{}")
        with self.fake_r2({"sources/input.json": b"wrong"}, []):
            with self.assertRaisesRegex(
                ValueError, "size or hash mismatch"
            ):
                runner.r2_inputs.acquire(spec)
        self.assertFalse(runner.r2_inputs.path(spec).exists())
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
                    runner.r2_inputs.acquire(dict(spec, **changes))
        outside = self.root / "run"
        cached = self.inputs / spec["sha256"]
        cached.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "cloud input escapes the cache directory"):
            runner.r2_inputs.acquire(spec)

    def test_cache_reuses_same_bytes_without_duplicate_file_pins(self):
        runner = self.make()
        payload = b"archive byte sequence"
        first = self.cloud(payload, "folder1/shared.bin")
        second = self.cloud(payload, "folder2/shared.bin")
        count = len(runner.source_pins)
        with self.fake_r2({first["r2_key"]: payload}, []) as download:
            self.assertEqual(runner.r2_inputs.acquire(first), runner.r2_inputs.acquire(second))
            download.assert_called_once()
        self.assertEqual(len(runner.source_pins), count + 1)

    def test_resume_rejects_changed_build_configuration(self):
        first = self.make()
        config = read_json(first.config_path)
        first.close()
        config["selection_notes"] = "changed after starting"
        first.config_path.write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, "resume request, input selection or output identity changed"):
            pipeline.Pipeline(
                first.config_path,
                first.out,
                work_dir=self.root,
                resume=True,
            )

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
        runner = self.make()
        with self.fake_r2({}, []) as download:
            self.assertEqual(runner.r2_inputs.acquire(source), cached)
        download.assert_not_called()
        self.assertEqual(runner.r2_inputs.download_intervals, [])

    def test_relative_work_directory_is_relative_to_the_current_directory(self):
        config = write_json(self.inputs / "build.json", self.cfg)
        runner = pipeline.Pipeline(
            config, self.root / "run", work_dir=os.path.relpath(self.root)
        )
        self.addCleanup(runner.close)
        self.assertEqual(runner.root, self.root)

    def test_cached_cloud_corruption_and_zip_path_escapes_fail_closed(self):
        payload = b"{}"
        spec = self.cloud(payload)
        cached = self.root / "inputs" / spec["sha256"] / "input.json"
        cached.parent.mkdir(parents=True)
        runner = self.make()
        with self.fake_r2({}, []) as download:
            cached.mkdir()
            with self.assertRaisesRegex(
                ValueError, "size or hash mismatch"
            ):
                runner.r2_inputs.acquire(spec)
            cached.rmdir()
            cached.write_bytes(b"xx")
            with self.assertRaisesRegex(
                ValueError, "size or hash mismatch"
            ):
                runner.r2_inputs.acquire(spec)
        download.assert_not_called()
        cached.write_bytes(payload)
        with self.assertRaisesRegex(ValueError, "unsafe ZIP member"):
            runner.r2_inputs.acquire(
                dict(archive=spec, member="../outside", sha256="a" * 64, size_bytes=1)
            )

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
                **water,
                file_count=1,
                files=[
                    {
                        "path": "raw/water.parquet",
                        "sha256": sha256_file(shard),
                        "size_bytes": shard.stat().st_size,
                    }
                ],
            ),
        )
        self.cfg["physical_controls"] = {
            "minimum_free_bytes": 0,
            "max_parallel_shards": 1,
        }
        runner = self.make()
        with (
            patch.object(physical_build.land, "run", wraps=physical_build.land.run) as land_run,
            patch.object(physical_build.water, "run", wraps=physical_build.water.run) as water_run,
        ):
            physical = runner.physical()
        self.assertIs(land_run.call_args.args[-1], runner.grid)
        self.assertIs(water_run.call_args.args[-1], runner.grid)
        config_path = runner.out / "physical-build-config.json"
        original_config = config_path.read_bytes()
        self.assertEqual(
            read_json(config_path)["land_config"],
            runner.physical_config["land_config"],
        )
        config_path.write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "saved physical build configuration changed"):
            runner.physical()
        config_path.write_bytes(original_config)
        reused = pipeline.Pipeline(
            runner.config_path, self.root / "reused", work_dir=self.root, reuse_from=runner.out
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
            pipeline.physical_reference(reused.out, runner.physical_config)["source_run"],
            str(runner.out),
        )
        self.assertEqual((physical / "report.json").read_bytes(), producer_report)
        notes = dict(land)
        notes["selection_notes"] = "Reworded description of the same selected sources"
        self.assertEqual(
            pipeline.physical_reference(
                runner.out, {**runner.physical_config, "land_config": notes}
            )["status"],
            "reused",
        )
        changed = dict(notes, land=[], different=True)
        with self.assertRaisesRegex(ValueError, "physical input differs"):
            pipeline.physical_reference(
                runner.out, {**runner.physical_config, "land_config": changed}
            )
        shorter_sources = dict(
            runner.physical_config, grid={**grid, "height": grid["height"] - 1}
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
        # An earlier completed run saved separate settings and source list pins.
        old_manifest = {
            key: runner.physical_config["inland_water"][key]
            for key in ("file_count", "files")
        }
        old_manifest = json.loads(json_bytes(old_manifest))
        entry = old_manifest["files"][0]
        identity_path = runner.out / "physical/pipeline-identity.json"
        identity = read_json(identity_path)
        del identity["inland_water"]
        for name, settings in (
            ("land_config", dict(land, grid=grid)),
            ("water_config", dict(water, grid=grid)),
        ):
            old_path = write_json(self.inputs / f"legacy-{name}.json", settings)
            identity[name] = pin_file(old_path)
        report_path = runner.out / "physical/report.json"
        report = read_json(report_path)
        size = entry.pop("size_bytes")
        for size_key in ("size_bytes", "size"):
            with self.subTest(old_water_size_key=size_key):
                old_manifest["files"] = [{**entry, size_key: size}]
                old_path = write_json(
                    self.inputs / f"legacy-manifest-{size_key}.json", old_manifest
                )
                identity["source_manifest"] = pin_file(old_path)
                identity_path.write_bytes(json_bytes(identity))
                report["pipeline_identity_sha256"] = sha256_file(identity_path)
                report_path.write_bytes(json_bytes(report))
                reuse = pipeline.physical_reference(runner.out, runner.physical_config)
                self.assertEqual(reuse["status"], "reused")
                self.assertEqual(
                    reuse["pins"], [pin_file(pin["path"]) for pin in reuse["pins"]]
                )

    def test_single_cloud_configuration_matches_local_raw_and_component_streams_in_another_root(
        self,
    ):
        self.test_actual_raw_sources_to_fresh_components_in_process()
        coastline = (self.inputs / "raw/land.geojson").read_bytes()
        zipped = io.BytesIO()
        with zipfile.ZipFile(zipped, "w") as archive:
            archive.writestr("land/land.geojson", coastline)
        payloads = {
            "sources/land.zip": zipped.getvalue(),
            "sources/water.parquet": (self.inputs / "raw/water.parquet").read_bytes(),
        }
        land_source = dict(
            archive=self.cloud(payloads["sources/land.zip"], "sources/land.zip"),
            member="land/land.geojson",
            sha256=hashlib.sha256(coastline).hexdigest(),
            size_bytes=len(coastline),
        )
        land = dict(self.cfg["sources"]["land_config"])
        land["land"] = [
            {"dataset": land_source["member"], "where": None, "files": [land_source]}
        ]
        water_source = self.cloud(
            payloads["sources/water.parquet"], "sources/water.parquet"
        )
        manifest = {
            "file_count": 1,
            "files": [
                {
                    "path": "raw/water.parquet",
                    "sha256": water_source["sha256"],
                    "size_bytes": water_source["size_bytes"],
                    "r2_bucket": water_source["r2_bucket"],
                    "r2_key": water_source["r2_key"],
                }
            ],
        }
        cfg = {
            **self.cfg,
            "sources": dict(
                land_config=land,
                inland_water=self.cfg["sources"]["inland_water"] | manifest,
            ),
            "r2_endpoint": "https://" + "0" * 32 + ".r2.cloudflarestorage.com",
        }
        config = write_json(self.inputs / "single-cloud-config.json", cfg)
        calls = []
        with self.fake_r2(payloads, calls):
            other = self.root / "another-computer"
            runner = pipeline.Pipeline(config, other / "run", work_dir=other)
            self.addCleanup(runner.close)
            self.assertEqual(calls, [])
            self.assertFalse((other / "inputs").exists())
            physical = runner.physical()
        report = read_json(runner.out / "physical/report.json")
        self.assertEqual(report["downloaded_shard_count"], 1)
        self.assertGreater(report["source_download_elapsed_seconds"], 0)
        runner.r2_inputs.path(land_source).unlink()
        runner.r2_inputs.path(land_source["archive"]).unlink()
        with self.fake_r2({}, []) as download:
            reused = pipeline.Pipeline(
                config, other / "reused", work_dir=other, reuse_from=runner.out
            )
            self.addCleanup(reused.close)
            self.assertEqual(reused.physical(), physical)
        download.assert_not_called()
        components = runner.out / "components"
        build_components(Grid(**cfg["grid"]), physical, components)
        for local, cloud in [
            (self.root / "run/physical/physical", physical),
            (self.root / "run/components", components),
        ]:
            for name in ("rows.u32le", "runs.u32le"):
                self.assertEqual(sha256_file(local / name), sha256_file(cloud / name))
        self.assertEqual(calls, ["sources/land.zip", "sources/water.parquet"])


if __name__ == "__main__":
    unittest.main()
