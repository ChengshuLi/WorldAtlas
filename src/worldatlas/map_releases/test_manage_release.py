"""Exercise release packaging, staging, publication and cleanup without cloud writes."""

from contextlib import contextmanager, nullcontext, redirect_stderr, redirect_stdout
import gzip
import hashlib
import io
import json
import mimetypes
import os
from pathlib import Path
import runpy
import shutil
import struct
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

from worldatlas.shared.r2 import R2Client, R2ObjectMissing
from worldatlas.map_build.execution.code_archive import capture_source, write_source
from worldatlas.map_build.inputs.selection import canonical_bytes
from worldatlas.map_build.test_support import selection
from worldatlas.map_releases.catalog import (
    RELEASE_BUCKET,
    lookup_release,
    read_manifest,
    release_endpoint,
    validate_manifest,
)
from worldatlas.map_releases.inputs import (
    FILENAME,
    read_inputs,
    restore_inputs,
    write_inputs,
)
from worldatlas.map_releases.manage_release import (
    build_bundle,
    main,
    publish,
    release_categories,
    retire_previews,
    stage,
    verify_object,
    version,
)
from worldatlas.shared.files import pin_file


class BundleTests(unittest.TestCase):
    """Package a completed build from its pinned files and frozen geography."""

    def setUp(self):
        """Create a two-cell build and record its inputs and outputs as pins."""
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        root = Path(work.name).resolve()
        self.run = root / "run"
        self.viewer = root / "viewer"
        self.output = root / "bundle"
        for directory in (self.run / "final", self.viewer, self.output):
            directory.mkdir(parents=True)
        request = root / "config.json"
        self.snapshot = self.run / "input-selection.json"
        self.selection = selection()
        self.selection["geography"]["entities"].append(
            dict(
                id=42,
                name="Africa",
                physical_class="mixed",
                level_id="continent",
                parent_id=0,
                color_rgb="#E9B44C",
            )
        )
        self.selection["geography"]["category_bindings"] = [
            dict(code=1, entity_id=42, physical_class="water"),
            dict(code=17, entity_id=42, physical_class="land"),
        ]
        self.snapshot.write_text(json.dumps(self.selection))
        request.write_text(
            json.dumps(
                {
                    "sources": {
                        "land_config": {"land": []},
                        "inland_water": {
                            "rasterization": {},
                            "files": [dict(
                                path="raw/shard.parquet", r2_bucket="test", r2_key="sources/shard.parquet",
                                sha256="c" * 64, size_bytes=10,
                            )],
                        },
                    },
                    "physical_controls": {
                        "max_parallel_shards": 1,
                        "source_staging": {"mode": "r2-s3", "endpoint_url": release_endpoint()},
                    },
                }
            )
        )
        identity = self.run / "run-identity.json"
        identity.write_text(
            json.dumps(
                {
                    "request": pin_file(request),
                    "divide": [0, 12],
                    "input_selection_sha256": hashlib.sha256(
                        canonical_bytes(self.selection)
                    ).hexdigest(),
                }
            )
        )
        (self.viewer / "index.html").write_text(
            "<html><head></head><body></body></html>"
        )
        (self.viewer / "config.json").write_text('{"water_rgb":[84,141,183]}')
        # The only row contains one water cell and one land cell, both in Africa.
        self.rows = struct.pack("<2I", 0, 2)
        self.runs = struct.pack("<4I", 1, 1, 2, 17)
        final = self.run / "final"
        (final / "rows.u32le").write_bytes(self.rows)
        (final / "runs.u32le").write_bytes(self.runs)
        (final / "report.json").write_text(
            '{"counts":{"1":1,"17":1},"run_count":2,"grid":{"width":2,"height":1,"step":180}}'
        )
        project = root / "source-project"
        package = project / "src/worldatlas"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("")
        (package / "build.py").write_text("value = 42\n")
        for name in ("environment.yml", "pyproject.toml", "README.md"):
            (project / name).write_text("setup: " + name)
        (project / "database").mkdir()
        (project / "database/schema.sql").write_text("CREATE SCHEMA atlas;\n")
        self.code = capture_source(package)
        self.attempt = self.run / "attempts/first"
        self.attempt.mkdir(parents=True)
        write_source(self.attempt / "source-code.json.gz", self.code)
        (self.attempt / "producer.json").write_text(
            json.dumps({"source_archive": pin_file(self.attempt / "source-code.json.gz")})
        )
        self.report = self.run / "report.json"
        self.report.write_text(
            json.dumps(
                {
                    "schema": "worldatlas-end-to-end-report-v2",
                    "status": "complete",
                    "original_run_identity": pin_file(identity),
                    "request": pin_file(request),
                    "comparison": None,
                    "final": {
                        name: pin_file(final / filename)
                        for name, filename in [
                            ("rows", "rows.u32le"),
                            ("runs", "runs.u32le"),
                            ("report", "report.json"),
                        ]
                    },
                    "stages": {
                        name: {"outputs_complete": True}
                        for name in ("physical", "division", "package", "verification")
                    },
                }
            )
        )

    def test_bundle_uses_exact_output_files_and_one_asset_base(self):
        manifest = build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)
        self.assertIn(
            '<base href="/releases/v9.0-rc.1/">',
            (self.output / "index.html").read_text(),
        )
        self.assertEqual(
            gzip.decompress((self.output / "rows.u32le.gz").read_bytes()), self.rows
        )
        self.assertEqual(
            gzip.decompress((self.output / "runs.u32le.gz").read_bytes()), self.runs
        )
        config = json.loads((self.output / "config.json").read_text())
        self.assertEqual(config["local_grid"]["rows"], "rows.u32le.gz")
        self.assertEqual(config["map_version"], "v9.0")
        self.assertEqual(config["water_rgb"], [84, 141, 183])
        self.assertNotIn("counts", config)
        self.assertEqual(config["legend"], "legend/entities.json")
        self.assertEqual(
            config["categories"],
            [
                {"id": 1, "entity_id": 42, "physical_class": "water"},
                {"id": 17, "entity_id": 42, "physical_class": "land"},
            ],
        )
        self.assertEqual(
            json.loads((self.output / config["legend"]).read_bytes()),
            [
                {"id": 42, "name": "Africa", "color": [233, 180, 76], "count": 2},
            ],
        )
        self.assertIn(config["legend"], manifest["objects"])
        self.assertEqual(
            config["combined_sha256"], hashlib.sha256(self.rows + self.runs).hexdigest()
        )
        self.assertEqual(
            manifest["decoded_sha256"]["runs"], hashlib.sha256(self.runs).hexdigest()
        )

    def test_changed_map_output_cannot_be_staged(self):
        (self.run / "final/runs.u32le").write_bytes(b"x" * len(self.runs))
        with self.assertRaisesRegex(ValueError, "runs size or checksum differs"):
            build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)

    def test_stage_checks_map_stream_size_when_checksum_matches(self):
        rows = self.run / "final/rows.u32le"
        rows.write_bytes(self.rows + b"\0" * 4)
        report = json.loads(self.report.read_bytes())
        report["final"]["rows"] = pin_file(rows)
        self.report.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "rows size or checksum differs"):
            build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)

    def test_bundle_requires_completed_stages_and_original_identity(self):
        report = json.loads(self.report.read_bytes())
        incomplete = dict(report, stages={})
        self.report.write_text(json.dumps(incomplete))
        with self.assertRaisesRegex(ValueError, "a completed map build is required"):
            build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)
        identity = self.run / "run-identity.json"
        identity.write_text("{}")
        self.report.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "build identity does not match"):
            build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)
        identity.write_text('{"request": {}}')
        report["original_run_identity"] = pin_file(identity)
        self.report.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "build configuration does not match"):
            build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)

    def test_bundle_requires_outputs_together_under_the_run(self):
        report = json.loads(self.report.read_bytes())
        path = self.run.parent / "rows.u32le"
        path.write_bytes(self.rows)
        report["final"]["rows"] = pin_file(path)
        self.report.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "outputs together inside the build directory"):
            build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)

    def test_bundle_checks_map_count_coverage_and_category_ids(self):
        report = json.loads(self.report.read_bytes())
        path = self.run / "final/report.json"
        summary = json.loads(path.read_bytes())
        for counts, error in (({"1": 1}, "counts must cover"), ({"99": 2}, "missing categories")):
            with self.subTest(counts=counts), self.assertRaisesRegex(ValueError, error):
                path.write_text(json.dumps(dict(summary, counts=counts)))
                report["final"]["report"] = pin_file(path)
                self.report.write_text(json.dumps(report))
                build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)

    def test_viewer_requires_an_unversioned_homepage_and_regular_asset_paths(self):
        asset = self.viewer / "script link.js"
        asset.touch()
        with self.assertRaisesRegex(ValueError, "invalid viewer asset path"):
            build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)
        asset.unlink()
        (self.viewer / "index.html").write_text('<head><base href="/other/"></head>')
        with self.assertRaisesRegex(ValueError, "single head and no base URL"):
            build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)

    def test_viewer_readmes_are_excluded(self):
        (self.viewer / "docs").mkdir()
        (self.viewer / "docs" / "README.md").write_text("viewer documentation")
        manifest = build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)
        self.assertNotIn("docs/README.md", manifest["objects"])

    def test_bundle_requires_captured_code(self):
        producer = self.attempt / "producer.json"
        producer.write_text("{}")
        with self.assertRaisesRegex(ValueError, "build attempt first has no captured code snapshot"):
            build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)
        producer.unlink()
        with self.assertRaisesRegex(ValueError, "completed build has no captured code snapshot"):
            build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)

    def test_bundle_media_types_are_independent_of_host_settings(self):
        (self.viewer / "app.js").write_text("export const value = 1;\n")
        first = build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)
        other = self.output.with_name("other-bundle")
        other.mkdir()
        with patch.dict(mimetypes.types_map, {".js": "application/javascript"}):
            second = build_bundle("v9.0-rc.1", self.run, self.viewer, other)
        self.assertEqual(first["objects"]["app.js"]["content_type"], "text/javascript")
        self.assertEqual(first, second)

    def test_changed_saved_selection_blocks_staging(self):
        self.selection["geography"]["entities"][1]["name"] = "changed"
        self.snapshot.write_text(json.dumps(self.selection))
        with self.assertRaisesRegex(ValueError, "saved geographic selection changed"):
            build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)

    def test_colors_are_read_from_the_saved_selection(self):
        manifest = build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)
        self.assertEqual(manifest["inputs"]["archive"], FILENAME)
        self.assertEqual(manifest["inputs"].keys(), {"archive"})
        archived = read_inputs((self.output / FILENAME).read_bytes(), "v9.0-rc.1")
        self.assertEqual(archived["selection"], self.selection)
        self.assertEqual(
            archived["configuration"],
            json.loads((self.run.parent / "config.json").read_text()),
        )
        self.assertEqual(archived["report"]["status"], "complete")
        self.assertIn(FILENAME, manifest["objects"])
        self.assertNotIn("configuration", manifest["inputs"])

    def test_bundle_does_not_reinterpret_the_frozen_geographic_rules(self):
        self.selection["geography"]["schema"] = "worldatlas-geographic-division-v1"
        self.snapshot.write_text(json.dumps(self.selection))
        identity_file = self.run / "run-identity.json"
        identity = json.loads(identity_file.read_bytes())
        identity["input_selection_sha256"] = hashlib.sha256(canonical_bytes(self.selection)).hexdigest()
        identity_file.write_text(json.dumps(identity))
        report = json.loads(self.report.read_bytes())
        report["original_run_identity"] = pin_file(identity_file)
        self.report.write_text(json.dumps(report))
        build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)
        archived = read_inputs((self.output / FILENAME).read_bytes(), "v9.0-rc.1")
        self.assertEqual(archived["selection"], self.selection)

    def test_input_archive_is_repeatable_and_restores_without_database(self):
        manifest = build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)
        body = (self.output / FILENAME).read_bytes()
        archived = read_inputs(body, "v9.0-rc.1")
        with self.assertRaisesRegex(ValueError, "identity"):
            read_inputs(body, "v9.0-rc.2")
        restored = self.output / "restored"
        restore_inputs(archived, restored)
        self.assertEqual(
            json.loads((restored / "selection.json").read_bytes()), self.selection
        )
        self.assertEqual(json.loads((restored / "run.json").read_bytes())["divide"], [0, 12])
        with self.assertRaises(FileExistsError):
            restore_inputs(archived, restored)
        again = self.output / "again.gz"
        write_inputs(
            again,
            release_id=archived["release_id"],
            configuration=archived["configuration"],
            selection=archived["selection"],
            run=archived["run"],
            report=archived["report"],
            source_code=archived.get("source_code"),
        )
        self.assertEqual(again.read_bytes(), body)

    def test_release_keeps_captured_code_and_deduplicates_unchanged_attempts(self):
        second = self.run / "attempts/second"
        second.mkdir()
        shutil.copyfile(
            self.attempt / "source-code.json.gz", second / "source-code.json.gz"
        )
        (second / "producer.json").write_text(
            json.dumps({"source_archive": pin_file(second / "source-code.json.gz")})
        )
        build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)
        archived = read_inputs((self.output / FILENAME).read_bytes(), "v9.0-rc.1")
        self.assertEqual(len(archived["source_code"]), 1)
        self.assertEqual(len(archived["run"]["attempts"]), 2)
        restored = self.run.parent / "restored-code"
        restore_inputs(archived, restored)
        code_id = next(iter(archived["source_code"]))
        self.assertEqual(
            (restored / "code" / code_id / "src/worldatlas/build.py").read_text(),
            "value = 42\n",
        )

    def test_changed_code_archive_cannot_be_staged(self):
        (self.attempt / "source-code.json.gz").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "checkpoint/input hash mismatch"):
            build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)

    def test_source_archive_must_belong_to_the_reported_attempt(self):
        other = self.run.parent / "source-code.json.gz"
        shutil.copyfile(self.attempt / "source-code.json.gz", other)
        (self.attempt / "producer.json").write_text(json.dumps({"source_archive": pin_file(other)}))
        with self.assertRaisesRegex(ValueError, "inside its build attempt"):
            build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)

    def test_historical_restore_applies_locations_without_rewriting_original_records(
        self,
    ):
        body = self.output / FILENAME
        write_inputs(
            body,
            release_id="v8.0",
            configuration={"source": "evidence/a"},
            selection=None,
            run=None,
            report=None,
            records=[{"source_id": "old", "document_text": "original text"}],
            raw_sources=[{"r2_key": "evidence/a"}],
            notes=["Original code was not recorded."],
            relocations={"evidence/a": "sources/a"},
        )
        saved = read_inputs(body.read_bytes(), "v8.0")
        destination = self.output / "restored"
        restore_inputs(saved, destination)
        self.assertEqual(saved["configuration"]["source"], "evidence/a")
        self.assertEqual(
            json.loads((destination / "configuration.json").read_bytes())["source"],
            "sources/a",
        )
        self.assertFalse((destination / "selection.json").exists())
        self.assertEqual(
            json.loads((destination / "supporting_records.json").read_bytes()),
            saved["supporting_records"],
        )

    def test_release_rejects_a_code_bound_to_a_missing_entity(self):
        self.selection["geography"]["category_bindings"][0]["entity_id"] = 999
        with self.assertRaisesRegex(ValueError, "category binding"):
            release_categories(self.selection)

    def test_missing_land_color_blocks_staging(self):
        self.selection["geography"]["entities"][1]["color_rgb"] = None
        self.snapshot.write_text(json.dumps(self.selection))
        identity_path = self.run / "run-identity.json"
        identity = json.loads(identity_path.read_text())
        identity["input_selection_sha256"] = hashlib.sha256(
            canonical_bytes(self.selection)
        ).hexdigest()
        identity_path.write_text(json.dumps(identity))
        report = json.loads(self.report.read_text())
        report["original_run_identity"] = pin_file(identity_path)
        self.report.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "missing for land entities"):
            build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)

    def test_candidate_name_identifies_the_release(self):
        self.assertEqual(version("v9.0-rc.2"), "v9.0")
        self.assertEqual(version("v8.3-rc.1"), "v8.3")
        self.assertEqual(version("v8.3-rc.12"), "v8.3")
        with self.assertRaises(ValueError):
            version("v8.3-rc5")
        with self.assertRaises(ValueError):
            version("../v9.0")
        for invalid in ("v8.3-rc", "v8.3-rc.0", "v8.3-rc.01", "v8.3-rc.1/extra"):
            with self.assertRaises(ValueError):
                version(invalid)


