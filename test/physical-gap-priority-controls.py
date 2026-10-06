import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from evidence.immutable import canonical_json, sha256
from physical_gap_priority import investigation_record, partition_accounting, hierarchy_context, investigation_ranks, related_issue_scopes, legacy_grid_links, attach_rank_positions, validate_rank_positions, legacy_water_links, difference_unknown_accounting, issue_subject_index


def fixture(area=1e-12, shore=False, contacts=None):
    if contacts is None:
        contacts = [{'id': 'leaf-a', 'kind': 'positive-length-boundary', 'source': 'original-a', 'reference_year': '2017'},
                    {'id': 'leaf-b', 'kind': 'positive-length-boundary', 'source': 'original-b', 'reference_year': '2019'}]
    feature = {'id': 'fragment-a', 'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [[[0,0],[1,0],[0,1],[0,0]]]},
               'properties': {'area_m2': area, 'exact_location_contacts': contacts, 'water_diagnostics': []}}
    digest = sha256(canonical_json(feature))
    component = {'id': 'component-a', 'properties': {'fragment_bindings': [{'id': 'fragment-a', 'feature_sha256': digest}],
                 'unmeasured_fragment_ids': ['fragment-a'] if area is None else [], 'touches_reference_shore': shore,
                 'measured_fragment_area_sum_m2': 0 if area is None else area}}
    resolved = {'component': 'component-a', 'status': 'complete-recorded-contacts',
                'fragment_contacts': [{'fragment': 'fragment-a', 'feature_sha256': digest,
                                      'status': 'recorded', 'exact_location_contacts': contacts}]}
    return component, resolved, {'fragment-a': feature}


