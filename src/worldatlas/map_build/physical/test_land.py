import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from osgeo import gdal, ogr, osr
from pydantic import TypeAdapter
from worldatlas.map_build.execution.runtime import RunFilePins
from worldatlas.map_build.inputs.configuration import LandSettings, PhysicalControls
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.physical import land as b
from worldatlas.map_build.physical.sources import checked_files
from worldatlas.shared.files import FilePin, sha256_file


class RasterizeLandTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.d = Path(self.t.name)
        self.inputs = self.d / 'inputs'
        self.inputs.mkdir()
        self.p = self.inputs / 'land.geojson'
        self.p.write_text(
            json.dumps(
                {
                    'type': 'FeatureCollection',
                    'features': [
                        {
                            'type': 'Feature',
                            'properties': {},
                            'geometry': {
                                'type': 'Polygon',
                                'coordinates': [
                                    [[-180, 90], [-45, 90], [-45, 0], [-180, 0], [-180, 90]]
                                ],
                            },
                        }
                    ],
                }
            )
        )
        self.grid = Grid(8, 4, 45)
        self.cfg = {
            'schema': 'land-raster-candidate-v1',
            'selection_notes': 'synthetic',
            'strip_rows': 1,
            'minimum_free_bytes': 0,
            'land': [
                {
                    'dataset': str(self.p),
                    'where': None,
                    'files': [{'path': str(self.p), 'sha256': sha256_file(self.p)}],
                }
            ],
        }
        self.config = self.inputs / 'config.json'
        self.config.write_text(json.dumps(self.cfg))

    def tearDown(self):
        self.t.cleanup()

    def rasterize(self, config, output, grid, **kwargs):
        settings = json.loads(config.read_bytes())
        controls = TypeAdapter(PhysicalControls).validate_python(
            {'minimum_free_bytes': settings.pop('minimum_free_bytes', 0)}, strict=True,
        )
        return b.run(
            sha256_file(config), output, grid,
            settings=TypeAdapter(LandSettings[FilePin]).validate_python(settings, strict=True),
            minimum_free_bytes=controls['minimum_free_bytes'], files=RunFilePins(), **kwargs,
        )

    def test_polygon_and_strip_invariance(self):
        a = self.d / 'a'
        self.rasterize(self.config, a, self.grid)
        expected = np.zeros((4, 8), dtype=np.uint8)
        expected[:2, :3] = 1
        np.testing.assert_array_equal(gdal.Open(str(a / 'land.tif')).ReadAsArray(), expected)
        report = json.loads((a / 'report.json').read_text())
        self.assertEqual(report['land_cells'], 6)
        self.assertEqual(report['feature_counts'], [1])
        self.cfg['strip_rows'] = 4096
        self.config.write_text(json.dumps(self.cfg))
        out = self.d / 'all-rows'
        self.rasterize(self.config, out, self.grid)
        np.testing.assert_array_equal(gdal.Open(str(out / 'land.tif')).ReadAsArray(), expected)

    def test_coastline_requires_lookup_by_feature_id(self):
        out = self.d / 'unsupported-coastline'
        for binding, method, result, error in (
            (ogr.Layer, 'TestCapability', False, 'must support lookup by feature ID'),
            (ogr.Feature, 'GetFID', -1, 'is missing a feature ID'),
        ):
            with self.subTest(method=method), patch.object(binding, method, return_value=result):
                with self.assertRaisesRegex(ValueError, error):
                    self.rasterize(self.config, out, self.grid)
                self.assertFalse(out.exists())

    def test_invalid_rasterization_settings_leave_no_output(self):
        land = self.cfg['land']
        out = self.d / 'invalid'
        for changes, error in (
            ({'schema': 'unknown'}, 'schema'),
            ({'land': []}, 'nonempty explicitly pinned land inputs'),
            ({'strip_rows': False}, 'strip_rows'),
            ({'minimum_free_bytes': -1}, 'minimum_free_bytes'),
            ({'feature_index': 'scan'}, 'feature_index'),
            ({'land': land * 2}, 'input paths must be unique'),
        ):
            with self.subTest(changes=changes):
                self.config.write_text(json.dumps(dict(self.cfg, **changes)))
                with self.assertRaisesRegex(ValueError, error):
                    self.rasterize(self.config, out, self.grid)
                self.assertFalse(out.exists())

    def test_layer_requires_explicit_polygon_selection(self):
        source = json.loads(self.p.read_text())
        first = source['features'][0]
        for item, options, error in (
            (first, {'layer': 'absent'}, 'layer not found'),
            (first, {}, 'selection predicate must be explicit'),
            (first, {'where': 'FID < 0'}, 'selection yielded no features'),
            (dict(first, geometry=None), {'where': None}, 'empty geometry'),
            (
                dict(first, geometry={'type': 'Point', 'coordinates': [0, 0]}),
                {'where': None},
                'nonpolygon geometry',
            ),
        ):
            with self.subTest(error=error):
                self.p.write_text(json.dumps(dict(source, features=[item])))
                spec = dict(
                    dataset=str(self.p),
                    files=[{'path': str(self.p), 'sha256': sha256_file(self.p)}],
                    **options,
                )
                self.config.write_text(json.dumps(dict(self.cfg, land=[spec])))
                with self.assertRaisesRegex(ValueError, error):
                    self.rasterize(self.config, self.d / 'invalid', self.grid)

    def test_unreadable_layer_or_missing_coordinate_reference_is_rejected(self):
        for binding, method, message in (
            (ogr, 'Open', 'cannot open dataset'),
            (ogr.Layer, 'GetSpatialRef', 'must explicitly declare EPSG:4326'),
        ):
            with self.subTest(method=method), patch.object(binding, method, return_value=None):
                with self.assertRaisesRegex(ValueError, message):
                    self.rasterize(self.config, self.d / 'invalid', self.grid)

    def test_shapefile_companions_must_all_be_pinned(self):
        path = self.inputs / 'coast.v2.shp'
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        with ogr.GetDriverByName('ESRI Shapefile').CreateDataSource(
            str(path)
        ) as source:
            layer = source.CreateLayer('coast.v2', srs, ogr.wkbPolygon)
            feature = ogr.Feature(layer.GetLayerDefn())
            feature.SetGeometry(
                ogr.CreateGeometryFromWkt(
                    'POLYGON ((-180 90,-45 90,-45 0,-180 0,-180 90))'
                )
            )
            self.assertEqual(layer.CreateFeature(feature), 0)
        files = sorted(self.inputs.glob('coast.v2.*'))
        spec = dict(
            dataset=str(path),
            files=[dict(path=str(file), sha256=sha256_file(file)) for file in files],
        )
        self.assertEqual(
            set(checked_files(spec, RunFilePins())), {str(file.resolve()) for file in files}
        )
        self.cfg['land'] = [dict(spec, where=None)]
        self.config.write_text(json.dumps(self.cfg))
        self.assertEqual(
            self.rasterize(self.config, self.d / 'dotted', self.grid)['land_cells'], 6
        )
        for omitted, error in (
            ('.shp', 'dataset must be among hash-pinned files'),
            ('.prj', 'shapefile needs pinned'),
        ):
            with self.subTest(omitted=omitted):
                pins = [p for p in spec['files'] if not p['path'].endswith(omitted)]
                with self.assertRaisesRegex(ValueError, error):
                    checked_files(dict(spec, files=pins), RunFilePins())
        path.with_suffix('.cpg').write_text('UTF-8')
        with self.assertRaisesRegex(ValueError, 'unpinned shapefile companion'):
            checked_files(spec, RunFilePins())

    def test_missing_indexed_feature_leaves_no_report(self):
        with patch.object(ogr.Layer, 'GetFeature', return_value=None):
            with self.assertRaisesRegex(ValueError, 'indexed land feature missing'):
                self.rasterize(self.config, self.d / 'missing', self.grid)
        self.assertFalse((self.d / 'missing' / 'report.json').exists())

    def test_land_source_with_a_different_crs_cannot_be_rasterized_as_longitude_latitude(self):
        document = json.loads(self.p.read_bytes())
        document['crs'] = dict(type='name', properties=dict(name='EPSG:3857'))
        self.p.write_text(json.dumps(document))
        self.cfg['land'][0]['files'][0]['sha256'] = sha256_file(self.p)
        self.config.write_text(json.dumps(self.cfg))
        out = self.d / 'wrong-crs'
        with self.assertRaisesRegex(ValueError, 'must explicitly declare EPSG:4326'):
            self.rasterize(self.config, out, self.grid)
        self.assertFalse(out.exists())

    def test_land_does_not_publish_if_disk_space_runs_out(self):
        self.cfg['minimum_free_bytes'] = 1
        self.config.write_text(json.dumps(self.cfg))
        output = self.d / 'low-disk'
        with patch.object(
            b.shutil, 'disk_usage',
            side_effect=lambda path: SimpleNamespace(free=0 if Path(path) == output.resolve() else 1024),
        ):
            with self.assertRaisesRegex(ValueError, 'partial output preserved'):
                self.rasterize(self.config, output, self.grid)
        self.assertFalse((output / 'report.json').exists())

    def test_index_keeps_selection_and_exact_strip_boundary_polygons(self):
        geometries = [
            {
                'type': 'Polygon',
                'coordinates': [
                    [[-180, 90], [-90, 90], [-90, -45], [-180, -45], [-180, 90]],
                    [
                        [-157.5, 67.5],
                        [-112.5, 67.5],
                        [-112.5, -22.5],
                        [-157.5, -22.5],
                        [-157.5, 67.5],
                    ],
                ],
            },
            {
                'type': 'Polygon',
                'coordinates': [[[-45, 45], [45, 45], [45, 0], [-45, 0], [-45, 45]]],
            },
            {
                'type': 'Polygon',
                'coordinates': [[[181, 90], [190, 90], [190, 80], [181, 80], [181, 90]]],
            },
            {
                'type': 'Polygon',
                'coordinates': [[[10, 20], [20, 20], [20, 10], [10, 10], [10, 20]]],
            },
            {
                'type': 'Polygon',
                'coordinates': [[[10, -80], [20, -80], [20, -70], [10, -70], [10, -80]]],
            },
        ]
        self.p.write_text(
            json.dumps(
                {
                    'type': 'FeatureCollection',
                    'features': [
                        {'type': 'Feature', 'properties': {'keep': i % 2}, 'geometry': g}
                        for i, g in enumerate(geometries)
                    ],
                }
            )
        )
        self.cfg['land'][0].update(
            {'where': 'keep = 0', 'files': [{'path': str(self.p), 'sha256': sha256_file(self.p)}]}
        )
        self.grid = Grid(8, 3, 45)
        self.config.write_text(json.dumps(self.cfg))
        out = self.d / 'indexed'
        self.rasterize(self.config, out, self.grid)
        # The filter leaves the large polygon and its hole, plus polygons off the grid.
        expected = np.zeros((3, 8), dtype=np.uint8)
        expected[2, :2] = 1
        np.testing.assert_array_equal(
            gdal.Open(str(out / 'land.tif')).ReadAsArray(), expected
        )

    def test_rejects_bad_digest_and_output_collision(self):
        self.cfg['land'][0]['files'][0]['sha256'] = '0' * 64
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            self.rasterize(self.config, self.d / 'bad', self.grid)
        self.assertFalse((self.d / 'bad').exists())
        self.cfg['land'][0]['files'][0]['sha256'] = sha256_file(self.p)
        self.config.write_text(json.dumps(self.cfg))
        (self.d / 'exists').mkdir()
        with self.assertRaises(FileExistsError):
            self.rasterize(self.config, self.d / 'exists', self.grid)

    def test_rejects_invalid_geometry(self):
        self.p.write_text(
            json.dumps(
                {
                    'type': 'FeatureCollection',
                    'features': [
                        {
                            'type': 'Feature',
                            'properties': {},
                            'geometry': {
                                'type': 'Polygon',
                                'coordinates': [
                                    [[-180, 90], [-45, 0], [-45, 90], [-180, 0], [-180, 90]]
                                ],
                            },
                        }
                    ],
                }
            )
        )
        self.cfg['land'][0]['files'][0]['sha256'] = sha256_file(self.p)
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'invalid geometry'):
            self.rasterize(self.config, self.d / 'bad', self.grid)
        self.assertFalse((self.d / 'bad').exists())

    def test_invalid_filter_fails_even_when_ogr_exceptions_are_disabled(self):
        self.cfg['land'][0]['where'] = 'missing_field = 1'
        self.config.write_text(json.dumps(self.cfg))
        with ogr.ExceptionMgr(useExceptions=False), self.assertRaisesRegex(ValueError, 'invalid source selection'):
            self.rasterize(self.config, self.d / 'bad-filter', self.grid)
        self.assertFalse((self.d / 'bad-filter').exists())


if __name__ == '__main__':
    unittest.main()