class R2VerificationTests(unittest.TestCase):
    """Check that staging retries preserve exact bytes and file metadata."""

    def test_staging_writes_only_its_candidate_and_pins_manifest_last(self):
        class Storage:
            """Keep object bytes in memory and reject replacement writes."""

            def __init__(self):
                self.objects = {"index.html": b"published"}
                self.types = {}

            def put_object(self, **options):
                assert options["IfNoneMatch"] == "*"
                if options["Key"] in self.objects:
                    raise ClientError({"ResponseMetadata": {"HTTPStatusCode": 412}}, "PutObject")
                body = options["Body"]
                self.objects[options["Key"]] = (
                    body.read() if hasattr(body, "read") else body
                )
                self.types[options["Key"]] = options["ContentType"]

            def get_object(self, **options):
                key = options["Key"]
                body = self.objects[key]
                return dict(
                    ContentLength=len(body),
                    ContentType=self.types[key],
                    Body=io.BytesIO(body),
                )

        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp)
            objects = {}
            folder = "releases/v9.0-rc.1/"
            for name in (
                "index.html",
                "rows.u32le.gz",
                "runs.u32le.gz",
                "inputs.json.gz",
            ):
                body = name.encode()
                (bundle / name).write_bytes(body)
                objects[name] = dict(
                    r2_key=folder + name,
                    sha256=hashlib.sha256(body).hexdigest(),
                    size_bytes=len(body),
                    content_type="application/octet-stream",
                )
            manifest = dict(objects=objects)
            db = Mock()
            db.execute.return_value.fetchone.return_value = None
            storage = Storage()
            candidate = "v9.0-rc.1"
            stage(db, R2Client(storage), candidate, bundle, manifest)
            self.assertEqual(storage.objects["index.html"], b"published")
            self.assertEqual(list(storage.objects)[-1], folder + "manifest.json")
            self.assertEqual(
                json.loads(storage.objects[folder + "manifest.json"]), manifest
            )
            checksum = hashlib.sha256(storage.objects[folder + "manifest.json"]).hexdigest()
            record = (RELEASE_BUCKET, checksum)
            db.execute.reset_mock()
            db.execute.return_value.fetchone.side_effect = [(candidate,), record]
            stage(db, R2Client(storage), candidate, bundle, manifest)
            self.assertEqual(len(db.execute.call_args_list), 2)
            db.execute.return_value.fetchone.side_effect = [None, record]
            with self.assertRaisesRegex(ValueError, "already exists with different contents"):
                stage(db, R2Client(storage), candidate, bundle, dict(manifest, new_field=True))
            inputs = objects.pop(FILENAME)
            db.execute.return_value.fetchone.side_effect = [None]
            with self.assertRaisesRegex(ValueError, "no frozen input archive"):
                stage(db, R2Client(storage), candidate, bundle, manifest)
            objects[FILENAME] = inputs
            class FailingStorage(Storage):
                def put_object(self, **options):
                    filename = options["Key"].removeprefix(folder)
                    if filename == self.failure:
                        raise ClientError({"ResponseMetadata": {"HTTPStatusCode": 403}}, "PutObject")
                    super().put_object(**options)

            for name in ("rows.u32le.gz", "manifest.json"):
                failed = FailingStorage()
                failed.failure = name
                db.execute.return_value.fetchone.side_effect = [None, None]
                with self.subTest(name=name), self.assertRaises(ClientError):
                    stage(db, R2Client(failed), candidate, bundle, manifest)
                self.assertNotIn(folder + "manifest.json", failed.objects)

    def test_no_new_candidate_can_be_staged_after_its_version_is_official(self):
        db, storage = Mock(), Mock()
        db.execute.return_value.fetchone.return_value = ("v9.0-rc.1",)
        with self.assertRaisesRegex(ValueError, "v9.0-rc.1 is already official"):
            stage(db, R2Client(storage), "v9.0-rc.2", None, {})
        storage.put_object.assert_not_called()

    def test_matching_size_cannot_pass_checksum_verification(self):
        class Storage:
            def get_object(self, **options):
                return dict(
                    ContentLength=4, ContentType="text/html", Body=io.BytesIO(b"evil")
                )

        with self.assertRaisesRegex(ValueError, "published bytes differ"):
            verify_object(
                R2Client(Storage()),
                "test",
                "index.html",
                dict(
                    size_bytes=4,
                    content_type="text/html",
                    sha256=hashlib.sha256(b"good").hexdigest(),
                ),
            )

    def test_asset_metadata_must_match_before_checking_body(self):
        body = b"grid"
        asset = dict(size_bytes=len(body), content_type="text/html", sha256=hashlib.sha256(body).hexdigest())
        for metadata, error in (
            ({"ContentLength": 2}, "wrong size or encoding"),
            ({"ContentEncoding": "gzip"}, "wrong size or encoding"),
            ({"ContentType": "text/plain"}, "wrong content type"),
        ):
            storage = Mock()
            response = dict(ContentLength=len(body), ContentType="text/html", Body=io.BytesIO(body))
            storage.get_object.return_value = response | metadata
            with self.subTest(metadata=metadata), self.assertRaisesRegex(ValueError, error):
                verify_object(R2Client(storage), RELEASE_BUCKET, "index.html", asset)
            self.assertTrue(response["Body"].closed)


