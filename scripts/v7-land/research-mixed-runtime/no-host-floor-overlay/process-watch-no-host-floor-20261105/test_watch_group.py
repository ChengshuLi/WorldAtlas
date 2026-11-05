import json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
WATCH=Path(__file__).with_name('watch_group.py').resolve();PY='/usr/bin/python3'
def args(log,cmd,timeout=5,rss=150000):return [PY,str(WATCH),'--log-dir',str(log),'--disk-path',str(log.parent),'--disk-floor-bytes','1048576','--group-rss-kib',str(rss),'--timeout',str(timeout),'--',*cmd]
class Watcher(unittest.TestCase):
 def test_success(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);mark=root/'done';r=subprocess.run(args(root/'log',[PY,'-c',"from pathlib import Path;Path(%r).write_text('ok')"%str(mark)]),capture_output=True,text=True,timeout=10)
   self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(mark.read_text(),'ok');self.assertEqual(json.loads((root/'log'/'watchdog.json').read_bytes())['status'],'complete')
 def test_timeout_kills_descendant(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);mark=root/'late';script="import subprocess,time,sys;subprocess.Popen([sys.executable,'-c',%r]);time.sleep(10)"%("import time;from pathlib import Path;time.sleep(2);Path(%r).write_text('late')"%str(mark))
   r=subprocess.run(args(root/'log',[PY,'-c',script],timeout=.5),capture_output=True,text=True,timeout=10);self.assertNotEqual(r.returncode,0);time.sleep(2.3);self.assertFalse(mark.exists())
 def test_group_rss_limit(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);r=subprocess.run(args(root/'log',[PY,'-c','import time;time.sleep(3)'],rss=1),capture_output=True,text=True,timeout=10);self.assertNotEqual(r.returncode,0);self.assertIn('RSS limit',r.stderr)
 def test_monitor_parent_death_kills_descendant(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);started=root/'started';late=root/'late'
   worker="import time;from pathlib import Path;Path(%r).write_text('start');time.sleep(2);Path(%r).write_text('late')"%(str(started),str(late))
   argv=args(root/'log',[PY,'-c',worker],timeout=10)
   parent="import subprocess,time,os;from pathlib import Path;p=subprocess.Popen(%r,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);s=Path(%r);deadline=time.monotonic()+5\nwhile not s.exists() and time.monotonic()<deadline:time.sleep(.02)\nos._exit(0 if s.exists() else 3)"%(argv,str(started))
   r=subprocess.run([PY,'-c',parent],timeout=8);self.assertEqual(r.returncode,0);time.sleep(2.3);self.assertFalse(late.exists())
if __name__=='__main__':unittest.main()
