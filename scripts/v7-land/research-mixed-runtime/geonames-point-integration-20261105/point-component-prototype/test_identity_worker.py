import importlib.util, json, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

path=Path(__file__).resolve().parent.parent/'named-identity-prototype/identity_worker.py'
spec=importlib.util.spec_from_file_location('identity_worker_test',path)
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)

class IdentityWorkerTest(unittest.TestCase):
 def test_validated_result_without_timeout(self):
  response=SimpleNamespace(returncode=0,stdout=json.dumps({'schema':'named-identity-worker-v1','result':{'ok':True}}).encode(),stderr=b'')
  with patch.object(worker.subprocess,'run',return_value=response) as run:
   self.assertEqual(worker.run(b'pass',{}),{'ok':True})
   self.assertNotIn('timeout',run.call_args.kwargs)
 def test_worker_failure_is_rejected(self):
  response=SimpleNamespace(returncode=1,stdout=b'',stderr=b'bad')
  with patch.object(worker.subprocess,'run',return_value=response):
   with self.assertRaisesRegex(ValueError,'worker failed'):worker.run(b'pass',{})