class CatalogTests(unittest.TestCase):
    """Check release identities and manifest pins before operating on objects."""

    def test_lookups_require_one_release_identity(self):
        database = Mock()
        database.execute.return_value.fetchall.return_value = []
        with self.assertRaisesRegex(ValueError, "no unique release for v9.0"):
            lookup_release(database, "v9.0")

    def test_manifest_checksum_must_match_the_catalog(self):
        storage = Mock()
        storage.get_object.return_value = {"Body": io.BytesIO(b"{}")}
        release = dict(id="v9.0-rc.1", r2_bucket=RELEASE_BUCKET, manifest_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "Neon checksum"):
            read_manifest(R2Client(storage), release)

    def test_manifest_requires_file_identities_within_its_release_folder(self):
        candidate = "v9.0-rc.1"
        asset = dict(r2_key=f"releases/{candidate}/rows.u32le.gz", sha256="a" * 64,
                     size_bytes=4, content_type="application/gzip")
        for manifest, error in (
            ({}, "invalid release manifest"),
            ({"objects": {"rows.u32le.gz": None}}, "invalid release object"),
            ({"objects": {"../rows.u32le.gz": asset}}, "escapes its own immutable folder"),
            ({"objects": {"rows.u32le.gz": dict(asset, r2_key="other/rows.u32le.gz")}}, "escapes"),
            ({"objects": {"rows.u32le.gz": dict(asset, sha256="z" * 64)}}, "invalid release object byte identity"),
            ({"objects": {"rows.u32le.gz": asset}}, "lacks map streams"),
        ):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                validate_manifest(manifest, candidate)


