# Synthetic fixtures only; no project geographic records.
import unittest
from unittest.mock import patch
import identity_watch as w
OK=b'import sys,json,resource; sys.stdin.buffer.read(); print(json.dumps({"schema":"named-identity-worker-v1","result":{"strict_contains":True},"peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))'
SLOW=b'import sys,time; sys.stdin.buffer.read(); time.sleep(2)'
class WatchTests(unittest.TestCase):
 def test_success(self):
  r=w.run(OK,{},lambda:4000000);self.assertTrue(r['result']['strict_contains']);self.assertGreater(r['memory_monitor']['worker_reported_peak_rss_kib'],0)
 def test_start_headroom_guard(self):
  with self.assertRaisesRegex(ValueError,'insufficient host'):w.run(OK,{},lambda:w.FLOOR_KIB)
 def test_worker_peak_over_cap_rejected(self):
  code=b'import sys,json;sys.stdin.buffer.read();print(json.dumps({"schema":"named-identity-worker-v1","result":{},"peak_rss_kib":999999}))'
  with self.assertRaisesRegex(ValueError,'peak RSS'):w.run(code,{},lambda:4000000)
 def test_worker_error_rejected(self):
  with self.assertRaisesRegex(ValueError,'worker failed'):w.run(b'import sys;sys.exit(1)',{},lambda:4000000)
 def test_timeout_terminates(self):
  with patch.object(w,'TIMEOUT_SECONDS',.05),patch.object(w,'POLL_SECONDS',.01):
   with self.assertRaisesRegex(ValueError,'timed out'):w.run(SLOW,{},lambda:4000000)
 def test_rss_cap_terminates(self):
  with patch.object(w,'child_rss',return_value=w.RSS_CAP_KIB+1):
   with self.assertRaisesRegex(ValueError,'RSS cap'):w.run(SLOW,{},lambda:4000000)
 def test_host_floor_terminates(self):
  values=iter([4000000,w.FLOOR_KIB-1]);
  with self.assertRaisesRegex(ValueError,'host memory floor'):w.run(SLOW,{},lambda:next(values))
if __name__=='__main__':unittest.main()
