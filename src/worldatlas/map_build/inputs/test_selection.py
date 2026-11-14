import json
import os
from pathlib import Path
import tempfile
import unittest
import hashlib
from copy import deepcopy

import psycopg
from psycopg.types.json import Jsonb

from worldatlas.map_build.inputs.selection import (
    canonical_bytes,
    read_selection,
    read_saved,
    validate_bindings,
)


class BindingTests(unittest.TestCase):
    def setUp(self):
        bindings = [
            dict(code=301, entity_id=81, physical_class="land"),
            dict(code=999, entity_id=42, physical_class="land"),
            dict(code=4321, entity_id=81, physical_class="water"),
        ]
        self.selection = dict(
            schema="worldatlas-input-selection-v1",
            domains={
                name: dict(category_bindings=deepcopy(bindings))
                for name in ("mainland", "regional", "water", "ocean")
            },
        )
        self.selection["domains"]["water"].update(features=[], basins=[])

    def test_reordered_rows_and_different_registry_names_keep_the_same_meanings(self):
        for name, domain in self.selection["domains"].items():
            domain["entity_revision"] = {"id": name}
            domain["category_bindings"].reverse()
        validate_bindings(self.selection["domains"])

    def test_saved_replay_preserves_legacy_document_metadata(self):
        selected = dict(
            self.selection,
            documents=[
                dict(
                    source_id="saved-construction",
                    version="1",
                    document_text=' {"a": 1}\n',
                    sha256="a" * 64,
                    size_bytes=10,
                )
            ],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "selection.json"
            path.write_text(json.dumps(selected))
            self.assertEqual(read_saved(path), selected)

    def test_replay_rejects_swapped_entity_meanings_in_every_stage(self):
        for name in self.selection["domains"]:
            with self.subTest(stage=name), tempfile.TemporaryDirectory() as directory:
                selected = deepcopy(self.selection)
                bindings = selected["domains"][name]["category_bindings"]
                bindings[0]["entity_id"], bindings[1]["entity_id"] = (
                    bindings[1]["entity_id"],
                    bindings[0]["entity_id"],
                )
                path = Path(directory) / "selection.json"
                path.write_text(json.dumps(selected))
                with self.assertRaisesRegex(ValueError, "category bindings differ"):
                    read_saved(path)

    def test_physical_classes_and_missing_rows_are_part_of_the_mapping(self):
        for change in ("class", "missing"):
            with self.subTest(change=change):
                selected = deepcopy(self.selection)
                bindings = selected["domains"]["regional"]["category_bindings"]
                if change == "class":
                    bindings[1]["physical_class"] = "water"
                else:
                    bindings.pop()
                with self.assertRaisesRegex(ValueError, "category bindings differ"):
                    validate_bindings(selected["domains"])

    def test_duplicate_codes_or_entity_classes_cannot_hide_a_disagreement(self):
        for duplicate in (
            dict(code=301, entity_id=42, physical_class="water"),
            dict(code=123, entity_id=81, physical_class="land"),
        ):
            with self.subTest(binding=duplicate):
                selected = deepcopy(self.selection)
                selected["domains"]["regional"]["category_bindings"].append(duplicate)
                with self.assertRaisesRegex(ValueError, "duplicate category bindings"):
                    validate_bindings(selected["domains"])


@unittest.skipUnless(
    os.environ.get("WORLDATLAS_TEST_DATABASE_URL"), "requires disposable PostgreSQL"
)
class SelectionTests(unittest.TestCase):
    def setUp(self):
        from psycopg.types.json import Jsonb

        self.url = os.environ["WORLDATLAS_TEST_DATABASE_URL"]
        self.writer = psycopg.connect(self.url, autocommit=True)
        self.addCleanup(self.writer.close)
        self.addCleanup(self.remove)
        self.writer.execute(
            "INSERT INTO atlas.geographic_entity_ids(id,color_rgb) VALUES (970000001,'#123456')"
        )
        self.writer.execute(
            "INSERT INTO atlas.geographic_entities(id,name,level) VALUES (970000001,'Selected entity','continent')"
        )
        self.writer.execute(
            "INSERT INTO atlas.review_category_bindings VALUES (17,970000001,'land')"
        )
        self.writer.execute(
            "INSERT INTO atlas.source_assets(source_id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes) VALUES ('__selected_raw','Test','Test','test:source','Test','test:license','Test','test','source.geojson',%s,1)",
            ("a" * 64,),
        )
        self.geometry = {"type": "Point", "coordinates": [10.0, 20.0]}
        from worldatlas.source_imports.features.geometry import geometry_hash

        self.writer.execute(
            "INSERT INTO atlas.decision_features(feature_id,source_id,source_feature_id,geometry_sha256,evidence,geometry,coordinate_reference) VALUES ('__selected_point','__selected_raw','provider',%s,'{}',%s,'OGC:CRS84')",
            (geometry_hash(self.geometry), Jsonb(self.geometry)),
        )

    def remove(self):
        self.writer.execute(
            "DELETE FROM atlas.decision_features WHERE feature_id='__selected_point'"
        )
        self.writer.execute(
            "DELETE FROM atlas.construction_records WHERE source_id='__selected_recipe'"
        )
        self.writer.execute(
            "DELETE FROM atlas.source_assets WHERE source_id='__selected_raw'"
        )
        self.writer.execute(
            "DELETE FROM atlas.review_category_bindings WHERE entity_id=970000001"
        )
        self.writer.execute("DELETE FROM atlas.geographic_entities WHERE id=970000001")
        self.writer.execute(
            "DELETE FROM atlas.geographic_entity_ids WHERE id=970000001"
        )

    def read(self, **options):
        with psycopg.connect(self.url) as db:
            result = read_selection(db, **options)
            self.assertEqual(
                db.info.transaction_status, psycopg.pq.TransactionStatus.IDLE
            )
            return result

    def test_freezes_coordinates_catalog_bindings_and_colors(self):
        selected = self.read()
        self.assertEqual(selected["schema"], "worldatlas-input-selection-v3")
        self.assertNotIn("revisions", selected)
        self.assertEqual(
            selected["geography"]["features"][0]["geometry"], self.geometry
        )
        self.assertEqual(selected["raw_sources"][0]["sha256"], "a" * 64)
        self.assertEqual(
            selected["entity_colors"], [dict(entity_id=970000001, color_rgb="#123456")]
        )

    def test_later_working_edit_does_not_change_saved_inputs(self):
        first = self.read()
        from psycopg.types.json import Jsonb
        from worldatlas.source_imports.features.geometry import geometry_hash

        changed = {"type": "Point", "coordinates": [11.0, 21.0]}
        self.writer.execute(
            "UPDATE atlas.decision_features SET geometry=%s,geometry_sha256=%s WHERE feature_id=%s",
            (Jsonb(changed), geometry_hash(changed), "__selected_point"),
        )
        second = self.read()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "selection.json"
            path.write_bytes(canonical_bytes(first))
            restored = read_saved(path)
        self.assertEqual(
            restored["geography"]["features"][0]["geometry"], self.geometry
        )
        self.assertEqual(second["geography"]["features"][0]["geometry"], changed)

    def test_construction_edits_are_copied_into_each_build(self):
        from psycopg.types.json import Jsonb

        document = dict(
            method="osm_way_chain",
            source_id="__selected_raw",
            boundary_id="boundary",
            basis="First",
        )
        self.writer.execute(
            "INSERT INTO atlas.construction_records VALUES ('__selected_recipe',%s)",
            (Jsonb(document),),
        )
        self.writer.execute(
            "UPDATE atlas.decision_features SET construction_id='__selected_recipe' WHERE feature_id='__selected_point'"
        )
        first = self.read()
        self.writer.execute(
            "UPDATE atlas.construction_records SET document=document || '{\"basis\":\"Second\"}' WHERE source_id='__selected_recipe'"
        )
        second = self.read()
        self.assertEqual(first["construction_records"][0]["document"]["basis"], "First")
        self.assertEqual(
            second["construction_records"][0]["document"]["basis"], "Second"
        )

    def test_missing_explicit_inputs_fail(self):
        for options in (dict(raw_sources=["missing"]), dict(constructions=["missing"])):
            with (
                self.subTest(options=options),
                self.assertRaisesRegex(ValueError, "missing"),
            ):
                self.read(**options)

    def test_concurrent_edits_do_not_mix_database_snapshots(self):
        with psycopg.connect(self.url) as db:
            outer = self

            class ConcurrentEdit:
                def transaction(self):
                    return db.transaction()

                def cursor(self, **kw):
                    return db.cursor(**kw)

                def execute(self, query, params=None):
                    result = db.execute(query, params)
                    if query.startswith("SELECT to_jsonb(a)"):
                        outer.writer.execute(
                            "UPDATE atlas.geographic_entity_ids SET color_rgb='#654321' WHERE id=970000001"
                        )
                    return result

            first = read_selection(ConcurrentEdit())
        self.assertEqual(first["entity_colors"][0]["color_rgb"], "#123456")
        self.assertEqual(self.read()["entity_colors"][0]["color_rgb"], "#654321")
