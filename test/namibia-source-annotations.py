import copy
import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('namibia_annotations', ROOT/'scripts/prepare-namibia-source-annotations.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SourceQualityPlan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = module.read(ROOT/'data/namibia-source-quality-annotations.json')
        retained = ROOT/'data/retained-geographic-sources/namibia'
        cls.features = module.read(retained/'archived-atlas-locations.geojson.gz')['features']
        cls.units = module.read(retained/'archived-atlas-hierarchy.json.gz')

    def test_every_current_location_and_parent_is_exactly_guarded(self):
        self.assertTrue(module.validate_against_current(self.plan, self.features, self.units))
        self.assertEqual(self.plan['counts']['locations'], 111)
        self.assertEqual(self.plan['counts']['parent_groups'], 24)
        self.assertTrue(all(set(r['metadata_patch']) == {'source_quality_review'} for r in self.plan['feature_annotations'] + self.plan['group_annotations']))

    def test_partial_country_or_ancestor_annotations_rejected(self):
        for field in ['feature_annotations', 'group_annotations']:
            plan = copy.deepcopy(self.plan)
            plan[field].pop()
            with self.assertRaises(AssertionError):
                module.validate_against_current(plan, self.features, self.units)

    def test_changes_to_geometry_name_parent_or_source_rejected(self):
        for field in ['name', 'parent_id', 'source_id']:
            plan = copy.deepcopy(self.plan)
            plan['feature_annotations'][0]['expected'][field] = 'unexpected-change'
            with self.assertRaises(AssertionError):
                module.validate_against_current(plan, self.features, self.units)
        features = copy.deepcopy(self.features)
        features[0]['geometry']['coordinates'][0][0][0] += .0001
        with self.assertRaises(AssertionError):
            module.validate_against_current(self.plan, features, self.units)

    def test_nonmetadata_mutation_fields_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan['feature_annotations'][0]['metadata_patch']['owner'] = 'Unapproved'
        with self.assertRaises(AssertionError):
            module.validate_against_current(plan, self.features, self.units)

    def test_entire_profile_stays_open_including_plausible_names(self):
        profile = self.plan['profile_review']
        self.assertFalse(profile['semantic_complete'])
        self.assertEqual(profile['current_location_count'], 111)
        self.assertEqual(profile['candidate_location_count'], 107)
        self.assertEqual(profile['candidate_source']['status'], 'blocked')
        self.assertEqual(profile['current_source']['vintage'], '2007')
        self.assertIn('2011', profile['candidate_source']['vintage'])
        self.assertTrue(all(r['metadata_patch']['source_quality_review']['status'] == 'pending-source-replacement' for r in self.plan['feature_annotations']))
        self.assertEqual(sum('Normalized label matches' in r['metadata_patch']['source_quality_review']['individual_correspondence'] for r in self.plan['feature_annotations']), 3)
        self.assertTrue(all('Namibia descendant' in r['metadata_patch']['source_quality_review']['scope'] for r in self.plan['group_annotations']))

    def test_every_public_evidence_pointer_has_durable_matching_bytes(self):
        for row in self.plan['profile_review']['public_evidence_files']:
            path = ROOT/'data'/row['path']
            self.assertTrue(path.exists(), row['path'])
            self.assertEqual(module.file_hash(path), row['sha256'])


if __name__ == '__main__':
    unittest.main()
