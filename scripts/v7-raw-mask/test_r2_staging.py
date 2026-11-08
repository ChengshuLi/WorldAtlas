import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r2_staging', HERE / 'run_with_r2_staging.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.logs = self.root / 'logs'; self.logs.mkdir()
        self.src = self.root / 'raw' / 'shard'; self.dest = self.root / 'out'
        self.payload = b'complete pinned source'
        self.digest = hashlib.sha256(self.payload).hexdigest()
        self.entry = {'source_id':'one', 'sha256':self.digest, 'size':len(self.payload),
                      'r2_bucket':'bucket', 'r2_key':'prefix/shard'}
        self.stager = module.Stager({self.src:self.entry}, 'r2-endpoint', self.logs,
                                    remove_downloads=True)
        def stage(*args):
            self.dest.mkdir()
            (self.dest/'report.json').write_text(json.dumps({'status':'candidate-only',
                                                              'source_sha256':self.digest}))
        self.stager.original_stage = stage

    def fetch(self, endpoint, entry, destination):
        destination.write_bytes(self.payload)

    def call(self):
        self.stager.run_stage('overture/rasterize_water_shard.py', self.src, self.digest,
                              self.dest, 'water-config')

    def test_download_validated_and_only_new_temporary_removed(self):
        with mock.patch.object(module.physical, 'download_r2', side_effect=self.fetch): self.call()
        self.assertFalse(self.src.exists())
        event = json.loads((self.logs/'events.jsonl').read_text())
        self.assertTrue(event['downloaded']); self.assertTrue(event['removed_download'])

    def test_existing_input_is_never_removed(self):
        self.src.parent.mkdir(); self.src.write_bytes(self.payload)
        with mock.patch.object(module.physical, 'download_r2') as get:
            self.call(); get.assert_not_called()
        self.assertEqual(self.src.read_bytes(), self.payload)

    def test_wrong_download_is_retained_and_rejected(self):
        def bad(endpoint, entry, destination): destination.write_bytes(b'wrong')
        with mock.patch.object(module.physical, 'download_r2', side_effect=bad):
            with self.assertRaises(ValueError): self.call()
        self.assertEqual(self.src.with_name('shard.partial').read_bytes(), b'wrong')
        self.assertFalse(self.src.exists())

    def test_failed_raster_retains_download(self):
        self.stager.original_stage = mock.Mock(side_effect=RuntimeError('failed'))
        with mock.patch.object(module.physical, 'download_r2', side_effect=self.fetch):
            with self.assertRaises(RuntimeError): self.call()
        self.assertEqual(self.src.read_bytes(), self.payload)

    def test_unlisted_and_wrong_pins_fail(self):
        with self.assertRaises(ValueError):
            self.stager.run_stage('overture/rasterize_water_shard.py', self.src, '0'*64, self.dest, 'config')

    def test_manifest_pin_and_path_validation(self):
        m = self.root/'manifest.json'; entry = dict(self.entry, path='raw/shard')
        m.write_text(json.dumps({'file_count':1, 'files':[entry]}))
        cfg = self.root/'config.json'; cfg.write_text(json.dumps({'source_manifest':{'path':str(m),'sha256':module.sha(m)}}))
        self.assertEqual(module.manifest_entries(cfg)[self.src]['sha256'], self.digest)
        entry['path'] = '../escape'; m.write_text(json.dumps({'file_count':1, 'files':[entry]}))
        cfg.write_text(json.dumps({'source_manifest':{'path':str(m),'sha256':module.sha(m)}}))
        with self.assertRaises(ValueError): module.manifest_entries(cfg)

