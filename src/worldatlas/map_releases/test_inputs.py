"""Check that archived map inputs can be restored and used on another machine."""

import gzip
import json
from pathlib import Path
import tempfile
import unittest

from worldatlas.map_releases.inputs import SCHEMA, read_inputs, restore_inputs, validate_replay_sources, write_inputs


class ReplaySourcesTests(unittest.TestCase):
    """Distinguish portable physical inputs from files tied to the build cache."""

    def setUp(self):
        """Prepare an inline request with a cataloged coastline and water shard."""
        self.shape = {"archive": {"r2_source": "coast"}, "member": "shore.shp"}
        self.shard = {"path": "shard.parquet", "r2_source": "inland"}
        self.sources = {
            "land_config": {"land": [{"dataset": "shore.shp", "files": [self.shape]}]},
            "inland_water": {"files": [self.shard]},
        }
        self.configuration = dict(sources=self.sources)
        self.selection = {"raw_sources": [{"source_id": "coast"}, {"source_id": "inland"}]}

    def test_inline_documents_resolve_catalog_references_and_archive_members(self):
        validate_replay_sources(self.configuration, self.selection)

    def test_local_only_raw_inputs_are_rejected(self):
        land = self.sources["land_config"]["land"][0]
        water = self.sources["inland_water"]
        local = {"path": "/other-machine/file", "sha256": "a" * 64}
        for settings, key, value, field in (
            (land, "files", [local], r"land_config\.land\[0\]\.files\[0\]"),
            (land, "files", [dict(self.shape, archive=local["path"])],
             r"land_config\.land\[0\]\.files\[0\]"),
            (water, "files", [local], r"inland_water\.files\[0\]"),
        ):
            with self.subTest(field=field):
                original = settings[key]
                settings[key] = value
                with self.assertRaisesRegex(ValueError, field):
                    validate_replay_sources(self.configuration, self.selection)
                settings[key] = original
        self.assertEqual(water["files"], [self.shard])

    def test_dataset_must_name_one_pinned_file(self):
        land = self.sources["land_config"]["land"][0]
        for dataset, files in (("missing.shp", [self.shape]), ("shore.shp", [self.shape] * 2)):
            with self.subTest(dataset=dataset):
                land.update(dataset=dataset, files=files)
                with self.assertRaisesRegex(ValueError, "must name exactly one entry in files"):
                    validate_replay_sources(self.configuration, self.selection)

    def test_direct_water_shard_pin_requires_a_byte_size(self):
        self.sources["inland_water"]["files"] = [dict(
            path="old.parquet", r2_bucket="test", r2_key="sources/old.parquet", sha256="a" * 64,
        )]
        with self.assertRaisesRegex(ValueError, "requires an R2 object and byte size"):
            validate_replay_sources(self.configuration, self.selection)

    def test_water_file_requires_its_catalog_entry(self):
        self.selection["raw_sources"].pop()
        with self.assertRaisesRegex(ValueError, r"requires an R2 pin for inland_water\.files\[0\]"):
            validate_replay_sources(self.configuration, self.selection)


class ReplayConfiguration(unittest.TestCase):
    """Verify which archived values are copied or adjusted during extraction."""

    def test_comparison_paths_are_omitted_without_changing_captured_values(self):
        configuration = dict(
            sources=dict(
                land_config={"json": {"source": "coast"}},
                reference_rows={"path": "/old-machine/rows.u32le"},
                reference_runs={"path": "/old-machine/runs.u32le"},
            )
        )
        captured = dict(
            configuration=configuration, selection={"coordinates": [1.5, 2.5]}
        )
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "restored"
            restore_inputs(captured, output)
            restored = json.loads((output / "configuration.json").read_text())
            self.assertEqual(
                restored["sources"],
                {"land_config": configuration["sources"]["land_config"]},
            )
            self.assertEqual(
                json.loads((output / "selection.json").read_text()),
                captured["selection"],
            )
        self.assertIn("reference_rows", configuration["sources"])
        self.assertIn("reference_runs", configuration["sources"])

    def test_archive_can_include_optional_historical_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "inputs.json.gz"
            metadata = {"producer": "historical backfill"}
            write_inputs(path, release_id="v8.0", configuration=None, selection=None,
                         run=None, report=None, metadata=metadata)
            content = read_inputs(path.read_bytes(), "v8.0")
            self.assertEqual(content["metadata"], metadata)
            bad_schema = gzip.compress(json.dumps(dict(content, schema=SCHEMA + "-unknown")).encode())
            with self.assertRaisesRegex(ValueError, "different format"):
                read_inputs(bad_schema, "v8.0")

    def test_invalid_code_identity_fails_before_creating_the_output_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "restored"
            for identity in ("short", "!" * 64):
                with self.subTest(identity=identity), self.assertRaisesRegex(ValueError, "invalid source archive identity"):
                    restore_inputs({"source_code": {identity: {}}}, output)
                self.assertFalse(output.exists())
