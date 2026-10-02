"""Migration invariants using complete tiny geographic trees."""
import copy
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('geographic_decisions', ROOT / 'scripts/apply-geographic-decisions.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
EVIDENCE = [{'url': 'https://example.org/inspected-source', 'title': 'Fixture source', 'inspected_fact': 'The two province fragments share one original named source identity.'}]

def fixture():
    links = [('c', 'continent', None), ('s', 'subcontinent', 'c'), ('r', 'region', 's'), ('a1', 'area', 'r'), ('a2', 'area', 'r'), ('p1', 'province', 'a1'), ('p2', 'province', 'a2')]
    units = {id: {'id': id, 'name': id, 'level': level, 'parent_id': parent, 'metadata': {}} for id, level, parent in links}
    features = [{'id': id, 'geometry': {'type': 'Polygon', 'coordinates': [[[x, 0], [x+1, 0], [x+1, 1], [x, 1], [x, 0]]]}, 'properties': {'name': id, 'parent_id': parent, 'reference_owner': 'Unrelated current owner', 'metadata': {}}} for id, parent, x in [('l1', 'p1', 0), ('l2', 'p2', 1)]]
    decisions = [{'id': id, 'level': u['level'], 'current_name': u['name'], 'current_parent_id': u['parent_id'], 'action': 'open', 'boundary_status': 'open', 'rationale': 'Individual local review pending', 'evidence': [], 'remaining_reasons': ['Local semantic review']} for id, u in units.items()]
    document = {'continent': 'c', 'inventory': {'group_ids': list(units), 'location_ids': ['l1', 'l2']}, 'decisions': decisions, 'location_review': [{'ids': ['l1', 'l2'], 'status': 'open', 'rationale': 'Source roles need review', 'evidence': []}]}
    return units, features, document

class GeographicDecisions(unittest.TestCase):
    def test_complete_inventory_rejects_missing_or_duplicate_location(self):
        units, features, doc = fixture()
        module.validate_inventory(doc, units, features)
        doc['location_review'][0]['ids'] = ['l1', 'l1']
        with self.assertRaisesRegex(ValueError, 'every location'):
            module.validate_inventory(doc, units, features)

    def test_exact_parent_merge_preserves_land_and_original_objects(self):
        units, features, doc = fixture()
        before = copy.deepcopy([units, features])
        row = next(r for r in doc['decisions'] if r['id'] == 'p1')
        row.update(action='merge', target_id='p2', evidence=EVIDENCE, boundary_status='supported')
        revised, migrated, retired = module.apply_documents([doc], units, features)
        self.assertEqual(migrated[0]['properties']['parent_id'], 'p2')
        self.assertEqual([f['geometry'] for f in migrated], [f['geometry'] for f in features])
        self.assertEqual(set(retired), {'p1', 'a1'})
        self.assertEqual(revised['p2']['metadata']['child_count'], 2)
        self.assertEqual([units, features], before)

    def test_stale_decision_rejected_before_any_input_mutation(self):
        units, features, doc = fixture()
        before = copy.deepcopy([units, features])
        doc['decisions'][0]['current_name'] = 'Stale name'
        with self.assertRaisesRegex(ValueError, 'Stale decision'):
            module.apply_documents([doc], units, features)
        self.assertEqual([units, features], before)

    def test_unsupported_geometry_or_cross_tier_merge_rejected(self):
        units, features, doc = fixture()
        row = next(r for r in doc['decisions'] if r['id'] == 'p1')
        row.update(action='merge', target_id='r', evidence=EVIDENCE)
        with self.assertRaisesRegex(ValueError, 'preserve adjacent'):
            module.apply_documents([doc], units, features)

    def test_no_uninspected_or_non_adjacent_parent_assignment(self):
        units, features, doc = fixture()
        row = next(r for r in doc['decisions'] if r['id'] == 'p1')
        row.update(action='reparent', new_parent_id='r')
        with self.assertRaisesRegex(ValueError, 'evidence required'):
            module.apply_documents([doc], units, features)
        row['evidence'] = EVIDENCE
        with self.assertRaisesRegex(ValueError, 'Non-adjacent'):
            module.apply_documents([doc], units, features)

    def test_new_source_group_requires_actual_members(self):
        units, features, doc = fixture()
        doc['decisions'].append({'id': 'a3', 'level': 'area', 'action': 'create', 'new_name': 'Supported physical cluster', 'new_parent_id': 'r', 'boundary_status': 'supported', 'rationale': 'Named source cluster', 'evidence': EVIDENCE, 'remaining_reasons': []})
        with self.assertRaisesRegex(ValueError, 'empty'):
            module.apply_documents([doc], units, features)
        next(r for r in doc['decisions'] if r['id']=='p1').update(action='reparent', new_parent_id='a3', evidence=EVIDENCE)
        revised, migrated, retired = module.apply_documents([doc], units, features)
        self.assertEqual(revised['p1']['parent_id'], 'a3')
        self.assertIn('a1', retired)
        self.assertEqual(migrated[0]['properties']['reference_owner'], features[0]['properties']['reference_owner'])

    def test_location_changes_and_source_roles_preserve_geometry(self):
        units, features, doc = fixture()
        doc['location_changes'] = [{'id':'l1','current_name':'l1','current_parent_id':'p1','action':'rename','new_name':'Decoded name','rationale':'Exact source spelling','evidence':EVIDENCE}]
        doc['location_metadata_changes'] = [{'id':'l1','current_name':'l1','changes':{'source_role':'Physical district'},'rationale':'Inspect original source role','evidence':EVIDENCE}]
        _, changed, _ = module.apply_documents([doc], units, features)
        self.assertEqual(changed[0]['properties']['name'],'Decoded name')
        self.assertEqual(changed[0]['properties']['metadata']['source_role'],'Physical district')
        self.assertEqual(changed[0]['geometry'],features[0]['geometry'])
        doc['location_metadata_changes'][0]['changes'] = {'reference_owner':'Invented owner'}
        with self.assertRaisesRegex(ValueError,'Unsupported reference metadata'):
            module.apply_documents([doc],units,features)

if __name__ == '__main__':
    unittest.main()
