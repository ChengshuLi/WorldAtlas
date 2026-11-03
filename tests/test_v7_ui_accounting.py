import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('builder', Path(__file__).parents[1] / 'scripts' / 'build_full_v7_ui_bundle.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

class AccountingProofTest(unittest.TestCase):
    def test_missing_and_wrong_are_rejected_correct_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            ui = Path(tmp)
            proof = b'proof'
            proposal = {'accounting': {'url': 'accounting.json', 'sha256': hashlib.sha256(proof).hexdigest()}}
            with self.assertRaises(ValueError): builder.validate_ui_accounting(ui, proposal)
            (ui / 'accounting.json').write_bytes(b'wrong')
            with self.assertRaises(ValueError): builder.validate_ui_accounting(ui, proposal)
            (ui / 'accounting.json').write_bytes(proof)
            builder.validate_ui_accounting(ui, proposal)

if __name__ == '__main__': unittest.main()
