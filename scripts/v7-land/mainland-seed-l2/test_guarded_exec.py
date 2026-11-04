import tempfile,pathlib,subprocess,sys,time,unittest
class GuardedExec(unittest.TestCase):
 def test_parent_death_prevents_orphan_work(self):
  with tempfile.TemporaryDirectory() as t:
   d=pathlib.Path(t);started=d/'started';escaped=d/'escaped';program=d/'checker.py';program.write_text("import pathlib,time;pathlib.Path(%r).write_text('started');time.sleep(2);pathlib.Path(%r).write_text('escaped')"%(str(started),str(escaped)));wrapper=pathlib.Path(__file__).with_name('guarded_exec.py')
   parent=d/'parent.py';parent.write_text("import os,subprocess,sys,time;subprocess.Popen([sys.executable,%r,str(os.getpid()),%r],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);p=%r\nfor i in range(100):\n if os.path.exists(p):break\n time.sleep(.01)\nos._exit(0)"%(str(wrapper),str(program),str(started)))
   p=subprocess.run([sys.executable,str(parent)],timeout=5);self.assertEqual(p.returncode,0);self.assertTrue(started.exists());time.sleep(2.3);self.assertFalse(escaped.exists())
if __name__=='__main__':unittest.main()
