import io,unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch
import watch_group as w
class RetryTests(unittest.TestCase):
 def run_with(self,stats,status):
  entry=SimpleNamespace(name='321',path='/proc/321')
  with patch.object(w.os,'scandir',return_value=nullcontext(iter([entry]))),patch.object(w.Path,'read_text',side_effect=stats),patch('builtins.open',side_effect=status),patch.object(w.time,'sleep'):
   return w.group_rss(123)
 def test_transient_missing_rss_eventually_visible(self):
  count=[0]
  def status(*a,**k):
   count[0]+=1;return io.StringIO('Name:\ttest\n' if count[0]<=8 else 'Name:\ttest\nVmRSS:\t42 kB\n')
  self.assertEqual(self.run_with(lambda:'321 (p) R 1 123 0',status),(42,1));self.assertEqual(count[0],9)
 def test_unobservable_live_process_fails_closed(self):
  with self.assertRaisesRegex(RuntimeError,'RSS unavailable'):self.run_with(lambda:'321 (p) R 1 123 0',lambda *a,**k:io.StringIO('Name:\ttest\n'))
 def test_process_exits_during_retry(self):
  states=iter(['321 (p) R 1 123 0','321 (p) Z 1 123 0'])
  self.assertEqual(self.run_with(lambda:next(states),lambda *a,**k:io.StringIO('Name:\ttest\n')),(0,0))
 def test_retry_guard_is_not_suppressed(self):
  entry=SimpleNamespace(name='321',path='/proc/321')
  def stop(_):raise RuntimeError('host memory floor')
  with patch.object(w.os,'scandir',return_value=nullcontext(iter([entry]))),patch.object(w.Path,'read_text',return_value='321 (p) R 1 123 0'),patch('builtins.open',return_value=io.StringIO('Name:\ttest\n')):
   with self.assertRaisesRegex(RuntimeError,'host memory floor'):w.group_rss(123,stop)
if __name__=='__main__':unittest.main()
