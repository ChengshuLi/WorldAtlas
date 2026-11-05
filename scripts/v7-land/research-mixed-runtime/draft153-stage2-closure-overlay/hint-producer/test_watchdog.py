import json,unittest
from unittest import mock
import test_cli
import watch_diagnostic
class WatchTests(unittest.TestCase):
 def setUp(self):self.x=test_cli.CLITests();self.x.setUp()
 def tearDown(self):self.x.tearDown()
 def test_success_marker_and_bound_report(self):
  out=self.x.p/'out'/'watched';r=watch_diagnostic.run(self.x.req,out,300000,.05)
  self.assertEqual(r['status'],'sampled-complete');self.assertTrue((out/'report.json').is_file());self.assertTrue((out/'monitor.json').is_file())
 def test_pidfd_open_failure_kills_and_reaps(self):
  child=mock.Mock();child.pid=123
  with mock.patch.object(watch_diagnostic.subprocess,'Popen',return_value=child),mock.patch.object(watch_diagnostic.os,'pidfd_open',side_effect=OSError('failed')):
   with self.assertRaises(OSError):watch_diagnostic.run(self.x.req,self.x.p/'out'/'pidfd',300000,.05)
  child.kill.assert_called_once();child.wait.assert_called_once()
 def test_rss_limit_rejects_completion(self):
  out=self.x.p/'out'/'killed'
  with self.assertRaisesRegex(RuntimeError,'diagnostic not accepted'):watch_diagnostic.run(self.x.req,out,1,.05)
  self.assertFalse((out/'monitor.json').exists())
if __name__=='__main__':unittest.main()
