import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from osgeo import gdal, ogr, osr
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.physical import land as b
from worldatlas.map_build.physical.sources import checked_files
from worldatlas.shared.files import sha256_file


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

    def test_polygon_and_strip_invariance(self):
        a = self.d / 'a'
        b.run(self.config, a, self.grid)
        expected = np.zeros((4, 8), dtype=np.uint8)
        expected[:2, :3] = 1
        np.testing.assert_array_equal(gdal.Open(str(a / 'land.tif')).ReadAsArray(), expected)
        report = json.loads((a / 'report.json').read_text())
        self.assertEqual(report['land_cells'], 6)
        self.assertEqual(report['feature_counts'], [1])
        self.cfg['strip_rows'] = 4096
        self.config.write_text(json.dumps(self.cfg))
        out = self.d / 'all-rows'
        b.run(self.config, out, self.grid)
        np.testing.assert_array_equal(gdal.Open(str(out / 'land.tif')).ReadAsArray(), expected)
        self.cfg['strip_rows'] = 1
        self.cfg['feature_index'] = 'scan'
        self.config.write_text(json.dumps(self.cfg))
        out = self.d / 'scan'
        b.run(self.config, out, self.grid)
        self.assertEqual(sha256_file(a / 'land.tif'), sha256_file(out / 'land.tif'))
        self.cfg['feature_index'] = 'row-fids'
        self.config.write_text(json.dumps(self.cfg))
        fallback = self.d / 'no-feature-ids'
        with patch.object(ogr.Feature, 'GetFID', return_value=-1):
            b.run(self.config, fallback, self.grid)
        self.assertEqual(sha256_file(a / 'land.tif'), sha256_file(fallback / 'land.tif'))

    def test_invalid_rasterization_settings_leave_no_output(self):
        land = self.cfg['land']
        out = self.d / 'invalid'
        for changes, error in (
            ({'schema': 'unknown'}, 'schema and selection notes'),
            ({'land': []}, 'nonempty explicitly pinned land inputs'),
            ({'strip_rows': False}, 'invalid strip_rows'),
            ({'minimum_free_bytes': -1}, 'invalid free-space reserve'),
            ({'feature_index': 'unsupported'}, 'feature_index'),
            ({'land': land * 2}, 'input paths must be unique'),
        ):
            with self.subTest(changes=changes):
                self.config.write_text(json.dumps(dict(self.cfg, **changes)))
                with self.assertRaisesRegex(ValueError, error):
                    b.run(self.config, out, self.grid)
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
                    b.run(self.config, self.d / 'invalid', self.grid)

    def test_unreadable_layer_or_missing_coordinate_reference_is_rejected(self):
        for binding, method, message in (
            (ogr, 'Open', 'cannot open dataset'),
            (ogr.Layer, 'GetSpatialRef', 'must explicitly declare EPSG:4326'),
        ):
            with self.subTest(method=method), patch.object(binding, method, return_value=None):
                with self.assertRaisesRegex(ValueError, message):
                    b.run(self.config, self.d / 'invalid', self.grid)

    def test_shapefile_companions_must_all_be_pinned(self):
        path = self.inputs / 'coast.shp'
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        with ogr.GetDriverByName('ESRI Shapefile').CreateDataSource(str(path)) as source:
            source.CreateLayer('coast', srs, ogr.wkbPolygon)
        files = sorted(self.inputs.glob('coast.*'))
        spec = dict(
            dataset=str(path),
            files=[dict(path=str(file), sha256=sha256_file(file)) for file in files],
        )
        self.assertEqual(set(checked_files(spec)), {str(file.resolve()) for file in files})
        for omitted, error in (
            ('.shp', 'dataset must be among hash-pinned files'),
            ('.prj', 'shapefile needs pinned'),
        ):
            with self.subTest(omitted=omitted):
                pins = [p for p in spec['files'] if not p['path'].endswith(omitted)]
                with self.assertRaisesRegex(ValueError, error):
                    checked_files(dict(spec, files=pins))
        path.with_suffix('.cpg').write_text('UTF-8')
        with self.assertRaisesRegex(ValueError, 'unpinned shapefile companion'):
            checked_files(spec)

    def test_land_raster_requires_current_inputs_through_to_publication(self):
        original = self.config.read_bytes()
        output = self.d / 'changed'

        def change_config(*_, **__):
            self.config.write_bytes(original + b'\n')

        with self.assertRaisesRegex(ValueError, 'configuration changed during processing'):
            b.run(self.config, output, self.grid, emit=change_config)
        self.assertFalse((output / 'report.json').exists())
        self.config.write_bytes(original)

        with patch.object(ogr.Layer, 'GetFeature', return_value=None):
            with self.assertRaisesRegex(ValueError, 'indexed land feature missing'):
                b.run(self.config, self.d / 'missing', self.grid)
        self.assertFalse((self.d / 'missing' / 'report.json').exists())

    def test_land_source_with_a_different_crs_cannot_be_rasterized_as_longitude_latitude(self):
        document = json.loads(self.p.read_bytes())
        document['crs'] = dict(type='name', properties=dict(name='EPSG:3857'))
        self.p.write_text(json.dumps(document))
        self.cfg['land'][0]['files'][0]['sha256'] = sha256_file(self.p)
        self.config.write_text(json.dumps(self.cfg))
        out = self.d / 'wrong-crs'
        with self.assertRaisesRegex(ValueError, 'must explicitly declare EPSG:4326'):
            b.run(self.config, out, self.grid)
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
                b.run(self.config, output, self.grid)
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
        masks = []
        for engine in ('scan', 'row-fids'):
            self.cfg['feature_index'] = engine
            self.config.write_text(json.dumps(self.cfg))
            out = self.d / engine
            b.run(self.config, out, self.grid)
            masks.append(gdal.Open(str(out / 'land.tif')).ReadAsArray())
        np.testing.assert_array_equal(*masks)

    def test_rejects_bad_digest_and_output_collision(self):
        self.cfg['land'][0]['files'][0]['sha256'] = '0' * 64
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            b.run(self.config, self.d / 'bad', self.grid)
        self.assertFalse((self.d / 'bad').exists())
        self.cfg['land'][0]['files'][0]['sha256'] = sha256_file(self.p)
        self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError, 'outside input'):
            b.run(self.config, self.inputs / 'bad', self.grid)
        (self.d / 'exists').mkdir()
        with self.assertRaises(FileExistsError):
            b.run(self.config, self.d / 'exists', self.grid)

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
            b.run(self.config, self.d / 'bad', self.grid)
        self.assertFalse((self.d / 'bad').exists())

    def test_invalid_filter_fails_even_when_ogr_exceptions_are_disabled(self):
        self.cfg['land'][0]['where'] = 'missing_field = 1'
        self.config.write_text(json.dumps(self.cfg))
        with ogr.ExceptionMgr(useExceptions=False), self.assertRaisesRegex(ValueError, 'invalid source selection'):
            b.run(self.config, self.d / 'bad-filter', self.grid)
        self.assertFalse((self.d / 'bad-filter').exists())


if __name__ == '__main__':
    unittest.main()
