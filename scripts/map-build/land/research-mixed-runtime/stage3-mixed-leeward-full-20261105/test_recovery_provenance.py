import unittest
from unittest.mock import Mock
from apply_selected_mixed import validate_stage2_handoff

class HandoffTests(unittest.TestCase):
 def test_provisional_passes_pinned_inputs_to_validator(self):
  validator=Mock();pins={'report':'pinned'};code={'orchestrator':'pinned'}
  self.assertIs(validate_stage2_handoff(validator,pins,code,True),validator.validate.return_value)
  validator.validate.assert_called_once_with(pins,code,provisional_diagnostic=True)
 def test_validator_failure_is_not_bypassed(self):
  validator=Mock();validator.validate.side_effect=ValueError('derived manifest mismatch')
  with self.assertRaisesRegex(ValueError,'derived manifest mismatch'):
   validate_stage2_handoff(validator,{}, {},True)
 def test_normal_candidate_does_not_enable_provisional_mode(self):
  validator=Mock();validate_stage2_handoff(validator,{}, {},False)
  validator.validate.assert_called_once_with({}, {})
