"""Regression checks for stage-2 controls and disk-only checkpoint guards."""
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
 def test_disk_guard_is_independent(self):
  ns=load_functions('checkpoints.py',{'guard'},{'shutil':shutil})
  with tempfile.TemporaryDirectory() as path:
   with patch.object(shutil,'disk_usage',return_value=shutil._ntuple_diskusage(100,50,50)):
    ns['guard'](path,0)
    with self.assertRaisesRegex(RuntimeError,'disk guard'):
     ns['guard'](path,51)
 def test_controls_have_no_memory_or_cache_limits(self):
  def need(ok,msg):
   if not ok: raise ValueError(msg)
  ns=load_functions('build_stage2.py',{'validate_controls'},{'need':need})
  c={'minimum_free_bytes':1,'chunk_columns':1,'checkpoint_seconds':1,'numerical_guard_metres':1000,'block_records':1}
  ns['validate_controls'](c)
  for key,value in [('minimum_free_bytes',0),('chunk_columns',0)]:
   d=dict(c);d[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):ns['validate_controls'](d)
  self.assertEqual(set(c),{'minimum_free_bytes','chunk_columns','checkpoint_seconds','numerical_guard_metres','block_records'})
if __name__=='__main__':unittest.main()