class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.log = self.root/'logs'; self.log.mkdir()
        self.check = self.root/'old'; (self.check/'land').mkdir(parents=True); (self.check/'shards'/'00000').mkdir(parents=True)
        self.repo = self.root/'repo'; (self.repo/'overture').mkdir(parents=True)
        for f, data in [('rasterize_land.py',b'land code'),('build.py',b'shared code'),('overture/rasterize_water_shard.py',b'water code')]:
            (self.repo/f).write_bytes(data)
        self.patch = mock.patch.object(module.physical, 'HERE', self.repo); self.patch.start(); self.addCleanup(self.patch.stop)
        self.source=self.root/'raw'/'part'; self.source.parent.mkdir(); self.data=b'shard'; self.source_sha=hashlib.sha256(self.data).hexdigest()
        self.landfile=self.root/'land.shp';self.landfile.write_bytes(b'land input')
        self.landcfg=self.root/'land.json'; self.landcfg.write_text(json.dumps({'grid':{'width':8},'land':[{'files':[{'path':str(self.landfile),'sha256':module.sha(self.landfile)}]}]}))
        self.watercfg=self.root/'water.json';self.watercfg.write_text(json.dumps({'grid':{'width':8},'policy':{'method':'x'},'batch_size':8,'rasterizer':'python'}))
        self.entry={'source_id':'s','sha256':self.source_sha,'size':len(self.data),'r2_bucket':'b','r2_key':'k'}
        self.stager=module.Stager({self.source:self.entry},'r2-endpoint',self.log);self.stager.original_stage=mock.Mock()
        land=self.check/'land'; (land/'config.json').write_bytes(self.landcfg.read_bytes()); (land/'land.tif').write_bytes(b'land raster')
        (land/'report.json').write_text(json.dumps({'status':'candidate-only','grid':{'width':8},'configuration_sha256':module.sha(self.landcfg),'land_sha256':module.sha(land/'land.tif')}))
        shard=self.check/'shards'/'00000';(shard/'water.tif').write_bytes(b'water raster')
        (shard/'report.json').write_text(json.dumps({'status':'candidate-only','source':str(self.source),'source_sha256':self.source_sha,'configuration_sha256':module.sha(self.watercfg),'script_sha256':module.sha(self.repo/'overture/rasterize_water_shard.py'),'grid':{'width':8},'policy':{'method':'x'},'batch_size':8,'rasterizer':'python','native_kernel':None,'output_sha256':module.sha(shard/'water.tif')}))
        self.events=self.root/'events.jsonl';self.events.write_text(json.dumps({'event':'shard_complete','source_id':'s','source':str(self.source),'sha256':self.source_sha,'size':len(self.data),'output_sha256':module.sha(shard/'water.tif')})+'\n')
        self.resume=module.CheckpointStager(self.stager,self.check,self.events,module.sha(land/'report.json'),module.sha(self.repo/'rasterize_land.py'),module.sha(self.repo/'build.py'))
    def test_land_and_shard_reused_in_new_output(self):
        dest=self.root/'new';(dest/'shards').mkdir(parents=True)
        self.resume.run_stage('rasterize_land.py',self.landcfg,dest/'land')
        self.resume.run_stage('overture/rasterize_water_shard.py',self.source,self.source_sha,dest/'shards'/'00000',self.watercfg,8)
        self.stager.original_stage.assert_not_called()
        self.assertEqual((dest/'land'/'land.tif').read_bytes(),b'land raster')
        self.assertEqual((dest/'shards'/'00000'/'water.tif').read_bytes(),b'water raster')
        self.assertEqual((self.check/'shards'/'00000'/'water.tif').read_bytes(),b'water raster')
    def test_bad_shard_hash_fails_closed(self):
        (self.check/'shards'/'00000'/'water.tif').write_bytes(b'tampered')
        with self.assertRaises(ValueError): self.resume.run_stage('overture/rasterize_water_shard.py',self.source,self.source_sha,self.root/'00000',self.watercfg)
    def test_gdal_checkpoint_requires_pinned_python_binding_and_method(self):
        cfg=json.loads(self.watercfg.read_text());cfg['rasterizer']='gdal';self.watercfg.write_text(json.dumps(cfg))
        shard=self.check/'shards'/'00000';report=json.loads((shard/'report.json').read_text())
        (self.repo/'overture/water_batch.py').write_bytes(b'Python binding')
        report.update({'rasterizer':'gdal','configuration_sha256':module.sha(self.watercfg),'gdal_kernel':{
            'implementation':'python-gdal-c-api-v1','method':'hybrid',
            'binding_sha256':module.sha(self.repo/'overture/water_batch.py')}})
        (shard/'report.json').write_text(json.dumps(report));dest=self.root/'native-copy'/'00000';dest.parent.mkdir()
        self.resume.run_stage('overture/rasterize_water_shard.py',self.source,self.source_sha,dest,self.watercfg)
        self.assertFalse((dest/'water-native.so').exists())
        report['gdal_kernel']['method']='vector';(shard/'report.json').write_text(json.dumps(report))
        wrong=self.root/'wrong-method'/'00000';wrong.parent.mkdir()
        with self.assertRaisesRegex(ValueError,'in-process GDAL water checkpoint mismatch'):
            self.resume.run_stage('overture/rasterize_water_shard.py',self.source,self.source_sha,wrong,self.watercfg)
    def test_bad_land_code_fails_closed(self):
        (self.repo/'rasterize_land.py').write_bytes(b'changed')
        with self.assertRaises(ValueError): self.resume.run_stage('rasterize_land.py',self.landcfg,self.root/'newland')
    def test_missing_stage_runs_normally(self):
        self.stager.run_stage=mock.Mock()
        dest=self.root/'00001';self.resume.run_stage('overture/rasterize_water_shard.py',self.source,self.source_sha,dest,self.watercfg)
        self.stager.run_stage.assert_called_once()


if __name__ == '__main__': unittest.main()
