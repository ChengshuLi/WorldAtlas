import copy, json, unittest
from pathlib import Path
import polygon_policy
class AssertionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.s=json.loads(Path('actual-neon-list1-export-20261104/v16/snapshot.json').read_text());p=json.loads(Path('aegean-chalki-decision-preparation-20261104/proposal.json').read_text())
  for key,value in [('sources',p['source']),('source_lineage_assets',p['source_lineage_asset']),('features',p['feature']),('affiliations',p['affiliation'])]: cls.s[key].append(value)
  cls.ids={a['affiliation_id'] for a in cls.s['affiliations'] if a.get('method') in ('component_intersection_v1','osm_relation_component_intersection_v1','component_containment_v1','osm_archipelago_component_intersection_v1','osm_archipelago_anchored_rings_intersection_v1')}
 def setUp(self): self.snapshot=copy.deepcopy(self.s); self.a=next(a for a in self.snapshot['affiliations'] if a['affiliation_id']=='list1-chalki-alimia-eea-group-europe')
 def adapt(self):return polygon_policy.adapt(self.snapshot,self.ids)
 def test_valid_assertion_is_labelled_and_preserved(self):
  d=next(x for x in self.adapt()['decisions'] if x['affiliation_id']==self.a['affiliation_id']);a=d['exclusion_witness_assertion'];self.assertEqual(a['kind'],'selected_assertion_not_recomputed');self.assertEqual(a['witness'],self.a['evidence']['selector']['exclude_witnesses'][0])
 def test_wrong_coordinate_rejected(self):
  self.a['evidence']['exclusion_witness_evidence']['witness']['lat']='1'
  with self.assertRaisesRegex(ValueError,'assertion witness'):self.adapt()
 def test_wrong_ring_rejected(self):
  self.a['evidence']['exclusion_witness_evidence']['ring_geometry_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'anchor mismatch'):self.adapt()
 def test_wrong_affiliation_revision_rejected(self):
  ref=next(x for x in self.snapshot['affiliations'] if x['affiliation_id']=='list1-aegean-rhodes-astypalaia-anchored-europe');ref['decision_revision']='old'
  with self.assertRaisesRegex(ValueError,'invalid (polygon|selected anchor) affiliation'):self.adapt()
 def test_missing_field_rejected(self):
  del self.a['evidence']['exclusion_witness_evidence']['proof_sha256']
  with self.assertRaisesRegex(ValueError,'invalid exclusion witness assertion'):self.adapt()
 def test_reference_must_be_selected(self):
  self.ids=self.ids-{'list1-aegean-rhodes-astypalaia-anchored-europe'}
  with self.assertRaisesRegex(ValueError,'invalid selected anchor affiliation'):self.adapt()
if __name__=='__main__':unittest.main()
