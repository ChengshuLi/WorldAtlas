"""Small raw-source → imported records → physical grid → final map fixture."""

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np
import psycopg
from psycopg.types.json import Jsonb
import pyarrow as pa
import pyarrow.parquet as pq
from osgeo import ogr

from worldatlas.source_imports.run_import import run_import
from worldatlas.map_build import compare as comparison_command
from worldatlas.map_build.build import Pipeline, physical_reference
from worldatlas.map_build.division import engine
from worldatlas.map_build.inputs import selection as selection_inputs
from worldatlas.map_build.inputs.selection import read_selection
from worldatlas.map_build.physical.build import run as build_physical
from worldatlas.shared.files import compact_json_bytes, pin_file, read_json, sha256_file, write_json


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
                ("island", (-90, -45, -67.5, -22.5), [-78.75, -33.75]),
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
            coast = write_json(
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
            inputs = root / "inputs"
            inputs.mkdir()
            shard = inputs / "water.parquet"
            pq.write_table(table, shard)
            with psycopg.connect(url) as db:
                db.execute(
                    "INSERT INTO atlas.geographic_levels VALUES ('world',NULL),('continent','world')"
                )
                db.execute(
                    "INSERT INTO atlas.geographic_entities(id,name,level_id,parent_id,physical_class,color_rgb) VALUES (0,'World','world',NULL,'mixed',NULL),(81,'First','continent',0,'mixed','#FF8000'),(42,'Second','continent',0,'mixed','#0080FF')"
                )
                db.execute(
                    "UPDATE atlas.map_category_bindings b SET id=fixture.code "
                    "FROM (VALUES (301,81,'land'),(999,42,'land'),(4321,81,'water'),(70000,42,'water')) "
                    "AS fixture(code,entity_id,physical_class) "
                    "WHERE (b.entity_id,b.physical_class)=(fixture.entity_id,fixture.physical_class)"
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
                    "INSERT INTO atlas.construction_records(id,method,arguments,basis) "
                    "VALUES ('__e2e_import','selected_vector_features',%s,'Selected point records')",
                    (Jsonb(recipe),),
                )
            try:
                storage = Mock()
                storage.get_object.side_effect = lambda **kw: dict(
                    Body=io.BytesIO(coast.read_bytes())
                )
                with patch("boto3.client", return_value=storage):
                    run_import(
                        lambda: psycopg.connect(url),
                        "__e2e_import",
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
                        "INSERT INTO atlas.geographic_rules VALUES "
                        "('__e2e_coast',0,'nearest_coastal_water','water','cell',false,'Shared coast'),"
                        "('__e2e_water',0,'nearest_water','water','cell',true,'Complete water'),"
                        "('__e2e_island',0,'nearest_land','land','component',true,'Nearest mainland shore')"
                    )
                    db.execute(
                        "INSERT INTO atlas.geographic_rule_features VALUES "
                        "('__e2e_island','__e2e_first','distance_reference'),"
                        "('__e2e_island','__e2e_second','distance_reference')"
                    )
                with psycopg.connect(url) as db:
                    frozen = read_selection(db)
                selected = raw / "selection.json"
                selected.write_bytes(compact_json_bytes(frozen))
                land_config = dict(
                    schema="land-raster-candidate-v1",
                    selection_notes="Fixture coast",
                    strip_rows=4,
                    feature_index="row-fids",
                    land=[
                        dict(
                            dataset=str(coast),
                            layer=None,
                            where="kind = 'land'",
                            files=[
                                dict(pin_file(coast), size_bytes=coast.stat().st_size)
                            ],
                        )
                    ],
                )
                water_config = dict(
                    schema="water-shard-candidate-v2",
                    selection_notes="Fixture water",
                    tile_size=4,
                    policy=dict(method="overture-inland-subtype-v1"),
                )
                cfg = write_json(
                    raw / "build.json",
                    dict(
                        schema="worldatlas-end-to-end-pipeline-v3",
                        selection_notes="Input-contract fixture",
                        grid=grid,
                        coastal_band_metres=22224,
                        division_workers=1,
                        physical_controls=dict(
                            minimum_free_bytes=0, max_parallel_shards=1
                        ),
                        sources=dict(
                            land_config=land_config,
                            inland_water=dict(
                                **water_config,
                                file_count=1,
                                files=[
                                    dict(
                                        path=shard.name,
                                        sha256=pin_file(shard)["sha256"],
                                    )
                                ],
                            ),
                        ),
                    ),
                )
                without_band = json.loads(cfg.read_text())
                del without_band["coastal_band_metres"]
                incomplete_config = write_json(raw / "without-band.json", without_band)
                with self.assertRaisesRegex(ValueError, "requires coastal_band_metres"):
                    Pipeline(incomplete_config, root / "invalid", work_dir=root, selection=selected)
                runner = Pipeline(cfg, root / "run", work_dir=root, selection=selected)
                execute_rule = engine.execute_rule
                started_rules = []

                def interrupt(context, rule, snapshot, directory):
                    started_rules.append(rule["id"])
                    runner.cancel()
                    return execute_rule(context, rule, snapshot, directory)

                with patch.object(engine, "execute_rule", new=interrupt):
                    with self.assertRaisesRegex(InterruptedError, "pipeline cancelled"):
                        runner.run()
                self.assertEqual(len(started_rules), 1)
                checkpoint_dir = root / "run/checkpoints"
                physical_receipts = {
                    path: path.read_bytes()
                    for path in checkpoint_dir.glob("physical-*/complete.json")
                }
                self.assertEqual(
                    {path.parent.name for path in physical_receipts},
                    {"physical-land", "physical-shard-00000", "physical-union",
                     "physical-compose", "physical-report"},
                )
                errors = list((root / "run/checkpoints").glob("*/attempt-*/error.log"))
                self.assertTrue(
                    any("InterruptedError" in path.read_text() for path in errors)
                )
                self.assertFalse((root / "run/logs").exists())
                compile_rule = selection_inputs.RuleIndex.compile
                with patch.object(
                    selection_inputs.RuleIndex, "compile", autospec=True, side_effect=compile_rule
                ) as compile_parent:
                    runner = Pipeline(cfg, root / "run", work_dir=root, resume=True)
                    report = runner.run()
                self.assertEqual(
                    {path: path.read_bytes() for path in physical_receipts},
                    physical_receipts,
                )
                self.assertEqual(
                    list((root / "run").rglob("timing-events.jsonl")),
                    [root / "run/timing-events.jsonl"],
                )
                compile_parent.assert_called_once()
                self.assertEqual(compile_parent.call_args.args[1], 0)
                self.assertEqual(report["status"], "complete")
                self.assertTrue(
                    all(r["outputs_complete"] for r in report["stages"].values())
                )
                counts = json.loads(
                    Path(report["final"]["report"]["path"]).read_text()
                )["counts"]
                self.assertEqual(sum(counts.values()), 128)
                self.assertEqual(set(counts), {"301", "999", "4321", "70000"})
                self.assertEqual(counts["301"], 3)
                self.assertEqual(counts["999"], 2)
                resumed = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "worldatlas.map_build.build",
                        str(cfg),
                        str(root / "run"),
                        "--work-dir",
                        str(root),
                        "--resume",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(json.loads(resumed.stdout), report)
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

                standalone = root / "standalone-physical"
                standalone.mkdir()
                physical = build_physical(
                    root / "run/physical-build-config.json", standalone / "physical"
                )
                self.assertEqual(
                    physical["physical_output_sha256"],
                    read_json(root / "run/physical/report.json")["physical_output_sha256"],
                )
                result = Pipeline(
                    cfg,
                    root / "reuse-standalone",
                    work_dir=root,
                    selection=selected,
                    reuse_from=standalone,
                ).run()
                self.assertEqual(
                    result["final"]["runs"]["sha256"], report["final"]["runs"]["sha256"]
                )

                interrupted = Pipeline(
                    cfg,
                    root / "continued",
                    work_dir=root,
                    selection=selected,
                    divide=[0],
                    reuse_from=root / "reused",
                )
                interrupted.close()
                resumed = Pipeline(cfg, root / "continued", work_dir=root, resume=True)
                self.assertEqual(resumed.requested_parents, [0])
                self.assertEqual(resumed.reuse_from, (root / "reused").resolve())
                self.assertEqual(
                    resumed.physical_reuse["source_run"], str((root / "run").resolve())
                )
                self.assertEqual(
                    resumed.run()["final"]["runs"]["sha256"],
                    report["final"]["runs"]["sha256"],
                )
                for flags in (
                    {"divide": [0]},
                    {"reuse_from": root / "reused"},
                    {"recompute_division": True},
                ):
                    with (
                        self.subTest(flags=flags),
                        self.assertRaisesRegex(
                            ValueError, "--resume uses saved options"
                        ),
                    ):
                        Pipeline(
                            cfg, root / "continued", work_dir=root, resume=True, **flags
                        )

                reference = Path(report["final"]["rows"]["path"]).parent
                release_folder = raw / "comparison-release"
                release_folder.mkdir()
                release_rows = release_folder / "rows.u32le"
                release_runs = release_folder / "runs.u32le"
                release_rows.write_bytes((reference / "rows.u32le").read_bytes())
                runs = np.fromfile(reference / "runs.u32le", dtype="<u4").reshape(-1, 2)
                runs[:, 1] += 100
                runs.tofile(release_runs)
                release_config = write_json(
                    release_folder / "config.json",
                    {
                        **grid,
                        "categories": [
                            dict(
                                id=binding["code"] + 100,
                                entity_id=binding["entity_id"],
                                physical_class=binding["physical_class"],
                            )
                            for binding in frozen["geography"]["category_bindings"]
                        ],
                    },
                )
                comparison_pins = {
                    "reference_rows": pin_file(release_rows),
                    "reference_runs": pin_file(release_runs),
                    "reference_config": release_config,
                }
                physical_only = Pipeline(
                    cfg,
                    root / "physical-only",
                    work_dir=root,
                    selection=selected,
                    reuse_from=root / "reused",
                    recompute_division=True,
                )
                physical_only.close()
                resumed = Pipeline(
                    cfg, root / "physical-only", work_dir=root, resume=True
                )
                self.assertTrue(resumed.recompute_division)
                result = resumed.run()
                self.assertEqual(result["physical_outputs"], report["physical_outputs"])
                division = json.loads(
                    (root / "physical-only/division/report.json").read_text()
                )
                self.assertFalse(division["parents"]["0"]["reused"])
                self.assertFalse(division["parents"]["0"]["land"]["reused"])
                run_path = root / "physical-only"
                report_pin = pin_file(run_path / "report.json")
                comparison_path = root / "comparison"
                with patch.object(
                    comparison_command,
                    "cache_release_reference",
                    return_value=comparison_pins,
                ):
                    compared = comparison_command.compare_release(
                        run_path, "v9.0", comparison_path, work_dir=root
                    )
                self.assertEqual(compared["compared_by"], "entity_and_physical_class")
                self.assertEqual(compared["changed_cells"], 0)
                self.assertEqual(read_json(comparison_path / "report.json"), compared)
                self.assertFalse((run_path / "comparison").exists())
                self.assertEqual(pin_file(run_path / "report.json"), report_pin)

                changed = Pipeline(
                    cfg,
                    root / "changed-config",
                    work_dir=root,
                    selection=selected,
                    reuse_from=root / "run",
                )
                original_config = cfg.read_bytes()
                cfg.write_bytes(original_config + b"\n")
                changed_report = changed.run()
                self.assertEqual(
                    changed_report["request"]["sha256"],
                    sha256_file(changed.out / "build-config.json"),
                )
                self.assertEqual(
                    (changed.out / "build-config.json").read_bytes(), original_config
                )
                cfg.write_bytes(original_config)

                changed_snapshot = Pipeline(
                    cfg,
                    root / "changed-snapshot",
                    work_dir=root,
                    selection=selected,
                    reuse_from=root / "run",
                )
                snapshot = changed_snapshot.out / "build-config.json"
                snapshot.write_bytes(snapshot.read_bytes() + b"\n")
                with self.assertRaisesRegex(
                    ValueError, "saved build configuration changed during pipeline"
                ):
                    changed_snapshot.run()
                self.assertFalse((changed_snapshot.out / "report.json").exists())

                unknown_stage = Pipeline(
                    cfg,
                    root / "unknown-stage",
                    work_dir=root,
                    selection=selected,
                    reuse_from=root / "run",
                )
                with unknown_stage.timing.measure("unexpected", "unfinished stage"):
                    pass
                with self.assertRaisesRegex(
                    ValueError, "all stage outputs must be complete"
                ):
                    unknown_stage.run()
                self.assertFalse((unknown_stage.out / "report.json").exists())

                physical_report = root / "run/physical/report.json"
                original = physical_report.read_bytes()
                physical_report.write_text(
                    json.dumps(dict(json.loads(original), status="incomplete"))
                )
                with self.assertRaisesRegex(
                    ValueError, "physical source run is incomplete"
                ):
                    physical_reference(root / "run", runner.physical_config)
                physical_report.write_bytes(original)
                (root / "run/physical/configs/land.json").unlink()
                self.assertEqual(
                    physical_reference(root / "run", runner.physical_config)["status"],
                    "reused",
                )
                settings = root / "run/physical-build-config.json"
                settings.write_bytes(settings.read_bytes() + b"\n")
                with self.assertRaisesRegex(
                    ValueError, "physical source configuration changed"
                ):
                    physical_reference(root / "run", runner.physical_config)
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
                        "DELETE FROM atlas.geographic_entities WHERE id IN (0,81,42)"
                    )
                    db.execute(
                        "DELETE FROM atlas.geographic_levels WHERE id IN ('world','continent')"
                    )
