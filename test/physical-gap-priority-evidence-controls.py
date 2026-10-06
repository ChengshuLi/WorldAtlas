import copy
import importlib.util
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from physical_gap_priority import investigation_record, investigation_ranks, attach_rank_positions

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

validator=load('scripts/validate-physical-gap-priorities.py','priority_validator')
fixtures=load('test/physical-gap-priority-controls.py','priority_fixtures')

class OriginalEvidenceControls(unittest.TestCase):
    def setUp(self):
        component,resolved,features=fixtures.fixture()
        row=investigation_record(component,resolved,features)
        row.update(legacy_grid_context=[],archived_water_context=[],missing_native_contact_ids=[])
        row['investigation_orders']=investigation_ranks(row,{})
        self.expected=copy.deepcopy(row)
        attach_rank_positions([row])
        self.row=row

    def test_unchanged_complete_semantic_record(self):
        validator.require_semantic_row(self.row,self.expected)

    def test_rehashed_contact_omission_rejected(self):
        self.row['source_contact_references'].pop()
        with self.assertRaises(ValueError):validator.require_semantic_row(self.row,self.expected)

    def test_promoted_physical_surface_rejected(self):
        self.row['surface_status']='dry-land'
        with self.assertRaises(ValueError):validator.require_semantic_row(self.row,self.expected)

    def test_redirected_fragment_binding_rejected(self):
        self.row['original_fragment_bindings'][0]['feature_sha256']='f'*64
        with self.assertRaises(ValueError):validator.require_semantic_row(self.row,self.expected)

    def test_omitted_uncertainty_field_rejected(self):
        del self.row['operation_unknowns']
        with self.assertRaises(ValueError):validator.require_semantic_row(self.row,self.expected)

    def test_invented_issue_scope_rejected(self):
        self.row['linked_followups']=[{'issue':99999,'qualification':'complete-recorded-edge-subject-roster'}]
        with self.assertRaises(ValueError):validator.require_semantic_row(self.row,self.expected)

    def test_altered_recorded_measurement_rejected(self):
        self.row['measured_fragment_area_sum_m2']=0
        with self.assertRaises(ValueError):validator.require_semantic_row(self.row,self.expected)

if __name__=='__main__':unittest.main()
