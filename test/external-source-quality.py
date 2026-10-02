"""External source issues never mutate geography or approve blocked replacements."""
import copy,gzip,hashlib,importlib.util,json,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('quality',ROOT/'scripts/external-source-quality.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class ExternalQuality(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.data=ROOT/'data';base=cls.data/'retained-geographic-sources/namibia'
  cls.features=module.annotations.read(base/'archived-atlas-locations.geojson.gz')['features'];cls.units=module.annotations.read(base/'archived-atlas-hierarchy.json.gz')
 def test_complete_proven_review_preserves_exact_input(self):
  before=json.dumps([self.features,self.units],sort_keys=True)
  reviews=module.validated_reviews(self.data,self.features,self.units)
  self.assertEqual(before,json.dumps([self.features,self.units],sort_keys=True))
  self.assertEqual(len(reviews['locations']),111);self.assertEqual(len(reviews['groups']),24)
  self.assertFalse(reviews['profiles']['Namibia']['semantic_complete'])
  self.assertEqual(reviews['profiles']['Namibia']['candidate_source']['status'],'blocked')
 def test_source_territory_survives_sovereign_owner_normalization(self):
  self.assertEqual(module.source_country_codes({'id':'ASM-5000','properties':{'reference_owner':'United States of America','metadata':{}}}),['ASM'])
  self.assertEqual(module.source_country_codes({'id':'atlas:physical:example','properties':{'metadata':{'source_id':'resolve:100','source_member_ids':['gb:MNP:ADM2:123','gb:USA:ADM2:456']}}}),['MNP','USA'])
 def test_optional_absent_file_supports_independent_fixtures(self):
  with tempfile.TemporaryDirectory() as tmp:self.assertEqual(module.validated_reviews(pathlib.Path(tmp),[],[]),{'profiles':{},'locations':{},'groups':{},'manifest':[]})
 def test_bad_current_membership_is_rejected(self):
  features=copy.deepcopy(self.features);features[0]['properties']['parent_id']='wrong'
  with self.assertRaises(AssertionError):module.validated_reviews(self.data,features,self.units)
 def test_stale_evidence_is_rejected_without_input_mutation(self):
  with tempfile.TemporaryDirectory() as tmp:
   data=pathlib.Path(tmp);plan=module.annotations.read(self.data/'namibia-source-quality-annotations.json')
   for proof in plan['profile_review']['public_evidence_files']:
    path=data/proof['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((self.data/proof['path']).read_bytes())
   (data/'namibia-source-review.json.gz').write_bytes(b'stale')
   (data/'namibia-source-quality-annotations.json').write_text(json.dumps(plan))
   with self.assertRaisesRegex(ValueError,'Stale source evidence'):module.validated_reviews(data,self.features,self.units)
if __name__=='__main__':unittest.main()
