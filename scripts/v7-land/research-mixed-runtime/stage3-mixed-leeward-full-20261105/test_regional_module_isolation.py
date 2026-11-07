import hashlib,importlib.util,sys,tempfile,types,unittest
from pathlib import Path

class IsolationTests(unittest.TestCase):
 def test_regional_pair_is_separate_from_stage2_module(self):
  hook=Path(__file__).parent.parent/'lydekker-regional-writer-integration/driver_hook.py'
  spec=importlib.util.spec_from_file_location('regional_hook_isolation_test',hook);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  original=sys.modules.get('run_pair');sentinel=types.ModuleType('run_pair');sys.modules['run_pair']=sentinel
  try:
   with tempfile.TemporaryDirectory() as d:
    p=Path(d)/'pair.py';p.write_text('value = 42\n');digest=hashlib.sha256(p.read_bytes()).hexdigest()
    loaded=module.load_pinned_module('run_pair',p,digest)
    self.assertEqual(loaded.value,42);self.assertIs(sys.modules['run_pair'],sentinel)
    self.assertIs(module.load_pinned_module('run_pair',p,digest),loaded)
    sys.modules.pop('_worldatlas_regional_run_pair_'+digest,None)
  finally:
   if original is None:sys.modules.pop('run_pair',None)
   else:sys.modules['run_pair']=original
