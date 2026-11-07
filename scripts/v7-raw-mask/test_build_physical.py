import hashlib
import json
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from osgeo import gdal, ogr
import build_physical as b

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.config_dir=self.root/'configs';self.config_dir.mkdir()
        self.land_dir=self.root/'land-input';self.land_dir.mkdir()
        self.raw=self.root/'raw';self.raw.mkdir()
        self.grid={'width':8,'height':4,'west':-180,'north':90,'step':45}
        land=self.land_dir/'land.geojson'
        land.write_text(json.dumps({'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':{'type':'Polygon','coordinates':[[[-180,90],[-45,90],[-45,0],[-180,0],[-180,90]]]}}]}))
        land_cfg={'schema':'land-raster-candidate-v1','grid':self.grid,'selection_notes':'synthetic','strip_rows':2,'minimum_free_bytes':0,
                  'land':[{'dataset':str(land),'where':None,'files':[{'path':str(land),'sha256':b.sha(land)}]}]}
        self.land_cfg=self.config_dir/'land.json';self.land_cfg.write_text(json.dumps(land_cfg))
        water_cfg={'schema':'water-shard-candidate-v2','grid':self.grid,'tile_size':4,'minimum_free_bytes':0,'selection_notes':'synthetic',
                   'policy':{'method':'overture-inland-subtype-v1'}}
        self.water_cfg=self.config_dir/'water.json';self.water_cfg.write_text(json.dumps(water_cfg))
        geom=bytes(ogr.CreateGeometryFromWkt('POLYGON ((-180 90,-135 90,-135 45,-180 45,-180 90))').ExportToWkb())
        rows=[{'id':'lake','subtype':'lake','class':'lake','sources':[{'property':'','dataset':'OpenStreetMap'}],'geometry':geom}]
        table=pa.Table.from_pylist(rows).replace_schema_metadata({b'geo':json.dumps({'primary_column':'geometry','columns':{'geometry':{'encoding':'WKB'}}}).encode()})
        shard=self.raw/'water.parquet';pq.write_table(table,shard)
        source=self.raw/'manifest.json';source.write_text(json.dumps({'file_count':1,'files':[{'path':'water.parquet','sha256':b.sha(shard)}]}))
        self.cfg={'schema':'raw-physical-pipeline-v1','selection_notes':'synthetic','minimum_free_bytes':0,
                  'land_config':{'path':str(self.land_cfg),'sha256':b.sha(self.land_cfg)},
                  'water_config':{'path':str(self.water_cfg),'sha256':b.sha(self.water_cfg)},
                  'source_manifest':{'path':str(source),'sha256':b.sha(source)}}
        self.config=self.config_dir/'pipeline.json';self.config.write_text(json.dumps(self.cfg))
    def tearDown(self):self.tmp.cleanup()
    def test_r2_staging_is_serial_verified_timed_and_owned(self):
        shard=self.raw/'water.parquet';content=shard.read_bytes();digest=b.sha(shard)
        source=Path(self.cfg['source_manifest']['path'])
        source.write_text(json.dumps({'file_count':1,'files':[{'path':shard.name,'sha256':digest,'size':len(content),'r2_bucket':'test-bucket','r2_key':'source/water.parquet'}]}))
        self.cfg['source_manifest']['sha256']=b.sha(source);self.cfg['max_parallel_shards']=1
        wrangler=self.config_dir/'wrangler';wrangler.write_text('test');config=self.config_dir/'wrangler.jsonc';config.write_text('{}')
        self.cfg['source_staging']={'mode':'wrangler-r2','wrangler_path':str(wrangler),'wrangler_config':str(config)}
        self.config.write_text(json.dumps(self.cfg));shard.unlink();out=self.root/'staged';actual_run=b.subprocess.run
        def download(args,**kwargs):
            if args[0]!=str(wrangler):return actual_run(args,**kwargs)
            self.assertEqual(args[1:5],['r2','object','get','test-bucket/source/water.parquet'])
            self.assertTrue(Path(kwargs['env']['TMPDIR']).is_relative_to(out));time.sleep(.05)
            Path(args[args.index('--file')+1]).write_bytes(content)
        with mock.patch.object(b.subprocess,'run',side_effect=download):b.run(self.config,out)
        report=json.loads((out/'report.json').read_text());self.assertEqual(report['staged_shard_count'],1)
        self.assertGreaterEqual(report['source_download_elapsed_seconds'],.05);self.assertGreaterEqual(report['processing_elapsed_seconds'],0)
        self.assertFalse((out/'source-staging/00000.parquet').exists());self.assertFalse(shard.exists())
        self.assertEqual(report['physical_output_sha256']['runs.u32le'],b.sha(out/'physical/runs.u32le'))
        shard.write_bytes(content);local=self.root/'already-local'
        with mock.patch.object(b.subprocess,'run',side_effect=download):b.run(self.config,local)
        self.assertEqual(shard.read_bytes(),content)
        self.assertEqual(json.loads((local/'report.json').read_text())['staged_shard_count'],0)
        self.assertEqual(b.sha(local/'physical/runs.u32le'),b.sha(out/'physical/runs.u32le'))
        self.cfg['max_parallel_shards']=2;self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError,'one shard worker'):b.run(self.config,self.root/'unsafe-parallel')

    def test_r2_bad_hash_retains_evidence_and_does_not_publish(self):
        shard=self.raw/'water.parquet';content=shard.read_bytes();source=Path(self.cfg['source_manifest']['path'])
        source.write_text(json.dumps({'file_count':1,'files':[{'path':shard.name,'sha256':b.sha(shard),'size':len(content),'r2_bucket':'test-bucket','r2_key':'source/water.parquet'}]}))
        self.cfg['source_manifest']['sha256']=b.sha(source);self.cfg['max_parallel_shards']=1
        wrangler=self.config_dir/'wrangler';wrangler.write_text('test');config=self.config_dir/'wrangler.jsonc';config.write_text('{}')
        self.cfg['source_staging']={'mode':'wrangler-r2','wrangler_path':str(wrangler),'wrangler_config':str(config)};self.config.write_text(json.dumps(self.cfg));shard.unlink();out=self.root/'bad-staged';actual_run=b.subprocess.run
        def download(args,**kwargs):
            if args[0]!=str(wrangler):return actual_run(args,**kwargs)
            Path(args[args.index('--file')+1]).write_bytes(b'X'+content[1:])
        with mock.patch.object(b.subprocess,'run',side_effect=download):
            with self.assertRaisesRegex(ValueError,'size/hash mismatch'):b.run(self.config,out)
        self.assertTrue((out/'source-staging/00000.parquet').exists());self.assertFalse((out/'report.json').exists())
    def test_end_to_end_without_reference(self):
        out=self.root/'out';b.run(self.config,out)
        report=json.loads((out/'report.json').read_text());self.assertEqual(report['status'],'candidate-only');self.assertEqual(report['shard_count'],1)
        self.assertGreaterEqual(report['processing_elapsed_seconds'],0)
        self.assertEqual(report['physical_output_sha256']['rows.u32le'],b.sha(out/'physical/rows.u32le'))
        expected=np.zeros((4,8),dtype=np.uint8);expected[:2,:3]=1;expected[0,0]=0
        np.testing.assert_array_equal(gdal.Open(str(out/'physical/physical-dry.tif')).ReadAsArray(),expected)
        rows=np.fromfile(out/'physical/rows.u32le',dtype='<u4');runs=np.fromfile(out/'physical/runs.u32le',dtype='<u4').reshape(-1,2)
        self.assertEqual(rows.tolist(),[0,3,5,6,7]);self.assertEqual(runs.tolist(),[[1,1],[3,17],[8,1],[3,17],[8,1],[8,1],[8,1]])
        self.assertNotIn('historic_dry_cells',json.loads((out/'physical/report.json').read_text()))
        # Optional validation uses the same candidate as a synthetic reference.
        mask=out/'physical/physical-dry.tif';rowpath=out/'physical/rows.u32le';runpath=out/'physical/runs.u32le';water=out/'union/water-union.tif'
        pin=lambda p:{'path':str(p),'sha256':b.sha(p)}
        self.cfg['water_reference']=pin(water);self.cfg['physical_reference_mask']=pin(mask)
        self.cfg['physical_reference_streams']={'rows':pin(rowpath),'runs':pin(runpath)}
        self.config.write_text(json.dumps(self.cfg));out_ref=self.root/'out-reference';b.run(self.config,out_ref)
        self.assertEqual(json.loads((out_ref/'union/report.json').read_text())['mismatch_spans'],0)
        self.assertEqual(json.loads((out_ref/'physical/report.json').read_text())['mismatch_spans'],0)
        self.assertEqual(b.sha(out_ref/'physical/runs.u32le'),b.sha(runpath))
    def test_parallel_shards_match_serial_and_bad_worker_count_fails(self):
        first=self.raw/'water.parquet';table=pq.read_table(first);row=table.to_pylist()[0];row['id']='second-lake'
        second=self.raw/'second.parquet';pq.write_table(pa.Table.from_pylist([row]).replace_schema_metadata(table.schema.metadata),second)
        source=Path(self.cfg['source_manifest']['path']);source.write_text(json.dumps({'file_count':2,'files':[
            {'path':first.name,'sha256':b.sha(first)},{'path':second.name,'sha256':b.sha(second)}]}))
        self.cfg['source_manifest']['sha256']=b.sha(source)
        self.cfg['max_parallel_shards']=0;self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError,'max_parallel_shards'):b.run(self.config,self.root/'bad-workers')
        self.assertFalse((self.root/'bad-workers').exists())
        self.cfg['max_parallel_shards']=1;self.config.write_text(json.dumps(self.cfg));serial=self.root/'serial';b.run(self.config,serial)
        self.cfg['max_parallel_shards']=2;self.config.write_text(json.dumps(self.cfg));parallel=self.root/'parallel';b.run(self.config,parallel)
        self.assertEqual(b.sha(serial/'physical/physical-dry.tif'),b.sha(parallel/'physical/physical-dry.tif'))
        self.assertEqual(b.sha(serial/'physical/rows.u32le'),b.sha(parallel/'physical/rows.u32le'))
        self.assertEqual(b.sha(serial/'physical/runs.u32le'),b.sha(parallel/'physical/runs.u32le'))
        self.assertEqual(b.sha(serial/'union/water-union.tif'),b.sha(parallel/'union/water-union.tif'))
        self.assertEqual(json.loads((parallel/'report.json').read_text())['max_parallel_shards'],2)
        self.cfg.pop('max_parallel_shards');self.config.write_text(json.dumps(self.cfg));defaulted=self.root/'default-parallel';b.run(self.config,defaulted)
        self.assertEqual(b.sha(serial/'physical/physical-dry.tif'),b.sha(defaulted/'physical/physical-dry.tif'))
        self.assertEqual(b.sha(serial/'physical/rows.u32le'),b.sha(defaulted/'physical/rows.u32le'))
        self.assertEqual(b.sha(serial/'physical/runs.u32le'),b.sha(defaulted/'physical/runs.u32le'))
        self.assertEqual(b.sha(serial/'union/water-union.tif'),b.sha(defaulted/'union/water-union.tif'))
        self.assertEqual(json.loads((defaulted/'report.json').read_text())['max_parallel_shards'],2)
        # No arbitrary worker ceiling: the actual pool is naturally limited by
        # the number of independent shards, even when configuration is larger.
        self.cfg['max_parallel_shards']=10000;self.config.write_text(json.dumps(self.cfg));oversized=self.root/'oversized-worker-setting';b.run(self.config,oversized)
        self.assertEqual(b.sha(serial/'physical/physical-dry.tif'),b.sha(oversized/'physical/physical-dry.tif'))
        self.assertEqual(b.sha(serial/'physical/rows.u32le'),b.sha(oversized/'physical/rows.u32le'))
        self.assertEqual(b.sha(serial/'physical/runs.u32le'),b.sha(oversized/'physical/runs.u32le'))
        self.assertEqual(b.sha(serial/'union/water-union.tif'),b.sha(oversized/'union/water-union.tif'))
        self.assertEqual(json.loads((oversized/'report.json').read_text())['max_parallel_shards'],10000)

    def test_parallel_incomplete_shard_fails_before_union(self):
        first=self.raw/'water.parquet';table=pq.read_table(first);row=table.to_pylist()[0];row['id']='bad';row['subtype']=None
        bad=self.raw/'bad.parquet';pq.write_table(pa.Table.from_pylist([row]).replace_schema_metadata(table.schema.metadata),bad)
        source=Path(self.cfg['source_manifest']['path']);source.write_text(json.dumps({'file_count':2,'files':[
            {'path':first.name,'sha256':b.sha(first)},{'path':bad.name,'sha256':b.sha(bad)}]}))
        self.cfg['source_manifest']['sha256']=b.sha(source);self.cfg['max_parallel_shards']=2
        self.config.write_text(json.dumps(self.cfg));out=self.root/'parallel-incomplete'
        with self.assertRaisesRegex(ValueError,'incomplete water shard'):b.run(self.config,out)
        self.assertFalse((out/'union').exists());self.assertFalse((out/'report.json').exists())

    def test_incomplete_water_cannot_publish_pipeline_report(self):
        shard=self.raw/'water.parquet';table=pq.read_table(shard);rows=table.to_pylist()
        item=dict(rows[0]);item['id']='unclassified';item['subtype']=None;rows.append(item)
        revised=pa.Table.from_pylist(rows).replace_schema_metadata(table.schema.metadata);pq.write_table(revised,shard)
        source=Path(self.cfg['source_manifest']['path']);source.write_text(json.dumps({'file_count':1,'files':[{'path':'water.parquet','sha256':b.sha(shard)}]}))
        self.cfg['source_manifest']['sha256']=b.sha(source);self.config.write_text(json.dumps(self.cfg));out=self.root/'incomplete'
        with self.assertRaisesRegex(ValueError,'incomplete water shard'):b.run(self.config,out)
        self.assertTrue((out/'shards/00000/report.json').exists())
        self.assertFalse((out/'report.json').exists())
        self.assertFalse((out/'physical').exists())

    def test_rejects_source_path_traversal_before_output(self):
        source=Path(self.cfg['source_manifest']['path']);source.write_text(json.dumps({'file_count':1,'files':[{'path':'../bad.parquet','sha256':'1'*64}]}))
        self.cfg['source_manifest']['sha256']=b.sha(source);self.config.write_text(json.dumps(self.cfg));out=self.root/'traversal'
        with self.assertRaisesRegex(ValueError,'relative to manifest directory'):b.run(self.config,out)
        self.assertFalse(out.exists())

    def test_preflight_rejects_changed_pin_and_partial_reference(self):
        self.cfg['land_config']['sha256']='0'*64;self.config.write_text(json.dumps(self.cfg));out=self.root/'bad'
        with self.assertRaisesRegex(ValueError,'hash mismatch'):b.run(self.config,out)
        self.assertFalse(out.exists())
        self.cfg['land_config']['sha256']=b.sha(self.land_cfg);self.cfg['physical_reference_mask']={'path':str(self.land_cfg),'sha256':b.sha(self.land_cfg)};self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError,'supplied together'):b.run(self.config,out)
        self.assertFalse(out.exists())
if __name__=='__main__':unittest.main()
