"""Resource-guard tests use synthetic requests, not project data."""
import json, os, select, signal, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import run_direct, watch_direct

class WatchTest(unittest.TestCase):
 def test_direct_run_requires_guardian(self):
  with self.assertRaisesRegex(ValueError,'monitored guardian'):run_direct.run('/not-a-request','/not-an-output')
 def test_watchdog_rejects_retired_driver_before_launch(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);cfg=root/'request';cfg.write_text(json.dumps({'limits':{'minimum_memory_kib':1887437,'minimum_free_bytes':2*1024**3,'max_rss_kib':524288}}))
   with self.assertRaisesRegex(RuntimeError,'planar nearest-side method retired'):watch_direct.run(cfg,root/'out',524288)
   self.assertFalse((root/'out').exists())
 def test_guardian_binds_process_group(self):
  with tempfile.TemporaryDirectory() as t:
   marker=Path(t)/'marker';cr,cw=os.pipe();sr,sw=os.pipe()
   code="import sys;sys.path.insert(0,%r);import run_direct;run_direct.require_guardian();open(%r,'w').write('ok')"%(str(Path(run_direct.__file__).parent),str(marker))
   proc=subprocess.Popen([sys.executable,str(Path(run_direct.__file__).with_name('guardian.py')),str(cr),str(sw),sys.executable,'-c',code],start_new_session=True,pass_fds=(cr,sw),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   os.close(cr);os.close(sw)
   try:
    f=os.fdopen(sr,'rb',buffering=0)
    def event():
     ready,_,_=select.select([f],[],[],5);self.assertTrue(ready,'guardian timeout');return json.loads(f.readline())
    self.assertEqual(event()['event'],'ready');os.write(cw,b'START\n');self.assertEqual(event()['event'],'started');done=event();self.assertEqual((done['event'],done['returncode']),('done',0));self.assertEqual(marker.read_text(),'ok');os.write(cw,b'RELEASE\n');self.assertEqual(proc.wait(timeout=5),0);f.close()
   finally:
    os.close(cw)
    if proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
if __name__=='__main__':unittest.main()

