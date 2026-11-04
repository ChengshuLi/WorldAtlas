import tempfile,pathlib,subprocess,sys,time,unittest,os,struct
from seed_producer import group_rss_kib
class RasterGuard(unittest.TestCase):
 def test_raster_wrapper_allows_output_above_eight_mib(self):
  with tempfile.TemporaryDirectory() as t:
   d=pathlib.Path(t);script=d/'write.py';out=d/'large';script.write_text("with open(%r,'wb') as f:f.seek(9*1024*1024);f.write(b'x')"%str(out));p=subprocess.run(['/usr/bin/python3',str(pathlib.Path(__file__).with_name('guarded_raster_exec.py')),str(os.getpid()),str(script)],timeout=10);self.assertEqual(p.returncode,0);self.assertGreater(out.stat().st_size,8<<20)
 def test_group_rss_measurable(self):self.assertGreater(group_rss_kib(os.getpgrp()),0)
 def test_raster_kernel_parent_death(self):
  with tempfile.TemporaryDirectory() as t:
   d=pathlib.Path(t);binary=d/'kernel';source=pathlib.Path(__file__).parent/'rasterizer'/'seed_kernel.cpp';subprocess.run(['g++','-O2','-std=c++17',str(source),'-o',str(binary)],check=True);(d/'rows').write_bytes(struct.pack('<II',0,1));(d/'runs').write_bytes(struct.pack('<III',0,1,1));(d/'rules').write_text('1 0 17 17\n');pidfile=d/'pid';parent=d/'parent.py';parent.write_text("import os,subprocess,time,pathlib; p=subprocess.Popen([%r,%r,%r,%r,%r,%r,'8','1',str(os.getpid())],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);pathlib.Path(%r).write_text(str(p.pid));time.sleep(30)"%(str(binary),str(d/'rows'),str(d/'runs'),str(d/'rules'),str(d/'outrows'),str(d/'outruns'),str(pidfile)))
   p=subprocess.Popen([sys.executable,str(parent)]);self.addCleanup(lambda: p.poll() is None and p.kill())
   for _ in range(100):
    if pidfile.exists() and (d/'outrows').exists():break
    time.sleep(.02)
   self.assertTrue(pidfile.exists());self.assertTrue((d/'outrows').exists());child=int(pidfile.read_text());p.kill();p.wait(timeout=3)
   for _ in range(100):
    try:
     text=pathlib.Path('/proc/%s/stat'%child).read_text();state=text[text.rfind(')')+2:].split()[0]
     if state in ('Z','X'):break
    except (FileNotFoundError,ProcessLookupError):break
    time.sleep(.02)
   else:self.fail('rasterizer kernel remained live after its parent died')
if __name__=='__main__':unittest.main()
