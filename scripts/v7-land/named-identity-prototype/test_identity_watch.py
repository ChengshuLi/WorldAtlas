# Synthetic fixtures only; no project geographic records.
import unittest
from unittest.mock import patch
import identity_watch as w
OK=b'import sys,json; sys.stdin.buffer.read(); print(json.dumps({"schema":"named-identity-worker-v1","result":{"strict_contains":True}}))'
SLOW=b'import sys,time; sys.stdin.buffer.read(); time.sleep(2)'
class WatchTests(unittest.TestCase):
 def test_success(self):self.assertTrue(w.run(OK,{})['strict_contains'])
 def test_worker_error_rejected(self):
  with self.assertRaisesRegex(ValueError,'worker failed'):w.run(b'import sys;sys.exit(1)',{})
 def test_timeout_terminates(self):
  with patch.object(w,'TIMEOUT_SECONDS',.05):
   with self.assertRaisesRegex(ValueError,'timed out'):w.run(SLOW,{})
if __name__=='__main__':unittest.main()
