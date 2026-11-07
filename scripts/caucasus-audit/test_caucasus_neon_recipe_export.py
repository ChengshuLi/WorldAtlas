import hashlib
import json
import unittest

from caucasus_neon_recipe_export import canonical_recipe


class RecipeExportTest(unittest.TestCase):
    def test_preserves_integral_floats_and_rejects_normalization(self):
        raw = '{"schema":"caucasus-selector-runs-research-v1","edge":[4,1.0]}'
        expected = json.dumps(json.loads(raw), sort_keys=True, separators=(',', ':')).encode()
        pin = hashlib.sha256(expected).hexdigest()
        self.assertEqual(canonical_recipe(raw, pin), expected)
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            canonical_recipe(raw.replace('1.0', '1'), pin)

    def test_duplicate_and_nonfinite_values_rejected(self):
        for raw in ('{"schema":"caucasus-selector-runs-research-v1","x":1,"x":2}',
                    '{"schema":"caucasus-selector-runs-research-v1","x":NaN}'):
            with self.assertRaises(ValueError):
                canonical_recipe(raw, '0' * 64)


if __name__ == '__main__':
    unittest.main()
