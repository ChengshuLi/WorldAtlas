import gzip
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import Mock

from worldatlas.map_build.execution.runtime import pin
from worldatlas.map_build.inputs.selection import canonical_bytes
from worldatlas.map_releases.manage_release import (
    build_bundle,
    release_categories,
    retire_previews,
    stage,
    verify_object,
    version,
)
from worldatlas.map_releases.inputs import (
    FILENAME,
    read_inputs,
    restore_inputs,
    write_inputs,
)


class BundleTests(unittest.TestCase):
    def setUp(self):
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
        self.selection = {
            "schema": "worldatlas-input-selection-v1",
            "revisions": {"mainland": "test"},
            "domains": {
                "mainland": {
                    "decision_revision": {"entity_revision": "entities"},
                    "entities": [{"id": 42, "name": "Africa"}],
                    "category_bindings": [
                        {"code": 1, "entity_id": 42, "physical_class": "water"},
                        {"code": 17, "entity_id": 42, "physical_class": "land"},
                    ],
                }
            },
            "registry_colors": {
                "entities": [{"entity_id": 42, "color_rgb": "#E9B44C"}]
            },
        }
        self.snapshot.write_text(json.dumps(self.selection))
        request.write_text(
            json.dumps(
                {
                    "sources": {
                        "land_config": {
                            "json": {"grid": {"width": 2, "height": 1, "step": 180}}
                        },
                    },
                }
            )
        )
        identity = self.run / "run-identity.json"
        identity.write_text(
            json.dumps(
                {
                    "request": pin(request),
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
        self.rows = struct.pack("<2I", 0, 2)
        self.runs = struct.pack("<4I", 1, 1, 2, 17)
        final = self.run / "final"
        (final / "rows.u32le").write_bytes(self.rows)
        (final / "runs.u32le").write_bytes(self.runs)
        (final / "report.json").write_text(
            '{"counts":{"1":1,"17":1},"run_count":2,"grid":{"width":2,"height":1,"step":180}}'
        )
        self.report = self.run / "report.json"
        self.report.write_text(
            json.dumps(
                {
                    "schema": "worldatlas-end-to-end-report-v1",
                    "status": "complete",
                    "original_run_identity": pin(identity),
                    "request": pin(request),
                    "comparison": None,
                    "final": {
                        name: pin(final / filename)
                        for name, filename in [
                            ("rows", "rows.u32le"),
                            ("runs", "runs.u32le"),
                            ("report", "report.json"),
                        ]
                    },
                    "stages": {
                        name: {"outputs_complete": True}
                        for name in ("physical", "mainland", "water", "verification")
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
        self.assertEqual(config["legend"], "legend/continents.json")
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
        (self.run / "final/runs.u32le").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "checkpoint/input hash mismatch"):
            build_bundle("v9.0-rc.1", self.run, self.viewer, self.output)

    def test_changed_saved_selection_blocks_staging(self):
        self.selection["domains"]["mainland"]["entities"][0]["name"] = "changed"
        self.snapshot.write_text(json.dumps(self.selection))
        with self.assertRaisesRegex(ValueError, "saved geographic selection changed"):
            build_bundle("v9.0-rc1", self.run, self.viewer, self.output)

    def test_flat_working_selection_has_the_same_legend_as_the_archived_format(self):
        from copy import deepcopy

        archived = release_categories(self.selection)
        geography = deepcopy(self.selection["domains"]["mainland"])
        geography["routes"] = []
        current = {
            "schema": "worldatlas-input-selection-v3",
            "geography": geography,
            "entity_colors": deepcopy(self.selection["registry_colors"]["entities"]),
        }
        self.assertEqual(release_categories(current), archived)

    def test_colors_are_read_from_the_saved_selection(self):
        manifest = build_bundle("v9.0-rc1", self.run, self.viewer, self.output)
        self.assertEqual(manifest["inputs"]["archive"], FILENAME)
        self.assertEqual(manifest["inputs"].keys(), {"archive"})
        archived = read_inputs((self.output / FILENAME).read_bytes(), "v9.0-rc1")
        self.assertEqual(archived["selection"], self.selection)
        self.assertEqual(
            archived["configuration"],
            json.loads((self.run.parent / "config.json").read_text()),
        )
        self.assertEqual(archived["report"]["status"], "complete")
        self.assertIn(FILENAME, manifest["objects"])
        self.assertNotIn("configuration", manifest["inputs"])

    def test_input_archive_is_repeatable_and_restores_without_database(self):
        manifest = build_bundle("v9.0-rc1", self.run, self.viewer, self.output)
        body = (self.output / FILENAME).read_bytes()
        archived = read_inputs(body, "v9.0-rc1")
        with self.assertRaisesRegex(ValueError, "identity"):
            read_inputs(body, "v9.0-rc2")
        restored = self.output / "restored"
        restore_inputs(archived, restored)
        self.assertEqual(
            json.loads((restored / "selection.json").read_bytes()), self.selection
        )
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
        )
        self.assertEqual(again.read_bytes(), body)

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

    def test_release_rejects_a_code_with_different_meanings_between_stages(self):
        self.selection["domains"]["regional"] = {
            "category_bindings": [
                dict(code=1, entity_id=42, physical_class="water"),
                dict(code=17, entity_id=999, physical_class="land"),
            ]
        }
        with self.assertRaisesRegex(ValueError, "category bindings differ"):
            release_categories(self.selection)

    def test_missing_land_color_blocks_staging(self):
        self.selection["registry_colors"]["entities"][0]["color_rgb"] = None
        self.snapshot.write_text(json.dumps(self.selection))
        identity_path = self.run / "run-identity.json"
        identity = json.loads(identity_path.read_text())
        identity["input_selection_sha256"] = hashlib.sha256(
            canonical_bytes(self.selection)
        ).hexdigest()
        identity_path.write_text(json.dumps(identity))
        report = json.loads(self.report.read_text())
        report["original_run_identity"] = pin(identity_path)
        self.report.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "missing for land entities"):
            build_bundle("v9.0-rc1", self.run, self.viewer, self.output)

    def test_candidate_name_identifies_the_release(self):
        self.assertEqual(version("v9.0-rc.2"), "v9.0")
        self.assertEqual(version("v8.3-rc1"), "v8.3")
        self.assertEqual(version("v8.3-rc12"), "v8.3")
        with self.assertRaises(ValueError):
            version("../v9.0")
        for invalid in ("v8.3-rc", "v8.3-rc0", "v8.3-rc01", "v8.3-rc1/extra"):
            with self.assertRaises(ValueError):
                version(invalid)


class R2VerificationTests(unittest.TestCase):
    def test_staging_writes_only_the_numbered_candidate(self):
        class Storage:
            def __init__(self):
                self.objects = {"index.html": b"published"}

            def put_object(self, **options):
                assert options["IfNoneMatch"] == "*"
                self.objects[options["Key"]] = options["Body"].read()

            def get_object(self, **options):
                body = self.objects[options["Key"]]
                return {
                    "ContentLength": len(body),
                    "ContentType": "text/html",
                    "Body": io.BytesIO(body),
                }

        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)
            body = b"numbered candidate"
            (bundle / "index.html").write_bytes(body)
            manifest = {
                "objects": {
                    "index.html": {
                        "r2_key": "releases/v9.0-rc.1/index.html",
                        "size_bytes": len(body),
                        "content_type": "text/html",
                        "sha256": hashlib.sha256(body).hexdigest(),
                    }
                }
            }
            db, storage = Mock(), Storage()
            db.execute.return_value.fetchone.return_value = None
            stage(db, storage, "test", "v9.0-rc.1", bundle, manifest)
            self.assertEqual(
                storage.objects,
                {"index.html": b"published", "releases/v9.0-rc.1/index.html": body},
            )

    def test_matching_size_alone_cannot_pass_release_verification(self):
        class Storage:
            def get_object(self, **options):
                return {
                    "ContentLength": 4,
                    "ContentType": "text/html",
                    "Body": io.BytesIO(b"evil"),
                }

        with self.assertRaisesRegex(ValueError, "published bytes differ"):
            verify_object(
                Storage(),
                "test",
                "index.html",
                {
                    "size_bytes": 4,
                    "content_type": "text/html",
                    "sha256": hashlib.sha256(b"good").hexdigest(),
                },
            )


class PreviewRetirementTests(unittest.TestCase):
    def test_only_superseded_candidates_of_a_published_version_are_retired(self):
        db, storage = Mock(), Mock()
        db.execute.return_value.fetchone.return_value = ("v9.0-rc3",)
        db.execute.return_value.fetchall.return_value = [
            (
                "v9.0-rc1",
                "test",
                {"objects": {"index.html": {"r2_key": "releases/v9.0-rc1/index.html"}}},
            ),
            (
                "v9.0-rc2",
                "test",
                {"objects": {"index.html": {"r2_key": "releases/v9.0-rc2/index.html"}}},
            ),
        ]
        self.assertEqual(retire_previews(db, storage, "v9.0"), ["v9.0-rc1", "v9.0-rc2"])
        self.assertEqual(
            [c.kwargs["Key"] for c in storage.delete_object.call_args_list],
            ["releases/v9.0-rc1/index.html", "releases/v9.0-rc2/index.html"],
        )
        query, parameters = db.execute.call_args_list[1].args
        self.assertEqual(parameters, ("v9.0", "v9.0-rc3"))

    def test_unpublished_versions_and_files_outside_candidate_folder_are_preserved(
        self,
    ):
        db, storage = Mock(), Mock()
        db.execute.return_value.fetchone.return_value = None
        with self.assertRaisesRegex(ValueError, "publish a final"):
            retire_previews(db, storage, "v9.0")
        db.execute.return_value.fetchone.return_value = ("v9.0-rc2",)
        db.execute.return_value.fetchall.return_value = [
            ("v9.0-rc1", "test", {"objects": {"raw": {"r2_key": "sources/raw.zip"}}})
        ]
        with self.assertRaisesRegex(ValueError, "outside its own"):
            retire_previews(db, storage, "v9.0")
        storage.delete_object.assert_not_called()

    def test_interrupted_retirement_keeps_the_manifest_for_retry(self):
        db, storage = Mock(), Mock()
        db.execute.return_value.fetchone.return_value = ("v9.0-rc2",)
        db.execute.return_value.fetchall.return_value = [
            (
                "v9.0-rc1",
                "test",
                {"objects": {"map": {"r2_key": "releases/v9.0-rc1/runs.u32le.gz"}}},
            )
        ]
        storage.delete_object.side_effect = OSError("connection lost")
        with self.assertRaises(OSError):
            retire_previews(db, storage, "v9.0")
        self.assertFalse(
            any("DELETE FROM" in c.args[0] for c in db.execute.call_args_list)
        )
