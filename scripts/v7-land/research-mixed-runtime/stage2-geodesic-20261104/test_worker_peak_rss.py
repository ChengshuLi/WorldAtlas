"""Unit checks plus Linux regressions for post-exec RSS high-water accounting."""
import ast,importlib.util,io,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent
BASE=ROOT/'v7-land/named-identity-prototype'
if not BASE.is_dir():BASE=ROOT.parents[2]/'v7-recovery/land/stage2-geodesic-20261104/v7-land/named-identity-prototype'
def load(name):
 s=importlib.util.spec_from_file_location('rss_'+name,BASE/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
worker=load('named_identity');watch=load('identity_watch')
class Parser(unittest.TestCase):
 def test_valid(self):
  with patch('builtins.open',return_value=io.StringIO('Name: worker\nVmHWM:\t1234 kB\n')):self.assertEqual(worker.process_peak_rss_kib(),1234)
 def test_bad_metrics_fail_closed(self):
  for value in ['Name: worker\n','VmHWM: 0 kB\n','VmHWM: -2 kB\n','VmHWM: 2 MB\n','VmHWM: nan kB\n','VmHWM: 2 kB\nVmHWM: 3 kB\n']:
   with self.subTest(value=value),patch('builtins.open',return_value=io.StringIO(value)),self.assertRaises(ValueError):worker.process_peak_rss_kib()
 def test_unavailable_fails_closed(self):
  with patch('builtins.open',side_effect=PermissionError()),self.assertRaises(PermissionError):worker.process_peak_rss_kib()
 def test_legacy_metric_is_rejected(self):
  code=b'import json;print(json.dumps({"schema":"named-identity-worker-v1","peak_rss_kib":1,"result":{}}))'
  with self.assertRaisesRegex(ValueError,'missing metric'):watch.run(code,{},lambda:1)

@unittest.skipUnless(sys.platform=='linux','requires Linux /proc and RSS accounting')
class LinuxPeak(unittest.TestCase):
 def checker(self,allocate=0):
  source=(BASE/'named_identity.py').read_text();tree=ast.parse(source);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('need','process_peak_rss_kib')];body='\n\n'.join(ast.get_source_segment(source,n) for n in nodes)
  code='import re,json,resource\n'+body+'\n'
  if allocate:code+='data=bytearray(%d);del data\n'%allocate
  code+='print(json.dumps({"schema":"named-identity-worker-v2","result":{},"peak_rss_kib":process_peak_rss_kib(),"peak_rss_source":"linux-proc-self-status-VmHWM-kib","rusage_peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))\n'
  return code.encode()
 def test_large_parent_small_exec_child(self):
  large=bytearray(220*1024*1024)
  result=watch.run(self.checker(),{},lambda:1);m=result['memory_monitor']
  self.assertGreater(m['worker_rusage_peak_rss_kib'],watch.RSS_CAP_KIB)
  self.assertLessEqual(m['worker_reported_peak_rss_kib'],watch.RSS_CAP_KIB)
  self.assertEqual(m['worker_reported_peak_rss_source'],'linux-proc-self-status-VmHWM-kib');self.assertEqual(len(large),220*1024*1024)
 def test_released_worker_spike_is_still_rejected(self):
  # Suppress polling only in this test: post-exec peak must catch a missed spike.
  with patch.object(watch,'child_rss',return_value=0),self.assertRaisesRegex(ValueError,'VmHWM_kib='):
   watch.run(self.checker(220*1024*1024),{},lambda:1)
if __name__=='__main__':unittest.main()
