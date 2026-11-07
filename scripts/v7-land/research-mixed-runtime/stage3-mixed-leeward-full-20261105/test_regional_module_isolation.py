import sys,types,unittest
from apply_selected_mixed import prepare_regional_hook
class IsolationTests(unittest.TestCase):
 def test_restores_existing_module_even_on_failure(self):
  original=sys.modules.get('run_pair');sentinel=types.ModuleType('run_pair');sys.modules['run_pair']=sentinel
  class Hook:
   def prepare(self,*a,**k):
    assert 'run_pair' not in sys.modules
    sys.modules['run_pair']=types.ModuleType('historical')
    raise ValueError('test')
  req={'code':{'run_pair':{'sha256':'82edc904cd917a41adf7b7c24cdeb3289e7286f9f72498991510818669dec40c'}}}
  try:
   with self.assertRaises(ValueError):prepare_regional_hook(Hook(),req,(),{},True)
   self.assertIs(sys.modules['run_pair'],sentinel)
  finally:
   if original is None:sys.modules.pop('run_pair',None)
   else:sys.modules['run_pair']=original
if __name__=='__main__':unittest.main()
