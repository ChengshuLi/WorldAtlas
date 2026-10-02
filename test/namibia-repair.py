"""Independent checks of the isolated complete-country replacement stage."""
import gzip
import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from shapely.geometry import shape
from shapely import union_all
from ellipsoidal_area import area


def read(path):
    with gzip.open(path, 'rt') if str(path).endswith('.gz') else open(path) as stream:
        return json.load(stream)


class NamibiaReplacement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage = ROOT / '.cache/namibia-repair-stage'
        if not (cls.stage / 'migration.json.gz').exists():
            raise RuntimeError('Run python scripts/stage-namibia-repair.py before the dataset gate')
        cls.report = read(cls.stage / 'migration.json.gz')
        cls.locations = read(cls.stage / 'locations.geojson.gz')['features']
        cls.units = read(cls.stage / 'hierarchy.json')
        cls.archived = read(cls.stage / 'archive.geojson.gz')['features']

    def test_all_old_and_new_entities_accounted_for(self):
        self.assertEqual(len(self.locations), 107)
        self.assertEqual(len({f['properties']['id'] for f in self.locations}), 107)
        self.assertEqual(len(self.archived), 111)
        audit = read(ROOT / 'data/namibia-source-review.json.gz')
        self.assertEqual({f['properties']['id'] for f in self.archived}, {r['id'] for r in audit['current_locations']})
        self.assertEqual({f['properties']['metadata']['original_id'] for f in self.locations}, {r['code'] for r in audit['candidate_locations']})
        self.assertTrue({f['properties']['id'] for f in self.locations}.isdisjoint({f['properties']['id'] for f in self.archived}))

    def test_complete_nonempty_adjacent_parent_chains(self):
        units = {u['id']: u for u in self.units}
        counts = {}
        for f in self.locations:
            parent = f['properties']['parent_id']
            for level in ['province', 'area', 'region', 'subcontinent', 'continent']:
                self.assertEqual(units[parent]['level'], level)
                counts[parent] = counts.get(parent, 0) + 1
                parent = units[parent]['parent_id']
            self.assertIsNone(parent)
        self.assertEqual(sum(u['level'] == 'province' for u in self.units), 14)
        self.assertTrue(all(counts.get(u['id'], 0) for u in self.units))
        self.assertTrue(any(counts[u['id']] > 1 for u in self.units if u['level'] == 'province'))

    def test_all_source_territories_valid_and_nonoverlapping(self):
        polygons = [shape(f['geometry']) for f in self.locations]
        self.assertTrue(all(g.is_valid and not g.is_empty for g in polygons))
        self.assertAlmostEqual(sum(area(g) for g in polygons), area(union_all(polygons)), delta=.1)
        self.assertAlmostEqual(area(union_all(polygons))/1e6, self.report['geometry']['land_footprint_km2'], places=6)

    def test_source_errors_not_reintroduced_as_identity_or_history(self):
        arandis = next(f for f in self.locations if f['properties']['name'] == 'Arandis')
        point = shape(arandis['geometry']).representative_point()
        self.assertLess(point.x, 17)  # Original corrupt Arandis row was around 21-22°E.
        self.assertGreater(point.y, -24)
        self.assertLess(point.y, -20)
        for f in self.locations:
            p = f['properties']
            self.assertEqual(p['metadata']['reference_year'], '2011')
            self.assertIn('No imported historical attributes', p['metadata']['historical_assignment'])
            for attribute in ['owner', 'population', 'culture', 'religion', 'rank', 'habitation']:
                self.assertNotIn(attribute, p)
        self.assertEqual(self.report['status'], 'blocked')
        self.assertEqual({b['code'] for b in self.report['blocks']}, {'neighbor-source-boundary-conflicts', 'old-land-left-without-source-territory'})

    def test_every_residual_land_component_explicitly_unassigned(self):
        unresolved = read(self.stage / 'unresolved-land.geojson.gz')['features']
        self.assertTrue(unresolved)
        self.assertTrue(all(f['properties']['assigned_location'] is None for f in unresolved))
        measured = sum(area(shape(f['geometry'])) for f in unresolved)
        self.assertAlmostEqual(measured/1e6, self.report['geometry']['old_land_lost_not_mapped_elsewhere_km2'], places=6)
        self.assertEqual(self.report['world_locations_inspected'], 49614)
        self.assertEqual(len(self.report['neighbor_conflicts']), 25)

    def test_all_original_source_proofs_retained_and_hash_validated(self):
        root = ROOT / 'data/retained-geographic-sources/namibia'
        manifest = read(root / 'manifest.json')
        for record in manifest['sources']:
            stored = (root / record['path']).read_bytes()
            self.assertLess(len(stored), 16*1024*1024)
            self.assertEqual(hashlib.sha256(stored).hexdigest(), record['retained_sha256'])
            raw = gzip.decompress(stored) if record['encoding'] == 'gzip' else stored
            self.assertEqual(hashlib.sha256(raw).hexdigest(), record['original_sha256'])

    def test_fresh_checkout_restores_all_inputs_without_network(self):
        spec = importlib.util.spec_from_file_location('stage_namibia_repair', ROOT/'scripts/stage-namibia-repair.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            temporary = pathlib.Path(folder)
            with patch.object(module, 'ROOT', temporary), patch.object(module, 'CACHE', temporary/'.cache/namibia-source-review'):
                module.restore_pinned_inputs()
                manifest = read(module.RETAINED/'manifest.json')
                for record in manifest['sources']:
                    if 'input_cache_path' in record:
                        restored = module.CACHE/record['input_cache_path']
                        self.assertEqual(hashlib.sha256(restored.read_bytes()).hexdigest(), record['original_sha256'])

    def test_coast_extensions_have_full_source_concordance_and_no_new_overlap(self):
        review = read(self.stage/'coastal-extension-review.json.gz')
        extended = read(self.stage/'locations-coastal-concordance.geojson.gz')['features']
        self.assertEqual(review['original_records_reviewed'], 109)
        self.assertEqual(review['candidate_groups_reviewed'], 107)
        self.assertEqual(len(review['source_groups']), 107)
        self.assertFalse(review['conflicts'])
        self.assertGreater(review['safe_coast_restored_m2'], 0)
        self.assertGreater(review['remaining_unresolved_old_land_m2'], 0)
        additions = []
        for old, new in zip(self.locations, extended):
            self.assertEqual(old['properties']['id'], new['properties']['id'])
            additions.append(shape(new['geometry']).difference(shape(old['geometry'])))
        self.assertAlmostEqual(sum(area(g) for g in additions), review['safe_coast_restored_m2'], delta=.1)
        self.assertAlmostEqual(sum(area(g) for g in additions), area(union_all(additions)), delta=.1)

    def test_synthetic_coast_restore_rejects_inland_and_weak_geometry_matches(self):
        spec = importlib.util.spec_from_file_location('stage_namibia_repair', ROOT/'scripts/stage-namibia-repair.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        from shapely.geometry import box, mapping, LineString
        original = {'features': [{'properties': {'ADM2': 'Untrusted wrong name'}, 'geometry': mapping(box(0, 0, 10, 10))}]}
        source = [{'properties': {'adm2_pcode': 'CODE', 'adm2_name': 'Verified name'}}]
        land = box(0, 0, 10, 10)
        coast = LineString([(10, 0), (10, 10)])
        with patch.object(module, 'load', return_value=original):
            safe, review = module.coastal_concordance(source, [box(0, 0, 9.8, 10)], land, coast, box(9.8, 0, 10, 10), land)
            self.assertGreater(review['safe_coast_restored_m2'], 0)
            self.assertEqual(review['historical_attribute_transfer'], 'None')
            safe, review = module.coastal_concordance(source, [box(0, 0, 10, 9.8)], land, coast, box(0, 9.8, 9, 10), land)
            self.assertEqual(review['safe_coast_restored_m2'], 0)
            self.assertTrue(any('inland' in row['decision'] for row in review['residual_components']))
            safe, review = module.coastal_concordance(source, [box(0, 0, 5, 10)], land, coast, box(5, 0, 10, 10), land)
            self.assertEqual(review['safe_coast_restored_m2'], 0)


if __name__ == '__main__':
    unittest.main()
