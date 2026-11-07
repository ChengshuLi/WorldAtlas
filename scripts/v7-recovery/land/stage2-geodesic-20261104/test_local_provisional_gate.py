import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock
import contracts
import test_contracts

HERE=Path(__file__).resolve().parent

def load(name,path,extra):
 sys.path.insert(0,str(extra))
 try:
  spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
 finally:sys.path.pop(0)

resolver=load('provisional_resolver',HERE/'v7-land/mainland-witness-prototype/resolve_mainland.py',HERE/'v7-land/mainland-witness-prototype')
adapter=load('provisional_adapter',HERE/'seed-producer/export_adapter.py',HERE/'seed-producer')
rules=load('provisional_rules',HERE/'seed-producer/seed_rules.py',HERE/'seed-producer')
hints=load('provisional_hints',HERE/'hint-producer/run_diagnostic.py',HERE/'hint-producer')

class ExactLocalGateTests(unittest.TestCase):
 def test_downstream_local_requires_explicit_flag_and_exact_digest(self):
  local={'source':'local-derived-from-neon-export'}
  for module in (resolver,adapter,rules,hints):
   with self.subTest(module=module.__name__):
    self.assertFalse(module.snapshot_source_allowed(local))
    self.assertFalse(module.snapshot_source_allowed(local,True))
    with mock.patch.object(module.hashlib,'sha256') as h:
     h.return_value.hexdigest.return_value='fddc8e6703d4bf8c089f5d94933f05bcf2c2f6580ef162508e772de9e0ed001f'
     self.assertFalse(module.snapshot_source_allowed(local,False))
     self.assertTrue(module.snapshot_source_allowed(local,True))
    self.assertTrue(module.snapshot_source_allowed({'source':'neon-export'}))
    with self.assertRaises(ValueError):module.snapshot_source_allowed(local,1)
 def test_normal_policy_rejects_local_even_if_allowlist_matches(self):
  fixture=test_contracts.ContractsTests();fixture.setUp();s=fixture.snapshot;s['source']='local-derived-from-neon-export'
  with mock.patch.object(contracts,'local_or_neon_source',return_value=True):
   with self.assertRaises(ValueError):contracts.snap_policy(s,'d','e','wgs','1')
   metric,_,_=contracts.snap_policy(s,'d','e','wgs','1',allow_local=True)
   self.assertEqual(metric['policy_id'],'wgs')
 def test_changed_local_snapshot_rejected_even_with_flag(self):
  fixture=test_contracts.ContractsTests();fixture.setUp();s=fixture.snapshot;s['source']='local-derived-from-neon-export';s['changed']=True
  with self.assertRaises(ValueError):contracts.snap_policy(s,'d','e','wgs','1',allow_local=True)

if __name__=='__main__':unittest.main()
