import hashlib,json,os,signal,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import watch_stage2 as w

class WatchTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name);self.code=self.root/'code';self.code.mkdir();self.inputs=self.root/'inputs';self.inputs.mkdir();self.out=self.root/'out';self.work=self.root/'work';self.watcher=self.code/'watch_stage2.py';self.watcher.write_bytes(Path(w.__file__).read_bytes());(self.code/'guardian.py').write_bytes(Path(w.__file__).with_name('guardian.py').read_bytes());(self.code/'build_stage2.py').write_text('# synthetic core\n');self.driver=self.code/'orchestrate_stage2.py';self.cfg=self.inputs/'config.json';self.cfg.write_text(json.dumps({'controls':{'minimum_memory_kib':1,'minimum_free_bytes':1}}))
 def driver_code(self,body):self.driver.write_text('import json,os,sys,time,subprocess\n'+body+'\n')
 def launch(self,limit=10**8):
  with patch.object(w,'__file__',str(self.watcher)):return w.run(self.cfg,self.work,self.out,limit,interval=.02)
 def test_complete_monitor_is_last_and_bound_to_report(self):
  self.driver_code("time.sleep(.15);h=lambda p:__import__('hashlib').sha256(open(p,'rb').read()).hexdigest();os.makedirs(os.path.join(sys.argv[2],'core-requests'));os.makedirs(os.path.join(sys.argv[2],'derived'));m=os.path.join(sys.argv[2],'derived','manifest.json');open(m,'w').write('{}');prov={'outer_config_sha256':h(sys.argv[1]),'orchestrator_sha256':h(__file__),'derived_manifest':{'path':m,'sha256':h(m)}};cp=os.path.join(sys.argv[2],'core-requests','config.json');json.dump({'orchestration':prov},open(cp,'w'));os.mkdir(sys.argv[3]);json.dump({'schema':'stage2-source-geodesic-report-v1','status':'stage2-research-awaiting-monitor','publishable':False,'monitor_required':True,'config_sha256':h(cp),'code_sha256':{'build_stage2.py':h(os.path.join(os.path.dirname(__file__),'build_stage2.py'))},'orchestration':prov},open(os.path.join(sys.argv[3],'report.json'),'w'));time.sleep(.15)")
  result=self.launch();self.assertEqual(result['status'],'sampled-complete');self.assertGreater(result['samples'],0);self.assertEqual(result['report_sha256'],hashlib.sha256((self.out/'report.json').read_bytes()).hexdigest());self.assertTrue((self.out/'monitor.json').exists())
 def test_rss_limit_kills_group_and_no_marker(self):
  self.driver_code('time.sleep(2)')
  with self.assertRaisesRegex(RuntimeError,'RSS limit'):self.launch(1)
  self.assertFalse((self.out/'monitor.json').exists())
 def test_failed_child_is_not_accepted(self):
  self.driver_code('time.sleep(.15);sys.exit(3)')
  with self.assertRaisesRegex(RuntimeError,'driver exit|RSS unavailable'):self.launch()
  self.assertFalse((self.out/'monitor.json').exists())
 def test_live_descendant_after_exit_is_rejected(self):
  self.driver_code("subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)']);time.sleep(.2)")
  with self.assertRaisesRegex(RuntimeError,'live process-group|RSS unavailable'):self.launch()
 def test_pidfd_setup_failure_kills_gated_guardian(self):
  marker=self.root/'started';self.driver_code(f"open({str(marker)!r},'w').write('bad');time.sleep(2)")
  with patch.object(w.os,'pidfd_open',side_effect=OSError('synthetic pidfd failure')):
   with self.assertRaisesRegex(OSError,'pidfd failure'):self.launch()
  self.assertFalse(marker.exists());self.assertFalse(self.out.exists())
 def test_monitor_death_kills_driver_and_descendant(self):
  ids=self.root/'ids';marker=self.root/'late';childcode=f"import time;time.sleep(2);open({str(marker)!r},'w').write('escaped')"
  self.driver_code(f"p=subprocess.Popen([sys.executable,'-c',{childcode!r}]);open({str(ids)!r},'w').write(str(os.getpgrp()));time.sleep(20)")
  monitor=subprocess.Popen([sys.executable,str(self.watcher),str(self.cfg),str(self.work),str(self.out),str(10**8)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   deadline=time.monotonic()+8
   while not ids.exists() and time.monotonic()<deadline:time.sleep(.05)
   self.assertTrue(ids.exists(),'driver did not start');group=int(ids.read_text());os.kill(monitor.pid,signal.SIGKILL);monitor.wait()
   deadline=time.monotonic()+5
   while time.monotonic()<deadline:
    try:_,live=w.group_rss(group)
    except RuntimeError:
     time.sleep(.05);continue
    if not live:break
    time.sleep(.05)
   self.assertEqual(live,0,'guardian failed to kill driver group');time.sleep(2.1);self.assertFalse(marker.exists());self.assertFalse((self.out/'monitor.json').exists())
  finally:
   if monitor.poll() is None:monitor.kill();monitor.wait()
 def test_nonzero_guardian_after_release_never_signals_reaped_group(self):
  self.driver_code('pass')
  guardian=self.code/'guardian.py';guardian.write_text("import json,os,sys,time\nc,s=map(int,sys.argv[1:3])\ndef emit(x): os.write(s,(json.dumps(x)+'\\n').encode())\nemit({'event':'ready','guardian':os.getpid(),'group':os.getpgrp()});os.read(c,100);emit({'event':'started','driver_pid':os.getpid()});emit({'event':'done','returncode':0});os.read(c,100);sys.exit(7)\n")
  with patch.object(w.os,'killpg') as kill:
   with self.assertRaisesRegex(ValueError,'guardian did not exit cleanly'):self.launch()
   kill.assert_not_called()
 def test_nondefault_sigchld_rejected_before_spawn(self):
  self.driver_code('time.sleep(1)')
  with patch.object(w.signal,'getsignal',return_value=signal.SIG_IGN):
   with self.assertRaisesRegex(ValueError,'dedicated single-threaded'):self.launch()
  self.assertFalse(self.out.exists())
 def test_lost_child_ownership_never_signals_group(self):
  self.driver_code('time.sleep(1)');real_popen=w.subprocess.Popen;spawned=[]
  def capture(*a,**k):
   p=real_popen(*a,**k);spawned.append(p);return p
  with patch.object(w.subprocess,'Popen',side_effect=capture),patch.object(w.os,'waitid',side_effect=ChildProcessError()),patch.object(w.os,'killpg') as kill:
   with self.assertRaisesRegex(RuntimeError,'cleanup uncertain'):self.launch()
   kill.assert_not_called()
  if spawned:
   try:spawned[0].wait(timeout=5)
   except subprocess.TimeoutExpired:self.fail('guardian did not self-clean after control EOF')
 def test_prelaunch_memory_floor(self):
  self.driver_code('time.sleep(1)')
  with patch.object(w,'memory_available',return_value=0):
   with self.assertRaisesRegex(ValueError,'resource floor'):self.launch()
  self.assertFalse(self.out.exists())

def process_group():
 p=subprocess.Popen([sys.executable,'-c',"import subprocess,sys,time;subprocess.Popen([sys.executable,'-c','import time;time.sleep(2)']);time.sleep(2)"],start_new_session=True)
 try:
  time.sleep(.3);return w.group_rss(p.pid)
 finally:
  try:os.killpg(p.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  p.wait()
class GroupTests(unittest.TestCase):
 def test_exited_process_lookup_race_is_skipped(self):
  from types import SimpleNamespace
  class Entries:
   def __enter__(self):return iter([SimpleNamespace(name='123',path='/proc/123')])
   def __exit__(self,*args):return False
  with patch.object(w.os,'scandir',return_value=Entries()),patch.object(w.Path,'read_text',side_effect=ProcessLookupError()):
   self.assertEqual(w.group_rss(123),(0,0))
 def test_transient_missing_rss_rechecks_exit_and_live_failure(self):
  from types import SimpleNamespace
  import io
  class Entries:
   def __enter__(self):return iter([SimpleNamespace(name='123',path='/proc/123')])
   def __exit__(self,*args):return False
  with patch.object(w.os,'scandir',return_value=Entries()),patch.object(w.Path,'read_text',side_effect=['123 (x) S 1 123','123 (x) Z 1 123']),patch('builtins.open',return_value=io.StringIO('Name: x\n')),patch.object(w.time,'sleep'):
   self.assertEqual(w.group_rss(123),(0,0))
  with patch.object(w.os,'scandir',return_value=Entries()),patch.object(w.Path,'read_text',return_value='123 (x) S 1 123'),patch('builtins.open',side_effect=lambda *a,**k:io.StringIO('Name: x\n')),patch.object(w.time,'sleep'):
   with self.assertRaisesRegex(RuntimeError,'RSS unavailable'):w.group_rss(123)
 def test_group_counts_descendant_rss(self):
  rss,members=process_group();self.assertGreater(rss,0);self.assertGreaterEqual(members,2)

if __name__=='__main__':unittest.main()
