"""Check portability and validation of the current release input archive."""

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from worldatlas.map_releases.inputs import (
    SCHEMA,
    read_inputs,
    restore_inputs,
    validate_replay_sources,
)


class ReplaySourcesTests(unittest.TestCase):
    """Check the inputs that must be available on a fresh machine."""

    def setUp(self):
        self.land = {
            "dataset": "shore.shp",
            "files": [
                {
                    "archive": {"r2_source": "coast"},
                    "member": "shore.shp",
                    "size_bytes": 12,
                    "sha256": "a" * 64,
                }
            ],
        }
        self.water = {
            "file_count": 1,
            "files": [
                {
                    "r2_bucket": "test",
                    "r2_key": "sources/water.parquet",
                    "size_bytes": 50,
                    "sha256": "b" * 64,
                }
            ],
        }
        self.configuration = {
            "sources": {"land_config": {"land": [self.land]}, "inland_water": self.water}
        }
        self.selection = {"raw_sources": [{"source_id": "coast"}]}

    def test_cataloged_zip_and_direct_water_pin_are_portable(self):
        validate_replay_sources(self.configuration, self.selection)

    def test_saved_build_with_a_local_raw_file_is_not_replayable(self):
        self.water["files"] = [{"path": "/old-machine/water.parquet", "sha256": "a" * 64}]
        with self.assertRaisesRegex(ValueError, "r2_bucket"):
            validate_replay_sources(self.configuration, self.selection)

    def test_a_cataloged_zip_requires_a_saved_source_row(self):
        self.selection["raw_sources"].clear()
        with self.assertRaisesRegex(ValueError, "missing catalog source 'coast'"):
            validate_replay_sources(self.configuration, self.selection)


class ReplayArchiveTests(unittest.TestCase):
    """Check that extraction requires a complete, current archive."""

    def test_reader_rejects_incomplete_or_unsupported_archives(self):
        current = dict(
            schema=SCHEMA,
            release_id="v8.4-rc.1",
            configuration={},
            selection={},
            run={},
            report={},
            source_code={"a" * 64: {}},
        )
        for content, message in (
            ([], "different format"),
            (dict(current, schema="unknown"), "different format"),
            (dict(current, relocations={}), "complete build"),
            (dict(current, selection=None), "complete build"),
            (dict(current, source_code={}), "captured code"),
        ):
            with self.subTest(content=content), self.assertRaisesRegex(ValueError, message):
                read_inputs(gzip.compress(json.dumps(content).encode()), "v8.4-rc.1")

    def test_invalid_code_identity_fails_before_creating_the_output_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "restored"
            with self.assertRaisesRegex(ValueError, "invalid source archive identity"):
                restore_inputs({"source_code": {"../outside": {}}}, output)
            self.assertFalse(output.exists())
