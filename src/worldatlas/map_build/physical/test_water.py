import hashlib
import json
import struct
import tempfile
import unittest
import weakref
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import ctypes
import subprocess
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import TypeAdapter
from osgeo import gdal, ogr
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.inputs.configuration import WaterSettings
from worldatlas.map_build.execution.runtime import RunFilePins
from worldatlas.map_build.physical import water as build
from worldatlas.shared.text import UNICODE_WHITESPACE
from worldatlas.map_build.physical import water_batch
from worldatlas.map_build.physical.water_batch import WaterBatch
from worldatlas.shared.files import sha256_file


class WaterShardTests(unittest.TestCase):
    def test_arrow_policy_matches_scalar_for_whitespace_and_dictionary_strings(self):
        values = [
            'ocean',
            'physical',
            'lake',
            ' ocean ',
            '',
            None,
            *UNICODE_WHITESPACE,
            '\x1c\x1d\x1e\x1f',
            '\u2000\u3000',
            '\u200blake',
            '\u200b',
        ]
        expected = [build.selected(v) for v in values]
        for array in (pa.array(values), pa.array(values).dictionary_encode()):
            eligible, missing, excluded = build.classifications(array)
            self.assertEqual(eligible.tolist(), [reason is None for reason in expected])
            self.assertEqual(missing, expected.count('missing_classification'))
            self.assertEqual(excluded, expected.count('excluded_classification'))
        self.assertEqual(build.classifications(pa.array([1, 2, None]))[0].tolist(), [0, 0, 0])

    def test_diagnostic_ids_cross_row_groups_and_preserve_requested_order(self):
        p, _ = self.fixture()
        table = pq.read_table(p)
        pq.write_table(table, p, row_group_size=2)
        ids = build.SourceIds(pq.ParquetFile(p))
        self.assertEqual(ids.get([5, 0, 2, 5]), ['pool', 'lake', 'label', 'pool'])
        self.assertEqual(ids.get([]), [])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        self.inputs = self.path / 'inputs'
        self.inputs.mkdir()
        self.grid = Grid(32, 16, 11.25)
        cfg = {
            'schema': 'water-shard-candidate-v2',
            'tile_size': 4,
            'selection_notes': 'synthetic test',
        }
        self.config = self.inputs / 'config.json'
        self.config.write_text(json.dumps(cfg))

    def tearDown(self):
        self.tmp.cleanup()

    def rasterize(self, source, digest, output, config, grid, batch_size=None, engine=None, **kwargs):
        settings = json.loads(config.read_bytes())
        reserve = settings.pop('minimum_free_bytes', 0)
        if batch_size is not None:
            settings['batch_size'] = batch_size
        if engine is not None:
            settings['rasterizer'] = engine
        return build.run(
            source, digest, output, sha256_file(config), grid,
            settings=TypeAdapter(WaterSettings).validate_python(settings, strict=True),
            minimum_free_bytes=reserve, files=RunFilePins(), **kwargs,
        )

    def fixture(self):
        def wkt(s):
            return bytes(ogr.CreateGeometryFromWkt(s).ExportToWkb())

        osm = [{'property': '', 'dataset': 'OpenStreetMap'}]
        alt = [{'property': '', 'dataset': 'Other'}]
        polygon = wkt('POLYGON ((-170 80,-120 80,-120 40,-170 40,-170 80))')
        rows = [
            {'id': 'lake', 'subtype': 'lake', 'class': 'lake', 'sources': osm, 'geometry': polygon},
            {
                'id': 'ocean',
                'subtype': 'ocean',
                'class': 'ocean',
                'sources': osm,
                'geometry': polygon,
            },
            {
                'id': 'label',
                'subtype': 'physical',
                'class': 'bay',
                'sources': osm,
                'geometry': polygon,
            },
            {'id': 'other', 'subtype': 'lake', 'class': 'sea', 'sources': alt, 'geometry': polygon},
            {
                'id': 'line',
                'subtype': 'river',
                'class': 'river',
                'sources': osm,
                'geometry': wkt('LINESTRING (-170 80,-120 40)'),
            },
            {
                'id': 'pool',
                'subtype': 'human_made',
                'class': 'swimming_pool',
                'sources': osm,
                'geometry': polygon,
            },
        ]
        table = pa.Table.from_pylist(rows).replace_schema_metadata(
            {
                b'geo': json.dumps(
                    {'primary_column': 'geometry', 'columns': {'geometry': {'encoding': 'WKB'}}}
                ).encode()
            }
        )
        p = self.inputs / 'water.parquet'
        pq.write_table(table, p)
        return p, hashlib.sha256(p.read_bytes()).hexdigest()

    def test_policy_and_batch_invariance(self):
        p, digest = self.fixture()
        for n in (1, 10):
            out = self.path / f'o{n}'
            mask, rasterizer = self.rasterize(p, digest, out, self.config, self.grid, n)
            report_path = out / 'report.json'
            report = json.loads(report_path.read_text())
            self.assertEqual(mask['sha256'], report['output_sha256'])
            self.assertEqual(mask['report']['sha256'], sha256_file(report_path))
            self.assertEqual(rasterizer[:2], (report['script_sha256'], report['rasterizer']))
            self.assertEqual(report['policy'], {'method': 'overture-inland-subtype-v1'})
            self.assertEqual(report['counts']['polygons'], 3)
            self.assertEqual(report['counts']['excluded_classification'], 2)
            self.assertEqual(report['counts']['non_polygon'], 1)
            self.assertNotIn('no_selected_geometry_provenance', report['counts'])
            self.assertEqual(report['status'], 'candidate-only')
        a = gdal.Open(str(self.path / 'o1/water.tif')).ReadAsArray()
        b = gdal.Open(str(self.path / 'o10/water.tif')).ReadAsArray()
        np.testing.assert_array_equal(a, b)
        self.assertGreater(a.sum(), 0)
        self.assertLess(a.sum(), a.size)
        target = gdal.GetDriverByName('MEM').Create('', 32, 16, 1, gdal.GDT_Byte)
        target.SetGeoTransform((-180, 11.25, 0, 90, 0, -11.25))
        ds = ogr.GetDriverByName('Memory').CreateDataSource('')
        layer = ds.CreateLayer('x', geom_type=ogr.wkbPolygon)
        feat = ogr.Feature(layer.GetLayerDefn())
        feat.SetGeometry(
            ogr.CreateGeometryFromWkt('POLYGON ((-170 80,-120 80,-120 40,-170 40,-170 80))')
        )
        layer.CreateFeature(feat)
        gdal.RasterizeLayer(target, [1], layer, burn_values=[1])
        np.testing.assert_array_equal(a, target.ReadAsArray())

    def test_gdal_matches_reference_with_holes_edges_and_nonpolygons(self):
        p, _ = self.fixture()
        table = pq.read_table(p)
        rows = table.to_pylist()
        geometries = [
            'POLYGON ((-180 90,-180 45,-135 45,-135 90,-180 90))',
            'POLYGON ((-174.375 84.375,-174.375 50.625,-140.625 50.625,-140.625 84.375,-174.375 84.375))',
            'POLYGON ((-180 90,0 90,0 -45,-180 -45,-180 90),(-135 45,-135 0,-90 0,-90 45,-135 45))',
            'MULTIPOLYGON (((-170 75,-160 75,-160 65,-170 65,-170 75)),((170 75,180 75,180 65,170 65,170 75)))',
            'POLYGON Z ((-160 60 1,-150 60 2,-150 50 3,-160 50 4,-160 60 1))',
            'POLYGON ((200 80,210 80,210 70,200 70,200 80))',
            'POINT (0 0)',
            'LINESTRING (-180 90,180 -45)',
            'GEOMETRYCOLLECTION (POINT (0 0))',
        ]
        for i, wkt in enumerate(geometries):
            rows.append(
                {
                    'id': str(i),
                    'subtype': 'lake',
                    'geometry': bytes(ogr.CreateGeometryFromWkt(wkt).ExportToWkb()),
                }
            )
        rng = np.random.default_rng(714)
        for i in range(100):
            x, y = rng.uniform(-200, 180), rng.uniform(-60, 95)
            w, h = rng.uniform(0.001, 80), rng.uniform(0.001, 60)
            geom = ogr.CreateGeometryFromWkt(
                f'POLYGON (({x} {y},{x+w} {y},{x+w} {y-h},{x} {y-h},{x} {y}))'
            )
            rows.append(
                {'id': f'random-{i}', 'subtype': 'lake', 'geometry': bytes(geom.ExportToWkb())}
            )
        table = pa.Table.from_pylist(rows).replace_schema_metadata(table.schema.metadata)
        pq.write_table(table, p)
        digest = sha256_file(p)
        reports = []
        for engine in ('python', 'gdal'):
            out = self.path / engine
            self.rasterize(p, digest, out, self.config, self.grid, 17, engine)
            reports.append(json.loads((out / 'report.json').read_text()))
        self.assertEqual(reports[0]['counts'], reports[1]['counts'])
        np.testing.assert_array_equal(
            gdal.Open(str(self.path / 'python/water.tif')).ReadAsArray(),
            gdal.Open(str(self.path / 'gdal/water.tif')).ReadAsArray(),
        )
        self.assertEqual(reports[0]['output_sha256'], reports[1]['output_sha256'])

    def test_gdal_arrow_slices_large_offsets_and_validity_bitmap(self):
        out = self.path / 'kernel'
        out.mkdir()
        kernel = WaterBatch()
        polygon = bytes(
            ogr.CreateGeometryFromWkt(
                'POLYGON ((-180 90,-135 90,-135 45,-180 45,-180 90))'
            ).ExportToWkb()
        )
        for dtype in (pa.binary(), pa.large_binary()):
            geometry = pa.array(
                [polygon, None, polygon, None, polygon], type=dtype
            ).slice(2, 3)
            raster = gdal.GetDriverByName('MEM').Create('', 8, 4, 1, gdal.GDT_Byte)
            raster.SetGeoTransform((-180, 45, 0, 90, 0, -45))
            status, failed = kernel.burn(
                raster, geometry, [1, 0, 1], [8, 4, -180, 90, 45], 4
            )
            self.assertIsNone(failed)
            self.assertEqual(status.tolist(), [1, 0, 1])
            self.assertEqual(int(raster.ReadAsArray().sum()), 1)
            status, failed = kernel.burn(
                raster, geometry, [1, 1, 1], [8, 4, -180, 90, 45], 4
            )
            self.assertEqual(failed, 1)
            self.assertEqual(status.tolist(), [1, 5, 0])

    def test_batch_backend_does_not_compile_or_start_processes(self):
        p, digest = self.fixture()
        with mock.patch.object(
            subprocess, 'Popen', side_effect=AssertionError('unexpected subprocess')
        ), mock.patch.object(
            ctypes, 'CDLL', side_effect=AssertionError('unexpected ctypes bridge')
        ), mock.patch.object(
            ogr, 'Feature', side_effect=AssertionError('unexpected per-row Feature creation')
        ):
            first = WaterBatch()
            second = WaterBatch()
            self.rasterize(p, digest, self.path / 'python-api', self.config, self.grid)
        self.assertEqual(first.provenance, second.provenance)
        first.timings['tile_burn_seconds'] = 1
        self.assertEqual(second.timings['tile_burn_seconds'], 0)

    def test_vector_point_status_preserves_first_failure_and_unselected_rows(self):
        kernel = WaterBatch()
        point = struct.pack('<BIdd', 1, 1, 1.0, 2.0)
        for values, selected, expected in (
            ([point, None, point], [1, 1, 1], [3, 5, 0]),
            ([None, point, None], [0, 1, 0], [0, 3, 0]),
        ):
            raster = gdal.GetDriverByName('MEM').Create('', 8, 4, 1, gdal.GDT_Byte)
            status, failed = kernel.burn(
                raster, pa.array(values), selected, [8, 4, -180, 90, 45], 4
            )
            self.assertEqual(status.tolist(), expected)
            self.assertEqual(failed, 1 if expected == [3, 5, 0] else None)

    def test_arrow_tile_layers_preserve_big_endian_m_zm_and_trailing_wkb(self):
        p, _ = self.fixture()
        metadata = pq.read_schema(p).metadata
        rows = []
        for i, wkt in enumerate(
            (
                'POLYGON ((-170 80,-120 80,-120 -20,-170 -20,-170 80))',
                'POLYGON M ((-100 80 1,-40 80 2,-40 -20 3,-100 -20 4,-100 80 1))',
                'POLYGON ZM ((20 80 1 2,100 80 3 4,100 -20 5 6,20 -20 7 8,20 80 1 2))',
            )
        ):
            geometry = ogr.CreateGeometryFromWkt(wkt)
            for order in (ogr.wkbXDR, ogr.wkbNDR):
                value = bytes(geometry.ExportToWkb(order))
                rows.append({'id': str(len(rows)), 'subtype': 'lake', 'geometry': value})
            rows.append({'id': str(len(rows)), 'subtype': 'lake', 'geometry': value + b'extra'})
        pq.write_table(pa.Table.from_pylist(rows).replace_schema_metadata(metadata), p)
        for engine in ('python', 'gdal'):
            self.rasterize(p, sha256_file(p), self.path / engine, self.config, self.grid, engine=engine)
        self.assertEqual(
            sha256_file(self.path / 'python/water.tif'), sha256_file(self.path / 'gdal/water.tif')
        )

    def test_point_shortcut_matches_ogr_for_endianness_dimensions_and_nonfinite_values(
        self,
    ):
        out = self.path / 'point-kernel'
        out.mkdir()
        kernel = WaterBatch()
        points = [
            struct.pack(order + 'BIdd', endian, 1, x, y)
            for order, endian in (('<', 1), ('>', 0))
            for x, y in (
                (0.0, 0.0),
                (-180.0, 90.0),
                (1e300, -1e300),
                (float('nan'), 0.0),
                (0.0, float('inf')),
                (float('nan'), float('nan')),
            )
        ]
        points.extend(
            bytes(ogr.CreateGeometryFromWkt(wkt).ExportToWkb())
            for wkt in ('POINT Z (1 2 3)', 'POINT M (1 2 3)', 'POINT ZM (1 2 3 4)')
        )
        points.extend((points[0] + b'extra', points[0][:-1], b'\x02' + points[0][1:]))
        for value in points:
            with self.subTest(wkb=value.hex()):
                try:
                    geometry = ogr.CreateGeometryFromWkb(value)
                except RuntimeError:
                    geometry = None
                expected = 2 if geometry is None or geometry.IsEmpty() else 3
                raster = gdal.GetDriverByName('MEM').Create('', 8, 4, 1, gdal.GDT_Byte)
                raster.SetGeoTransform((-180, 45, 0, 90, 0, -45))
                status, failed = kernel.burn(
                    raster, pa.array([value]), [1], [8, 4, -180, 90, 45], 4
                )
                self.assertEqual(status.tolist(), [expected])
                self.assertEqual(failed, 0 if expected == 2 else None)
                self.assertEqual(int(raster.ReadAsArray().sum()), 0)

    def test_finite_points_bypass_ogr_and_failed_batches_release_parsed_geometry(self):
        kernel = WaterBatch()
        raster = gdal.GetDriverByName('MEM').Create('', 8, 4, 1, gdal.GDT_Byte)
        raster.SetGeoTransform((-180, 45, 0, 90, 0, -45))
        points = [struct.pack('<BIdd', 1, 1, 1.0, 2.0), struct.pack('>BIdd', 0, 1, -3.0, 4.0)]
        with mock.patch.object(
            ogr, 'CreateGeometryFromWkb', side_effect=AssertionError('finite point was parsed')
        ):
            status, failed = kernel.burn(raster, pa.array(points), [1, 1], [8, 4, -180, 90, 45], 4)
        self.assertEqual(status.tolist(), [3, 3])
        self.assertIsNone(failed)
        polygon = bytes(
            ogr.CreateGeometryFromWkt(
                'POLYGON ((-180 90,-135 90,-135 45,-180 45,-180 90))'
            ).ExportToWkb()
        )
        created = []
        create = ogr.CreateGeometryFromWkb

        def tracked(value):
            geometry = create(value)
            created.append(weakref.ref(geometry))
            return geometry

        with mock.patch.object(ogr, 'CreateGeometryFromWkb', side_effect=tracked):
            status, failed = kernel.burn(
                raster, pa.array([polygon, None, polygon]), [1, 1, 1], [8, 4, -180, 90, 45], 4
            )
        self.assertEqual(status.tolist(), [1, 5, 0])
        self.assertEqual(failed, 1)
        self.assertEqual(len(created), 1)
        self.assertIsNone(created[0]())
        self.assertEqual(int(raster.ReadAsArray().sum()), 0)

    def test_borrowed_tile_buffer_preserves_existing_burns_and_partial_edge_tiles(self):
        out = self.path / 'edge-kernel'
        out.mkdir()
        kernel = WaterBatch()
        raster = gdal.GetDriverByName('MEM').Create('', 7, 3, 1, gdal.GDT_Byte)
        raster.SetGeoTransform((-180, 45, 0, 90, 0, -45))
        initial = np.zeros((3, 7), dtype=np.uint8)
        initial[0, 0] = 1
        raster.GetRasterBand(1).WriteArray(initial)
        polygon = bytes(
            ogr.CreateGeometryFromWkt(
                'POLYGON ((45 0,135 0,135 -45,45 -45,45 0))'
            ).ExportToWkb()
        )
        status, failed = kernel.burn(
            raster, pa.array([polygon]), [1], [7, 3, -180, 90, 45], 4
        )
        self.assertIsNone(failed)
        self.assertEqual(status.tolist(), [1])
        initial[2, 5:7] = 1
        np.testing.assert_array_equal(raster.ReadAsArray(), initial)

    def test_water_kernel_accepts_tagged_wkb_and_rejects_other_arrow_arrays(self):
        class Wkb(pa.ExtensionType):
            def __init__(self):
                super().__init__(pa.binary(), 'geoarrow.wkb')

            def __arrow_ext_serialize__(self):
                return b''

        kernel = WaterBatch()
        grid = (8, 4, -180, 90, 45)
        raster = gdal.GetDriverByName('MEM').Create('', 8, 4, 1, gdal.GDT_Byte)
        raster.SetGeoTransform((-180, 45, 0, 90, 0, -45))
        point = ogr.CreateGeometryFromWkt('POINT (12 34)')
        storage = pa.array([bytes(point.ExportToWkb())])
        wrapped = pa.ExtensionArray.from_storage(Wkb(), storage)
        status, failure = kernel.burn(raster, wrapped, [1], grid, 4)
        self.assertEqual((status.tolist(), failure), ([3], None))
        with self.assertRaisesRegex(ValueError, 'must be a binary WKB array'):
            kernel.burn(raster, pa.array(['POINT (12 34)']), [1], grid, 4)
        with self.assertRaisesRegex(ValueError, 'unexpected strip geometry type'):
            water_batch.strip_wkb(point, 45, 0, 45, {}, ())

    def test_tile_setup_and_rasterization_errors_do_not_write_water(self):
        kernel = WaterBatch()
        grid = (8, 4, -180, 90, 45)
        raster = gdal.GetDriverByName('MEM').Create('', 8, 4, 1, gdal.GDT_Byte)
        raster.SetGeoTransform((-180, 45, 0, 90, 0, -45))
        polygon = ogr.CreateGeometryFromWkt(
            'POLYGON ((-180 90,-135 90,-135 45,-180 45,-180 90))'
        )
        geometry = pa.array([bytes(polygon.ExportToWkb())])
        for owner, function, result, message in (
            (water_batch.gdal_array, 'OpenArray', None, 'GDAL tile transform failed'),
            (gdal, 'RasterizeLayer', 1, 'GDAL water geometry rasterization failed'),
        ):
            with self.subTest(function=function), mock.patch.object(owner, function, return_value=result):
                with self.assertRaisesRegex(ValueError, message):
                    kernel.burn(raster, geometry, [1], grid, 4)
                self.assertFalse(raster.ReadAsArray().any())

    def test_multipart_water_skips_empty_and_outside_parts(self):
        kernel = WaterBatch()
        grid = (8, 4, -180, 90, 45)
        raster = gdal.GetDriverByName('MEM').Create('', 8, 4, 1, gdal.GDT_Byte)
        raster.SetGeoTransform((-180, 45, 0, 90, 0, -45))
        polygon = ogr.CreateGeometryFromWkt(
            'MULTIPOLYGON (EMPTY, ((-180 90,-135 90,-135 0,-180 0,-180 90)), '
            '((190 45,200 45,200 0,190 0,190 45)))'
        )
        geometry = pa.array([bytes(polygon.ExportToWkb())])
        with mock.patch.object(water_batch, 'strip_wkb', return_value=None):
            status, failure = kernel.burn(raster, geometry, [1], grid, 1)
        self.assertEqual((status.tolist(), failure), ([1], None))
        self.assertFalse(raster.ReadAsArray().any())
        status, failure = kernel.burn(raster, geometry, [1], grid, 1)
        self.assertEqual((status.tolist(), failure), ([1], None))
        expected = np.zeros((4, 8), dtype=np.uint8)
        expected[:2, 0] = 1
        np.testing.assert_array_equal(raster.ReadAsArray(), expected)

    def test_nonfinite_polygon_envelope_aborts_before_rasterization(self):
        raster = gdal.GetDriverByName('MEM').Create('', 8, 4, 1, gdal.GDT_Byte)
        polygon = ogr.CreateGeometryFromWkt(
            'POLYGON ((-180 90,-135 90,-135 45,-180 45,-180 90))'
        )
        geometry = pa.array([bytes(polygon.ExportToWkb())])
        with mock.patch.object(ogr.Geometry, 'GetEnvelope', return_value=(np.nan, 0, 0, 0)):
            status, failure = WaterBatch().burn(raster, geometry, [1], (8, 4, -180, 90, 45), 1)
        self.assertEqual((status.tolist(), failure), ([6], 0))
        self.assertFalse(raster.ReadAsArray().any())

    def test_hybrid_global_burn_matches_local_tiles_at_pixel_centers(self):
        p, _ = self.fixture()
        metadata = pq.read_schema(p).metadata
        cfg = json.loads(self.config.read_text())
        self.grid = Grid(3600, 24, 0.1)
        cfg['tile_size'] = 4
        self.config.write_text(json.dumps(cfg))
        rows = []
        for column in (0, 3, 4, 7, 8, 31, 60):
            x = self.grid.longitude(column)
            for edge in (np.nextafter(x, -np.inf), x, np.nextafter(x, np.inf)):
                for y in (89.95, 89.65, 89.60):
                    geom = ogr.CreateGeometryFromWkt(
                        f'POLYGON (({edge} {y},{edge+.8} {y},{edge+.8} {y-1.6},{edge} {y-1.6},{edge} {y}))'
                    )
                    rows.append(
                        {
                            'id': str(len(rows)),
                            'subtype': 'lake',
                            'geometry': bytes(geom.ExportToWkb()),
                        }
                    )
        pq.write_table(pa.Table.from_pylist(rows).replace_schema_metadata(metadata), p)
        for engine in ('python', 'gdal'):
            self.rasterize(p, sha256_file(p), self.path / engine, self.config, self.grid, 19, engine)
        np.testing.assert_array_equal(
            gdal.Open(str(self.path / 'python/water.tif')).ReadAsArray(),
            gdal.Open(str(self.path / 'gdal/water.tif')).ReadAsArray(),
        )

    def test_gdal_rejects_bad_and_empty_wkb_without_burning_batch(self):
        out = self.path / 'kernel'
        out.mkdir()
        kernel = WaterBatch()
        polygon = bytes(
            ogr.CreateGeometryFromWkt(
                'POLYGON ((-180 90,-135 90,-135 45,-180 45,-180 90))'
            ).ExportToWkb()
        )
        for bad in (
            b'',
            b'invalid',
            bytes(ogr.CreateGeometryFromWkt('POLYGON EMPTY').ExportToWkb()),
        ):
            raster = gdal.GetDriverByName('MEM').Create('', 8, 4, 1, gdal.GDT_Byte)
            raster.SetGeoTransform((-180, 45, 0, 90, 0, -45))
            status, failed = kernel.burn(
                raster, pa.array([polygon, bad]), [1, 1], [8, 4, -180, 90, 45], 4
            )
            self.assertEqual(failed, 1)
            self.assertEqual(status.tolist(), [1, 2])
            self.assertEqual(int(raster.ReadAsArray().sum()), 0)

    def test_gdal_methods_and_first_error_preserve_source_order(self):
        polygon = bytes(
            ogr.CreateGeometryFromWkt(
                'POLYGON ((-180 90,0 90,0 -45,-180 -45,-180 90))'
            ).ExportToWkb()
        )
        multipart = bytes(
            ogr.CreateGeometryFromWkt(
                'MULTIPOLYGON (((-180 90,-135 90,-135 45,-180 45,-180 90)),((135 0,180 0,180 -45,135 -45,135 0)))'
            ).ExportToWkb()
        )
        results = []
        for method in ('hybrid', 'tiled'):
            out = self.path / method
            out.mkdir()
            kernel = WaterBatch(method)
            raster = gdal.GetDriverByName('MEM').Create('', 8, 4, 1, gdal.GDT_Byte)
            raster.SetGeoTransform((-180, 45, 0, 90, 0, -45))
            status, failed = kernel.burn(
                raster,
                pa.array([polygon, multipart] * 25),
                [1] * 50,
                [8, 4, -180, 90, 45],
                2,
            )
            self.assertIsNone(failed)
            self.assertEqual(status.tolist(), [1] * 50)
            results.append(raster.ReadAsArray())
            # A later malformed row can finish earlier than a broad polygon.
            # Diagnostics still report the first failure and nothing is burned.
            raster.GetRasterBand(1).Fill(0)
            status, failed = kernel.burn(
                raster,
                pa.array([polygon, None, polygon, b'bad', polygon]),
                [1] * 5,
                [8, 4, -180, 90, 45],
                2,
            )
            self.assertEqual(failed, 1)
            self.assertEqual(status.tolist(), [1, 5, 0, 0, 0])
            self.assertEqual(int(raster.ReadAsArray().sum()), 0)
        for result in results[1:]:
            np.testing.assert_array_equal(result, results[0])
        out = self.path / 'vector'
        out.mkdir()
        with self.assertRaisesRegex(ValueError, 'global vector mode does not preserve'):
            WaterBatch('vector')

    def test_production_grid_center_tie_edges_keep_reference_values(self):
        p, _ = self.fixture()
        metadata = pq.read_schema(p).metadata
        # Actual incident edges, from official Overture shards29/31. Extending
        # the opposite edge preserves each incident interior and makes tiny cases.
        edges = [
            [(27.97825, 66.2405), (27.978, 66.24075)],
            [(88.01575, 68.32825), (88.0155, 68.328)],
        ]
        rows = []
        for i, (a, b) in enumerate(edges):
            shift = -3 if i == 0 else 3
            points = [a, b, (b[0] + shift, b[1]), (a[0] + shift, a[1]), a]
            wkt = 'POLYGON ((' + ','.join(f'{x} {y}' for x, y in points) + '))'
            rows.append(
                {
                    'id': str(i),
                    'subtype': 'lake',
                    'geometry': bytes(ogr.CreateGeometryFromWkt(wkt).ExportToWkb()),
                }
            )
        pq.write_table(pa.Table.from_pylist(rows).replace_schema_metadata(metadata), p)
        cfg = json.loads(self.config.read_text())
        self.grid = Grid(131072, 54614, 360 / 131072)
        cfg['tile_size'] = 1024
        self.config.write_text(json.dumps(cfg))
        reports = []
        for engine in ('python', 'gdal'):
            out = self.path / engine
            self.rasterize(p, sha256_file(p), out, self.config, self.grid, engine=engine)
            reports.append(json.loads((out / 'report.json').read_text()))
            raster = gdal.Open(str(out / 'water.tif'))
            self.assertEqual(int(raster.ReadAsArray(75722, 8650, 1, 1)[0, 0]), 1)
            self.assertEqual(int(raster.ReadAsArray(97581, 7890, 1, 1)[0, 0]), 0)
        self.assertEqual(reports[0]['output_sha256'], reports[1]['output_sha256'])

    def test_strip_pruning_preserves_dense_rings_holes_multipart_and_z(self):
        p, _ = self.fixture()
        metadata = pq.read_schema(p).metadata

        def wave(center, amplitude):
            xs = np.linspace(-170, 170, 1001)
            ys = center + amplitude * np.sin(xs / 7)
            points = list(zip(xs, ys + 2)) + list(zip(xs[::-1], (ys - 2)[::-1]))
            outer = ogr.Geometry(ogr.wkbLinearRing)
            for x, y in points + [points[0]]:
                outer.AddPoint_2D(float(x), float(y))
            polygon = ogr.Geometry(ogr.wkbPolygon)
            polygon.AddGeometry(outer)
            hole = ogr.Geometry(ogr.wkbLinearRing)
            for angle in np.linspace(0, 2 * np.pi, 81):
                hole.AddPoint_2D(float(0.1 * np.cos(angle)), float(center + 0.5 * np.sin(angle)))
            hole.CloseRings()
            polygon.AddGeometry(hole)
            self.assertTrue(polygon.IsValid())
            return polygon

        north, south = wave(40, 12), wave(-35, 10)
        multi = ogr.Geometry(ogr.wkbMultiPolygon)
        multi.AddGeometry(north)
        multi.AddGeometry(south)
        elevated = north.Clone()
        elevated.Set3D(True)
        rows = [
            {'id': str(i), 'subtype': 'lake', 'geometry': bytes(g.ExportToWkb())}
            for i, g in enumerate((north, multi, elevated))
        ]
        pq.write_table(pa.Table.from_pylist(rows).replace_schema_metadata(metadata), p)
        cfg = json.loads(self.config.read_text())
        self.grid = Grid(64, 32, 5.625)
        cfg['tile_size'] = 4
        self.config.write_text(json.dumps(cfg))
        reports = []
        for engine in ('python', 'gdal'):
            out = self.path / engine
            self.rasterize(p, sha256_file(p), out, self.config, self.grid, engine=engine)
            reports.append(json.loads((out / 'report.json').read_text()))
        self.assertEqual(reports[0]['output_sha256'], reports[1]['output_sha256'])

    def test_batch_size_comes_from_settings(self):
        p, digest = self.fixture()
        cfg = json.loads(self.config.read_text())
        cfg['batch_size'] = 2
        self.config.write_text(json.dumps(cfg))
        out = self.path / 'batch-configured'
        self.rasterize(p, digest, out, self.config, self.grid)
        self.assertEqual(json.loads((out / 'report.json').read_text())['batch_size'], 2)

    def test_subtype_only_accepts_without_sources_or_class(self):
        polygon = bytes(
            ogr.CreateGeometryFromWkt(
                'POLYGON ((-170 80,-120 80,-120 40,-170 40,-170 80))'
            ).ExportToWkb()
        )
        rows = [
            {'id': 'valid', 'subtype': 'lake', 'geometry': polygon},
            {'id': 'ocean', 'subtype': 'ocean', 'geometry': polygon},
            {'id': 'label', 'subtype': 'physical', 'geometry': polygon},
        ]
        table = pa.Table.from_pylist(rows).replace_schema_metadata(
            {
                b'geo': json.dumps(
                    {'primary_column': 'geometry', 'columns': {'geometry': {'encoding': 'WKB'}}}
                ).encode()
            }
        )
        p = self.inputs / 'minimal.parquet'
        pq.write_table(table, p)
        out = self.path / 'minimal-output'
        self.rasterize(p, hashlib.sha256(p.read_bytes()).hexdigest(), out, self.config, self.grid)
        report = json.loads((out / 'report.json').read_text())
        self.assertEqual(report['counts']['polygons'], 1)
        self.assertEqual(report['counts']['excluded_classification'], 2)
        self.assertEqual(build.selected('lake'), None)
        self.assertEqual(build.selected(None), 'missing_classification')
        self.assertEqual(build.selected(''), 'missing_classification')

    def test_unsupported_water_settings_schema_is_rejected(self):
        p, digest = self.fixture()
        cfg = json.loads(self.config.read_text())
        cfg['schema'] = 'water-shard-candidate-v1'
        self.config.write_text(json.dumps(cfg))
        out = self.path / 'old-schema'
        with self.assertRaisesRegex(ValueError, 'schema'):
            self.rasterize(p, digest, out, self.config, self.grid)
        self.assertFalse(out.exists())

    def test_compiled_engine_configuration_is_rejected_before_output(self):
        p, digest = self.fixture()
        cfg = json.loads(self.config.read_bytes())
        cfg['rasterizer'] = 'native'
        self.config.write_text(json.dumps(cfg))
        out = self.path / 'retired-engine'
        with self.assertRaisesRegex(ValueError, 'rasterizer'):
            self.rasterize(p, digest, out, self.config, self.grid)
        self.assertFalse(out.exists())

    def test_free_space_guard(self):
        p, digest = self.fixture()
        cfg = json.loads(self.config.read_text())
        cfg['minimum_free_bytes'] = 1 << 60
        self.config.write_text(json.dumps(cfg))
        out = self.path / 'no-space'
        with self.assertRaisesRegex(ValueError, 'free disk below configured reserve'):
            self.rasterize(p, digest, out, self.config, self.grid)
        self.assertFalse(out.exists())

    def test_progress_can_report_rss_on_platforms_with_or_without_proc(self):
        source, digest = self.fixture()
        proc = Path('/proc/self/status')
        normal_read = Path.read_text
        for available in (False, True):
            with self.subTest(available=available):
                progress = []

                def read(path, *args, **kwargs):
                    if path != proc:
                        return normal_read(path, *args, **kwargs)
                    if not available:
                        raise FileNotFoundError(proc)
                    return 'Name:\tpython\nVmRSS:\t128 kB\n'

                with mock.patch.object(Path, 'read_text', new=read):
                    self.rasterize(
                        source, digest, self.path / f'proc-{available}', self.config, self.grid,
                        emit=lambda line, **_: progress.append(json.loads(line)),
                    )
                expected = 'VmRSS:\t128 kB' if available else 'unavailable'
                self.assertTrue(progress)
                self.assertTrue(all(item['rss'] == expected for item in progress))

    def test_water_shard_leaves_no_report_when_disk_space_drops_during_rasterization(self):
        source, digest = self.fixture()
        cfg = json.loads(self.config.read_text())
        self.config.write_text(json.dumps(dict(cfg, minimum_free_bytes=1)))
        out = self.path / 'low-space'
        with mock.patch.object(
            build.shutil, 'disk_usage',
            side_effect=lambda path: SimpleNamespace(free=0 if Path(path) == out.resolve() else 1024),
        ):
            with self.assertRaisesRegex(ValueError, 'partial output preserved'):
                self.rasterize(source, digest, out, self.config, self.grid)
        self.assertFalse((out / 'report.json').exists())

    def test_water_report_requires_unchanged_source(self):
        source, digest = self.fixture()
        original = source.read_bytes()
        out = self.path / 'changed-source'

        def change(*_, **__):
            source.write_bytes(original + b'\n')

        with self.assertRaisesRegex(ValueError, 'source changed during processing'):
            self.rasterize(source, digest, out, self.config, self.grid, emit=change)
        self.assertFalse((out / 'report.json').exists())

    def test_reports_source_id_for_missing_and_empty_selected_geometry(self):
        source, _ = self.fixture()
        table = pq.read_table(source)
        empty_polygon = bytes(ogr.CreateGeometryFromWkt('POLYGON EMPTY').ExportToWkb())
        for replacement, message in (
            (None, 'missing geometry: lake'),
            (empty_polygon, 'invalid or empty WKB geometry: lake'),
        ):
            rows = table.to_pylist()
            rows[0]['geometry'] = replacement
            pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), source)
            for engine in ('gdal', 'python'):
                with self.subTest(engine=engine, message=message):
                    out = self.path / f'{engine}-{replacement is None}'
                    with self.assertRaisesRegex(ValueError, message):
                        self.rasterize(source, sha256_file(source), out, self.config, self.grid, engine=engine)
                    self.assertFalse((out / 'report.json').exists())

    def test_python_rasterizer_reports_invalid_polygon_with_same_id_as_gdal(self):
        source, _ = self.fixture()
        table = pq.read_table(source)
        rows = table.to_pylist()
        rows[0]['geometry'] = bytes(
            ogr.CreateGeometryFromWkt(
                'POLYGON ((-170 80,-120 40,-170 40,-120 80,-170 80))'
            ).ExportToWkb()
        )
        pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), source)
        reports = []
        for engine in ('gdal', 'python'):
            out = self.path / engine
            with self.assertRaisesRegex(ValueError, 'incomplete water shard'):
                self.rasterize(source, sha256_file(source), out, self.config, self.grid, engine=engine)
            reports.append(json.loads((out / 'report.json').read_text()))
            self.assertEqual(json.loads((out / 'invalid-feature-ids.json').read_text()), ['lake'])
        self.assertEqual(reports[0]['counts'], reports[1]['counts'])
        self.assertTrue(all(r['status'] == 'incomplete-input-issues' for r in reports))

    def test_unprocessed_rows_leave_an_incomplete_report(self):
        source, digest = self.fixture()
        out = self.path / 'incomplete-rows'
        with mock.patch.object(build, 'gdal_batch'):
            with self.assertRaisesRegex(ValueError, 'incomplete water shard'):
                self.rasterize(source, digest, out, self.config, self.grid)
        report = json.loads((out / 'report.json').read_text())
        self.assertEqual(report['status'], 'incomplete-input-issues')
        self.assertEqual(report['rows_in_source'], 6)
        self.assertEqual(report['counts'].get('rows', 0), 0)

    def test_shard_input_declares_expected_grid_policy_and_geometry_format(self):
        source, digest = self.fixture()
        cfg = json.loads(self.config.read_text())
        out = self.path / 'invalid'
        table = pq.read_table(source)
        for column, message in (
            (dict(encoding='WKT'), 'unexpected GeoParquet geometry encoding'),
            (dict(encoding='WKB', crs=None), 'unsupported explicit CRS'),
        ):
            with self.subTest(column=column):
                metadata = dict(primary_column='geometry', columns=dict(geometry=column))
                pq.write_table(
                    table.replace_schema_metadata({b'geo': json.dumps(metadata).encode()}),
                    source,
                )
                with self.assertRaisesRegex(ValueError, message):
                    self.rasterize(source, sha256_file(source), out, self.config, self.grid)
                self.assertFalse(out.exists())

    def test_integrity_and_collision(self):
        p, digest = self.fixture()
        with self.assertRaises(ValueError):
            self.rasterize(p, '0' * 64, self.path / 'bad', self.config, self.grid)
        self.assertFalse((self.path / 'bad').exists())
        existing = self.path / 'existing'
        existing.mkdir()
        with self.assertRaises(FileExistsError):
            self.rasterize(p, digest, existing, self.config, self.grid)
        with self.assertRaises(FileExistsError):
            self.rasterize(p, digest, self.path, self.config, self.grid)


if __name__ == '__main__':
    unittest.main()
