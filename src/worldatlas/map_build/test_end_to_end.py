"""Small raw-source → imported records → physical grid → final map fixture."""

import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import psycopg
from psycopg.types.json import Jsonb
import pyarrow as pa
import pyarrow.parquet as pq
from osgeo import ogr

from worldatlas.source_imports.run_import import run_import
from worldatlas.map_build.build import Pipeline, pin, write
from worldatlas.map_build.inputs.selection import read_selection, canonical_bytes


@unittest.skipUnless(
    os.environ.get("WORLDATLAS_TEST_DATABASE_URL"), "requires disposable PostgreSQL"
)
class EndToEndTests(unittest.TestCase):
    def test_raw_inputs_import_division_package_and_trusted_resume(self):
        url = os.environ["WORLDATLAS_TEST_DATABASE_URL"]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            raw = root / "raw"
            raw.mkdir()
            grid = dict(width=16, height=8, step=22.5)
            features = []
            for ident, (west, south, east, north), point in (
                ("first", (-112.5, 0, -67.5, 22.5), [-90, 11.25]),
                ("second", (45, 0, 90, 22.5), [60, 11.25]),
            ):
                features.extend(
                    [
                        dict(
                            type="Feature",
                            properties=dict(id=ident, kind="land"),
                            geometry=dict(
                                type="Polygon",
                                coordinates=[
                                    [
                                        [west, south],
                                        [east, south],
                                        [east, north],
                                        [west, north],
                                        [west, south],
                                    ]
                                ],
                            ),
                        ),
                        dict(
                            type="Feature",
                            properties=dict(id=ident + "-point", kind="point"),
                            geometry=dict(type="Point", coordinates=point),
                        ),
                    ]
                )
            coast = write(
                raw / "coast.geojson", dict(type="FeatureCollection", features=features)
            )
            lake = bytes(
                ogr.CreateGeometryFromWkt(
                    "POLYGON ((0 80,5 80,5 85,0 85,0 80))"
                ).ExportToWkb()
            )
            table = pa.Table.from_pylist(
                [
                    dict(
                        id="lake",
                        subtype="lake",
                        **{"class": "lake"},
                        sources=[dict(property="", dataset="OpenStreetMap")],
                        geometry=lake,
                    )
                ]
            )
            table = table.replace_schema_metadata(
                {
                    b"geo": json.dumps(
                        dict(
                            primary_column="geometry",
                            columns=dict(geometry=dict(encoding="WKB")),
                        )
                    ).encode()
                }
            )
            shard = raw / "water.parquet"
            pq.write_table(table, shard)
            manifest = write(
                raw / "manifest.json",
                dict(
                    file_count=1,
                    files=[dict(path=shard.name, sha256=pin(shard)["sha256"])],
                ),
            )
            with psycopg.connect(url) as db:
                db.execute(
                    "INSERT INTO atlas.geographic_levels VALUES ('world',NULL),('continent','world')"
                )
                db.execute(
                    "INSERT INTO atlas.geographic_entities(id,name,level_id,parent_id,physical_class,color_rgb) VALUES (0,'World','world',NULL,'mixed',NULL),(81,'First','continent',0,'mixed','#FF8000'),(42,'Second','continent',0,'mixed','#0080FF')"
                )
                db.execute(
                    "INSERT INTO atlas.map_category_bindings VALUES (301,81,'land'),(999,42,'land'),(4321,81,'water'),(70000,42,'water')"
                )
                db.execute(
                    "INSERT INTO atlas.source_assets(id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes) VALUES ('__e2e_raw','Fixture','Fixture','test:raw','Test','test:license','Test','test','coast.geojson',%s,%s)",
                    (
                        hashlib.sha256(coast.read_bytes()).hexdigest(),
                        coast.stat().st_size,
                    ),
                )
                recipe = dict(
                    source_id="__e2e_raw",
                    basis="Selected point records",
                    id_field="id",
                    selections=[
                        dict(
                            feature_id="__e2e_" + ident,
                            source_feature_id=ident + "-point",
                        )
                        for ident in ("first", "second")
                    ],
                )
                db.execute(
                    "INSERT INTO atlas.construction_records(id,method,arguments) "
                    "VALUES ('__e2e_import','selected_vector_features',%s)",
                    (Jsonb(recipe),),
                )
            try:
                storage = Mock()
                storage.get_object.side_effect = lambda **kw: dict(
                    Body=io.BytesIO(coast.read_bytes())
                )
                run_import(
                    lambda: psycopg.connect(url),
                    "__e2e_import",
                    storage=storage,
                    work_dir=root / "inputs",
                )
                with psycopg.connect(url) as db:
                    for ident, entity in (("first", 81), ("second", 42)):
                        db.execute(
                            "INSERT INTO atlas.geographic_rules VALUES (%s,0,'assign_area','land','component',false,'Selected component')",
                            ("__e2e_" + ident,),
                        )
                        db.execute(
                            "INSERT INTO atlas.geographic_rule_features VALUES (%s,%s,'scope_component')",
                            ("__e2e_" + ident, "__e2e_" + ident),
                        )
                        db.execute(
                            "INSERT INTO atlas.geographic_rule_targets VALUES (%s,%s,%s,NULL)",
                            ("__e2e_target_" + ident, "__e2e_" + ident, entity),
                        )
                    db.execute(
                        "INSERT INTO atlas.geographic_rules VALUES ('__e2e_coast',0,'nearest_coastal_water','water','cell',false,'Shared coast'),('__e2e_water',0,'nearest_water','water','cell',true,'Complete water')"
                    )
                with psycopg.connect(url) as db:
                    frozen = read_selection(db)
                selected = raw / "selection.json"
                selected.write_bytes(canonical_bytes(frozen))
                land_config = write(
                    raw / "land.json",
                    dict(
                        schema="land-raster-candidate-v1",
                        selection_notes="Fixture coast",
                        grid=grid,
                        strip_rows=4,
                        minimum_free_bytes=0,
                        feature_index="row-fids",
                        land=[
                            dict(
                                dataset=str(coast),
                                layer=None,
                                where="kind = 'land'",
                                files=[
                                    dict(pin(coast), size_bytes=coast.stat().st_size)
                                ],
                            )
                        ],
                    ),
                )
                water_config = write(
                    raw / "water.json",
                    dict(
                        schema="water-shard-candidate-v2",
                        selection_notes="Fixture water",
                        grid=grid,
                        tile_size=4,
                        minimum_free_bytes=0,
                        policy=dict(method="overture-inland-subtype-v1"),
                    ),
                )
                cfg = write(
                    raw / "build.json",
                    dict(
                        schema="worldatlas-end-to-end-pipeline-v2",
                        selection_notes="Input-contract fixture",
                        grid=grid,
                        coastal_band_metres=22224,
                        physical_controls=dict(
                            minimum_free_bytes=0, max_parallel_shards=1
                        ),
                        sources=dict(
                            land_config=pin(land_config),
                            water_config=pin(water_config),
                            raw_manifest=pin(manifest),
                        ),
                    ),
                )
                runner = Pipeline(cfg, root / "run", work_dir=root, selection=selected)
                report = runner.run()
                self.assertEqual(report["status"], "complete")
                self.assertTrue(
                    all(r["outputs_complete"] for r in report["stages"].values())
                )
                counts = json.loads(
                    Path(report["final"]["report"]["path"]).read_text()
                )["counts"]
                self.assertEqual(sum(counts.values()), 128)
                self.assertEqual(set(counts), {"301", "999", "4321", "70000"})
                self.assertEqual(counts["301"], 2)
                self.assertEqual(counts["999"], 2)
                resumed = Pipeline(
                    cfg, root / "run", work_dir=root, selection=selected, resume=True
                )
                self.assertEqual(resumed.run(), report)
                reused = Pipeline(
                    cfg,
                    root / "reused",
                    work_dir=root,
                    selection=selected,
                    reuse_from=root / "run",
                )
                new = reused.run()
                self.assertEqual(
                    new["final"]["runs"]["sha256"], report["final"]["runs"]["sha256"]
                )
                division = json.loads(
                    (root / "reused/division/report.json").read_text()
                )
                self.assertTrue(division["parents"]["0"]["reused"])
            finally:
                with psycopg.connect(url) as db:
                    db.execute(
                        "DELETE FROM atlas.geographic_rules WHERE id LIKE '__e2e_%'"
                    )
                    db.execute(
                        "DELETE FROM atlas.source_features WHERE construction_id='__e2e_import'"
                    )
                    db.execute(
                        "DELETE FROM atlas.construction_records WHERE id='__e2e_import'"
                    )
                    db.execute("DELETE FROM atlas.source_assets WHERE id='__e2e_raw'")
                    db.execute(
                        "DELETE FROM atlas.map_category_bindings WHERE entity_id IN (81,42)"
                    )
                    db.execute(
                        "DELETE FROM atlas.geographic_entities WHERE id IN (0,81,42)"
                    )
                    db.execute(
                        "DELETE FROM atlas.geographic_levels WHERE id IN ('world','continent')"
                    )
