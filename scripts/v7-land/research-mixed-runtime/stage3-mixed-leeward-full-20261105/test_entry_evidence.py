import copy,hashlib,tempfile,unittest
from pathlib import Path
from entry_evidence import resolve
class EvidenceTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)/'article';self.p.write_bytes(b'Human-reviewed text')
  pin={'source_id':'article','version':'v1','sha256':hashlib.sha256(self.p.read_bytes()).hexdigest(),'size_bytes':self.p.stat().st_size,'r2_bucket':'b','r2_key':'k'}
  self.s={'sources':[pin],'source_lineage_assets':[{**pin,'kind':'raw','provenance':{'representation':'provider_original'},'source_uri':'https://example.org/article','provider':'Journal','attribution':'Author','license_name':'CC BY','license_uri':'https://example.org/license'}], 'list1_entry_evidence_sources':[{'decision_revision':'r','entry_id':'e','role':'geographic_membership_evidence','source_id':'article','source_version':'v1','citation_section':'Study area','interpretation':'Yamdena is in Wallacea','limitations':['Human inference; not geometry']}]};self.s['source_lineage_dependencies']=[];self.c={'entry_ids':['e'],'revision':'r'};self.f=[{**pin,'path':str(self.p)}]
 def runv(self):return resolve(self.s,self.c,self.f,lambda:None)
 def test_trace_and_byte_authentication(self):
  x=self.runv()['e'][0];self.assertEqual(x['interpretation_status'],'selected_interpretation');self.assertEqual(x['citation_section'],'Study area');self.assertEqual(x['source_uri'],'https://example.org/article')
 def test_tampering_fails(self):
  self.p.write_bytes(b'bad');self.assertRaises(ValueError,self.runv)
 def test_orphan_revision_duplicate_extra_fail(self):
  orig=copy.deepcopy(self.s)
  for mutate in (lambda x:x['list1_entry_evidence_sources'][0].update(entry_id='unknown'),lambda x:x['list1_entry_evidence_sources'][0].update(decision_revision='other'),lambda x:x['list1_entry_evidence_sources'].append(copy.deepcopy(x['list1_entry_evidence_sources'][0])),lambda x:x['source_lineage_assets'][0].update(r2_key='other'),lambda x:x['source_lineage_assets'][0]['provenance'].update(representation='derived'),lambda x:x['source_lineage_dependencies'].append({'source_id':'article','version':'v1'})):
   self.s=copy.deepcopy(orig);mutate(self.s);self.assertRaises(ValueError,self.runv)
  self.s=orig;self.f.append({**self.f[0],'source_id':'extra'});self.assertRaises(ValueError,self.runv)
 def test_empty_links_allow_no_files(self):
  self.s['list1_entry_evidence_sources']=[];self.assertEqual(resolve(self.s,self.c,[],lambda:None),{'e':[]})