class PublicationTests(unittest.TestCase):
    """Verify the order of catalog commits, homepage writes, and cleanup."""

    def setUp(self):
        """Prepare a verified candidate and a distinct existing homepage ETag."""
        self.candidate = "v9.0-rc.1"
        self.folder = "releases/" + self.candidate + "/"
        self.files = {
            name: name.encode()
            for name in ("index.html", "rows.u32le.gz", "runs.u32le.gz", "inputs.json.gz")
        }
        self.manifest = {"objects": self.assets()}
        self.db = Mock()
        self.db.transaction.side_effect = nullcontext
        self.set_release()
        self.storage = Mock()
        self.storage.head_object.return_value = {"ETag": '"current"'}
        self.storage.get_object.side_effect = self.get_object
        self.storage.get_paginator.return_value.paginate.return_value = []

    def set_release(self, *, official=False, current=False, bucket=RELEASE_BUCKET, previews=()):
        """Set the release and preview rows returned by the mock catalog.

        Args:
            official: Whether this candidate is already official for its version.
            current: Whether Neon selected this candidate for the homepage.
            bucket: Bucket recorded in the candidate's catalog row.
            previews: Unpublished catalog rows found during preview cleanup.
        """
        raw = json.dumps(self.manifest).encode()
        self.db.execute.return_value.fetchall.side_effect = [
            [(self.candidate, "v9.0", bucket, hashlib.sha256(raw).hexdigest(), official, current)],
            previews,
        ]
        self.db.execute.return_value.fetchone.return_value = (self.candidate,) if official else None

    def assets(self):
        """Build manifest entries for the publication fixture.

        Returns:
            Asset records keyed by filename, with metadata matching the fixture bytes.
        """
        return {name: dict(r2_key=self.folder + name, size_bytes=len(body),
                           sha256=hashlib.sha256(body).hexdigest(), content_type="application/octet-stream")
                for name, body in self.files.items()}

    def get_object(self, *, Bucket, Key):
        """Return a fresh body for each fake R2 read.

        Args:
            Bucket: Bucket passed to the fake R2 client.
            Key: Manifest or asset key within the test candidate's folder.

        Returns:
            The response body and asset metadata used by the real verifier.
        """
        name = Key.removeprefix(self.folder)
        if name == "manifest.json":
            return {"Body": io.BytesIO(json.dumps(self.manifest).encode())}
        content = self.files[name]
        return dict(Body=io.BytesIO(content), ContentLength=len(content), ContentType="application/octet-stream")

    def test_publish_installs_verified_homepage_and_selects_candidate(self):
        committed = False

        @contextmanager
        def catalog_transaction():
            nonlocal committed
            yield
            committed = True

        def write_homepage(**_):
            self.assertTrue(committed)

        self.db.transaction.side_effect = catalog_transaction
        self.storage.put_object.side_effect = write_homepage
        self.db.execute.return_value.fetchone.side_effect = [None, (self.candidate,)]
        self.assertTrue(publish(self.db, R2Client(self.storage), self.candidate))
        self.storage.put_object.assert_called_once_with(
            Bucket=RELEASE_BUCKET, Key="index.html", Body=self.files["index.html"],
            ContentType="text/html", CacheControl="no-cache", IfMatch='"current"',
        )
        updates = [call.args for call in self.db.execute.call_args_list if call.args[0].startswith("UPDATE")]
        self.assertEqual(len(updates), 2)
        self.assertIn("SET is_current=false", updates[0][0])
        self.assertIn("SET is_official=true,is_current=true", updates[1][0])
        self.assertEqual([args for _, args in updates], [(self.candidate,)] * 2)

    def test_failed_catalog_commit_never_writes_the_homepage(self):
        @contextmanager
        def catalog_transaction():
            yield
            raise OSError("catalog commit interrupted")

        self.db.transaction.side_effect = catalog_transaction
        with self.assertRaisesRegex(OSError, "catalog commit interrupted"):
            publish(self.db, R2Client(self.storage), self.candidate)
        self.storage.put_object.assert_not_called()
        self.storage.get_paginator.assert_not_called()

    def test_failed_homepage_update_can_retry_while_release_is_current(self):
        self.storage.put_object.side_effect = OSError("homepage write interrupted")
        with self.assertRaisesRegex(OSError, "homepage write interrupted"):
            publish(self.db, R2Client(self.storage), self.candidate)
        self.assertIn("SET is_official=true,is_current=true", self.db.execute.call_args.args[0])
        self.storage.get_paginator.assert_not_called()
        self.set_release(official=True, current=True)
        self.storage.put_object.side_effect = None
        self.assertTrue(publish(self.db, R2Client(self.storage), self.candidate))
        self.assertEqual(self.storage.put_object.call_count, 2)

    def test_retry_for_older_official_release_never_rewrites_homepage(self):
        preview = "v9.0-rc.2"
        self.set_release(official=True, previews=[(preview, RELEASE_BUCKET, "a" * 64)])
        with patch("worldatlas.map_releases.manage_release.read_manifest", return_value={"objects": {}}):
            self.assertFalse(publish(self.db, R2Client(self.storage), self.candidate))
        self.storage.head_object.assert_not_called()
        self.storage.put_object.assert_not_called()
        self.db.transaction.assert_not_called()
        self.storage.delete_object.assert_called_once_with(
            Bucket=RELEASE_BUCKET, Key=f"releases/{preview}/manifest.json",
        )

    def test_publish_refuses_a_different_candidate_for_an_official_version(self):
        self.db.execute.return_value.fetchone.return_value = ("v9.0-rc.2",)
        with self.assertRaisesRegex(ValueError, "different official candidate"):
            publish(self.db, R2Client(self.storage), self.candidate)
        self.storage.get_object.assert_not_called()
        self.storage.put_object.assert_not_called()

    def test_publish_requires_the_website_bucket(self):
        self.set_release(bucket="other")
        with self.assertRaisesRegex(ValueError, "website serves releases"):
            publish(self.db, R2Client(self.storage), self.candidate)
        self.storage.put_object.assert_not_called()

    def test_publish_requires_replay_inputs_and_a_homepage(self):
        for name, error in (("inputs.json.gz", "frozen input archive"), ("index.html", "no viewer homepage")):
            with self.subTest(name=name):
                asset = self.manifest["objects"].pop(name)
                self.set_release()
                with self.assertRaisesRegex(ValueError, error):
                    publish(self.db, R2Client(self.storage), self.candidate)
                self.manifest["objects"][name] = asset
        self.storage.put_object.assert_not_called()

    def test_first_publication_creates_homepage_and_unexpected_errors_stop(self):
        self.storage.head_object.side_effect = ClientError({"ResponseMetadata": {"HTTPStatusCode": 403}}, "HeadObject")
        with self.assertRaises(ClientError):
            publish(self.db, R2Client(self.storage), self.candidate)
        self.storage.put_object.assert_not_called()
        self.storage.head_object.side_effect = ClientError({"ResponseMetadata": {"HTTPStatusCode": 404}}, "HeadObject")
        self.set_release()
        self.db.execute.return_value.fetchone.side_effect = [None, (self.candidate,)]
        self.assertTrue(publish(self.db, R2Client(self.storage), self.candidate))
        self.assertEqual(self.storage.put_object.call_args.kwargs["IfNoneMatch"], "*")


