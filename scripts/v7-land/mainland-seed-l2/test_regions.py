import unittest
from regions import assemble,geometry_hash
class Regions(unittest.TestCase):
 def setUp(self):
  self.rev='r1';self.source={('raw','1'):{'kind':'raw','sha256':'a'*64,'bucket':'worldatlas','key':'sources/raw'}}
  line={'type':'LineString','coordinates':[['0','0'],['1','0'],['1','1']]};route={'type':'LineString','coordinates':[['1','1'],['0','1'],['0','0']]}
  h=lambda g:geometry_hash({'type':'LineString','coordinates':[[float(x),float(y)] for x,y in g['coordinates']]})
  self.records={('boundary','east'):{'id':'east','kind':'boundary','revision_id':'r1','execution_status':'selected_for_research','geometry':line,'geometry_hash_method':'binary64-sorted-compact-geojson-v1','geometry_sha256':h(line),'source_refs':[{'source_id':'raw','version':'1'}],'qualified_source_refs':[{'source_id':'raw','version':'1','relationship':'construction_input','role':'construction_input'}],'lineage_status':'incomplete'},('route','closure'):{'id':'closure','kind':'route','role':'water_closure','closure_method':'physical_water_closure_v1','revision_id':'r1','execution_status':'selected_for_research','geometry':route,'geometry_hash_method':'binary64-sorted-compact-geojson-v1','geometry_sha256':h(route)}}
  self.d={'region_id':'europe','revision_id':'r1','execution_status':'selected_for_research','geometry_hash_method':'binary64-sorted-compact-geojson-v1','segments':[{'kind':'boundary','id':'east','start':0,'end':3,'reverse':False},{'kind':'route','id':'closure','start':0,'end':3,'reverse':False}],'geometry_sha256':geometry_hash({'type':'Polygon','coordinates':[[[0.,0.],[1.,0.],[1.,1.],[0.,1.],[0.,0.]]]}),'witnesses':[{'lon':'0.5','lat':'0.5','inside':True}]};self.check=lambda r,pts:{'schema':'physical-water-closure-proof-v1','status':'valid','geometry_sha256':geometry_hash({'type':'LineString','coordinates':[[float(x),float(y)] for x,y in pts]}),'physical_rows_sha256':'b'*64,'physical_runs_sha256':'c'*64,'checker_sha256':'d'*64,'contract_sha256':'e'*64}
 def runv(self):return assemble(self.rev,self.records,self.d,self.source,self.check,physical_rows_sha256='b'*64,physical_runs_sha256='c'*64,checker_sha256='d'*64,closure_contract_sha256='e'*64,guard=lambda:None)
 def test_selected_l2_geometry(self):
  geom,report=self.runv();self.assertEqual(len(geom['coordinates'][0]),5);self.assertEqual(report['lineage_limitations'],['east']);self.assertEqual(report['input_trace'][1]['closure_proof']['physical_rows_sha256'],'b'*64)
 def test_qualified_supporting_citation_in_trace(self):
  q=self.records[('boundary','east')]['qualified_source_refs'][0];q.update(relationship='local_geographic_comparison_not_terrain_or_construction_proof',role='supporting_research_evidence')
  _,report=self.runv();citation=report['input_trace'][0]['source_citations'][0]
  self.assertEqual(citation['role'],'supporting_research_evidence');self.assertEqual(citation['relationship'],q['relationship'])
 def test_inconsistent_role_rejected(self):
  self.records[('boundary','east')]['qualified_source_refs'][0]['role']='supporting_research_evidence'
  with self.assertRaisesRegex(ValueError,'inconsistent source role'):self.runv()
 def test_terminal_closure_bound_to_selected_boundary(self):
  rec=self.records[('route','closure')];rec['closure_method']='physical_terminal_closure_v1';rec['start_terminal']={'boundary_id':'east','endpoint':'end'};rec['end_terminal']={'boundary_id':'east','endpoint':'start'}
  def check(r,pts,refs):
   return {'schema':'physical-terminal-closure-proof-v1','status':'valid','geometry_sha256':geometry_hash({'type':'LineString','coordinates':[[float(x),float(y)] for x,y in pts]}),'physical_rows_sha256':'b'*64,'physical_runs_sha256':'c'*64,'checker_sha256':'f'*64,'contract_sha256':'e'*64,'start_geometry_sha256':refs[0]['geometry_sha256'],'end_geometry_sha256':refs[1]['geometry_sha256'],'start_endpoint':refs[0]['endpoint'],'end_endpoint':refs[1]['endpoint'],'no_land_land_edge_touched':True}
  def execute():return assemble(self.rev,self.records,self.d,self.source,check,physical_rows_sha256='b'*64,physical_runs_sha256='c'*64,checker_sha256='d'*64,closure_contract_sha256='e'*64,guard=lambda:None,terminal_checker_sha256='f'*64)
  execute();rec['start_terminal']['endpoint']='start'
  with self.assertRaisesRegex(ValueError,'endpoint does not match'):execute()
 def test_terminal_checker_pin_required(self):
  rec=self.records[('route','closure')];rec['closure_method']='physical_terminal_closure_v1';rec['start_terminal']={'boundary_id':'east','endpoint':'end'};rec['end_terminal']={'boundary_id':'east','endpoint':'start'}
  with self.assertRaisesRegex(ValueError,'terminal checker pin'):self.runv()
 def test_mismatched_checker_pin(self):
  self.check=lambda r,pts:{'schema':'physical-water-closure-proof-v1','status':'valid','geometry_sha256':geometry_hash({'type':'LineString','coordinates':[[float(x),float(y)] for x,y in pts]}),'physical_rows_sha256':'b'*64,'physical_runs_sha256':'c'*64,'checker_sha256':'0'*64,'contract_sha256':'e'*64}
  with self.assertRaisesRegex(ValueError,'checker pins'):self.runv()
 def test_wrong_closure_geometry_proof(self):
  self.check=lambda r,pts:{'schema':'physical-water-closure-proof-v1','status':'valid','geometry_sha256':'0'*64,'physical_rows_sha256':'b'*64,'physical_runs_sha256':'c'*64,'checker_sha256':'d'*64,'contract_sha256':'e'*64}
  with self.assertRaisesRegex(ValueError,'geometry, physical'):self.runv()
 def test_outside_witness_rejected(self):
  self.d['witnesses'][0]['lon']='181'
  with self.assertRaisesRegex(ValueError,'outside CRS84'):self.runv()
 def test_unselected_boundary(self):
  self.records[('boundary','east')]['execution_status']='proposed'
  with self.assertRaisesRegex(ValueError,'unselected'):self.runv()
 def test_unpinned_raw_citation(self):
  self.source[('raw','1')]['kind']='derived'
  with self.assertRaisesRegex(ValueError,'pinned raw'):self.runv()
 def test_unchecked_connector_rejected(self):
  self.records[('route','closure')]['role']='geographic_connector'
  with self.assertRaisesRegex(ValueError,'physical closure proof'):self.runv()
 def test_missing_water_proof(self):
  self.check=lambda *x:{}
  with self.assertRaisesRegex(ValueError,'water closure'):self.runv()
 def test_hash_method_must_be_explicit(self):
  self.records[('boundary','east')]['geometry_hash_method']='snapshot-encoding'
  with self.assertRaisesRegex(ValueError,'hash method'):self.runv()
 def test_gap(self):
  self.d['segments'][1]['reverse']=True
  with self.assertRaisesRegex(ValueError,'connect exactly'):self.runv()
 def test_geometry_tamper(self):
  self.records[('boundary','east')]['geometry']['coordinates'][1]=['0.9','0']
  with self.assertRaisesRegex(ValueError,'geometry hash'):self.runv()
 def test_wrong_revision(self):
  self.d['revision_id']='other'
  with self.assertRaisesRegex(ValueError,'selected region'):self.runv()
 def test_wrong_region_witness(self):
  self.d['witnesses'][0]['inside']=False
  with self.assertRaisesRegex(ValueError,'witness'):self.runv()
if __name__=='__main__':unittest.main()
