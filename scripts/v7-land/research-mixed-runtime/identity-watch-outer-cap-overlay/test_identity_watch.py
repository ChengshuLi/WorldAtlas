"""Synthetic regression: parent high-water mark must not reject an exec child."""
import importlib.util, pathlib, subprocess, sys, unittest
WATCH=(pathlib.Path(__file__).resolve().parent/'identity_watch.py')
class TestIdentityWatch(unittest.TestCase):
 def test_inherited_peak_is_not_child_cap(self):
  script='''import importlib.util\nspec=importlib.util.spec_from_file_location("watch",%r);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\nx=bytearray(220*1024*1024)\ncode=b'import json,resource\\nprint(json.dumps({"schema":"named-identity-worker-v1","peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,"result":42}))'\nr=m.run(code,{},lambda:1234567)\nassert r["result"]==42 and r["memory_monitor"]["rss_cap_kib"] is None and r["memory_monitor"]["worker_reported_peak_rss_kib"]>196608\n''' % str(WATCH)
  subprocess.run([sys.executable,'-c',script],check=True)
 def test_invalid_result_fails(self):
  spec=importlib.util.spec_from_file_location('watch',WATCH);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  with self.assertRaises(ValueError): m.run(b'print("{}")',{},lambda:1234567)
if __name__=='__main__':unittest.main()