class PreviewRetirementTests(unittest.TestCase):
    """Exercise cleanup of registered previews and interrupted uploads."""

    def manifest(self, identity):
        """List the objects to delete for a registered preview.

        Args:
            identity: Preview ID used to form its object keys.

        Returns:
            The asset keys a verified manifest would supply to cleanup.
        """
        return dict(
            objects={
                name: dict(r2_key="releases/" + identity + "/" + name)
                for name in ("rows.u32le.gz", "runs.u32le.gz")
            }
        )

    def test_only_unpublished_siblings_are_deleted(self):
        db, storage = Mock(), Mock()
        storage.get_paginator.return_value.paginate.return_value = []
        db.execute.return_value.fetchone.return_value = ("v9.0-rc.3",)
        db.execute.return_value.fetchall.return_value = [
            ("v9.0-rc.1", "test", "a" * 64)
        ]
        with patch(
            "worldatlas.map_releases.manage_release.read_manifest",
            return_value=self.manifest("v9.0-rc.1"),
        ):
            self.assertEqual(retire_previews(db, R2Client(storage), "v9.0"), ["v9.0-rc.1"])
        self.assertEqual(
            [c.kwargs["Key"] for c in storage.delete_object.call_args_list],
            [
                "releases/v9.0-rc.1/rows.u32le.gz",
                "releases/v9.0-rc.1/runs.u32le.gz",
                "releases/v9.0-rc.1/manifest.json",
            ],
        )
        self.assertIn("NOT is_official", db.execute.call_args_list[1].args[0])

    def test_abandoned_uploads_are_removed_only_for_the_exact_official_version(self):
        db, storage = Mock(), Mock()
        db.execute.return_value.fetchone.return_value = ("v9.0-rc.3",)
        db.execute.return_value.fetchall.return_value = []
        abandoned = "releases/v9.0-rc.2/"
        other_abandoned = "releases/v9.0-rc.10/"
        keys = [abandoned + "index.html", abandoned + "legend/entities.json"]
        second_keys = [other_abandoned + "rows.u32le.gz"]
        paginate = storage.get_paginator.return_value.paginate

        def list_pages(*, Bucket, Prefix, Delimiter=None):
            # The first listing finds candidate folders. Later listings return
            # each abandoned folder's files, including nested assets.
            self.assertEqual(Bucket, RELEASE_BUCKET)
            if Delimiter == "/":
                self.assertEqual(Prefix, "releases/v9.0-rc.")
                return [
                    {"CommonPrefixes": [{"Prefix": abandoned}, {"Prefix": "releases/v9.0-rc.3/"}]},
                    {"CommonPrefixes": [{"Prefix": folder} for folder in (
                        other_abandoned, "releases/v9.0-rc.03/", "releases/v9.01-rc.1/",
                    )]},
                ]
            self.assertIn(Prefix, (abandoned, other_abandoned))
            return [{"Contents": [{"Key": key}]} for key in (keys if Prefix == abandoned else second_keys)]

        paginate.side_effect = list_pages
        self.assertEqual(retire_previews(db, R2Client(storage), "v9.0"), ["v9.0-rc.10", "v9.0-rc.2"])
        self.assertEqual([call.kwargs["Key"] for call in storage.delete_object.call_args_list], second_keys + keys)
        storage.get_object.assert_not_called()
        self.assertEqual(db.execute.call_count, 2)

    def test_unpublished_family_is_preserved(self):
        db, storage = Mock(), Mock()
        db.execute.return_value.fetchone.return_value = None
        with self.assertRaisesRegex(ValueError, "publish a final"):
            retire_previews(db, R2Client(storage), "v9.0")
        storage.delete_object.assert_not_called()

    def test_failed_deletion_keeps_manifest_and_catalog_row_for_retry(self):
        db, storage = Mock(), Mock()
        db.execute.return_value.fetchone.return_value = ("v9.0-rc.3",)
        db.execute.return_value.fetchall.return_value = [
            ("v9.0-rc.1", "test", "a" * 64)
        ]
        storage.delete_object.side_effect = OSError("interrupted")
        with patch(
            "worldatlas.map_releases.manage_release.read_manifest",
            return_value=self.manifest("v9.0-rc.1"),
        ):
            with self.assertRaises(OSError):
                retire_previews(db, R2Client(storage), "v9.0")
        self.assertFalse(
            any("DELETE FROM" in c.args[0] for c in db.execute.call_args_list)
        )

    def test_retry_after_manifest_deletion_requires_an_empty_folder(self):
        candidate, folder = "v9.0-rc.1", "releases/v9.0-rc.1/"
        for remaining in ([], [{"Key": folder + "index.html"}]):
            with self.subTest(remaining=remaining):
                db, storage = Mock(), Mock()
                storage.get_paginator.return_value.paginate.return_value = []
                db.execute.return_value.fetchone.return_value = ("v9.0-rc.3",)
                db.execute.return_value.fetchall.return_value = [
                    (candidate, "test", "a" * 64)
                ]
                storage.get_object.side_effect = ClientError(
                    {"Error": {"Code": "NoSuchKey"}}, "GetObject"
                )
                storage.list_objects_v2.return_value = {"Contents": remaining}
                if remaining:
                    with self.assertRaises(R2ObjectMissing):
                        retire_previews(db, R2Client(storage), "v9.0")
                    self.assertFalse(
                        any("DELETE FROM" in c.args[0] for c in db.execute.call_args_list)
                    )
                else:
                    self.assertEqual(retire_previews(db, R2Client(storage), "v9.0"), [candidate])
                    self.assertIn("DELETE FROM", db.execute.call_args.args[0])
                storage.list_objects_v2.assert_called_once_with(
                    Bucket="test", Prefix=folder, MaxKeys=1
                )
                storage.delete_object.assert_not_called()

    def test_unexpected_manifest_read_error_stops_cleanup(self):
        db, storage = Mock(), Mock()
        db.execute.return_value.fetchone.return_value = ("v9.0-rc.2",)
        db.execute.return_value.fetchall.return_value = [("v9.0-rc.1", "test", "a" * 64)]
        storage.get_object.side_effect = ClientError({"Error": {"Code": "AccessDenied"}}, "GetObject")
        with self.assertRaises(ClientError):
            retire_previews(db, R2Client(storage), "v9.0")
        storage.delete_object.assert_not_called()
        storage.list_objects_v2.assert_not_called()


