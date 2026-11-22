"""Build a small boundary from files and check how the importer saves it."""
from contextlib import nullcontext
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

import numpy as np
from osgeo import gdal
import psycopg
from psycopg.types.json import Jsonb
from pyproj import CRS, Transformer
from shapely.geometry import box

from worldatlas.shared.r2 import R2Client
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.division.areas import divide_area
from worldatlas.map_build.division.scope import complete_row
from worldatlas.source_imports.run_import import run_import
from worldatlas.source_imports.watersheds.build_boundary import construct_boundary
from worldatlas.source_imports.watersheds.test_basins import write_basin_shapefile


def write_basin_archive(archive, *, north=.02):
    """Write the two fixture basins to the archive used by the construction.

    Args:
        archive: Destination ZIP path in the fixture directory.
        north: Northern latitude of both source polygons.
    """
    basin = archive.with_suffix('.shp')
    write_basin_shapefile(basin, 'BASIN', [(41, box(-.01, -.01, .003, north)),
                                         (99, box(.003, -.01, .02, north))])
    with zipfile.ZipFile(archive, 'w') as output:
        for suffix in ('.shp', '.shx', '.dbf', '.prj'):
            member = basin.with_suffix(suffix)
            output.write(member, member.name)


def fixtures(directory):
    """Write the tiny maps needed for a complete boundary test.

    Each row of heights is 0, 1, 2, 2, 1, 0. Water drains away from
    the two middle columns toward the two different basins.

    Args:
        directory: Temporary directory for the source files.

    Returns:
        The local source paths and the corresponding construction arguments.
    """
    raster = directory / 'dem.tif'
    ds = gdal.GetDriverByName('GTiff').Create(str(raster), 6, 6, 1, gdal.GDT_Float32)
    ds.SetGeoTransform((0., .001, 0., .006, 0., -.001))
    ds.SetProjection(CRS.from_epsg(4326).to_wkt())
    ds.GetRasterBand(1).WriteArray(np.tile([0, 1, 2, 2, 1, 0], (6, 1)))
    ds = None
    archive = directory / 'basins.zip'
    write_basin_archive(archive)
    geometry = directory / 'lines.geojson'
    geometry.write_text(json.dumps({'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'properties': {}, 'geometry': {'type': 'LineString',
         'coordinates': [[.001, .005], [.005, .005]]}},
        {'type': 'Feature', 'properties': {}, 'geometry': {'type': 'LineString',
         'coordinates': [[.001, .001], [.005, .001]]}},
    ]}))
    files = {'dem': raster, 'basins': archive, 'lines': geometry}
    recipe = {
        'feature_id': 'test-divide',
        'sources': {name: '__watershed_' + name for name in files},
        'lines': {name: {'source': 'lines', 'geojson_feature': i}
                  for i, name in enumerate(('before', 'after'))},
        'drainage': {'local': {'basins': [{'source': 'basins', 'member': 'basins.shp'}],
                     'basin_attribute': 'BASIN', 'groups': {'3': [41], '100': [99]}}},
        'terrains': {'ridge': {'primary': ['dem'], 'domains': [{'bounds': [0, 0, .006, .006]}],
                    'drainage': 'local', 'interfaces': [[3, 100]]}},
        'sections': [{'line': 'before'}, {'divide': 'ridge'}, {'line': 'after'}],
        'joins': [{'near': [.003, .005]}, {'near': [.003, .001]}],
        'start': {'point': [.001, .005]},
        'end': {'point': [.005, .001]},
    }
    return files, recipe


def build_fixture(recipe, files):
    """Run the watershed calculation with the fixture's construction settings.

    Args:
        recipe: Fixture recipe containing the selected sections and terrain.
        files: Verified local source paths keyed by source alias.

    Returns:
        Constructed boundary and its calculation report.
    """
    return construct_boundary(
        files, line_selections=recipe['lines'], sections=recipe['sections'],
        joins=recipe['joins'], start=recipe['start'], end=recipe['end'],
        terrains=recipe.get('terrains'), drainage=recipe.get('drainage'),
    )


