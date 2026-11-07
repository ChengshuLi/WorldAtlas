import copy,hashlib,json,unittest
import snapshot_compatibility as c

def raw(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
class CompareTest(unittest.TestCase):
 def setUp(self):
  self.a={'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export','decision_revision':{'id':'land','status':'draft','entity_revision':'e','evidence':{'x':'old'}},'entity_revision':{'id':'e','status':'draft'},'policies':[{'id':'land-policy','kind':'land','definition':{'a':1}}],'features':[{'id':'f','coordinates':[1,2]}],'affiliations':[{'decision_revision':'land','id':'a'}]}
  self.b=copy.deepcopy(self.a);self.b['decision_revision'].update(id='water',evidence={'x':'new'});self.b['affiliations'][0]['decision_revision']='water';self.b['policies'] += [{'id':'coast','kind':'coastline_assignment'},{'id':'closed','kind':'closed_water_assignment'}]
 def compare(self):
  a=raw(self.a);b=raw(self.b);return c.compare(a,sha(a),b,sha(b))
 def test_only_policy_addition_matches(self):self.assertEqual(self.compare()['status'],'projection-match-only-not-lineage-authorization')
 def test_changed_land_or_other_policy_rejected(self):
  for mutate in (lambda x:x['features'][0]['coordinates'].__setitem__(0,3),lambda x:x['policies'][0]['definition'].__setitem__('a',2),lambda x:x['affiliations'][0].__setitem__('decision_revision','wrong'),lambda x:x.__setitem__('extra',[])):
   b=copy.deepcopy(self.b);mutate(self.b)
   with self.assertRaises(ValueError):self.compare()
   self.b=b
 def test_bad_water_policy_cardinality_rejected(self):
  self.b['policies'].append({'id':'extra','kind':'coastline_assignment'})
  with self.assertRaisesRegex(ValueError,'exactly two'):self.compare()
 def test_nested_revision_payload_is_not_normalized(self):
  self.a['policies'][0]['definition']['decision_revision']='land';self.b['policies'][0]['definition']['decision_revision']='water'
  with self.assertRaisesRegex(ValueError,'land-relevant'):self.compare()
 def test_json_types_do_not_collapse(self):
  for value in (True,1.0):
   previous=self.b['features'][0]['coordinates'][0];self.b['features'][0]['coordinates'][0]=value
   with self.assertRaisesRegex(ValueError,'land-relevant'):self.compare()
   self.b['features'][0]['coordinates'][0]=previous
 def test_distinct_high_precision_numbers_are_not_collapsed(self):
  a=raw(self.a).replace(b'[1,2]',b'[1.00000000000000001,2]');b=raw(self.b).replace(b'[1,2]',b'[1.00000000000000002,2]')
  with self.assertRaisesRegex(ValueError,'land-relevant'):c.compare(a,sha(a),b,sha(b))
 def test_missing_entity_or_ambiguous_json_rejected(self):
  for invalid in (b'{\"source\":\"neon-export\",\"source\":\"neon-export\"}',b'{\"value\":NaN}',b'{\"value\":1e999}'):
   with self.assertRaises(ValueError):c.checked_snapshot(invalid,sha(invalid))
  self.b['entity_revision']['id']=None;self.b['decision_revision']['entity_revision']=None
  with self.assertRaisesRegex(ValueError,'entity identity'):self.compare()
 def test_hash_and_schema_rejected(self):
  x=raw(self.a)
  with self.assertRaisesRegex(ValueError,'pin mismatch'):c.compare(x,'0'*64,raw(self.b),sha(raw(self.b)))
  self.b['source']='file'
  with self.assertRaisesRegex(ValueError,'Neon export'):self.compare()
if __name__=='__main__':unittest.main()