class CommandTests(unittest.TestCase):
    """Check how command arguments select the storage, lock, and operation."""

    def test_module_entry_point_displays_help(self):
        with patch.object(sys, "argv", ["worldatlas-release", "--help"]), redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as result:
                runpy.run_module("worldatlas.map_releases", run_name="__main__")
        self.assertEqual(result.exception.code, 0)
        self.assertIn("restore-inputs", output.getvalue())

    def test_write_commands_require_a_direct_catalog_connection(self):
        for url, error in (("", "set NEON_DATABASE_URL"), ("host=atlas-pooler.example.org", "use a direct Neon connection")):
            with (self.subTest(error=error), patch.dict(os.environ, NEON_DATABASE_URL=url),
                  patch.object(sys, "argv", ["worldatlas-release", "publish", "v9.0-rc.1"]),
                  redirect_stderr(io.StringIO()) as output, self.assertRaises(SystemExit)):
                main()
            self.assertIn(error, output.getvalue())

    def test_write_commands_share_the_release_endpoint_and_lock(self):
        command = "worldatlas.map_releases.manage_release"
        candidate = "v9.0-rc.1"
        endpoint = release_endpoint()
        for action, arguments, published, receipt in (
            ("stage", ["run", "--viewer", "viewer"], False, "Preview:"),
            ("publish", [], True, "Published"),
            ("publish", [], False, "Finished preview cleanup"),
        ):
            db, storage = Mock(), Mock()
            lock = "SELECT pg_advisory_lock(hashtext('atlas.release_publication'))"

            def after_lock(*_):
                db.execute.assert_called_once_with(lock)
                return published

            with (self.subTest(action=action, published=published),
                  patch.object(sys, "argv", ["worldatlas-release", action, candidate, *arguments]),
                  patch.dict(os.environ, NEON_DATABASE_URL="host=test"),
                  patch("psycopg.connect", return_value=nullcontext(db)),
                  patch(command + ".make_r2_client", return_value=R2Client(storage)) as client,
                  patch(command + ".build_bundle", return_value={"inputs": {"r2_endpoint": "old-raw-endpoint"}}),
                  patch(f"{command}.{action}", side_effect=after_lock) as operation,
                  redirect_stdout(io.StringIO()) as output):
                main()
            client.assert_called_once_with(endpoint)
            operation.assert_called_once()
            self.assertIn(receipt, output.getvalue())

    def test_restore_extracts_pinned_files_without_taking_a_write_lock(self):
        command = "worldatlas.map_releases.manage_release"
        candidate = "v9.0-rc.1"
        db, storage = Mock(), Mock()
        with tempfile.TemporaryDirectory() as temp:
            archive, output = Path(temp) / FILENAME, Path(temp) / "restored"
            write_inputs(archive, release_id=candidate, configuration={}, selection={"coordinates": [0, 1]},
                         run=None, report=None)
            body = archive.read_bytes()
            asset = dict(r2_key=f"releases/{candidate}/{FILENAME}", size_bytes=len(body),
                         sha256=hashlib.sha256(body).hexdigest(), content_type="application/gzip")
            release = dict(id=candidate, r2_bucket=RELEASE_BUCKET)
            storage.get_object.return_value = dict(Body=io.BytesIO(body), ContentLength=len(body), ContentType="application/gzip")
            manifest = dict(inputs={}, objects={FILENAME: asset})
            with (patch.object(sys, "argv", ["worldatlas-release", "restore-inputs", candidate, str(output)]),
                  patch.dict(os.environ, NEON_DATABASE_URL="host=atlas-pooler.example.org"),
                  patch("psycopg.connect", return_value=nullcontext(db)),
                  patch(command + ".make_r2_client", return_value=R2Client(storage)) as client,
                  patch(command + ".lookup_release", return_value=release),
                  patch(command + ".read_manifest", return_value=manifest), redirect_stdout(io.StringIO())):
                main()
                manifest["objects"].clear()
                with self.assertRaisesRegex(ValueError, "no input archive"):
                    main()
            self.assertEqual(client.call_count, 2)
            client.assert_called_with(release_endpoint())
            db.execute.assert_not_called()
            self.assertEqual(json.loads((output / "selection.json").read_bytes()), {"coordinates": [0, 1]})
