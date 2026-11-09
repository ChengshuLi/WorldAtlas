import hashlib
import fcntl
import io
import json
import os
import subprocess
import sys
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
    def test_atomic_publish_preserves_pending_on_link_failure(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'report.json'
            with mock.patch.object(b.os,'link',side_effect=OSError('link failure')):
                with self.assertRaisesRegex(OSError,'link failure'):b.write_bytes_atomic(path,b'payload')
            self.assertFalse(path.exists());self.assertEqual([p.read_bytes() for p in Path(d).glob('.report.json.*.pending')],[b'payload'])
    def test_atomic_publish_does_not_overwrite_existing(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'report.json';path.write_bytes(b'existing')
            with self.assertRaises(FileExistsError):b.write_bytes_atomic(path,b'new')
            self.assertEqual(path.read_bytes(),b'existing')
    def test_interrupted_parallel_units_use_wall_time_union(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);j=b.ProcessingJournal(root,time.perf_counter(),False)
            j.add({'event':'attempt_start','attempt':'old'})
            for start,end in ((0,10),(5,15)):
                j.add({'event':'unit_complete','attempt':'old','unit':'test','start_monotonic_seconds':start,
                       'end_monotonic_seconds':end,'processing_elapsed_seconds':end-start})
            j.finish('complete');r=j.summary()
            self.assertFalse(r['timing_complete']);self.assertIsNone(r['processing_elapsed_seconds'])
            self.assertGreaterEqual(r['recorded_processing_elapsed_seconds'],15)
            self.assertLess(r['recorded_processing_elapsed_seconds'],20)
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
    def interrupt_before_union(self,out):
        actual=b.run_stage
        def stage(name,*args):
            if name=='overture/aggregate_compare.py':raise ValueError('simulated interruption')
            return actual(name,*args)
        with mock.patch.object(b,'run_stage',side_effect=stage):
            with self.assertRaisesRegex(ValueError,'simulated interruption'):b.run(self.config,out)

    def test_resume_reuses_verified_checkpoints_and_preserves_timing(self):
        out=self.root/'resume';self.interrupt_before_union(out);actual=b.run_stage;seen=[]
        def stage(name,*args):seen.append(name);return actual(name,*args)
        with mock.patch.object(b,'run_stage',side_effect=stage):b.run(self.config,out,resume=True)
        report=json.loads((out/'report.json').read_text())
        self.assertTrue(report['timing_complete']);self.assertGreater(report['processing_elapsed_seconds'],0)
        self.assertNotIn('rasterize_land.py',seen);self.assertNotIn('overture/rasterize_water_shard.py',seen)
        self.assertEqual(b.run(self.config,out,resume=True),report)

    def test_concurrent_attempt_is_rejected(self):
        out=self.root/'locked';lock=self.root/'locked.lock'
        with lock.open('w') as f:
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError,'already running'):b.run(self.config,out)
        self.assertFalse(out.exists())

    def test_resume_before_journal_creation_marks_timing_incomplete(self):
        out=self.root/'early-interruption'
        with mock.patch.object(b,'ProcessingJournal',side_effect=OSError('journal interrupted')):
            with self.assertRaisesRegex(OSError,'journal interrupted'):b.run(self.config,out)
        report=b.run(self.config,out,resume=True)
        self.assertFalse(report['timing_complete']);self.assertIsNone(report['processing_elapsed_seconds'])

    def test_resume_hard_interruption_reports_unknown_total(self):
        out=self.root/'crashed';self.interrupt_before_union(out);journal=out/'processing-events.jsonl'
        lines=journal.read_text().splitlines();self.assertEqual(json.loads(lines[-1])['event'],'attempt_end')
        journal.write_text('\n'.join(lines[:-1])+'\n{"event":');b.run(self.config,out,resume=True)
        report=json.loads((out/'report.json').read_text());self.assertFalse(report['timing_complete'])
        self.assertIsNone(report['processing_elapsed_seconds']);self.assertGreater(report['recorded_processing_elapsed_seconds'],0)
        self.assertEqual([p.read_text() for p in (out/'interrupted').glob('journal-tail-*')],['{"event":'])

    def test_actual_kill_preserves_units_and_marks_timing_incomplete(self):
        out=self.root/'actual-kill';marker=self.root/'waiting'
        code='''import build_physical as b, pathlib, sys, time\noriginal=b.run_stage\ndef stage(name,*args):\n if name=="overture/aggregate_compare.py":\n  pathlib.Path(sys.argv[3]).write_text("ready");time.sleep(60)\n return original(name,*args)\nb.run_stage=stage\nb.run(sys.argv[1],sys.argv[2])\n'''
        env=os.environ.copy();env['PYTHONPATH']=str(Path(b.__file__).parent)+os.pathsep+env.get('PYTHONPATH','')
        proc=subprocess.Popen([sys.executable,'-c',code,str(self.config),str(out),str(marker)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            deadline=time.monotonic()+30
            while not marker.exists() and proc.poll() is None and time.monotonic()<deadline:time.sleep(.05)
            if not marker.exists():
                if proc.poll() is None:proc.kill();proc.wait(timeout=10)
                self.fail('child did not reach checkpoint: '+proc.stderr.read().decode())
        finally:
            if proc.poll() is None:proc.kill()
            proc.wait(timeout=10)
        b.run(self.config,out,resume=True);report=json.loads((out/'report.json').read_text())
        self.assertFalse(report['timing_complete']);self.assertIsNone(report['processing_elapsed_seconds'])
        self.assertGreater(report['recorded_processing_elapsed_seconds'],0)

    def test_resume_rejects_tampered_checkpoint_and_input(self):
        out=self.root/'tampered';self.interrupt_before_union(out)
        (out/'shards/00000/water.tif').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError,'shard checkpoint mismatch'):b.run(self.config,out,resume=True)
        self.cfg['selection_notes']='changed';self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError,'resume identity mismatch'):b.run(self.config,out,resume=True)

    def test_completed_resume_revalidates_shard_inventory(self):
        out=self.root/'finished';b.run(self.config,out)
        (out/'shards/00000/water.tif').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError,'completed shard checkpoint mismatch'):b.run(self.config,out,resume=True)
    def test_completed_resume_revalidates_gdal_kernel_report(self):
        out=self.root/'finished-gdal';b.run(self.config,out)
        path=out/'shards/00000/report.json';report=json.loads(path.read_bytes())
        report['gdal_kernel']['binding_sha256']='0'*64;path.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError,'completed shard checkpoint mismatch'):b.run(self.config,out,resume=True)

    def test_complete_physical_stage_does_not_start_processes(self):
        with mock.patch.object(subprocess,'Popen',side_effect=AssertionError('unexpected subprocess')):
            report=b.run(self.config,self.root/'in-process')
        self.assertEqual(report['status'],'candidate-only')
        self.assertFalse(list((self.root/'in-process').rglob('*.so')))

    def test_resume_quarantines_incomplete_unit(self):
        out=self.root/'partial';actual=b.run_stage
        def stage(name,*args):
            if name=='overture/rasterize_water_shard.py':
                destination=Path(args[2]);destination.mkdir();(destination/'partial').write_text('preserve')
                raise ValueError('partial shard')
            return actual(name,*args)
        with mock.patch.object(b,'run_stage',side_effect=stage):
            with self.assertRaisesRegex(ValueError,'partial shard'):b.run(self.config,out)
        b.run(self.config,out,resume=True)
        self.assertEqual([p.read_text() for p in (out/'interrupted').glob('00000-*/partial')],['preserve'])

    def test_resume_reuses_union_after_composition_failure(self):
        out=self.root/'union-resume';actual=b.run_stage
        def fail_compose(name,*args):
            if name=='compose_physical.py':raise ValueError('composition interrupted')
            return actual(name,*args)
        with mock.patch.object(b,'run_stage',side_effect=fail_compose):
            with self.assertRaisesRegex(ValueError,'composition interrupted'):b.run(self.config,out)
        seen=[]
        def stage(name,*args):seen.append(name);return actual(name,*args)
        with mock.patch.object(b,'run_stage',side_effect=stage):b.run(self.config,out,resume=True)
        self.assertEqual(seen,['compose_physical.py'])

    def test_resume_after_report_write_failure_reuses_composition(self):
        out=self.root/'report-resume';actual_write=b.write_json
        def fail_report(path,value):
            if Path(path)==out/'report.json':raise ValueError('report interrupted')
            return actual_write(path,value)
        with mock.patch.object(b,'write_json',side_effect=fail_report):
            with self.assertRaisesRegex(ValueError,'report interrupted'):b.run(self.config,out)
        with mock.patch.object(b,'run_stage',side_effect=AssertionError('unexpected rebuild')):
            b.run(self.config,out,resume=True)
        self.assertTrue((out/'report.json').is_file())
    def test_r2_staging_is_serial_verified_timed_and_owned(self):
        shard=self.raw/'water.parquet';content=shard.read_bytes();digest=b.sha(shard)
        source=Path(self.cfg['source_manifest']['path'])
        source.write_text(json.dumps({'file_count':1,'files':[{'path':shard.name,'sha256':digest,'size':len(content),'r2_bucket':'test-bucket','r2_key':'source/water.parquet'}]}))
        self.cfg['source_manifest']['sha256']=b.sha(source);self.cfg['max_parallel_shards']=1
        endpoint='https://'+'a'*32+'.r2.cloudflarestorage.com'
        self.cfg['source_staging']={'mode':'r2-s3','endpoint_url':endpoint}
        self.config.write_text(json.dumps(self.cfg));shard.unlink();out=self.root/'staged'
        client=mock.Mock()
        def download(**kwargs):
            self.assertEqual(kwargs, {'Bucket':'test-bucket','Key':'source/water.parquet'})
            time.sleep(.05)
            return {'Body':io.BytesIO(content),'ContentLength':len(content)}
        client.get_object.side_effect=download
        with mock.patch.object(b,'make_r2_client',return_value=client) as make_client:
            b.run(self.config,out)
            make_client.assert_called_once_with(endpoint)
        client.get_object.assert_called_once()
        client.close.assert_called_once()
        report=json.loads((out/'report.json').read_text());self.assertEqual(report['staged_shard_count'],1)
        self.assertGreaterEqual(report['source_download_elapsed_seconds'],.05);self.assertGreaterEqual(report['processing_elapsed_seconds'],0)
        self.assertFalse((out/'source-staging'/shard.name).exists());self.assertFalse(shard.exists())
        self.assertEqual(report['physical_output_sha256']['runs.u32le'],b.sha(out/'physical/runs.u32le'))
        shard.write_bytes(content);local=self.root/'already-local'
        with mock.patch.object(b,'make_r2_client',side_effect=AssertionError('unexpected R2 request')):
            b.run(self.config,local)
        self.assertEqual(shard.read_bytes(),content)
        self.assertEqual(json.loads((local/'report.json').read_text())['staged_shard_count'],0)
        self.assertEqual(b.sha(local/'physical/runs.u32le'),b.sha(out/'physical/runs.u32le'))
        self.cfg['max_parallel_shards']=2;self.config.write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ValueError,'one shard worker'):b.run(self.config,self.root/'unsafe-parallel')

    def test_r2_bad_hash_retains_evidence_and_does_not_publish(self):
        shard=self.raw/'water.parquet';content=shard.read_bytes();source=Path(self.cfg['source_manifest']['path'])
        source.write_text(json.dumps({'file_count':1,'files':[{'path':shard.name,'sha256':b.sha(shard),'size':len(content),'r2_bucket':'test-bucket','r2_key':'source/water.parquet'}]}))
        self.cfg['source_manifest']['sha256']=b.sha(source);self.cfg['max_parallel_shards']=1
        self.cfg['source_staging']={'mode':'r2-s3','endpoint_url':'https://'+'a'*32+'.r2.cloudflarestorage.com'}
        self.config.write_text(json.dumps(self.cfg));shard.unlink();out=self.root/'bad-staged'
        client=mock.Mock()
        client.get_object.return_value={'Body':io.BytesIO(b'X'+content[1:]),'ContentLength':len(content)}
        with mock.patch.object(b,'make_r2_client',return_value=client):
            with self.assertRaisesRegex(ValueError,'size/hash mismatch'):b.run(self.config,out)
        self.assertTrue((out/'source-staging'/shard.name).exists());self.assertFalse((out/'report.json').exists())
        client.get_object.return_value={'Body':io.BytesIO(content),'ContentLength':len(content)}
        with mock.patch.object(b,'make_r2_client',return_value=client):
            b.run(self.config,out,resume=True)
        self.assertEqual(len(list((out/'interrupted').glob(shard.name+'-*'))),1)
        self.assertFalse((out/'source-staging'/shard.name).exists())
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
