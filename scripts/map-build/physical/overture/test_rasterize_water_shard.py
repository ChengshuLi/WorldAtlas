import hashlib
import json
import struct
import tempfile
import unittest
import weakref
from pathlib import Path
from unittest import mock
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from osgeo import gdal, ogr
import rasterize_water_shard as build
from water_batch import WaterBatch

class WaterShardTests(unittest.TestCase):
    def test_arrow_policy_matches_python_for_whitespace_and_dictionary_strings(self):
        values=['ocean','physical','lake',' ocean ','',None,*build.PYTHON_WHITESPACE,
                '\x1c\x1d\x1e\x1f','\u2000\u3000','\u200blake','\u200b']
        expected=[build.selected(v) for v in values]
        for array in (pa.array(values),pa.array(values).dictionary_encode()):
            eligible,missing,excluded=build.classifications(array)
            self.assertEqual(eligible.tolist(),[reason is None for reason in expected])
            self.assertEqual(missing,expected.count('missing_classification'))
            self.assertEqual(excluded,expected.count('excluded_classification'))
        self.assertEqual(build.classifications(pa.array([1,2,None]))[0].tolist(),[0,0,0])
    def test_diagnostic_ids_cross_row_groups_and_preserve_requested_order(self):
        p,_=self.fixture();table=pq.read_table(p);pq.write_table(table,p,row_group_size=2)
        ids=build.SourceIds(pq.ParquetFile(p))
        self.assertEqual(ids.get([5,0,2,5]),['pool','lake','label','pool'])
        self.assertEqual(ids.get([]),[])
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.path = Path(self.tmp.name)
        self.inputs=self.path/'inputs';self.inputs.mkdir()
        cfg={'schema':'water-shard-candidate-v2', 'grid':{'width':32,'height':16,'west':-180,'north':90,'step':11.25},
             'tile_size':4, 'selection_notes':'synthetic test',
             'policy':{'method':'overture-inland-subtype-v1'}}
        self.config=self.inputs/'config.json';self.config.write_text(json.dumps(cfg))
    def tearDown(self):
        self.tmp.cleanup()
    def fixture(self):
        def wkt(s): return bytes(ogr.CreateGeometryFromWkt(s).ExportToWkb())
        osm = [{'property':'', 'dataset':'OpenStreetMap'}]; alt = [{'property':'', 'dataset':'Other'}]
        polygon = wkt('POLYGON ((-170 80,-120 80,-120 40,-170 40,-170 80))')
        rows = [
          {'id':'lake', 'subtype':'lake','class':'lake','sources':osm,'geometry':polygon},
          {'id':'ocean', 'subtype':'ocean','class':'ocean','sources':osm,'geometry':polygon},
          {'id':'label', 'subtype':'physical','class':'bay','sources':osm,'geometry':polygon},
          {'id':'other', 'subtype':'lake','class':'sea','sources':alt,'geometry':polygon},
          {'id':'line', 'subtype':'river','class':'river','sources':osm,'geometry':wkt('LINESTRING (-170 80,-120 40)')},
          {'id':'pool', 'subtype':'human_made','class':'swimming_pool','sources':osm,'geometry':polygon}]
        table = pa.Table.from_pylist(rows).replace_schema_metadata({b'geo':json.dumps({'primary_column':'geometry','columns':{'geometry':{'encoding':'WKB'}}}).encode()})
        p = self.inputs/'water.parquet'; pq.write_table(table,p)
        return p, hashlib.sha256(p.read_bytes()).hexdigest()
    def test_policy_and_batch_invariance(self):
        p, digest = self.fixture()
        for n in (1, 10):
            out = self.path/f'o{n}'; build.run(p,digest,out,self.config,n)
            report = json.loads((out/'report.json').read_text())
            self.assertEqual(report['counts']['polygons'],3)
            self.assertEqual(report['counts']['excluded_classification'],2)
            self.assertEqual(report['counts']['non_polygon'],1)
            self.assertNotIn('no_selected_geometry_provenance',report['counts'])
            self.assertEqual(report['status'],'candidate-only')
        a = gdal.Open(str(self.path/'o1/water.tif')).ReadAsArray()
        b = gdal.Open(str(self.path/'o10/water.tif')).ReadAsArray()
        np.testing.assert_array_equal(a,b); self.assertGreater(a.sum(),0); self.assertLess(a.sum(),a.size)
        target = gdal.GetDriverByName('MEM').Create('', 32,16,1,gdal.GDT_Byte)
        target.SetGeoTransform((-180,11.25,0,90,0,-11.25))
        ds = ogr.GetDriverByName('Memory').CreateDataSource(''); layer = ds.CreateLayer('x',geom_type=ogr.wkbPolygon)
        feat = ogr.Feature(layer.GetLayerDefn()); feat.SetGeometry(ogr.CreateGeometryFromWkt('POLYGON ((-170 80,-120 80,-120 40,-170 40,-170 80))')); layer.CreateFeature(feat)
        gdal.RasterizeLayer(target,[1],layer,burn_values=[1])
        np.testing.assert_array_equal(a,target.ReadAsArray())
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
            'POINT (0 0)', 'LINESTRING (-180 90,180 -45)',
            'GEOMETRYCOLLECTION (POINT (0 0))',
        ]
        for i, wkt in enumerate(geometries):
            rows.append({'id':str(i),'subtype':'lake','geometry':bytes(ogr.CreateGeometryFromWkt(wkt).ExportToWkb())})
        rng = np.random.default_rng(714)
        for i in range(100):
            x,y = rng.uniform(-200,180),rng.uniform(-60,95)
            w,h = rng.uniform(.001,80),rng.uniform(.001,60)
            geom = ogr.CreateGeometryFromWkt(f'POLYGON (({x} {y},{x+w} {y},{x+w} {y-h},{x} {y-h},{x} {y}))')
            rows.append({'id':f'random-{i}','subtype':'lake','geometry':bytes(geom.ExportToWkb())})
        table = pa.Table.from_pylist(rows).replace_schema_metadata(table.schema.metadata)
        pq.write_table(table,p);digest = build.sha256(p)
        reports=[]
        for engine in ('python','gdal'):
            out=self.path/engine;build.run(p,digest,out,self.config,17,engine)
            reports.append(json.loads((out/'report.json').read_text()))
        self.assertEqual(reports[0]['counts'],reports[1]['counts'])
        np.testing.assert_array_equal(gdal.Open(str(self.path/'python/water.tif')).ReadAsArray(),
                                      gdal.Open(str(self.path/'gdal/water.tif')).ReadAsArray())
        self.assertEqual(reports[0]['output_sha256'],reports[1]['output_sha256'])

    def test_gdal_arrow_slices_large_offsets_and_validity_bitmap(self):
        out=self.path/'kernel';out.mkdir();kernel=WaterBatch(out)
        polygon=bytes(ogr.CreateGeometryFromWkt('POLYGON ((-180 90,-135 90,-135 45,-180 45,-180 90))').ExportToWkb())
        for dtype in (pa.binary(),pa.large_binary()):
            geometry=pa.array([polygon,None,polygon,None,polygon],type=dtype).slice(2,3)
            raster=gdal.GetDriverByName('MEM').Create('',8,4,1,gdal.GDT_Byte)
            raster.SetGeoTransform((-180,45,0,90,0,-45))
            status,failed=kernel.burn(raster,geometry,[1,0,1],[8,4,-180,90,45],4)
            self.assertIsNone(failed);self.assertEqual(status.tolist(),[1,0,1])
            self.assertEqual(int(raster.ReadAsArray().sum()),1)
            status,failed=kernel.burn(raster,geometry,[1,1,1],[8,4,-180,90,45],4)
            self.assertEqual(failed,1);self.assertEqual(status.tolist(),[1,5,0])

    def test_batch_backend_does_not_compile_or_start_processes(self):
        import ctypes
        import subprocess
        p,digest=self.fixture()
        with mock.patch.object(subprocess,'Popen',side_effect=AssertionError('unexpected subprocess')), \
                mock.patch.object(ctypes,'CDLL',side_effect=AssertionError('unexpected ctypes bridge')), \
                mock.patch.object(ogr,'Feature',side_effect=AssertionError('unexpected per-row Feature creation')):
            first=WaterBatch();second=WaterBatch()
            build.run(p,digest,self.path/'python-api',self.config)
        self.assertEqual(first.provenance,second.provenance)
        first.timings['tile_burn_seconds']=1
        self.assertEqual(second.timings['tile_burn_seconds'],0)

    def test_vector_point_status_preserves_first_failure_and_unselected_rows(self):
        kernel=WaterBatch();point=struct.pack('<BIdd',1,1,1.,2.)
        for values,selected,expected in (([point,None,point],[1,1,1],[3,5,0]),
                                        ([None,point,None],[0,1,0],[0,3,0])):
            raster=gdal.GetDriverByName('MEM').Create('',8,4,1,gdal.GDT_Byte)
            status,failed=kernel.burn(raster,pa.array(values),selected,[8,4,-180,90,45],4)
            self.assertEqual(status.tolist(),expected)
            self.assertEqual(failed,1 if expected==[3,5,0] else None)

    def test_arrow_tile_layers_preserve_big_endian_m_zm_and_trailing_wkb(self):
        p,_=self.fixture();metadata=pq.read_schema(p).metadata;rows=[]
        for i,wkt in enumerate(('POLYGON ((-170 80,-120 80,-120 -20,-170 -20,-170 80))',
                'POLYGON M ((-100 80 1,-40 80 2,-40 -20 3,-100 -20 4,-100 80 1))',
                'POLYGON ZM ((20 80 1 2,100 80 3 4,100 -20 5 6,20 -20 7 8,20 80 1 2))')):
            geometry=ogr.CreateGeometryFromWkt(wkt)
            for order in (ogr.wkbXDR,ogr.wkbNDR):
                value=bytes(geometry.ExportToWkb(order))
                rows.append({'id':str(len(rows)),'subtype':'lake','geometry':value})
            rows.append({'id':str(len(rows)),'subtype':'lake','geometry':value+b'extra'})
        pq.write_table(pa.Table.from_pylist(rows).replace_schema_metadata(metadata),p)
        for engine in ('python','gdal'):
            build.run(p,build.sha256(p),self.path/engine,self.config,engine=engine)
        self.assertEqual(build.sha256(self.path/'python/water.tif'),build.sha256(self.path/'gdal/water.tif'))

    def test_point_shortcut_matches_ogr_for_endianness_dimensions_and_nonfinite_values(self):
        out=self.path/'point-kernel';out.mkdir();kernel=WaterBatch(out)
        points=[struct.pack(order+'BIdd',endian,1,x,y)
                for order,endian in (('<',1),('>',0))
                for x,y in ((0.,0.),(-180.,90.),(1e300,-1e300),(float('nan'),0.),
                            (0.,float('inf')),(float('nan'),float('nan')))]
        points.extend(bytes(ogr.CreateGeometryFromWkt(wkt).ExportToWkb())
                      for wkt in ('POINT Z (1 2 3)','POINT M (1 2 3)','POINT ZM (1 2 3 4)'))
        points.extend((points[0]+b'extra',points[0][:-1],b'\x02'+points[0][1:]))
        for value in points:
            with self.subTest(wkb=value.hex()):
                try:geometry=ogr.CreateGeometryFromWkb(value)
                except RuntimeError:geometry=None
                expected=2 if geometry is None or geometry.IsEmpty() else 3
                raster=gdal.GetDriverByName('MEM').Create('',8,4,1,gdal.GDT_Byte)
                raster.SetGeoTransform((-180,45,0,90,0,-45))
                status,failed=kernel.burn(raster,pa.array([value]),[1],[8,4,-180,90,45],4)
                self.assertEqual(status.tolist(),[expected])
                self.assertEqual(failed,0 if expected==2 else None)
                self.assertEqual(int(raster.ReadAsArray().sum()),0)

    def test_finite_points_bypass_ogr_and_failed_batches_release_parsed_geometry(self):
        kernel=WaterBatch();raster=gdal.GetDriverByName('MEM').Create('',8,4,1,gdal.GDT_Byte)
        raster.SetGeoTransform((-180,45,0,90,0,-45))
        points=[struct.pack('<BIdd',1,1,1.,2.),struct.pack('>BIdd',0,1,-3.,4.)]
        with mock.patch.object(ogr,'CreateGeometryFromWkb',side_effect=AssertionError('finite point was parsed')):
            status,failed=kernel.burn(raster,pa.array(points),[1,1],[8,4,-180,90,45],4)
        self.assertEqual(status.tolist(),[3,3]);self.assertIsNone(failed)
        polygon=bytes(ogr.CreateGeometryFromWkt('POLYGON ((-180 90,-135 90,-135 45,-180 45,-180 90))').ExportToWkb())
        created=[];create=ogr.CreateGeometryFromWkb
        def tracked(value):
            geometry=create(value);created.append(weakref.ref(geometry));return geometry
        with mock.patch.object(ogr,'CreateGeometryFromWkb',side_effect=tracked):
            status,failed=kernel.burn(raster,pa.array([polygon,None,polygon]),[1,1,1],[8,4,-180,90,45],4)
        self.assertEqual(status.tolist(),[1,5,0]);self.assertEqual(failed,1);self.assertEqual(len(created),1)
        self.assertIsNone(created[0]())
        self.assertEqual(int(raster.ReadAsArray().sum()),0)

    def test_borrowed_tile_buffer_preserves_existing_burns_and_partial_edge_tiles(self):
        out=self.path/'edge-kernel';out.mkdir();kernel=WaterBatch(out)
        raster=gdal.GetDriverByName('MEM').Create('',7,3,1,gdal.GDT_Byte)
        raster.SetGeoTransform((-180,45,0,90,0,-45))
        initial=np.zeros((3,7),dtype=np.uint8);initial[0,0]=1
        raster.GetRasterBand(1).WriteArray(initial)
        polygon=bytes(ogr.CreateGeometryFromWkt('POLYGON ((45 0,135 0,135 -45,45 -45,45 0))').ExportToWkb())
        status,failed=kernel.burn(raster,pa.array([polygon]),[1],[7,3,-180,90,45],4)
        self.assertIsNone(failed);self.assertEqual(status.tolist(),[1])
        initial[2,5:7]=1
        np.testing.assert_array_equal(raster.ReadAsArray(),initial)

    def test_hybrid_global_burn_matches_local_tiles_at_pixel_centers(self):
        p,_=self.fixture();metadata=pq.read_schema(p).metadata
        cfg=json.loads(self.config.read_text())
        cfg['grid']={'width':64,'height':24,'west':-3.17,'north':2.13,'step':.1}
        cfg['tile_size']=4;self.config.write_text(json.dumps(cfg));rows=[]
        for column in (0,3,4,7,8,31,60):
            x=-3.17+(column+.5)*.1
            for edge in (np.nextafter(x,-np.inf),x,np.nextafter(x,np.inf)):
                for y in (2.08,1.78,1.73):
                    geom=ogr.CreateGeometryFromWkt(f'POLYGON (({edge} {y},{edge+.8} {y},{edge+.8} {y-1.6},{edge} {y-1.6},{edge} {y}))')
                    rows.append({'id':str(len(rows)),'subtype':'lake','geometry':bytes(geom.ExportToWkb())})
        pq.write_table(pa.Table.from_pylist(rows).replace_schema_metadata(metadata),p)
        for engine in ('python','gdal'):
            build.run(p,build.sha256(p),self.path/engine,self.config,19,engine)
        np.testing.assert_array_equal(gdal.Open(str(self.path/'python/water.tif')).ReadAsArray(),
                                      gdal.Open(str(self.path/'gdal/water.tif')).ReadAsArray())

    def test_gdal_rejects_bad_and_empty_wkb_without_burning_batch(self):
        out=self.path/'kernel';out.mkdir();kernel=WaterBatch(out)
        polygon=bytes(ogr.CreateGeometryFromWkt('POLYGON ((-180 90,-135 90,-135 45,-180 45,-180 90))').ExportToWkb())
        for bad in (b'',b'invalid',bytes(ogr.CreateGeometryFromWkt('POLYGON EMPTY').ExportToWkb())):
            raster=gdal.GetDriverByName('MEM').Create('',8,4,1,gdal.GDT_Byte)
            raster.SetGeoTransform((-180,45,0,90,0,-45))
            status,failed=kernel.burn(raster,pa.array([polygon,bad]),[1,1],[8,4,-180,90,45],4)
            self.assertEqual(failed,1);self.assertEqual(status.tolist(),[1,2])
            self.assertEqual(int(raster.ReadAsArray().sum()),0)

    def test_gdal_methods_and_first_error_preserve_source_order(self):
        polygon=bytes(ogr.CreateGeometryFromWkt('POLYGON ((-180 90,0 90,0 -45,-180 -45,-180 90))').ExportToWkb())
        multipart=bytes(ogr.CreateGeometryFromWkt('MULTIPOLYGON (((-180 90,-135 90,-135 45,-180 45,-180 90)),((135 0,180 0,180 -45,135 -45,135 0)))').ExportToWkb())
        results=[]
        for method in ('hybrid','tiled'):
            out=self.path/method;out.mkdir();kernel=WaterBatch(out,method)
            raster=gdal.GetDriverByName('MEM').Create('',8,4,1,gdal.GDT_Byte)
            raster.SetGeoTransform((-180,45,0,90,0,-45))
            status,failed=kernel.burn(raster,pa.array([polygon,multipart]*25),[1]*50,[8,4,-180,90,45],2)
            self.assertIsNone(failed);self.assertEqual(status.tolist(),[1]*50)
            results.append(raster.ReadAsArray())
            # A later malformed row can finish earlier than a broad polygon.
            # Diagnostics still report the first failure and nothing is burned.
            raster.GetRasterBand(1).Fill(0)
            status,failed=kernel.burn(raster,pa.array([polygon,None,polygon,b'bad',polygon]),[1]*5,[8,4,-180,90,45],2)
            self.assertEqual(failed,1);self.assertEqual(status.tolist(),[1,5,0,0,0])
            self.assertEqual(int(raster.ReadAsArray().sum()),0)
        for result in results[1:]:np.testing.assert_array_equal(result,results[0])
        out=self.path/'vector';out.mkdir()
        with self.assertRaisesRegex(ValueError,'global vector mode does not preserve'):
            WaterBatch(out,'vector')

    def test_production_grid_center_tie_edges_keep_reference_values(self):
        p,_=self.fixture();metadata=pq.read_schema(p).metadata
        # Actual incident edges, from official Overture shards29/31. Extending
        # the opposite edge preserves each incident interior and makes tiny cases.
        edges=[[(27.97825,66.2405),(27.978,66.24075)],
               [(88.01575,68.32825),(88.0155,68.328)]]
        rows=[]
        for i,(a,b) in enumerate(edges):
            shift=-3 if i==0 else 3
            points=[a,b,(b[0]+shift,b[1]),(a[0]+shift,a[1]),a]
            wkt='POLYGON (('+','.join(f'{x} {y}' for x,y in points)+'))'
            rows.append({'id':str(i),'subtype':'lake','geometry':bytes(ogr.CreateGeometryFromWkt(wkt).ExportToWkb())})
        pq.write_table(pa.Table.from_pylist(rows).replace_schema_metadata(metadata),p)
        cfg=json.loads(self.config.read_text());cfg['grid']={'width':131072,'height':54614,'west':-180,'north':90,'step':360/131072}
        cfg['tile_size']=1024;self.config.write_text(json.dumps(cfg));reports=[]
        for engine in ('python','gdal'):
            out=self.path/engine;build.run(p,build.sha256(p),out,self.config,engine=engine)
            reports.append(json.loads((out/'report.json').read_text()))
            raster=gdal.Open(str(out/'water.tif'))
            self.assertEqual(int(raster.ReadAsArray(75722,8650,1,1)[0,0]),1)
            self.assertEqual(int(raster.ReadAsArray(97581,7890,1,1)[0,0]),0)
        self.assertEqual(reports[0]['output_sha256'],reports[1]['output_sha256'])

    def test_strip_pruning_preserves_dense_rings_holes_multipart_and_z(self):
        p,_=self.fixture();metadata=pq.read_schema(p).metadata
        def wave(center,amplitude):
            xs=np.linspace(-170,170,1001);ys=center+amplitude*np.sin(xs/7)
            points=list(zip(xs,ys+2))+list(zip(xs[::-1],(ys-2)[::-1]))
            outer=ogr.Geometry(ogr.wkbLinearRing)
            for x,y in points+[points[0]]:outer.AddPoint_2D(float(x),float(y))
            polygon=ogr.Geometry(ogr.wkbPolygon);polygon.AddGeometry(outer)
            hole=ogr.Geometry(ogr.wkbLinearRing)
            for angle in np.linspace(0,2*np.pi,81):hole.AddPoint_2D(float(.1*np.cos(angle)),float(center+.5*np.sin(angle)))
            hole.CloseRings();polygon.AddGeometry(hole);self.assertTrue(polygon.IsValid());return polygon
        north,south=wave(40,12),wave(-35,10)
        multi=ogr.Geometry(ogr.wkbMultiPolygon);multi.AddGeometry(north);multi.AddGeometry(south)
        elevated=north.Clone();elevated.Set3D(True)
        rows=[{'id':str(i),'subtype':'lake','geometry':bytes(g.ExportToWkb())} for i,g in enumerate((north,multi,elevated))]
        pq.write_table(pa.Table.from_pylist(rows).replace_schema_metadata(metadata),p)
        cfg=json.loads(self.config.read_text());cfg['grid']={'width':64,'height':32,'west':-180,'north':90,'step':5.625}
        cfg['tile_size']=4;self.config.write_text(json.dumps(cfg));reports=[]
        for engine in ('python','gdal'):
            out=self.path/engine;build.run(p,build.sha256(p),out,self.config,engine=engine)
            reports.append(json.loads((out/'report.json').read_text()))
        self.assertEqual(reports[0]['output_sha256'],reports[1]['output_sha256'])
    def test_batch_config_and_override(self):
        p,digest=self.fixture();cfg=json.loads(self.config.read_text());cfg['batch_size']=2
        self.config.write_text(json.dumps(cfg))
        for name,override,expected in [('config',None,2),('override',3,3)]:
            out=self.path/name;build.run(p,digest,out,self.config,override)
            self.assertEqual(json.loads((out/'report.json').read_text())['batch_size'],expected)
        cfg['batch_size']=True;self.config.write_text(json.dumps(cfg))
        with self.assertRaisesRegex(ValueError,'positive integer'):
            build.run(p,digest,self.path/'invalid-batch',self.config)
        self.assertFalse((self.path/'invalid-batch').exists())

    def test_subtype_only_accepts_without_sources_or_class(self):
        polygon=bytes(ogr.CreateGeometryFromWkt('POLYGON ((-170 80,-120 80,-120 40,-170 40,-170 80))').ExportToWkb())
        rows=[{'id':'valid','subtype':'lake','geometry':polygon},{'id':'ocean','subtype':'ocean','geometry':polygon}, {'id':'label','subtype':'physical','geometry':polygon}]
        table=pa.Table.from_pylist(rows).replace_schema_metadata({b'geo':json.dumps({'primary_column':'geometry','columns':{'geometry':{'encoding':'WKB'}}}).encode()})
        p=self.inputs/'minimal.parquet';pq.write_table(table,p);out=self.path/'minimal-output';build.run(p,hashlib.sha256(p.read_bytes()).hexdigest(),out,self.config)
        report=json.loads((out/'report.json').read_text());self.assertEqual(report['counts']['polygons'],1);self.assertEqual(report['counts']['excluded_classification'],2)
        self.assertEqual(build.selected('lake'),None);self.assertEqual(build.selected(None),'missing_classification');self.assertEqual(build.selected(''),'missing_classification')
    def test_old_policy_rejected_instead_of_silently_reinterpreted(self):
        p,digest=self.fixture();cfg=json.loads(self.config.read_text());cfg['schema']='water-shard-candidate-v1';self.config.write_text(json.dumps(cfg));out=self.path/'old-policy'
        with self.assertRaisesRegex(ValueError,'supported configuration'):build.run(p,digest,out,self.config)
        self.assertFalse(out.exists())
    def test_compiled_engine_configuration_is_rejected_before_output(self):
        p,digest=self.fixture();cfg=json.loads(self.config.read_bytes());cfg['rasterizer']='native'
        self.config.write_text(json.dumps(cfg));out=self.path/'retired-engine'
        with self.assertRaisesRegex(ValueError,'runtime native compilation is retired'):
            build.run(p,digest,out,self.config)
        self.assertFalse(out.exists())
    def test_invalid_geometry_is_reported_and_not_claimed_complete(self):
        p,_ = self.fixture()
        table = pq.read_table(p).to_pylist()
        table[0]['geometry'] = bytes(ogr.CreateGeometryFromWkt('POLYGON ((-170 80,-120 40,-170 40,-120 80,-170 80))').ExportToWkb())
        table = pa.Table.from_pylist(table).replace_schema_metadata({b'geo':json.dumps({'primary_column':'geometry','columns':{'geometry':{'encoding':'WKB'}}}).encode()})
        p = self.inputs/'invalid.parquet'; pq.write_table(table,p)
        digest = hashlib.sha256(p.read_bytes()).hexdigest(); out=self.path/'invalid-output'
        build.run(p,digest,out,self.config,10)
        report=json.loads((out/'report.json').read_text())
        self.assertEqual(report['status'],'incomplete-input-issues')
        self.assertEqual(json.loads((out/'invalid-feature-ids.json').read_text()), ['lake'])

    def test_free_space_guard(self):
        p,digest=self.fixture();cfg=json.loads(self.config.read_text());cfg['minimum_free_bytes']=1 << 60
        self.config.write_text(json.dumps(cfg));out=self.path/'no-space'
        with self.assertRaisesRegex(ValueError,'free disk below configured reserve'):
            build.run(p,digest,out,self.config)
        self.assertFalse(out.exists())

    def test_integrity_and_collision(self):
        p,digest = self.fixture()
        with self.assertRaises(ValueError): build.run(p, '0'*64, self.path/'bad',self.config)
        self.assertFalse((self.path/'bad').exists())
        existing=self.path/'existing';existing.mkdir()
        with self.assertRaises(FileExistsError): build.run(p,digest,existing,self.config)
        with self.assertRaises(ValueError): build.run(p,digest,self.path,self.config)
        with self.assertRaises(ValueError): build.run(p,digest,self.inputs/'nested-output',self.config)
        self.config.write_text('{}')
        with self.assertRaises(ValueError): build.run(p,digest,self.path/'badconfig',self.config)
        self.assertFalse((self.path/'badconfig').exists())
if __name__ == '__main__': unittest.main()
