import unittest
import copy,hashlib,importlib.util,tempfile
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
import reconcile as r

def encode(a):
 ends=[];values=[]
 for i in range(1,len(a)+1):
  if i==len(a) or a[i]!=a[i-1]:ends.append(i);values.append(a[i-1])
 return np.array(ends,dtype=np.uint32),np.array(values,dtype=np.uint32)
def cov():return defaultdict(lambda:{'initial':0,'explained':0,'unresolved':0,'affiliation_ids':set(),'entry_ids':set()})
class RowTests(unittest.TestCase):
 def fixture(self):
  base=encode([17,17,18,18,0,17,17,17]);post=encode([17,18,17,18,0,18,17,17]);reference=encode([17,18,17,18,1,17,17,17]);clusters=[(1,2,18,17,1),(2,3,17,18,1)]
  trace=[{'row':0,'start':1,'end':2,'from_code':17,'to_code':18,'affiliation_ids':['a'],'entry_ids':['ea']},{'row':0,'start':2,'end':3,'from_code':18,'to_code':17,'affiliation_ids':['b'],'entry_ids':['eb']},{'row':0,'start':5,'end':6,'from_code':17,'to_code':18,'affiliation_ids':['a'],'entry_ids':['ea']}]
  return base,post,reference,clusters,trace
 def invoke(self,fixture):
  c=cov();n=Counter();r.evaluate_row(0,8,*fixture,{17,18},{1},{'a':18,'b':17},{'a':['ea'],'b':['eb']},c,n);return c,n
 def test_explained_and_extra_not_conflated(self):
  c,n=self.invoke(self.fixture());self.assertEqual((n['initial_mismatch_cells'],n['post_mismatch_cells'],n['extra_changed_shared_land_cells'],n['changed_cells']),(2,1,1,3));self.assertEqual((c[1]['initial'],c[1]['explained'],c[1]['unresolved']),(2,2,0));self.assertEqual(c[1]['entry_ids'],{'ea','eb'})
 def test_untraced_and_forged_are_rejected(self):
  b,p,ref,cs,t=self.fixture()
  with self.assertRaisesRegex(ValueError,'not exactly covered'):self.invoke((b,p,ref,cs,t[:-1]))
  t[0]['affiliation_ids']=['b']
  with self.assertRaisesRegex(ValueError,'selected decision'):self.invoke((b,p,ref,cs,t))
 def test_missing_cluster_span_rejected(self):
  b,p,ref,cs,t=self.fixture()
  with self.assertRaisesRegex(ValueError,'not exactly covered by clusters'):self.invoke((b,p,ref,cs[:1],t))
 def test_evidence_links_attach_and_missing_entry_rejected(self):
  class Good:
   @staticmethod
   def resolve(snapshot,compiled,files,guard):return {'e1':[{'source_id':'raw'}],'e2':[]}
  compiled={'entries':{'e1':{},'e2':{}}};e=r.attach_selected_evidence(Good,{},compiled,[]);self.assertEqual(compiled['entries']['e1']['geographic_membership_evidence'],[{'source_id':'raw'}]);self.assertEqual(e['e2'],[])
  class Bad:
   @staticmethod
   def resolve(snapshot,compiled,files,guard):return {'e1':[]}
  with self.assertRaisesRegex(ValueError,'evidence entries'):r.attach_selected_evidence(Bad,{},compiled,[])
 def test_real_evidence_reconstruction_and_tampering(self):
  spec=importlib.util.spec_from_file_location('actual_evidence',Path(__file__).resolve().parent.parent/'stage3-mixed-evidence-code-20261104/entry_evidence.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  with tempfile.TemporaryDirectory() as d:
   article=Path(d)/'source';article.write_bytes(b'Human-reviewed text');pin={'source_id':'article','version':'v1','sha256':hashlib.sha256(article.read_bytes()).hexdigest(),'size_bytes':article.stat().st_size,'r2_bucket':'b','r2_key':'k'}
   snap={'sources':[pin],'source_lineage_assets':[{**pin,'kind':'raw','provenance':{'representation':'provider_original'},'source_uri':'https://example.org/article','provider':'Journal','attribution':'Author','license_name':'CC BY','license_uri':'https://example.org/license'}],'source_lineage_dependencies':[],'list1_entry_evidence_sources':[{'decision_revision':'r','entry_id':'e','role':'geographic_membership_evidence','source_id':'article','source_version':'v1','citation_section':'Study area','interpretation':'Selected interpretation','limitations':['Human interpretation']}]}
   files=[{**pin,'path':str(article)}];compiled={'entry_ids':['e'],'revision':'r','entries':{'e':{}}};r.attach_selected_evidence(module,snap,compiled,files);report=copy.deepcopy(compiled);r.require_policy_match(compiled,report)
   report['entries']['e']['geographic_membership_evidence'][0]['interpretation']='altered'
   with self.assertRaisesRegex(ValueError,'policy/evidence'):r.require_policy_match(compiled,report)
   article.write_bytes(b'bad')
   with self.assertRaises(ValueError):r.attach_selected_evidence(module,snap,{'entry_ids':['e'],'revision':'r','entries':{'e':{}}},files)
 def test_zero_first_endpoint_rejected(self):
  offsets=np.array([0,2],dtype=np.uint32);runs=np.array([[0,17],[8,17]],dtype=np.uint32)
  with self.assertRaisesRegex(ValueError,'invalid row coverage'):r.row_grid(offsets,runs,0,8,{17})
 def test_physical_change_rejected(self):
  b,p,ref,cs,t=self.fixture();p=encode([17,18,17,18,17,18,17,17])
  with self.assertRaisesRegex(ValueError,'physical land/water'):self.invoke((b,p,ref,cs,t))
if __name__=='__main__':unittest.main()

class CustodyTests(unittest.TestCase):
 def test_custody_pins_and_tamper(self):
  from types import SimpleNamespace
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'source';f.write_bytes(b'hello');h=hashlib.sha256(b'hello').hexdigest();pin={'source_id':'s','version':'v','sha256':h,'size_bytes':5,'license_name':'unspecified'};cfg={'polygon_source_files':[{'source_id':'s','version':'v','sha256':h,'size_bytes':5,'path':str(f)}]};snap={'affiliations':[{'affiliation_id':'a','method':'component_containment_v1'}]};report={'policy':{'affiliation_entry_links':{'a':['e']}},'polygon_source_custody':[pin]};module=SimpleNamespace(adapt=lambda snap,ids:{'source_pins':[pin]});self.assertEqual(r.validate_polygon_custody(snap,report,cfg,module),[pin]);f.write_bytes(b'HELLO')
   with self.assertRaisesRegex(ValueError,'source bytes mismatch'):r.validate_polygon_custody(snap,report,cfg,module)
 def test_custody_changed_trace_fails(self):
  from types import SimpleNamespace
  snap={'affiliations':[{'affiliation_id':'a','method':'component_containment_v1'}]};report={'policy':{'affiliation_entry_links':{'a':['e']}},'polygon_source_custody':[{'license_name':'approved'}]};module=SimpleNamespace(adapt=lambda snap,ids:{'source_pins':[{'license_name':'unspecified'}]})
  with self.assertRaisesRegex(ValueError,'custody trace mismatch'):r.validate_polygon_custody(snap,report,{},module)

class BeringClaimTests(unittest.TestCase):
 def test_bering_claim_and_wrong_target(self):
  from reconcile import collect_claims
  a={'affiliation_id':'a','method':'label_contained_ecoregion_contact_v1','entity_id':4};s={'affiliations':[a],'category_bindings':[{'entity_id':4,'code':20,'physical_class':'land'}]};c={'affiliation_id':'a','method':a['method'],'entity_id':4,'entity_code':20};r={'policy':{'affiliation_entry_links':{'a':['e']}},'point_resolution':{'claims':[]},'polygon_resolution':{'claims':[]},'bering_resolution':{'claims':[c]}}
  self.assertEqual(collect_claims(r,s),{'a':20});c['entity_code']=18
  with self.assertRaises(ValueError):collect_claims(r,s)

class NewContainmentCustodyTests(unittest.TestCase):
 def test_osm_label_containment_is_in_custody_policy(self):
  from types import SimpleNamespace
  observed=[]
  module=SimpleNamespace(adapt=lambda snap,ids:(observed.append(ids) or {'source_pins':[]}))
  snapshot={'affiliations':[{'affiliation_id':'a','method':'osm_archipelago_component_containment_v1'}]}
  report={'policy':{'affiliation_entry_links':{'a':['entry']}},'polygon_source_custody':[]}
  self.assertEqual(r.validate_polygon_custody(snapshot,report,{'polygon_source_files':[]},module),[])
  self.assertEqual(observed,[{'a'}])