class PriorityControls(unittest.TestCase):
    def test_compiled_issue_rosters_preserve_exact_matches(self):
        rosters = {10:['a','b','c'], 11:['b','d'], 12:['x'], 13:[]}
        indexed=issue_subject_index(rosters)
        for contacts,edges in [(['a','b'],['a','b']),(['b','d'],['d']),([],[]),(['z'],[]),(['x','c'],['x','c'])]:
            observed=related_issue_scopes(contacts,edges,rosters,compiled=indexed)
            expected=[]
            for number,subjects in sorted(rosters.items()):
                matches=sorted(set(contacts)&set(subjects))
                if matches:
                    expected.append({'issue':number,'matching_contact_subject_ids':matches,
                        'qualification':'complete-recorded-edge-subject-roster' if len(set(edges))>=2 and set(edges)<=set(subjects) else 'partial-contact-context',
                        'scope_status':'related-subjects-only-geometry-coverage-unverified'})
            self.assertEqual(observed,expected)

    def test_tiny_positive_interior_seam_retained(self):
        r = investigation_record(*fixture())
        self.assertEqual(r['partition'], 'interior-multiple-edge-neighbors')
        self.assertEqual(r['measured_fragment_area_sum_m2'], 1e-12)
        self.assertEqual(r['surface_status'], 'unverified')
        self.assertIsNone(r['administrative_assignment'])
    def test_point_contacts_do_not_become_neighbors(self):
        contacts = [{'id': i, 'kind': 'point-only-ambiguous', 'source': 's', 'reference_year': None} for i in ('a','b')]
        r = investigation_record(*fixture(contacts=contacts))
        self.assertEqual(r['partition'], 'interior-other-native-cases')
        self.assertEqual(r['positive_length_neighbor_ids'], [])
    def test_no_contact_coast_retained(self):
        r = investigation_record(*fixture(shore=True, contacts=[]))
        self.assertEqual(r['partition'], 'shore-without-source-contacts')
        self.assertEqual(r['surface_status'], 'unverified')
    def test_unmeasured_is_not_zero_impact(self):
        r = investigation_record(*fixture(area=None))
        self.assertEqual(r['partition'], 'original-unknowns')
        self.assertIsNone(investigation_ranks(r, {})['measured_impact'][1])
    def test_changed_whole_feature_rejected(self):
        c, r, f = fixture()
        f['fragment-a']['geometry']['coordinates'][0][1][0] = 1.0000000000000002
        with self.assertRaises(ValueError): investigation_record(c,r,f)
    def test_duplicate_fragment_binding_rejected(self):
        c, r, f = fixture()
        r['fragment_contacts'].append(copy.deepcopy(r['fragment_contacts'][0]))
        with self.assertRaises(ValueError): investigation_record(c,r,f)
    def test_missing_fragment_binding_rejected(self):
        c, r, f = fixture()
        r['fragment_contacts'] = []
        with self.assertRaises(ValueError): investigation_record(c,r,f)
    def test_contact_payload_change_rejected(self):
        c, r, f = fixture()
        r = copy.deepcopy(r)
        r['fragment_contacts'][0]['exact_location_contacts'][0]['id'] = 'different-leaf'
        with self.assertRaises(ValueError): investigation_record(c,r,f)
    def test_removed_original_uncertainty_rejected(self):
        c, r, f = fixture(area=None)
        c['properties']['unmeasured_fragment_ids'] = []
        with self.assertRaises(ValueError): investigation_record(c,r,f)
    def test_partition_omission_and_duplicate_rejected(self):
        r = investigation_record(*fixture())
        for rows, expected in (([],['component-a']),([r,r],['component-a']),([r],['component-a','component-a'])):
            with self.subTest(rows=len(rows), expected=expected):
                with self.assertRaises(ValueError): partition_accounting(rows,expected)
    def test_exact_parent_chain_only(self):
        leaf = {'id': 'id-country-looking-prefix', 'properties': {'parent_id': 'province'}}
        nodes = {'province': {'id':'province','parent_id':'region','level':'province','name':'P'},
                 'region': {'id':'region','parent_id':None,'level':'region','name':'R'}}
        r = hierarchy_context(leaf,nodes)
        self.assertEqual(r['status'],'complete-recorded-ancestry')
        self.assertEqual([n['id'] for n in r['ancestry']],['province','region'])
    def test_missing_and_cycle_are_explicit(self):
        leaf={'id':'leaf','properties':{'parent_id':'p'}}
        self.assertEqual(hierarchy_context(leaf,{})['status'],'missing-recorded-ancestor')
        nodes={'p':{'id':'p','parent_id':'leaf','level':'province'}}
        self.assertEqual(hierarchy_context(leaf,nodes)['status'],'cyclic-recorded-parent')
        leaf['properties']['parent_id']=None
        self.assertEqual(hierarchy_context(leaf,nodes)['status'],'missing-recorded-leaf-parent')
    def test_missing_source_does_not_gain_readiness(self):
        r=investigation_record(*fixture(contacts=[]))
        self.assertEqual(investigation_ranks(r,{})['source_locator_readiness'][:2],[1,1])
    def test_overlay_unknown_precedes_other_partition(self):
        r=investigation_record(*fixture(),links=[{'issue':1}],operation_unknowns=[{'status':'failed'}])
        self.assertEqual(r['partition'],'original-unknowns')
    def test_partial_issue_contact_is_not_full_neighbor_scope(self):
        links=related_issue_scopes(['a','b'],['a','b'],{1:['a'],2:['a','b']})
        self.assertEqual([r['qualification'] for r in links],['partial-contact-context','complete-recorded-edge-subject-roster'])
        self.assertTrue(all(r['scope_status']=='related-subjects-only-geometry-coverage-unverified' for r in links))
    def test_point_only_issue_match_cannot_promote_partition(self):
        links=related_issue_scopes(['leaf-a','leaf-b'],[],{1:['leaf-a','leaf-b']})
        r=investigation_record(*fixture(),links=links)
        self.assertEqual(r['partition'],'interior-multiple-edge-neighbors')
    def test_old_point_relation_sample_remains_historical_only(self):
        link={'new_component':'n','old_component':'o','kinds':['point-only-contact'],'pair_numbers':[1]}
        sample={'component_id':'o','status':'centre-in-gap-unassigned'}
        r=legacy_grid_links('n',[(7,link)],{'o':sample})[0]
        self.assertEqual(r['new_component_grid_status'],'not-exhaustively-assessed')
        self.assertEqual(r['original_relation_kinds'],['point-only-contact'])
    def test_missing_original_grid_sample_is_rejected(self):
        link={'new_component':'n','old_component':'o','kinds':['equal-point-set'],'pair_numbers':[1]}
        with self.assertRaises(ValueError): legacy_grid_links('n',[(1,link)],{})
    def test_changed_known_measurement_sum_rejected(self):
        c,r,f=fixture()
        c['properties']['measured_fragment_area_sum_m2']=0
        with self.assertRaises(ValueError): investigation_record(c,r,f)

    def test_recorded_contact_cannot_be_hidden_as_unknown(self):
        c,r,f=fixture()
        r['fragment_contacts'][0]['status']='unknown-not-recorded'
        r['status']='incomplete-source-contact-recording'
        with self.assertRaises(ValueError): investigation_record(c,r,f)
    def test_missing_ancestor_parent_is_not_completed_ancestry(self):
        leaf={'id':'leaf','properties':{'parent_id':'p'}}
        nodes={'p':{'id':'p','level':'province'}}
        self.assertEqual(hierarchy_context(leaf,nodes)['status'],'missing-recorded-ancestor-parent')

    def test_three_complete_total_orders_without_duplicate_id_tables(self):
        records=[]
        for name,source,coord,impact in [('a',0,2,-2),('b',1,1,-1),('c',2,3,None)]:
            records.append({'component':name,'investigation_orders':{
                'source_locator_readiness':[source,name], 'coordination_complexity':[coord,name],
                'measured_impact':[int(impact is None),impact,name], 'limits':[]}})
        self.assertEqual(attach_rank_positions(records),{name:3 for name in records[0]['rank_positions']})
        self.assertEqual(records[0]['rank_positions']['source_locator_readiness'],0)
        self.assertEqual(records[0]['rank_positions']['coordination_complexity'],1)
        self.assertEqual(records[2]['rank_positions']['measured_impact'],2)
        records[2]['rank_positions']['measured_impact']=0
        with self.assertRaises(ValueError):validate_rank_positions(records)
    def test_duplicate_component_cannot_receive_rank(self):
        r={'component':'a'}
        with self.assertRaises(ValueError):attach_rank_positions([r,r])
    def test_archived_water_does_not_classify_changed_shape(self):
        pilot={'component_id':'o','original_component_feature_sha256':'h',
               'comparison':{'sampled_months':['2017-01','2017-07']},
               'explicit_pilot_aoi':None,'full_component_sampled':True}
        link={'new_component':'n','old_component':'o','kinds':['positive-area-overlap']}
        row=legacy_water_links('n',[(2,link)],{'o':{'original_component_feature_sha256':'h'}},[pilot],{'sha256':'report'})[0]
        self.assertEqual(row['new_component_water_status'],'unverified')
        self.assertEqual(row['measurement_status'],'archived-context-not-recomputed')
        self.assertEqual(row['sampled_months'],['2017-01','2017-07'])
        with self.assertRaises(ValueError):legacy_water_links('n',[(2,link)],{'o':{'original_component_feature_sha256':'changed'}},[pilot],{'sha256':'report'})

    def test_unmatched_old_operation_failure_is_retained(self):
        row={'side':'old','fragment':'f-old','difference':{'status':'unknown-original-operation-failed'}}
        mapped,unmatched,accounting=difference_unknown_accounting([row],{}, {'f-old':'c-old'}, {})
        self.assertEqual(mapped,{})
        self.assertEqual(unmatched[0]['original'],row)
        self.assertEqual(accounting['unmatched_original_error_count'],1)
        self.assertEqual(accounting['mapped_original_error_count'],0)
    def test_one_old_failure_to_two_components_counts_one_original_error(self):
        rows=[{'side':'old','fragment':'o'},{'side':'new','fragment':'n'}]
        mapped,unmatched,a=difference_unknown_accounting(rows,{'n':'a'},{'o':'old'},{'old':['a','b']})
        self.assertEqual(a,{'original_error_count':2,'mapped_original_error_count':2,
                            'unmatched_original_error_count':0,'affected_component_associations':3})
        self.assertEqual(len(mapped['a']),2)
        self.assertEqual(unmatched,[])

if __name__=='__main__': unittest.main()
