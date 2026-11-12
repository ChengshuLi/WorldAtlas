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

from watersheds.build_boundary import build_boundary, construct


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
        'sources': {name: {'source_id': '__watershed_' + name, 'version': '1'} for name in files},
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


@unittest.skipUnless(os.environ.get('WORLDATLAS_TEST_DATABASE_URL'), 'requires disposable PostgreSQL')
class StorageTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        self.db = psycopg.connect(os.environ['WORLDATLAS_TEST_DATABASE_URL'])
        self.addCleanup(self.db.close)
        self.addCleanup(self.db.rollback)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.files, self.recipe = fixtures(self.directory)
        self.db.execute("INSERT INTO atlas.entity_registry_revisions VALUES ('__watershed_entities')")
        self.db.execute("INSERT INTO atlas.decision_revisions VALUES ('__watershed', '__watershed_entities', '{}')")
        self.data = {path.name: path.read_bytes() for path in self.files.values()}
        for name, path in self.files.items():
            raw = path.read_bytes()
            self.db.execute(
                "INSERT INTO atlas.source_assets (source_id,version,title,kind,provider,source_uri,"
                "license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes,provenance) "
                "VALUES (%s,'1','Test','raw','Test','test:input','Test','test:license','Test','test',"
                "%s,%s,%s,'{\"origin\":\"test:input\",\"representation\":\"provider_original\"}')",
                ('__watershed_' + name, path.name, hashlib.sha256(raw).hexdigest(), len(raw)))
        self.store_recipe('1', self.recipe)
        self.client = Mock()
        self.client.get_object.side_effect = lambda **kw: {'Body': io.BytesIO(self.data[kw['Key']])}

    def store_recipe(self, version, recipe):
        text = json.dumps(recipe, sort_keys=True, separators=(',', ':'))
        self.db.execute('INSERT INTO atlas.structured_documents VALUES (%s,%s,%s,%s,%s::json)',
                        ('__watershed_recipe', version, hashlib.sha256(text.encode()).hexdigest(),
                         len(text.encode()), text))

    def build(self, version='1'):
        return build_boundary(lambda: nullcontext(self.db), self.client, '__watershed_recipe', version,
                              '__watershed', self.directory / 'cache')

    def row(self):
        return self.db.execute('SELECT geometry,geometry_sha256,provenance '
                               'FROM atlas.decision_mainland_boundaries WHERE revision=%s',
                               ('__watershed',)).fetchone()

    def test_database_connections_close_during_calculation(self):
        import psycopg

        self.db.commit()

        def remove_committed_fixtures():
            self.db.rollback()
            with self.db.transaction():
                for table in ('decision_mainland_boundary_sources', 'decision_mainland_boundaries'):
                    self.db.execute('DELETE FROM atlas.' + table + " WHERE revision='__watershed'")
                self.db.execute("DELETE FROM atlas.decision_revisions WHERE revision='__watershed'")
                self.db.execute("DELETE FROM atlas.entity_registry_revisions WHERE revision='__watershed_entities'")
                self.db.execute("DELETE FROM atlas.structured_documents WHERE source_id='__watershed_recipe'")
                self.db.execute("DELETE FROM atlas.source_assets WHERE source_id LIKE '__watershed_%'")

        self.addCleanup(remove_committed_fixtures)
        connections = []

        def connect():
            database = psycopg.connect(os.environ['WORLDATLAS_TEST_DATABASE_URL'])
            connections.append(database)
            return database

        def calculate(recipe, files):
            self.assertEqual(len(connections), 1)
            self.assertTrue(connections[0].closed)
            return construct(recipe, files)

        with patch('watersheds.build_boundary.construct', side_effect=calculate):
            receipt = build_boundary(connect, self.client, '__watershed_recipe', '1',
                                     '__watershed', self.directory / 'cache')
        self.assertEqual(len(connections), 2)
        self.assertTrue(all(database.closed for database in connections))
        self.assertEqual(self.row()[1], receipt['sha256'])

    def test_repeat_version_change_and_preserved_notes(self):
        result = self.build()
        first = self.row()
        self.assertEqual(first[1], result['sha256'])
        self.assertEqual(first[2]['construction']['recipe_version'], '1')
        self.assertEqual(len(first[2]['construction']['sources']), 3)
        self.assertEqual(self.build()['sha256'], result['sha256'])
        self.assertEqual(self.client.get_object.call_count, 3)
        self.db.execute("UPDATE atlas.decision_mainland_boundaries SET provenance=provenance || "
                        "'{\"note\":\"retain this\",\"custom_context\":{\"source\":\"reviewed\"}}' "
                        "WHERE revision='__watershed'")
        changed = dict(self.recipe, basis='Updated explanation')
        self.store_recipe('2', changed)
        self.assertEqual(self.build('2')['sha256'], result['sha256'])
        self.assertEqual(self.row()[2]['note'], 'retain this')
        self.assertEqual(self.row()[2]['custom_context'], {'source': 'reviewed'})
        self.assertEqual(self.row()[2]['construction']['recipe_version'], '2')
        links = self.db.execute('SELECT source_id,source_version FROM atlas.decision_mainland_boundary_sources '
                                "WHERE revision='__watershed'").fetchall()
        self.assertEqual(set(links), {(v['source_id'], '1') for v in self.recipe['sources'].values()})

    def test_failed_calculation_leaves_existing_boundary_and_links_unchanged(self):
        self.build()
        previous = self.row()
        broken = dict(self.recipe, joins=[{'near': [5, 5]}])
        self.store_recipe('broken', broken)
        with self.assertRaisesRegex(ValueError, 'one geographic join'):
            self.build('broken')
        self.assertEqual(self.row(), previous)
        count = self.db.execute("SELECT count(*) FROM atlas.decision_mainland_boundary_sources "
                                "WHERE revision='__watershed'").fetchone()[0]
        self.assertEqual(count, 3)

    def test_supporting_sources_are_linked_without_being_downloaded(self):
        self.db.execute(
            "INSERT INTO atlas.source_assets (source_id,version,title,kind,provider,source_uri,"
            "license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes,provenance) "
            "SELECT source_id,'evidence',title,kind,provider,source_uri,license_name,license_uri,"
            "attribution,r2_bucket,r2_key||'-evidence',sha256,size_bytes,provenance "
            "FROM atlas.source_assets WHERE source_id='__watershed_dem' AND version='1'")
        recipe = dict(self.recipe, evidence_sources=[{'source_id': '__watershed_dem', 'version': 'evidence'}])
        self.store_recipe('with-evidence', recipe)
        self.build('with-evidence')
        self.build('with-evidence')
        self.assertEqual(self.client.get_object.call_count, 3)
        relationship = self.db.execute(
            "SELECT relationship FROM atlas.decision_mainland_boundary_sources "
            "WHERE revision='__watershed' AND source_id='__watershed_dem' AND source_version='evidence'"
        ).fetchone()[0]
        self.assertEqual(relationship, 'supporting_evidence')


if __name__ == '__main__':
    unittest.main()
