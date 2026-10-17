"""Real adverse invocations of all new preparation methods; no scientific replay."""
import pathlib,subprocess,sys,tempfile,unittest
W=pathlib.Path(sys.argv.pop(1)).resolve();C=sys.argv.pop(1);P=W/'coordination/engineering/korea-native-repair-20261017'
class BoundaryControls(unittest.TestCase):
 def test_refusals(self):
  for name in ['prepare-stage.py','screen-foreign.py','prepare-native-config.py']:
   for case in ['existing-output','dangling-output','invalid-commit','method-not-at-commit']:
    with self.subTest(method=name,case=case),tempfile.TemporaryDirectory(prefix='kor-controls-')as d:
     root=pathlib.Path(d);out=root/'output';commit=C
     if case=='existing-output':out.mkdir();(out/'sentinel').write_text('preserve')
     elif case=='dangling-output':out.symlink_to(root/'missing')
     elif case=='invalid-commit':commit='HEAD'
     else:commit='3b3e9e675cfb37999d5665438f9fbf25bbd4238b'
     r=subprocess.run([sys.executable,str(P/'method'/name),str(W),commit,str(out)],capture_output=True,text=True,timeout=30)
     self.assertNotEqual(r.returncode,0,r.stdout)
     if case=='existing-output':self.assertEqual((out/'sentinel').read_text(),'preserve');self.assertEqual(list(out.iterdir()),[out/'sentinel'])
     elif case=='dangling-output':self.assertTrue(out.is_symlink());self.assertFalse((root/'missing').exists())
     else:self.assertFalse(out.exists())
     print(name,case,'refused without publication',flush=True)
unittest.main(verbosity=2)
