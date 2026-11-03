import json
import unittest
from pathlib import Path


class V7BasinPoliciesTest(unittest.TestCase):
    def test_reviewed_sources_are_unique_and_gulf_is_pending(self):
        path = Path(__file__).resolve().parents[1] / 'data/v7/basin-policies.json'
        policy = json.loads(path.read_text())
        records = policy['named_basins']
        ids = [r['source_id'] for r in records]
        self.assertEqual(len(ids), 92)
        self.assertEqual(len(set(ids)), len(ids))
        gulf = next(r for r in records if r['source_id'] == '24063')
        self.assertEqual(gulf['participant_water_codes'], [6])
        self.assertIn('full rebuild not yet performed', gulf['status'])
        self.assertEqual(gulf['measured_named_basin_overlap_cells'], 0)
        self.assertEqual(len(gulf['raw_source_file_sha256']), 64)
        self.assertTrue(policy['unresolved'])
        self.assertEqual(policy['custom_basins'], [])
        excluded = policy['excluded_named_basins'][0]
        self.assertEqual(excluded['source_id'], 'teluk-cenderawasih-water-to-oceania-v2')
        result = excluded['local_candidate']
        self.assertEqual(result['coastal_oceania_cells'] + result['enclosed_oceania_cells'] + result['pacific_cells'], result['former_named_cells'])
        self.assertEqual(result['candidate_total_v2_to_v7_changed_cells'], 435432577 - result['pacific_cells'])
        self.assertIn('full recomposition pending', excluded['replacement_status'])
        for record in records:
            self.assertTrue(record['participant_water_codes'])
            self.assertTrue(all(1 <= n <= 6 for n in record['participant_water_codes']))


if __name__ == '__main__':
    unittest.main()
