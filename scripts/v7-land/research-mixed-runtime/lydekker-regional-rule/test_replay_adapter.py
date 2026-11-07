import unittest
from replay_adapter import resolve_with_mixed_replay


def c(w=0,e=0,o=0):
    n=w+e+o
    return dict(total=n,in_scope=n,west=w,east=e,boundary=0,outside_latitude=o)

class MixedFixture:
    def __init__(self, claims): self.claims=claims; self.called=False
    def combine(self,compiled,snapshot,reports,protected):
        self.called=True
        assert compiled == {'revision':'test'} and snapshot == {'snapshot':'test'} and reports == ['report'] and protected == {7}
        return self.claims

class TestReplayAdapter(unittest.TestCase):
    def test_selected_groups_override_line_and_endpoints(self):
        claims={1:[{'affiliation_id':'source-group','entry_ids':['entry'], 'code':22}],
                2:[{'affiliation_id':'selected-asia','entry_ids':['entry'], 'code':18}],
                3:[{'affiliation_id':'other-continent','entry_ids':['entry'], 'code':9}]}
        module=MixedFixture(claims)
        result=resolve_with_mixed_replay({1:c(w=5),2:c(w=2,o=3),3:c(e=2),4:c(w=2),7:c(e=1)},
                                         {'revision':'test'},{'snapshot':'test'},['report'],{7},module)
        self.assertTrue(module.called)
        self.assertEqual(result['proposals'][1]['code'],22)
        self.assertEqual(result['proposals'][2]['code'],18)
        self.assertEqual(result['review'][3],'existing_other_continent')
        self.assertEqual(result['proposals'][4]['code'],18)
        self.assertEqual(result['review'][7],'protected_mainland')
        self.assertEqual(result['replayed_claims'][1],claims[1])
    def test_pending_source_group_is_not_assigned(self):
        module=MixedFixture({})
        pending=[{'component_id':1,'source_id':'place-source','source_version':'v1','source_feature_id':'boo','source_sha256':'a'*64,'review_reason':'group conflict'}]
        out=resolve_with_mixed_replay({1:c(w=3)},{'revision':'test'},{'snapshot':'test'},['report'],{7},module,pending)
        self.assertNotIn(1,out['proposals']);self.assertEqual(out['review'][1],'source_group_pending_review')
        self.assertEqual(out['pending_source_claims'][1],pending)
    def test_pending_review_precedes_other_continent_claim(self):
        module=MixedFixture({1:[{'code':9}]})
        pending=[{'component_id':1,'source_id':'s','source_version':'v1','source_feature_id':'f','source_sha256':'a'*64,'review_reason':'conflict'}]
        out=resolve_with_mixed_replay({1:c(w=3)},{'revision':'test'},{'snapshot':'test'},['report'],{7},module,pending)
        self.assertEqual(out['review'][1],'source_group_pending_review')
        self.assertNotIn(1,out['proposals'])

    def test_conflicting_replayed_claims_fail(self):
        module=MixedFixture({1:[{'code':18},{'code':22}]})
        with self.assertRaisesRegex(ValueError,'conflicting'): resolve_with_mixed_replay({1:c(w=1)},{'revision':'test'},{'snapshot':'test'},['report'],{7},module)


class TestActualMixedClaims(unittest.TestCase):
    def test_with_existing_mixed_resolver(self):
        import importlib.util, os
        from pathlib import Path
        path=os.environ.get('MIXED_CLAIMS_PATH')
        if not path:
            candidate=Path(__file__).resolve().parent.parent/'stage3-mixed-leeward-full-20261105'/'mixed_claims.py'
            if not candidate.exists(): self.skipTest('existing mixed resolver unavailable in isolated checkout')
            path=str(candidate)
        spec=importlib.util.spec_from_file_location('actual_mixed_claims',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        compiled={'revision':'r1','entity_revision':'e1','affiliation_ids':['group'], 'affiliation_entry_links':{'group':['e']}}
        snapshot={'affiliations':[{'affiliation_id':'group','method':'component_intersection_v1','entity_id':5}],
                  'category_bindings':[{'entity_id':5,'physical_class':'land','code':22}]}
        reports=[{'schema':'source-polygon-component-report-v1','status':'research-only-not-a-build','revision':'r1','entity_revision':'e1','claims':[{'affiliation_id':'group','entity_id':5,'entity_code':22,'method':'component_intersection_v1','component_ids':[1]}]}]
        result=resolve_with_mixed_replay({1:c(w=3),2:c(e=2)},compiled,snapshot,reports,set(),module)
        self.assertEqual(result['proposals'][1]['code'],22)
        self.assertEqual(result['proposals'][2]['code'],22)
        with self.assertRaisesRegex(ValueError,'selected affiliation not resolved'):
            resolve_with_mixed_replay({1:c(w=3)},compiled,snapshot,[dict(reports[0],claims=[])],set(),module)

if __name__=='__main__': unittest.main()
