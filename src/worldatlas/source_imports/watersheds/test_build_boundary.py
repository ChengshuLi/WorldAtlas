"""Run a real native-grid construction and its database writes with small sources."""
from contextlib import nullcontext
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

import numpy as np
from osgeo import gdal
from pyproj import CRS, Transformer
import shapefile

from worldatlas.source_imports.run_import import run_import
from worldatlas.source_imports.watersheds.build_boundary import construct


def fixtures(directory):
    raster = directory / 'dem.tif'
    ds = gdal.GetDriverByName('GTiff').Create(str(raster), 6, 6, 1, gdal.GDT_Float32)
    ds.SetGeoTransform((0., .001, 0., .006, 0., -.001))
    ds.SetProjection(CRS.from_epsg(4326).to_wkt())
    ds.GetRasterBand(1).WriteArray(np.tile([0, 1, 2, 2, 1, 0], (6, 1)))
    ds = None
    basin = directory / 'basins'
    with shapefile.Writer(str(basin)) as writer:
        writer.field('BASIN', 'N')
        for ident, west, east in ((41, -.01, .003), (99, .003, .02)):
            writer.poly([[(west, -.01), (west, .02), (east, .02), (east, -.01), (west, -.01)]])
            writer.record(ident)
    basin.with_suffix('.prj').write_text(CRS.from_epsg(4326).to_wkt())
    archive = directory / 'basins.zip'
    with zipfile.ZipFile(archive, 'w') as output:
        for suffix in ('.shp', '.shx', '.dbf', '.prj'):
            output.write(basin.with_suffix(suffix), 'basins' + suffix)
    geometry = directory / 'lines.geojson'
    geometry.write_text(json.dumps({'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'properties': {}, 'geometry': {'type': 'LineString',
         'coordinates': [[.001, .005], [.005, .005]]}},
        {'type': 'Feature', 'properties': {}, 'geometry': {'type': 'LineString',
         'coordinates': [[.001, .001], [.005, .001]]}},
    ]}))
    files = {'dem': raster, 'basins': archive, 'lines': geometry}
    recipe = {
        'method': 'watershed_boundary', 'boundary_id': 'test-divide', 'basis': 'Test drainage divide',
        'sources': {name: {'source_id': '__watershed_' + name} for name in files},
        'lines': {name: [{'source': 'lines', 'geojson_feature': i}]
                  for i, name in enumerate(('before', 'after'))},
        'terrains': {'ridge': {'primary': ['dem'], 'domains': [[0, 0, .006, .006]],
                    'basins': [{'source': 'basins', 'member': 'basins.shp'}],
                    'basin_attribute': 'BASIN', 'groups': {'3': [41], '100': [99]},
                    'interfaces': [[3, 100]]}},
        'sections': [{'line': 'before'}, {'divide': 'ridge'}, {'line': 'after'}],
        'joins': [{'near': [.003, .005]}, {'near': [.003, .001]}],
        'start': {'line': 'before', 'endpoint': 'start'},
        'end': {'line': 'after', 'endpoint': 'end'},
    }
    return files, recipe


