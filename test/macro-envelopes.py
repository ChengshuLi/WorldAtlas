import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('envelopes', ROOT / 'scripts/prepare-macro-envelopes.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def polygon(west, east):
    return {'type': 'Polygon', 'coordinates': [[[west, 0], [east, 0], [east, 1], [west, 1], [west, 0]]]}


def fixture(directory):
    directory.mkdir()
    units, features = [], []
    for i in range(6):
        parent = None
        for tier in ['continent', 'subcontinent', 'region', 'area', 'province']:
            identity = f'{tier}:{i}'
            units.append({'id': identity, 'name': identity, 'level': tier, 'parent_id': parent})
            parent = identity
        identity = f'location:{i}'
        features.append({'id': identity, 'type': 'Feature', 'properties': {
            'id': identity, 'parent_id': parent}, 'geometry': polygon(i * 10, i * 10 + 1)})
    (directory / 'hierarchy.json').write_text(json.dumps(units))
    (directory / 'world-index.json').write_text(json.dumps({'parts': ['locations.json']}))
    (directory / 'locations.json').write_text(json.dumps({'type': 'FeatureCollection', 'features': features}))
    return features


class EnvelopeTest(unittest.TestCase):
    def test_interior_split_preserves_frozen_outer_envelope(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            data, baseline = root / 'data', root / 'baseline'
            features = fixture(data)
            first = module.prepare(data, baseline)
            self.assertEqual(first['groups'], 18)
            self.assertEqual(first['overlap_pairs'], 0)
            self.assertEqual(first['parent_union_mismatches'], 0)
            features[0]['geometry'] = polygon(0, .5)
            extra = json.loads(json.dumps(features[0]))
            extra['id'] = extra['properties']['id'] = 'location:split'
            extra['geometry'] = polygon(.5, 1)
            features.append(extra)
            (data / 'locations.json').write_text(json.dumps({'features': features}))
            second = module.prepare(data, root / 'split', baseline)
            self.assertEqual(second['locations'], 7)
            self.assertEqual(second['baseline_changes'], 0)
            features[0]['geometry'] = polygon(.1, .5)
            (data / 'locations.json').write_text(json.dumps({'features': features}))
            changed = module.prepare(data, root / 'changed', baseline)
            self.assertEqual(changed['baseline_changes'], 3)

    def test_overlaps_and_changed_baseline_are_visible(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            data = root / 'data'
            features = fixture(data)
            features[1]['geometry'] = polygon(.5, 1.5)
            (data / 'locations.json').write_text(json.dumps({'features': features}))
            result = module.prepare(data, root / 'out')
            self.assertEqual(result['overlap_pairs'], 3)
            report = module.read(root / 'out/envelope-index.json')
            self.assertTrue(all(row['area_m2'] > 0 for row in report['same_tier_overlaps']))
            self.assertFalse(report['source_coverage_approved'])
            damaged = root / 'out' / report['groups'][0]['path']
            damaged.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'baseline envelope asset changed'):
                module.prepare(data, root / 'second', root / 'out')


if __name__ == '__main__':
    unittest.main()
