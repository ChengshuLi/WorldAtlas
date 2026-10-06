"""Controls for the actual identity inventory adapter; never production writes."""
import pathlib
import sys
import unittest
from copy import deepcopy
from shapely.geometry import box, mapping
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from worldwide_gap_inventory import verify, digest, require_equivalent
from geographic_components import components
from physical_gap_crosswalk import membership


class InventoryControls(unittest.TestCase):
    def test_actual_byte_custody(self):
        raw = b'{"original-source":true}'
        row = {'path': 'source.json', 'bytes': len(raw), 'sha256': digest(raw)}
        self.assertEqual(verify(raw, row), raw)
        with self.assertRaises(ValueError): verify(raw + b' ', row)
        with self.assertRaises(ValueError): verify(raw[:-1], row)
        with self.assertRaises(TypeError): verify(None, row)

    def test_forced_changed_operand_reuse_fails(self):
        original = {'geometry': [0, 0, 1, 1], 'metadata': {'id': 'a'}}
        require_equivalent(original, deepcopy(original))
        changed = deepcopy(original); changed['geometry'][2] += 1e-12
        with self.assertRaises(ValueError): require_equivalent(original, changed)
        changed = deepcopy(original); changed['metadata']['id'] = 'b'
        with self.assertRaises(ValueError): require_equivalent(original, changed)

    def test_query_order_and_unknown_state_are_part_of_identity(self):
        original = {'locations': ['a', 'b'], 'blocked': ['missing-source']}
        for changed in ({'locations': ['b', 'a'], 'blocked': ['missing-source']},
                        {'locations': ['a', 'b'], 'blocked': []}):
            with self.assertRaises(ValueError): require_equivalent(original, changed)

    def test_identity_membership_cannot_omit_or_tamper_a_member(self):
        features = [{'type': 'Feature', 'id': 'a', 'geometry': mapping(box(0, 0, 1, 1)),
                     'properties': {'area_m2': None}}]
        records, _ = components(features)
        self.assertEqual(set(membership(features, records)), {'a'})
        with self.assertRaises(ValueError): membership(features, [])
        changed = deepcopy(features); changed[0]['properties']['area_m2'] = 1
        with self.assertRaises(ValueError): membership(changed, records)
        self.assertEqual(records[0]['properties']['unmeasured_fragment_ids'], ['a'])


if __name__ == '__main__': unittest.main()
