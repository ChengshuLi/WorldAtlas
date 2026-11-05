import importlib.util,json,unittest
from pathlib import Path
from unittest.mock import patch
p=Path(__file__).resolve().parent/'v7-land/named-identity-prototype/identity_watch.py'
if not p.is_file():p=Path(__file__).resolve().parent.parents[2]/'v7-recovery/land/stage2-geodesic-20261104/v7-land/named-identity-prototype/identity_watch.py'
spec=importlib.util.spec_from_file_location('iw_test',p);watch=importlib.util.module_from_spec(spec);spec.loader.exec_module(watch)
class WatchTest(unittest.TestCase):
 def test_low_memory_sample_recorded_without_floor(self):
  worker=b'import json; print(json.dumps({"schema":"named-identity-worker-v2","peak_rss_source":"linux-proc-self-status-VmHWM-kib","rusage_peak_rss_kib":300000,"peak_rss_kib":123,"result":{"root":7}}))'
  result=watch.run(worker,{},lambda:1)
  self.assertEqual(result['result'],{'root':7});m=result['memory_monitor'];self.assertIsNone(m['host_floor_kib']);self.assertEqual(m['initial_available_kib'],1);self.assertEqual(m['minimum_sampled_available_kib'],1);self.assertEqual(m['worker_reported_peak_rss_kib'],123)
 def test_reported_peak_rss_still_enforced(self):
  worker=('import json; print(json.dumps({"schema":"named-identity-worker-v2","peak_rss_source":"linux-proc-self-status-VmHWM-kib","rusage_peak_rss_kib":300000,"peak_rss_kib":%d,"result":{}}))' % (watch.RSS_CAP_KIB+1)).encode()
  with self.assertRaisesRegex(ValueError,'peak RSS'):watch.run(worker,{},lambda:1)
 def test_sampled_rss_still_enforced(self):
  with patch.object(watch,'child_rss',return_value=watch.RSS_CAP_KIB+1):
   with self.assertRaisesRegex(ValueError,'child RSS cap'):watch.run(b'import time; time.sleep(2)',{},lambda:1)
if __name__=='__main__':unittest.main()
