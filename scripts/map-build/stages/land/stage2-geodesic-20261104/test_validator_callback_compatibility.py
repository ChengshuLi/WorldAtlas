"""The optional validation callback is forwarded without an implicit no-op."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import validate_stage2_candidate as v
class CallbackCompatibilityTests(unittest.TestCase):
 def test_supplied_callback_reaches_input_hashing(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'file';p.write_bytes(b'x');names={'report','derived_manifest','outer_config','rows','runs','snapshot','physical_rows','physical_runs','physical_report','physical_lineage_request','physical_lineage_report'};pins={k:{'path':str(p),'sha256':'a'*64} for k in names};guard=lambda:None
   with patch.object(v.verify_inputs,'sha_file',side_effect=RuntimeError('seen')) as sha:
    with self.assertRaisesRegex(RuntimeError,'seen'):v.validate(pins,{},guard)
    self.assertIs(sha.call_args.args[1],guard)
 def test_absent_callback_does_not_inject_noop(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'file';p.write_bytes(b'x');names={'report','derived_manifest','outer_config','rows','runs','snapshot','physical_rows','physical_runs','physical_report','physical_lineage_request','physical_lineage_report'};pins={k:{'path':str(p),'sha256':'a'*64} for k in names}
   with patch.object(v.verify_inputs,'sha_file',side_effect=RuntimeError('seen')) as sha:
    with self.assertRaisesRegex(RuntimeError,'seen'):v.validate(pins,{})
    self.assertEqual(len(sha.call_args.args),1)
if __name__=='__main__':unittest.main()
