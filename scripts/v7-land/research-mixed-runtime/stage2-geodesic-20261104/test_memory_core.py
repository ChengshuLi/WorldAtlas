"""Focused checks of retained disk and control behavior without optional scientific packages."""
import ast
import pathlib
import shutil
import tempfile
import unittest
from unittest.mock import patch
HERE=pathlib.Path(__file__).resolve().parent

def load_functions(filename, names, namespace):
 tree=ast.parse((HERE/filename).read_text())
 nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 exec(compile(ast.Module(body=nodes, type_ignores=[]),str(HERE/filename),'exec'),namespace)
 return namespace

class CoreGuardTest(unittest.TestCase):
 def setUp(self):
  self.ns=load_functions('checkpoints.py',{'guard'},{'shutil':shutil,'memory_available_kib':lambda:50})
 def test_disk_guard_retained_independent_of_former_floor(self):
  with tempfile.TemporaryDirectory() as path:
   with patch.object(shutil,'disk_usage',return_value=shutil._ntuple_diskusage(100,50,50)):
    self.ns['guard'](path,0,50)
    self.ns['guard'](path,50,50)
    with self.assertRaisesRegex(RuntimeError,'memory guard'):
     self.ns['guard'](path,51,50)
    with self.assertRaisesRegex(RuntimeError,'disk guard'):
     self.ns['guard'](path,0,51)
 def test_controls_allow_zero_memory_but_keep_other_bounds(self):
  def need(ok,msg):
   if not ok: raise ValueError(msg)
  ns=load_functions('build_stage2.py',{'validate_controls'},{'need':need})
  c={'minimum_memory_kib':0,'minimum_free_bytes':1,'chunk_columns':1,'checkpoint_seconds':1,'tile_cache_bytes':1024,'numerical_guard_metres':1000,'block_records':1}
  ns['validate_controls'](c)
  for key,value in [('minimum_memory_kib',-1),('minimum_free_bytes',0),('chunk_columns',0),('tile_cache_bytes',0)]:
   d=dict(c);d[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):ns['validate_controls'](d)
if __name__=='__main__':unittest.main()