class ConstructionTests(unittest.TestCase):
    """Calculate small native-grid boundaries from local source files."""

    def test_numeric_and_text_waterway_reversals_produce_the_same_result(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            river = Path(directory) / 'river.osm'
            river.write_text('<osm version="0.6"><node id="1" lon=".001" lat=".005" version="1"/>'
                             '<node id="2" lon=".001" lat=".001" version="1"/>'
                             '<way id="11" version="1"><nd ref="1"/><nd ref="2"/>'
                             '<tag k="waterway" v="stream"/></way></osm>')
            files['river'] = river
            drainage = recipe['drainage']['local']
            drainage.update(waterways=['river'], waterway_groups={'3': ['11']})
            for way_id in (11, '11'):
                with self.subTest(way_id=way_id):
                    drainage['reverse_waterways'] = [way_id]
                    geometry, report = build_fixture(recipe, files)
                    self.assertEqual(geometry['coordinates'][1:-1], [
                        [.003, .005], [.003, .004], [.003, .003], [.003, .002], [.003, .001],
                    ])
                    self.assertEqual(
                        report['terrain']['ridge']['network']['reversed_waterways'], {'11': 1},
                    )

    def test_unresolved_river_stops_before_terrain_processing(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            river = Path(directory) / 'rivers.osm'
            river.write_text('<osm version="0.6"><node id="1" lon=".001" lat=".005"/>'
                             '<node id="2" lon=".002" lat=".003"/>'
                             '<node id="3" lon=".001" lat=".001"/>'
                             '<node id="4" lon=".005" lat=".001"/>'
                             '<way id="10"><nd ref="1"/><nd ref="2"/><tag k="waterway" v="stream"/></way>'
                             '<way id="20"><nd ref="2"/><nd ref="3"/><tag k="waterway" v="stream"/></way>'
                             '<way id="30"><nd ref="2"/><nd ref="4"/><tag k="waterway" v="stream"/></way></osm>')
            files['rivers'] = river
            recipe['drainage']['local'].update(waterways=['rivers'], waterway_groups={3: ['20']})
            with patch('worldatlas.source_imports.watersheds.build_boundary.prepare_elevation_grid') as terrain:
                with self.assertRaisesRegex(ValueError, 'unresolved downstream route'):
                    build_fixture(recipe, files)
                terrain.assert_not_called()

    def test_final_connector_crossing_is_rejected_by_the_pipeline(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            river = Path(directory) / 'river.osm'
            river.write_text('<osm version="0.6"><node id="1" lon=".002" lat=".0022"/>'
                             '<node id="2" lon=".002" lat=".0038"/>'
                             '<way id="10"><nd ref="1"/><nd ref="2"/>'
                             '<tag k="waterway" v="stream"/></way></osm>')
            files['river'] = river
            recipe['drainage']['local']['waterways'] = ['river']
            recipe['sections'][1].update(via=[{'point': [.001, .003]}], max_step_m=10.)
            with self.assertRaisesRegex(ValueError, 'boundary crosses a river or stream'):
                build_fixture(recipe, files)

    def test_divide_waypoints_need_no_stored_attachment_coordinates(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            points = [[.0032, .004], [.0028, .002]]
            recipe['sections'][1].update(via=[{'point': p} for p in points], max_step_m=10.)
            geometry, report = build_fixture(recipe, files)
            coordinates = geometry['coordinates']
            self.assertEqual(coordinates[0], [.001, .005])
            self.assertEqual(coordinates[-1], [.005, .001])
            self.assertLess(coordinates.index(points[0]), coordinates.index(points[1]))
            self.assertIn('waypoints', report['connections']['1'])

    def test_divide_can_pass_through_a_fork_with_distinct_destinations(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            river = Path(directory) / 'fork.osm'
            river.write_text('<osm version="0.6"><node id="1" lon=".0028" lat=".0035"/>'
                             '<node id="2" lon=".003" lat=".003"/>'
                             '<node id="3" lon=".001" lat=".0025"/>'
                             '<node id="4" lon=".005" lat=".0025"/>'
                             '<way id="10"><nd ref="1"/><nd ref="2"/><tag k="waterway" v="stream"/></way>'
                             '<way id="20"><nd ref="2"/><nd ref="3"/><tag k="waterway" v="stream"/></way>'
                             '<way id="30"><nd ref="2"/><nd ref="4"/><tag k="waterway" v="stream"/></way></osm>')
            files['river'] = river
            drainage = recipe['drainage']['local']
            drainage.update(waterways=['river'], waterway_groups={'3': [20], '100': [30]})
            recipe['sections'][1].update(via=[{'source': 'river', 'node': 2}], max_step_m=10.)
            geometry, report = build_fixture(recipe, files)
            self.assertIn([.003, .003], geometry['coordinates'])
            self.assertEqual(report['river_checks'][0]['shared_drainage_contacts'], [{'node': '2', 'groups': [3, 100]}])
            drainage['waterway_groups'] = {'3': [20, 30]}
            _, report = build_fixture(recipe, files)
            self.assertEqual(report['river_checks'][0]['shared_drainage_contacts'], [])

    def test_closed_sink_is_applied_only_to_domains_that_contain_it(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            expected, _ = build_fixture(recipe, files)
            recipe['terrains']['ridge']['domains'] = [
                {'bounds': [0, .003, .006, .006]}, {'bounds': [0, 0, .006, .003]}]
            recipe['terrains']['ridge']['closed_sinks'] = [
                {'point': {'point': [.001, .005]}, 'group': 3}]
            actual, _ = build_fixture(recipe, files)
            self.assertEqual(actual, expected)

    def test_closed_sink_outside_all_domains_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            recipe['terrains']['ridge']['closed_sinks'] = [
                {'point': {'point': [.02, .02]}, 'group': 3}]
            with self.assertRaisesRegex(ValueError, 'outside every analysis domain'):
                build_fixture(recipe, files)

    def test_terrain_requires_a_domain_and_known_sink_groups(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            terrain = recipe['terrains']['ridge']
            valid_domains = terrain['domains']
            terrain['domains'] = []
            with self.assertRaisesRegex(ValueError, 'at least one analysis domain'):
                build_fixture(recipe, files)
            terrain['domains'] = valid_domains
            terrain['closed_sinks'] = [{'point': {'point': [.001, .002]}, 'group': -1}]
            with self.assertRaisesRegex(ValueError, 'known group IDs'):
                build_fixture(recipe, files)

    def test_closed_sink_must_agree_with_mapped_stream(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            river = Path(directory) / 'river.osm'
            river.write_text('<osm version="0.6"><node id="1" lon=".0012" lat=".0045"/>'
                             '<node id="2" lon=".0012" lat=".0015"/>'
                             '<way id="11"><nd ref="1"/><nd ref="2"/>'
                             '<tag k="waterway" v="stream"/></way></osm>')
            files['river'] = river
            recipe['drainage']['local'].update(waterways=['river'], waterway_groups={'3': [11]})
            expected, _ = build_fixture(recipe, files)
            sink = {'point': {'point': [.0012, .0035]}, 'group': 3}
            recipe['terrains']['ridge']['closed_sinks'] = [sink]
            actual, _ = build_fixture(recipe, files)
            self.assertEqual(actual, expected)
            sink['group'] = 100
            with self.assertRaisesRegex(ValueError, 'closed drainage destination conflicts'):
                build_fixture(recipe, files)

    def test_boundary_can_use_a_stream_head_and_explicit_geodesic_connector(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            point = {'point': [.0045, .0035]}
            last = {'point': [.0055, .0035]}
            head = {'terrain': 'ridge', 'point': point, 'inside_group': 100,
                    'outside_groups': [3], 'max_step_m': 30.}
            recipe.update(
                sections=[{'divide': 'ridge'}, {'flow': head},
                          {'geodesic': {'start': point, 'end': last, 'max_step_m': 30.}}],
                joins=[{'near': [.003, .0035]}, {'near': point['point']}],
                start={'nearest_divide': 'ridge', 'near': {'point': [.003, .005]}}, end=last,
            )
            geometry, report = build_fixture(recipe, files)
            self.assertIn(point['point'], geometry['coordinates'])
            self.assertEqual(geometry['coordinates'][-1], last['point'])
            self.assertGreater(report['connections']['1']['flow_cells'], 0)
            self.assertEqual(report['connectors']['2']['start'], point['point'])
            domains = recipe['terrains']['ridge']['domains']
            domains.append({'bounds': [0, .003, .006, .006]})
            with self.assertRaisesRegex(ValueError, 'requires one continuous terrain domain'):
                build_fixture(recipe, files)

    def test_unknown_boundary_section_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            recipe['sections'][0] = {'unknown': 'before'}
            with self.assertRaisesRegex(ValueError, 'unknown boundary section type'):
                build_fixture(recipe, files)

    def test_boundary_can_start_and_end_on_a_selected_divide(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            recipe['sections'] = [{'divide': 'ridge'}]
            recipe['joins'] = []
            recipe['start'] = {'nearest_divide': 'ridge', 'near': {'point': [.003, .005]}}
            recipe['end'] = {'nearest_divide': 'ridge', 'near': {'point': [.003, .001]}}
            geometry, _ = build_fixture(recipe, files)
            self.assertEqual(geometry['coordinates'][0], [.003, .005])
            self.assertEqual(geometry['coordinates'][-1], [.003, .001])

    def test_local_watershed_partitions_cells_when_it_reaches_the_scope_edges(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            files, recipe = fixtures(directory)
            recipe.update(
                sections=[{'divide': 'ridge'}], joins=[],
                start={'nearest_divide': 'ridge', 'near': {'point': [.003, .005]}},
                end={'nearest_divide': 'ridge', 'near': {'point': [.003, .001]}},
            )
            geometry, _ = build_fixture(recipe, files)
            # The global grid contains this local six-column scope near 0°E, 0°N.
            grid = Grid(360_000, 90_000, .001)
            west, east, north, south = 180_000, 180_006, 89_995, 89_999
            query = complete_row(grid.width, [(west, east, 1)])
            scope = SimpleNamespace(
                grid=grid,
                rule={'id': 'local-watershed', 'unit': 'cell'},
                context_intervals=lambda _: [(west, east)],
                context_rows=lambda: range(north, south),
                query_rows=lambda: range(north, south),
                query_row=lambda _: query,
            )
            targets = [
                {'entity_id': owner, 'point': {'geometry': {'coordinates': [lon, .0035]}}}
                for owner, lon in [(301, .0015), (909, .0045)]
            ]
            boundaries = [{'geometry': geometry}]
            result = divide_area(scope, boundaries, targets, directory / 'locations')
            self.assertEqual(result['counts'], {'301': 12, '909': 12})
            # One extra row allows both sides to connect around the line's end.
            north -= 1
            with self.assertRaisesRegex(ValueError, 'conflicting labels 301 and 909 share a face'):
                divide_area(scope, boundaries, targets, directory / 'extended-scope')

    def test_boundary_can_start_at_a_calculated_source_intersection(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            document = json.loads(files['lines'].read_text())
            document['features'].append({'type': 'Feature', 'properties': {}, 'geometry': {
                'type': 'LineString', 'coordinates': [[.001, .004], [.003, .006]]}})
            files['lines'].write_text(json.dumps(document))
            recipe['lines']['crossing'] = {'source': 'lines', 'geojson_feature': 2}
            recipe['start'] = {'intersection': ['before', 'crossing'], 'near': [.002, .005]}
            geometry, _ = build_fixture(recipe, files)
            self.assertEqual(geometry['coordinates'][0], [.002, .005])

    def test_complete_native_divide_and_source_joins(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            geometry, report = build_fixture(recipe, files)
            points = geometry['coordinates']
            self.assertEqual(points[0], [.001, .005])
            self.assertEqual(points[-1], [.005, .001])
            self.assertEqual(report['terrain']['ridge']['domains'][0]['unknown_cells'], 0)
            self.assertEqual(report['joins'], [[.003, .005], [.003, .001]])
            self.assertEqual(build_fixture(recipe, files)[0], geometry)
            self.assertFalse((files['basins'].parent / 'extracted').exists())

    def test_terrains_can_share_drainage_settings_or_select_separate_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            river = Path(directory) / 'river.osm'
            river.write_text('<osm version="0.6"><node id="1" lon=".001" lat=".005"/>'
                             '<node id="2" lon=".001" lat=".001"/>'
                             '<way id="11"><nd ref="1"/><nd ref="2"/>'
                             '<tag k="waterway" v="stream"/></way></osm>')
            files['river'] = river
            local = recipe['drainage']['local']
            local.update(waterways=['river'], waterway_groups={'3': [11]})
            ridge = recipe['terrains']['ridge']
            recipe['drainage']['alternate'] = dict(
                local, groups={'7': [41], '8': [99]}, waterway_groups={'7': [11]},
            )
            recipe['terrains'].update(
                same=dict(ridge), other=dict(ridge, drainage='alternate', interfaces=[[7, 8]]),
            )
            _, report = build_fixture(recipe, files)
            seeds = {name: terrain['domains'][0]['seeds']['seed_cells']
                     for name, terrain in report['terrain'].items()}
            self.assertGreater(seeds['ridge']['3'], 0)
            self.assertEqual(seeds['same'], seeds['ridge'])
            self.assertEqual(seeds['other'], {'7': seeds['ridge']['3']})

    def test_terrain_requires_named_drainage_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            recipe['terrains']['ridge']['drainage'] = 'missing'
            with self.assertRaisesRegex(ValueError, "terrain 'ridge' refers to unknown drainage settings 'missing'"):
                build_fixture(recipe, files)

    def test_native_terrain_can_be_read_directly_from_a_zip_member(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            original, _ = build_fixture(recipe, files)
            archive = Path(directory) / 'terrain.zip'
            with zipfile.ZipFile(archive, 'w') as output:
                output.write(files['dem'], 'nested/dem.tif')
            files['dem'] = archive
            recipe['terrains']['ridge']['primary'] = [{'source': 'dem', 'member': 'nested/dem.tif'}]
            geometry, _ = build_fixture(recipe, files)
            self.assertEqual(geometry, original)
            self.assertFalse((archive.parent / 'extracted').exists())

    def test_explicit_output_area_keeps_the_native_construction_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            original = build_fixture(recipe, files)[0]
            recipe['terrains']['ridge']['domains'] = [
                {'bounds': [0, 0, .006, .006], 'output_bounds': [0, 0, .006, .006]}]
            geometry, report = build_fixture(recipe, files)
            self.assertEqual(geometry, original)
            self.assertEqual(report['terrain']['ridge']['domains'][0]['output_bounds'],
                             [0, 0, .006, .006])

    def test_projected_analysis_bounds_use_geographic_sources_and_joins(self):
        with tempfile.TemporaryDirectory() as directory:
            files, recipe = fixtures(Path(directory))
            original = build_fixture(recipe, files)[0]
            bounds = Transformer.from_crs(4326, 3857, always_xy=True).transform_bounds(
                .00001, .00001, .00599, .00599)
            recipe['terrains']['ridge']['domains'] = [
                {'crs': 'EPSG:3857', 'bounds': bounds, 'output_bounds': bounds}]
            geometry, report = build_fixture(recipe, files)
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
            geometry, report = build_fixture(recipe, files)
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
            write_basin_archive(files['basins'], north=.004)
            files['water'] = directory / 'water.tif'
            ds = gdal.GetDriverByName('GTiff').Create(str(files['water']), 6, 6, 1, gdal.GDT_Byte)
            ds.SetGeoTransform((0., .001, 0., .006, 0., -.001))
            ds.SetProjection(CRS.from_epsg(4326).to_wkt())
            water = np.zeros((6, 6), dtype='uint8')
            water[0] = 1
            ds.GetRasterBand(1).WriteArray(water)
            ds = None
            recipe['terrains']['ridge']['ocean_mask'] = {'sources': ['water'], 'values': [1]}
            geometry, report = build_fixture(recipe, files)
            self.assertIn([.003, .005], geometry['coordinates'])
            coverage = report['terrain']['ridge']['domains'][0]['coast']['source_coverage']
            self.assertEqual({item['group'] for item in coverage['resolved']}, {3, 100})
            self.assertEqual(coverage['conflicting'], [])


@unittest.skipUnless(
    os.environ.get("WORLDATLAS_TEST_DATABASE_URL"), "requires disposable PostgreSQL"
)
class StorageTests(unittest.TestCase):
    """Check how the importer saves or rejects a complete construction."""

    def setUp(self):
        self.db = psycopg.connect(os.environ["WORLDATLAS_TEST_DATABASE_URL"])
        self.addCleanup(self.db.close)
        self.addCleanup(self.db.rollback)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.files, self.recipe = fixtures(self.directory)
        self.data = {path.name: path.read_bytes() for path in self.files.values()}
        for name, path in self.files.items():
            raw = path.read_bytes()
            self.db.execute(
                "INSERT INTO atlas.source_assets(id,title,provider,source_uri,license_name,license_uri,attribution,r2_bucket,r2_key,sha256,size_bytes) VALUES (%s,'Test','Test','test:input','Test','test:license','Test','test',%s,%s,%s)",
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
        """Store the current fixture recipe in the disposable database."""
        self.db.execute(
            "INSERT INTO atlas.construction_records(id,method,arguments,basis) "
            "VALUES ('watershed','watershed_boundary',%s,'Test drainage divide') "
            "ON CONFLICT(id) DO UPDATE SET arguments=EXCLUDED.arguments",
            (Jsonb(self.recipe),),
        )

    def build(self):
        """Run the importer using the test files and disposable database.

        Returns:
            The importer report for the saved geometry.
        """
        return run_import(
            lambda: nullcontext(self.db),
            "watershed",
            storage=R2Client(self.client),
            work_dir=self.directory / "cache",
        )

    def row(self):
        """Read the imported feature from the fixture database.

        Returns:
            A geometry and construction ID pair, or None before the first save.
        """
        return self.db.execute(
            "SELECT geometry,construction_id FROM atlas.source_features"
        ).fetchone()

    def test_repeat_and_edit_recipe_preserve_geometry_and_sources(self):
        self.build()
        before = self.row()
        self.build()
        self.assertEqual(self.row(), before)
        self.recipe.update(evidence_sources=None)
        self.store()
        self.build()
        self.assertEqual(self.row(), before)
        links = {
            r[0]
            for r in self.db.execute(
                "SELECT source_id FROM atlas.construction_sources"
            )
        }
        self.assertEqual(
            links, set(self.recipe["sources"].values())
        )

    def test_calculation_failure_leaves_geometry_and_links_unchanged(self):
        self.build()
        before = self.row()
        links = self.db.execute(
            "SELECT * FROM atlas.construction_sources ORDER BY source_id"
        ).fetchall()
        self.recipe["joins"] = [{"near": [5, 5]}]
        self.store()
        with self.assertRaises(ValueError):
            self.build()
        self.assertEqual(self.row(), before)
        self.assertEqual(
            self.db.execute(
                "SELECT * FROM atlas.construction_sources ORDER BY source_id"
            ).fetchall(),
            links,
        )
