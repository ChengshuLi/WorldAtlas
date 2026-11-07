import unittest
from unittest.mock import patch

import caucasus_stage2_validation as adapter


class ValidationAdapterTest(unittest.TestCase):
    def test_seed_snapshot_mismatch_rejected_before_validator(self):
        view = {'derived': True}
        trace = {'effective_snapshot': {'original_snapshot_sha256': 'a' * 64}}
        called = []
        with patch.object(adapter, 'verify_code'), patch.object(adapter, 'derive_verified', return_value=(view, trace)):
            with self.assertRaisesRegex(ValueError, 'original snapshot'):
                adapter.validate(lambda *a, **k: called.append(True), {'decision_snapshot_sha256': 'b' * 64},
                                 {}, {}, {}, request_path='request', request_sha256='c' * 64,
                                 recipe='recipe', recipe_sha256='d' * 64, hydro='hydro', author='author', code_sha256={})
        self.assertEqual(called, [])

    def test_independent_validator_receives_effective_view(self):
        view = {'derived': True}
        trace = {'effective_snapshot': {'original_snapshot_sha256': 'a' * 64}}
        expected = {'request': 'c' * 64, 'recipe': 'd' * 64,
                    'hydro': list(adapter.SOURCE_PINS.values())[0], 'author': list(adapter.SOURCE_PINS.values())[1]}
        received = []
        def validator(snapshot, seed, groups, codes, metric, guard):
            received.append(snapshot)
            return 'validated'
        with patch.object(adapter, 'verify_code'), patch.object(adapter, 'derive_verified', return_value=(view, trace)), patch.object(adapter, 'digest', side_effect=lambda p: expected[p]):
            result, report = adapter.validate(validator, {'decision_snapshot_sha256': 'a' * 64}, {}, {}, {},
                                              request_path='request', request_sha256='c' * 64,
                                              recipe='recipe', recipe_sha256='d' * 64, hydro='hydro', author='author', code_sha256={})
        self.assertEqual(received, [view])
        self.assertEqual(result, 'validated')
        self.assertEqual(report['schema'], 'caucasus-source-validation-v1')

    def test_incomplete_code_pins_rejected(self):
        with self.assertRaisesRegex(ValueError, 'complete code pins'):
            adapter.verify_code({})


if __name__ == '__main__':
    unittest.main()
