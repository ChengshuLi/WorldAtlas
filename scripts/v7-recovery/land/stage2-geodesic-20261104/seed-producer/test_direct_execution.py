import tempfile
import unittest
from pathlib import Path
from unittest import mock
import runpy

import closure_client
import region_client
import seed_producer

class DirectSeedExecutionTests(unittest.TestCase):
 def test_new_checker_pair_requires_provisional_mode(self):
  pins={k:{'sha256':v} for k,v in seed_producer.TRUSTED_CODE.items()}
  pins['closure_checker']['sha256']=seed_producer.PROVISIONAL_CLOSURE_CHECKER
  pins['terminal_checker']={'sha256':seed_producer.PROVISIONAL_TERMINAL_CHECKER}
  with self.assertRaisesRegex(ValueError,'unreviewed'):seed_producer.validate_executable_pins(pins,False)
  seed_producer.validate_executable_pins(pins,True)
  with self.assertRaisesRegex(ValueError,'local provisional snapshot'):seed_producer.validate_provisional_checker_source(pins,{'source':'neon-export'},True)
  seed_producer.validate_provisional_checker_source(pins,{'source':'local-derived-from-neon-export'},True)
  pins['closure_checker']['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'unreviewed'):seed_producer.validate_executable_pins(pins,True)
 def test_region_worker_is_invoked_in_process_and_code_is_bound(self):
  with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as wd:
   root=Path(td);work=Path(wd);physical=root/'physical';physical.mkdir();contract=root/'contract.json';contract.write_text('{}');checker=root/'checker.py';checker.write_text('pass')
   request={'closure':{'checker_path':str(checker),'contract_path':str(contract),'physical_dir':str(physical)}}
   expected={'schema':'stage2-region-worker-result-v1','status':'selected-research-region'}
   with mock.patch.object(runpy,'run_path',return_value={'execute':lambda req,guard: expected.copy()}) as run:
    result=region_client.execute(request,work,lambda:None)
   self.assertEqual(result['status'],'selected-research-region')
   self.assertIn('closure_client.py',result['code_sha256'])
   self.assertEqual(run.call_count,1)
   self.assertEqual(request['closure'].get('work_parent'),None)
 def test_pinned_checker_cli_runs_directly_and_captures_output(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);script=d/'checker.py';output=d/'proof.json';log=d/'checker.log'
   script.write_text("import sys\nwith open(sys.argv[1], 'w') as f: f.write('proof')\nprint('validated')\n")
   closure_client._run_checker(script,[output],log)
   self.assertEqual(output.read_text(),'proof')
   self.assertEqual(log.read_text().strip(),'validated')
 def test_seed_runtime_has_no_guarded_wrappers_or_child_supervisor(self):
  base=Path(region_client.__file__).parent
  self.assertFalse((base/'guarded_exec.py').exists())
  self.assertFalse((base/'guarded_raster_exec.py').exists())
  for path in (base/'region_client.py',base/'closure_client.py',base/'seed_producer.py'):
   text=path.read_text()
   self.assertNotIn('subprocess.Popen',text)
   self.assertNotIn('.kill()',text)
if __name__=='__main__':unittest.main()
