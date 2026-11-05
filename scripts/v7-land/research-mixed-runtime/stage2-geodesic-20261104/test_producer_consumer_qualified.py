"""Synthetic producer-to-crosswalk test; closure checker is deliberately mocked."""
import copy,unittest
from test_contracts_qualified import CrosswalkTests
from export_adapter import boundary_records,selected_regions
from regions import assemble
import contracts

class ProducerConsumer(CrosswalkTests):
 def test_producer_trace_matches_independent_consumer(self):
  s=self.snapshot;s['serialization']='worldatlas-canonical-json-v1';s['seed_regions'][0]['witnesses']=[{'lon':0.0,'lat':0.2,'inside':True}]
  rev,entity,boundaries,sources=boundary_records(s);decisions,records=selected_regions(s,rev,boundaries)
  pins=self.seed['input_sha256'];proof=copy.deepcopy(self.seed['region_traces'][0]['input_trace'][1]['closure_proof'])
  def mock_closure(record,selected,*args):return copy.deepcopy(proof)
  _,report=assemble(rev,records,decisions[0],sources,mock_closure,physical_rows_sha256=pins['physical_rows'],physical_runs_sha256=pins['physical_runs'],physical_report_sha256=pins['physical_report'],checker_sha256=pins['closure_checker'],closure_contract_sha256=pins['closure_contract'],terminal_checker_sha256=pins['terminal_checker'],guard=lambda:None)
  self.seed['region_traces']=[report];self.assertTrue(contracts.validate_selected_seed_decisions(s,self.seed,self.groups,self.codes,self.metric))
  self.seed['region_traces'][0]['input_trace'][0]['source_citations'][0]['role']='supporting_research_evidence'
  with self.assertRaisesRegex(ValueError,'boundary citations mismatch'):contracts.validate_selected_seed_decisions(s,self.seed,self.groups,self.codes,self.metric)
 def test_reversed_terminal_trace_matches_independent_consumer(self):
  import hashlib,json
  s=self.snapshot;s['serialization']='worldatlas-canonical-json-v1';region=s['seed_regions'][0];route=s['routes'][0];pins=self.seed['input_sha256'];route['closure_method']='physical_terminal_closure_v1';route['provenance']['checker_sha256']=pins['terminal_checker'];route['start_terminal']={'boundary_id':'b','endpoint':'end'};route['end_terminal']={'boundary_id':'b','endpoint':'start'}
  region['segments']=[{'kind':'route','id':'q','start':0,'end':3,'reverse':True},{'kind':'boundary','id':'b','start':0,'end':2,'reverse':True}];coords=[[-1.,0.],[0.,1.],[1.,0.],[-1.,0.]];region['geometry_sha256']=hashlib.sha256(json.dumps({'type':'Polygon','coordinates':[coords]},sort_keys=True,separators=(',',':')).encode()).hexdigest();region['witnesses']=[{'lon':0.0,'lat':0.2,'inside':True}]
  rev,entity,boundaries,sources=boundary_records(s);decisions,records=selected_regions(s,rev,boundaries)
  def mock_closure(record,selected,refs):
   geometry={'type':'LineString','coordinates':[[float(x),float(y)] for x,y in selected]};gh=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
   return {'schema':'physical-terminal-closure-proof-v1','status':'valid','geometry_sha256':gh(geometry),'physical_rows_sha256':pins['physical_rows'],'physical_runs_sha256':pins['physical_runs'],'physical_report_sha256':pins['physical_report'],'contract_sha256':pins['closure_contract'],'checker_sha256':pins['terminal_checker'],'support_checker_sha256':pins['closure_checker'],'no_land_land_edge_touched':True,'start_geometry_sha256':refs[0]['geometry_sha256'],'end_geometry_sha256':refs[1]['geometry_sha256'],'start_endpoint':refs[0]['endpoint'],'end_endpoint':refs[1]['endpoint']}
  _,report=assemble(rev,records,decisions[0],sources,mock_closure,physical_rows_sha256=pins['physical_rows'],physical_runs_sha256=pins['physical_runs'],physical_report_sha256=pins['physical_report'],checker_sha256=pins['closure_checker'],closure_contract_sha256=pins['closure_contract'],terminal_checker_sha256=pins['terminal_checker'],guard=lambda:None)
  self.seed['region_traces']=[report];self.assertTrue(contracts.validate_selected_seed_decisions(s,self.seed,self.groups,self.codes,self.metric));self.assertEqual(report['input_trace'][0]['closure_proof']['start_endpoint'],'start')
