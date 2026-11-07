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
        self.stager = module.Stager({self.src:self.entry}, '/official/wrangler.js', self.logs,
                                    remove_downloads=True)
        def stage(*args):
            self.dest.mkdir()
            (self.dest/'report.json').write_text(json.dumps({'status':'candidate-only',
                                                              'source_sha256':self.digest}))
        self.stager.original_stage = stage

    def fetch(self, cmd, **kwargs):
        Path(cmd[cmd.index('--file') + 1]).write_bytes(self.payload)

    def call(self):
        self.stager.run_stage('overture/rasterize_water_shard.py', self.src, self.digest,
                              'water-config', self.dest)

    def test_download_validated_and_only_new_temporary_removed(self):
        with mock.patch.object(module.subprocess, 'run', side_effect=self.fetch): self.call()
        self.assertFalse(self.src.exists())
        event = json.loads((self.logs/'events.jsonl').read_text())
        self.assertTrue(event['downloaded']); self.assertTrue(event['removed_download'])

    def test_existing_input_is_never_removed(self):
        self.src.parent.mkdir(); self.src.write_bytes(self.payload)
        with mock.patch.object(module.subprocess, 'run') as get:
            self.call(); get.assert_not_called()
        self.assertEqual(self.src.read_bytes(), self.payload)

    def test_wrong_download_is_retained_and_rejected(self):
        def bad(cmd, **kwargs): Path(cmd[cmd.index('--file')+1]).write_bytes(b'wrong')
        with mock.patch.object(module.subprocess, 'run', side_effect=bad):
            with self.assertRaises(ValueError): self.call()
        self.assertEqual(self.src.with_name('shard.partial').read_bytes(), b'wrong')
        self.assertFalse(self.src.exists())

    def test_failed_raster_retains_download(self):
        self.stager.original_stage = mock.Mock(side_effect=RuntimeError('failed'))
        with mock.patch.object(module.subprocess, 'run', side_effect=self.fetch):
            with self.assertRaises(RuntimeError): self.call()
        self.assertEqual(self.src.read_bytes(), self.payload)

    def test_unlisted_and_wrong_pins_fail(self):
        with self.assertRaises(ValueError):
            self.stager.run_stage('overture/rasterize_water_shard.py', self.src, '0'*64, 'config', self.dest)

    def test_manifest_pin_and_path_validation(self):
        m = self.root/'manifest.json'; entry = dict(self.entry, path='raw/shard')
        m.write_text(json.dumps({'file_count':1, 'files':[entry]}))
        cfg = self.root/'config.json'; cfg.write_text(json.dumps({'source_manifest':{'path':str(m),'sha256':module.sha(m)}}))
        self.assertEqual(module.manifest_entries(cfg)[self.src]['sha256'], self.digest)
        entry['path'] = '../escape'; m.write_text(json.dumps({'file_count':1, 'files':[entry]}))
        cfg.write_text(json.dumps({'source_manifest':{'path':str(m),'sha256':module.sha(m)}}))
        with self.assertRaises(ValueError): module.manifest_entries(cfg)


if __name__ == '__main__': unittest.main()