class ConstructionTests(unittest.TestCase):
    def test_unresolved_river_stops_before_terrain_processing(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            river = Path(directory) / 'rivers.osm'
            river.write_text('<osm><node id="1" lon=".001" lat=".005"/>'
                             '<node id="2" lon=".002" lat=".003"/>'
                             '<node id="3" lon=".001" lat=".001"/>'
                             '<node id="4" lon=".005" lat=".001"/>'
                             '<way id="10"><nd ref="1"/><nd ref="2"/><tag k="waterway" v="stream"/></way>'
                             '<way id="20"><nd ref="2"/><nd ref="3"/><tag k="waterway" v="stream"/></way>'
                             '<way id="30"><nd ref="2"/><nd ref="4"/><tag k="waterway" v="stream"/></way></osm>')
            files['rivers'] = river
            recipe['terrains']['ridge'].update(waterways=['rivers'], waterway_groups={3: ['20']})
            with patch('worldatlas.source_imports.watersheds.build_boundary.prepare') as terrain:
                with self.assertRaisesRegex(ValueError, 'unresolved downstream route'):
                    construct(recipe, files)
                terrain.assert_not_called()

    def test_final_connector_crossing_is_rejected_by_the_pipeline(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            river = Path(directory) / 'river.osm'
            river.write_text('<osm><node id="1" lon=".002" lat=".0022"/>'
                             '<node id="2" lon=".002" lat=".0038"/>'
                             '<way id="10"><nd ref="1"/><nd ref="2"/>'
                             '<tag k="waterway" v="stream"/></way></osm>')
            files['river'] = river
            recipe['terrains']['ridge']['waterways'] = ['river']
            recipe['sections'][1].update(via=[{'point': [.001, .003]}], max_step_m=10.)
            with self.assertRaisesRegex(ValueError, 'boundary crosses natural waterway'):
                construct(recipe, files)

    def test_divide_waypoints_need_no_stored_attachment_coordinates(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            points = [[.0032, .004], [.0028, .002]]
            recipe['sections'][1].update(via=[{'point': p} for p in points], max_step_m=10.)
            geometry, report = construct(recipe, files)
            coordinates = geometry['coordinates']
            self.assertEqual(coordinates[0], [.001, .005])
            self.assertEqual(coordinates[-1], [.005, .001])
            self.assertLess(coordinates.index(points[0]), coordinates.index(points[1]))
            self.assertIn('waypoints', report['connections']['1'])

    def test_closed_sink_is_applied_only_to_domains_that_contain_it(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            expected, _ = construct(recipe, files)
            recipe['terrains']['ridge']['domains'] = [[0, .003, .006, .006], [0, 0, .006, .003]]
            recipe['terrains']['ridge']['closed_sinks'] = [
                {'point': {'point': [.001, .005]}, 'group': 3}]
            actual, _ = construct(recipe, files)
            self.assertEqual(actual, expected)

    def test_closed_sink_outside_all_domains_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            recipe['terrains']['ridge']['closed_sinks'] = [
                {'point': {'point': [.02, .02]}, 'group': 3}]
            with self.assertRaisesRegex(ValueError, 'outside every analysis domain'):
                construct(recipe, files)

    def test_boundary_can_start_and_end_on_a_selected_divide(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            recipe['sections'] = [{'divide': 'ridge'}]
            recipe['joins'] = []
            recipe['start'] = {'nearest_divide': 'ridge', 'near': {'point': [.003, .005]}}
            recipe['end'] = {'nearest_divide': 'ridge', 'near': {'point': [.003, .001]}}
            geometry, _ = construct(recipe, files)
            self.assertEqual(geometry['coordinates'][0], [.003, .005])
            self.assertEqual(geometry['coordinates'][-1], [.003, .001])

    def test_boundary_can_start_at_a_calculated_source_intersection(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            document = json.loads(files['lines'].read_text())
            document['features'].append({'type': 'Feature', 'properties': {}, 'geometry': {
                'type': 'LineString', 'coordinates': [[.001, .004], [.003, .006]]}})
            files['lines'].write_text(json.dumps(document))
            recipe['lines']['crossing'] = [{'source': 'lines', 'geojson_feature': 2}]
            recipe['start'] = {'intersection': ['before', 'crossing'], 'near': [.002, .005]}
            geometry, _ = construct(recipe, files)
            self.assertEqual(geometry['coordinates'][0], [.002, .005])

    def test_complete_native_divide_and_source_joins(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            geometry, report = construct(recipe, files)
            points = geometry['coordinates']
            self.assertEqual(points[0], [.001, .005])
            self.assertEqual(points[-1], [.005, .001])
            self.assertEqual(report['terrain']['ridge']['domains'][0]['unknown_cells'], 0)
            self.assertEqual(report['joins'], [[.003, .005], [.003, .001]])
            self.assertEqual(construct(recipe, files)[0], geometry)

    def test_explicit_output_area_keeps_the_native_construction_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            original = construct(recipe, files)[0]
            recipe['terrains']['ridge']['domains'] = [
                {'bounds': [0, 0, .006, .006], 'output_bounds': [0, 0, .006, .006]}]
            geometry, report = construct(recipe, files)
            self.assertEqual(geometry, original)
            self.assertEqual(report['terrain']['ridge']['domains'][0]['output_bounds'],
                             [0, 0, .006, .006])

    def test_projected_analysis_bounds_use_geographic_sources_and_joins(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            original = construct(recipe, files)[0]
            bounds = Transformer.from_crs(4326, 3857, always_xy=True).transform_bounds(
                .00001, .00001, .00599, .00599)
            recipe['terrains']['ridge']['domains'] = [
                {'crs': 'EPSG:3857', 'bounds': bounds, 'output_bounds': bounds}]
            geometry, report = construct(recipe, files)
            self.assertEqual(geometry, original)
            self.assertEqual(report['terrain']['ridge']['domains'][0]['bounds_crs'], 'EPSG:3857')

    def test_provider_ocean_mask_ends_the_divide_at_land_outlets(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            water = Path(directory) / 'water.tif'
            ds = gdal.GetDriverByName('GTiff').Create(str(water), 6, 6, 1, gdal.GDT_Byte)
            ds.SetGeoTransform((0., .001, 0., .006, 0., -.001))
            ds.SetProjection(CRS.from_epsg(4326).to_wkt())
            values = np.zeros((6, 6), dtype='uint8')
            values[0] = 1
            ds.GetRasterBand(1).WriteArray(values)
            ds = None
            files['water'] = water
            recipe['terrains']['ridge']['ocean_mask'] = {'sources': ['water'], 'values': [1]}
            geometry, report = construct(recipe, files)
            self.assertIn([.003, .005], geometry['coordinates'])
            self.assertEqual(report['terrain']['ridge']['domains'][0]['coast'],
                             {'ocean_cells': 6, 'land_outlet_cells': 6, 'river_basin_conflicts': 0,
                              'source_coverage': {'resolved': [], 'conflicting': [], 'unreferenced': 0}})

    def test_basin_coverage_gap_at_the_shore_does_not_cut_the_continuous_divide(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            files, recipe = fixtures(directory)
            ds = gdal.Open(str(files['dem']), gdal.GA_Update)
            ds.GetRasterBand(1).WriteArray(np.tile([0, 1, 2, 2, 1, 0], (6, 1)) +
                                         np.arange(6)[:, None] * 10)
            ds = None
            with shapefile.Writer(str(directory / 'basins')) as writer:
                writer.field('BASIN', 'N')
                for ident, west, east in ((41, -.01, .003), (99, .003, .02)):
                    writer.poly([[(west, -.01), (west, .004), (east, .004),
                                  (east, -.01), (west, -.01)]])
                    writer.record(ident)
            with zipfile.ZipFile(files['basins'], 'w') as output:
                for suffix in ('.shp', '.shx', '.dbf', '.prj'):
                    output.write(directory / ('basins' + suffix), 'basins' + suffix)
            files['water'] = directory / 'water.tif'
            ds = gdal.GetDriverByName('GTiff').Create(str(files['water']), 6, 6, 1, gdal.GDT_Byte)
            ds.SetGeoTransform((0., .001, 0., .006, 0., -.001))
            ds.SetProjection(CRS.from_epsg(4326).to_wkt())
            water = np.zeros((6, 6), dtype='uint8')
            water[0] = 1
            ds.GetRasterBand(1).WriteArray(water)
            ds = None
            recipe['terrains']['ridge']['ocean_mask'] = {'sources': ['water'], 'values': [1]}
            geometry, report = construct(recipe, files)
            self.assertIn([.003, .005], geometry['coordinates'])
            coverage = report['terrain']['ridge']['domains'][0]['coast']['source_coverage']
            self.assertEqual({item['group'] for item in coverage['resolved']}, {3, 100})
            self.assertEqual(coverage['conflicting'], [])


@unittest.skipUnless(
    os.environ.get("WORLDATLAS_TEST_DATABASE_URL"), "requires disposable PostgreSQL"
)
class StorageTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg.types.json import Jsonb

        self.db = psycopg.connect(os.environ["WORLDATLAS_TEST_DATABASE_URL"])
        self.addCleanup(self.db.close)
        self.addCleanup(self.db.rollback)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.files, self.recipe = fixtures(self.directory)
        for value in self.recipe["sources"].values():
            value.pop("version", None)
        self.data = {path.name: path.read_bytes() for path in self.files.values()}
        for name, path in self.files.items():
            raw = path.read_bytes()
            self.db.execute(
                "INSERT INTO atlas.source_assets(source_id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes) VALUES (%s,'Test','Test','test:input','Test','test:license','Test','test',%s,%s,%s)",
                (
                    "__watershed_" + name,
                    path.name,
                    hashlib.sha256(raw).hexdigest(),
                    len(raw),
                ),
            )
        self.store()
        self.client = Mock()
        self.client.get_object.side_effect = lambda **kw: {
            "Body": io.BytesIO(self.data[kw["Key"]])
        }

    def store(self):
        from psycopg.types.json import Jsonb

        self.db.execute(
            "INSERT INTO atlas.construction_records VALUES ('watershed',%s) ON CONFLICT(source_id) DO UPDATE SET document=EXCLUDED.document",
            (Jsonb(self.recipe),),
        )

    def build(self):
        return run_import(
            lambda: nullcontext(self.db),
            "watershed",
            storage=self.client,
            work_dir=self.directory / "cache",
        )

    def row(self):
        return self.db.execute(
            "SELECT geometry,geometry_sha256,provenance,construction_id FROM atlas.decision_mainland_boundaries"
        ).fetchone()

    def test_repeat_and_edit_recipe_preserve_geometry_notes_and_sources(self):
        result = self.build()
        self.assertEqual(self.build()["sha256"], result["sha256"])
        self.db.execute(
            'UPDATE atlas.decision_mainland_boundaries SET provenance=provenance || \'{"note":"keep"}\''
        )
        self.recipe["basis"] = "Updated explanation"
        self.store()
        self.build()
        self.assertEqual(self.row()[2]["note"], "keep")
        self.assertEqual(self.row()[3], "watershed")
        links = {
            r[0]
            for r in self.db.execute(
                "SELECT source_id FROM atlas.decision_mainland_boundary_sources"
            )
        }
        self.assertEqual(
            links, {v["source_id"] for v in self.recipe["sources"].values()}
        )

    def test_calculation_failure_leaves_geometry_and_links_unchanged(self):
        self.build()
        before = self.row()
        links = self.db.execute(
            "SELECT * FROM atlas.decision_mainland_boundary_sources ORDER BY source_id"
        ).fetchall()
        self.recipe["joins"] = [{"near": [5, 5]}]
        self.store()
        with self.assertRaises(ValueError):
            self.build()
        self.assertEqual(self.row(), before)
        self.assertEqual(
            self.db.execute(
                "SELECT * FROM atlas.decision_mainland_boundary_sources ORDER BY source_id"
            ).fetchall(),
            links,
        )
