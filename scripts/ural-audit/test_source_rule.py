import copy,unittest
from source_rule import derive,digest
class SourceRuleTest(unittest.TestCase):
 def setUp(self):
  b={'type':'LineString','coordinates':[[1,3],[1,1],[1,.5]]};c={'type':'LineString','coordinates':[[1,.5],[1,.25],[-1,.25],[-2,.25]]};self.snapshot={'mainland_boundaries':[{'boundary_id':'boundary','geometry_sha256':digest(b),'geometry':b}],'routes':[{'route_id':'closure','geometry_sha256':digest(c),'geometry':c}]};self.obs={'lineage':{'selected_boundary_sha256':digest(b),'selected_closure_sha256':digest(c)},'apply':{'config':{'bounds':[0,0,2,2],'europe_witness':[.5,1.5],'asia_witness':[1.5,1.5]}}};self.att={'schema':'neon-current-boundary-selection-attestation-v1','retrieved_at_utc':'now','boundary_id':'boundary','route_id':'closure','boundary_sha256':digest(b),'closure_sha256':digest(c)}
 def test_derives_from_sources_and_scope(self):
  d,c=derive(self.snapshot,self.obs,self.att);self.assertEqual(d,[[1,3],[1,1],[1,.5],[1,.25],[-1,.25]])
 def test_rejects_stale_boundary(self):
  a=copy.deepcopy(self.att);a['boundary_sha256']='stale'
  with self.assertRaises(ValueError):derive(self.snapshot,self.obs,a)
 def test_rejects_source_mutation(self):
  s=copy.deepcopy(self.snapshot);s['routes'][0]['geometry']['coordinates'][1][0]+=.1
  with self.assertRaises(ValueError):derive(s,self.obs,self.att)
 def test_rejects_ambiguous_side_witness(self):
  o=copy.deepcopy(self.obs);o['apply']['config']['asia_witness']=o['apply']['config']['europe_witness']
  with self.assertRaises(ValueError):derive(self.snapshot,o,self.att)
if __name__=='__main__':unittest.main()

class AttestationTest(unittest.TestCase):
    def test_identity_and_observation_must_match(self):
        from source_rule import authenticate_attestation
        current = {'project_id':'project-a','branch_id':'branch-a','observation_sha256':'hash-a'}
        authenticate_attestation(current, 'hash-a', 'project-a', 'branch-a')
        for h,p,b in [('hash-b','project-a','branch-a'),('hash-a','project-b','branch-a'),('hash-a','project-a','branch-b')]:
            with self.assertRaises(ValueError): authenticate_attestation(current,h,p,b)

class CategoryCodecTests(unittest.TestCase):
    def test_swapped_codes_follow_selected_registry(self):
        from source_rule import category_codec
        snap={'entities':[{'id':1,'name':'Asia','level':'continent'},{'id':2,'name':'Europe','level':'continent'}],
              'category_bindings':[{'entity_id':1,'physical_class':'land','code':19},{'entity_id':2,'physical_class':'land','code':18}]}
        result=category_codec(snap,{'18':'Europe','19':'Asia'})
        self.assertEqual((result['asia_code'],result['europe_code'],result['land_codes']),(19,18,[18,19]))
        with self.assertRaises(ValueError): category_codec(snap,{'18':'Asia','19':'Europe'})
    def test_changed_or_missing_land_set_fails_closed(self):
        from source_rule import category_codec
        snap={'entities':[{'id':1,'name':'Asia','level':'continent'},{'id':2,'name':'Europe','level':'continent'}],
              'category_bindings':[{'entity_id':1,'physical_class':'land','code':18},{'entity_id':2,'physical_class':'land','code':19}]}
        with self.assertRaises(ValueError): category_codec(snap,{'18':'Asia','19':'Europe','20':'North America'})


class ReferenceCodecTests(unittest.TestCase):
    def test_reference_codec_must_match_candidate(self):
        from source_rule import require_reference_categories
        ref={'categories':[{'id':18,'name':'Asia','physical_class':'land'},{'id':19,'name':'Europe','physical_class':'land'}]}
        require_reference_categories({'18':'Asia','19':'Europe'},ref)
        with self.assertRaises(ValueError): require_reference_categories({'18':'Europe','19':'Asia'},ref)
        with self.assertRaises(ValueError): require_reference_categories({'18':'Asia'},ref)
