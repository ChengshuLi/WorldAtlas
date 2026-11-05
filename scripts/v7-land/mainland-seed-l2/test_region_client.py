import tempfile,pathlib,unittest,hashlib
from region_client import execute
from regions import geometry_hash
class RegionClient(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);d=pathlib.Path(self.t.name);self.code=d/'checker';self.code.mkdir();self.mask=d/'mask';self.mask.mkdir();self.work=d/'work';self.work.mkdir();checker=self.code/'checker.py';checker.write_text('''import sys,json,hashlib,pathlib
a=sys.argv;v=lambda flag:a[a.index(flag)+1]
p={'schema':'physical-water-closure-proof-v1','status':'valid','geometry_sha256':v('--geometry-sha256'),'physical_rows_sha256':'b'*64,'physical_runs_sha256':'c'*64,'physical_report_sha256':'9'*64,'checker_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'contract_sha256':v('--contract-sha256')}
pathlib.Path(v('--output')).write_text(json.dumps(p))
''');contract=self.code/'contract.json';contract.write_text('{}');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();line={'type':'LineString','coordinates':[['0','0'],['1','0'],['1','1']]};route={'type':'LineString','coordinates':[['1','1'],['0','1'],['0','0']]};h=lambda g:geometry_hash({'type':'LineString','coordinates':[[float(x),float(y)] for x,y in g['coordinates']]});method='binary64-sorted-compact-geojson-v1'
  records=[{'id':'east','kind':'boundary','revision_id':'r1','execution_status':'selected_for_research','geometry':line,'geometry_sha256':h(line),'geometry_hash_method':method,'source_refs':[{'source_id':'raw','version':'1'}],'qualified_source_refs':[{'source_id':'raw','version':'1','relationship':'construction_input','role':'construction_input'}],'lineage_status':'incomplete'},{'id':'closure','kind':'route','provenance':{'lineage_status':'incomplete','source_refs':[{'source_id':'raw','version':'1'}]},'lineage_status':'incomplete','role':'water_closure','closure_method':'physical_water_closure_v1','revision_id':'r1','execution_status':'selected_for_research','geometry':route,'geometry_sha256':h(route),'geometry_hash_method':method}]
  self.req={'schema':'stage2-region-worker-request-v1','memory_floor_kib':0,'revision_id':'r1','records':records,'sources':[{'kind':'raw','source_id':'raw','version':'1','sha256':'a'*64,'bucket':'raw','key':'x','origin':'provider original'}],'decision':{'region_id':'europe','revision_id':'r1','execution_status':'selected_for_research','geometry_hash_method':method,'segments':[{'kind':'boundary','id':'east','start':0,'end':3,'reverse':False},{'kind':'route','id':'closure','start':0,'end':3,'reverse':False}],'geometry_sha256':geometry_hash({'type':'Polygon','coordinates':[[[0.,0.],[1.,0.],[1.,1.],[0.,1.],[0.,0.]]]}),'witnesses':[{'lon':'0.5','lat':'0.5','inside':True}]},'closure':{'checker_path':str(checker),'checker_sha256':sha(checker),'physical_dir':str(self.mask),'physical_rows_sha256':'b'*64,'physical_runs_sha256':'c'*64,'physical_report_sha256':'9'*64,'contract_path':str(contract),'contract_sha256':sha(contract),'timeout_seconds':10}}
 def test_selected_l2_region_isolated(self):
  r=execute(self.req,self.work,lambda:None,10);self.assertEqual(r['status'],'selected-research-region');self.assertEqual(r['report']['region_id'],'europe');self.assertIn('regions.py',r['code_sha256'])
 def test_work_input_overlap_rejected(self):
  with self.assertRaisesRegex(ValueError,'overlaps inputs'):execute(self.req,self.mask,lambda:None,10)
 def test_nonraw_source_rejected(self):
  self.req['sources'][0]['kind']='derived'
  with self.assertRaisesRegex(ValueError,'non-raw source'):execute(self.req,self.work,lambda:None,10)
 def test_duplicate_geometry_rejected(self):
  self.req['records'].append(dict(self.req['records'][0]))
  with self.assertRaisesRegex(ValueError,'duplicate geometry'):execute(self.req,self.work,lambda:None,10)
if __name__=='__main__':unittest.main()
