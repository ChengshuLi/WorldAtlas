import tempfile,pathlib,unittest,hashlib,json,struct
from unittest.mock import patch
import seed_producer
from regions import geometry_hash
from seed_producer import run
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return {'path':str(p),'sha256':sha(p)}
def pair(d,name,rows,kind):
 off=[0];v=[]
 for row in rows:v.extend(row);off.append(len(v))
 rp=d/(name+'-rows');sp=d/(name+'-runs');rp.write_bytes(b''.join(struct.pack('<I',x) for x in off));fmt='<III' if kind=='component' else '<II';sp.write_bytes(b''.join(struct.pack(fmt,*x) for x in v));return pin(rp),pin(sp)
class Producer(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.d=pathlib.Path(self.t.name);self.src=self.d/'inputs';self.src.mkdir();self.mask=self.src/'mask';self.mask.mkdir();self.work=self.d/'work';self.output=self.d/'output';self.grid={'width':8,'height':4,'west':-180,'north':90,'step':45}
  # One two-cell split component and four one-cell components.
  cr=[[],[(1,3,10)],[(0,1,20),(2,3,30),(4,5,40),(6,7,50)],[]];pr=[[(8,1)],[(1,1),(3,17),(8,1)],[(1,17),(2,1),(3,17),(4,1),(5,17),(6,1),(7,17),(8,1)],[(8,1)]]
  self.crows,self.cruns=pair(self.src,'component',cr,'component');prows,pruns=pair(self.mask,'physical',pr,'pair');(self.mask/'rows.u32le').write_bytes(pathlib.Path(prows['path']).read_bytes());(self.mask/'runs.u32le').write_bytes(pathlib.Path(pruns['path']).read_bytes());self.prows=pin(self.mask/'rows.u32le');self.pruns=pin(self.mask/'runs.u32le')
  preport=self.mask/'report.json';preport.write_text(json.dumps({'status':'candidate-only','grid':self.grid,'output_sha256':{'rows.u32le':self.prows['sha256'],'runs.u32le':self.pruns['sha256']}}));manifest=self.src/'manifest';manifest.write_text('component generation fixture')
  code=self.src/'code';code.mkdir();checker=code/'checker.py';checker.write_text('''import sys,json,hashlib,pathlib
a=sys.argv;v=lambda flag:a[a.index(flag)+1]
p={'schema':'physical-water-closure-proof-v1','status':'valid','geometry_sha256':v('--geometry-sha256'),'physical_rows_sha256':%r,'physical_runs_sha256':%r,'checker_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'contract_sha256':v('--contract-sha256')};pathlib.Path(v('--output')).write_text(json.dumps(p))
'''%(self.prows['sha256'],self.pruns['sha256']));contract=code/'contract.json';contract.write_text(json.dumps({'schema':'physical-water-closure-contract-v1','grid':{'crs':'EPSG:4326',**{k:self.grid[k] for k in ('width','height','west','north')},'step_numerator':45,'step_denominator':1},'physical':{'rows_sha256':self.prows['sha256'],'runs_sha256':self.pruns['sha256'],'report_sha256':sha(preport),'water_code':1,'land_code':17}}));method='binary64-sorted-compact-geojson-v1'
  line={'type':'LineString','coordinates':[['-135','0'],['-90','0'],['-90','45']]};route={'type':'LineString','coordinates':[['-90','45'],['-135','45'],['-135','0']]};h=lambda g:geometry_hash({'type':'LineString','coordinates':[[float(x),float(y)] for x,y in g['coordinates']]});source={'source_id':'raw','version':'1','sha256':'a'*64,'r2_bucket':'worldatlas','r2_key':'sources/raw','size_bytes':100};lineage={**source,'kind':'raw','provider':'provider','source_uri':'https://example.org/raw','provenance':{'origin':'provider original','representation':'provider_original'}}
  bounds=[{'boundary_id':'b','decision_revision':'r','execution_status':'selected_for_research','method':'stored_linestring_v1','coordinate_reference':'OGC:CRS84','geometry_hash_method':method,'geometry_sha256':h(line),'geometry':line,'provenance':{'source_refs':[{'source_id':'raw','version':'1'}],'lineage_status':'incomplete'}}]
  routes=[{'route_id':'c','decision_revision':'r','execution_status':'selected_for_research','route_type':'stored_linestring_v1','role':'water_closure','closure_method':'physical_water_closure_v1','coordinate_reference':'OGC:CRS84','geometry_hash_method':method,'geometry_sha256':h(route),'geometry':route}];poly={'type':'Polygon','coordinates':[[[-135.,0.],[-90.,0.],[-90.,45.],[-135.,45.],[-135.,0.]]]};regions=[{'region_id':'region','decision_revision':'r','execution_status':'selected_for_research','geometry_hash_method':method,'geometry_sha256':geometry_hash(poly),'segments':[{'kind':'boundary','id':'b','start':0,'end':3,'reverse':False},{'kind':'route','id':'c','start':0,'end':3,'reverse':False}],'witnesses':[{'lon':'-112.5','lat':'22.5','inside':True}]}]
  groups=[];rules=[]
  for i,(root,inside,outside,region) in enumerate([(10,1,2,'region'),(20,3,3,None),(30,4,4,None),(40,5,5,None),(50,6,6,None)]):
   gid='g'+str(i);rid='rule'+str(i);groups.append({'group_id':gid,'role':'mainland','target_entity_ids':sorted({inside,outside}),'component_id_current_generation_only':root});rules.append({'rule_id':rid,'decision_revision':'r','execution_status':'selected_for_research','group_id':gid,'region_id':region,'inside_entity_id':inside,'outside_entity_id':outside})
  snap={'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export','serialization':'worldatlas-canonical-json-v1','decision_revision':{'id':'r','status':'draft','entity_revision':'e'},'entity_revision':{'id':'e','status':'draft'},'sources':[source],'source_lineage_assets':[lineage],'source_lineage_dependencies':[],'mainland_boundaries':bounds,'routes':routes,'seed_regions':regions,'entities':[{'id':i,'level':'continent'} for i in range(1,7)],'category_bindings':[{'entity_id':i,'code':i+16,'physical_class':'land'} for i in range(1,7)],'mainland_component_rules':rules,'land_baseline_policy':{'decision_revision':'r','execution_status':'selected_for_research','island_overrides':'none','mainland_rule_ids':[r['rule_id'] for r in rules],'region_ids':['region'],'boundary_ids':['b'],'route_ids':['c']}}
  snapfile=self.src/'snapshot.json';snapfile.write_text(json.dumps(snap));resolution={'schema':'mainland-witness-resolution-v1','status':'selected-research-identity-claims-not-mainland-proof','snapshot_sha256':sha(snapfile),'decision_revision':'r','entity_revision':'e','component_manifest_sha256':sha(manifest),'grid':self.grid,'input_sha256':{'physical_rows':self.prows['sha256'],'physical_runs':self.pruns['sha256'],'component_rows':self.crows['sha256'],'component_runs':self.cruns['sha256']},'groups':groups};resfile=self.src/'resolution.json';resfile.write_text(json.dumps(resolution));portable=HERE/'rasterizer'
  inputs={'snapshot':pin(snapfile),'resolution':pin(resfile),'physical_rows':self.prows,'physical_runs':self.pruns,'physical_report':pin(preport),'component_rows':self.crows,'component_runs':self.cruns,'component_manifest':pin(manifest),'closure_checker':pin(checker),'closure_contract':pin(contract),'seed_builder':pin(portable/'build_seed.py'),'seed_kernel':pin(portable/'seed_kernel.cpp')};self.req={'schema':'worldatlas-stage2-seed-request-v1','grid':self.grid,'inputs':inputs,'controls':{'memory_floor_kib':0,'disk_reserve_bytes':0,'timeout_seconds':60,'strip_rows':2,'max_group_rss_kib':524288}};self.path=self.src/'request.json';self.path.write_text(json.dumps(self.req))
 def test_runs_from_selected_structured_inputs(self):
  with patch.dict(seed_producer.TRUSTED_CODE,{'closure_checker':self.req['inputs']['closure_checker']['sha256']}):r=run(self.path,self.work,self.output,lambda:None)
  self.assertEqual(r['schema'],'worldatlas-stage2-mainland-seed-report-v1');self.assertEqual(r['status'],'diagnostic-seed-pending-independent-provenance');self.assertEqual(r['seed_roots'],[10,20,30,40,50]);self.assertEqual(len(r['region_traces']),1);self.assertEqual(r['seed_rows_sha256'],sha(self.output/'rows.u32le'));self.assertTrue((self.output/'rasterizer-report.json').exists());self.assertEqual(r['physical_code_contract'],{'water':1,'land':17})
  rows=list(struct.iter_unpack('<I',(self.output/'rows.u32le').read_bytes()));runs=list(struct.iter_unpack('<II',(self.output/'runs.u32le').read_bytes()))
  def cell(y,x):
   row=runs[rows[y][0]:rows[y+1][0]];return next(code for end,code in row if x<end)
  self.assertEqual([cell(1,1),cell(1,2),cell(2,0),cell(2,2),cell(2,4),cell(2,6)],[17,18,19,20,21,22]);self.assertEqual(cell(0,0),0)
 def test_empty_partition_rejected(self):
  p=pathlib.Path(self.req['inputs']['snapshot']['path']);s=json.loads(p.read_text());line={'type':'LineString','coordinates':[['-135','0'],['-45','0'],['-45','45']]};route={'type':'LineString','coordinates':[['-45','45'],['-135','45'],['-135','0']]};h=lambda g:geometry_hash({'type':'LineString','coordinates':[[float(x),float(y)] for x,y in g['coordinates']]});s['mainland_boundaries'][0]['geometry']=line;s['mainland_boundaries'][0]['geometry_sha256']=h(line);s['routes'][0]['geometry']=route;s['routes'][0]['geometry_sha256']=h(route);s['seed_regions'][0]['geometry_sha256']=geometry_hash({'type':'Polygon','coordinates':[[[-135.,0.],[-45.,0.],[-45.,45.],[-135.,45.],[-135.,0.]]]});p.write_text(json.dumps(s));self.req['inputs']['snapshot']=pin(p);rp=pathlib.Path(self.req['inputs']['resolution']['path']);r=json.loads(rp.read_text());r['snapshot_sha256']=sha(p);rp.write_text(json.dumps(r));self.req['inputs']['resolution']=pin(rp);self.path.write_text(json.dumps(self.req))
  with patch.dict(seed_producer.TRUSTED_CODE,{'closure_checker':self.req['inputs']['closure_checker']['sha256']}):
   with self.assertRaisesRegex(ValueError,'missing mainland category population|empty mainland rule partition'):run(self.path,self.work,self.output,lambda:None)
  self.assertFalse(self.output.exists())
 def test_unreviewed_terminal_checker_rejected(self):
  self.req['inputs']['terminal_checker']=self.req['inputs']['closure_checker'];self.path.write_text(json.dumps(self.req))
  with patch.dict(seed_producer.TRUSTED_CODE,{'closure_checker':self.req['inputs']['closure_checker']['sha256']}):
   with self.assertRaisesRegex(ValueError,'unreviewed terminal checker'):run(self.path,self.work,self.output,lambda:None)
 def test_unreviewed_checker_rejected(self):
  with self.assertRaisesRegex(ValueError,'unreviewed executable'):run(self.path,self.work,self.output,lambda:None)
 def test_resolution_grid_mismatch_fails(self):
  p=pathlib.Path(self.req['inputs']['resolution']['path']);r=json.loads(p.read_text());r['grid']['width']=9;p.write_text(json.dumps(r));self.req['inputs']['resolution']=pin(p);self.path.write_text(json.dumps(self.req))
  with patch.dict(seed_producer.TRUSTED_CODE,{'closure_checker':self.req['inputs']['closure_checker']['sha256']}):
   with self.assertRaisesRegex(ValueError,'resolution input mismatch'):run(self.path,self.work,self.output,lambda:None)
  self.assertFalse(self.output.exists())
 def test_resolution_input_pin_mismatch_fails(self):
  p=pathlib.Path(self.req['inputs']['resolution']['path']);r=json.loads(p.read_text());r['input_sha256']['physical_rows']='0'*64;p.write_text(json.dumps(r));self.req['inputs']['resolution']=pin(p);self.path.write_text(json.dumps(self.req))
  with patch.dict(seed_producer.TRUSTED_CODE,{'closure_checker':self.req['inputs']['closure_checker']['sha256']}):
   with self.assertRaisesRegex(ValueError,'resolution input mismatch'):run(self.path,self.work,self.output,lambda:None)
  self.assertFalse(self.output.exists())
 def test_rejects_prior_or_unselected_snapshot(self):
  p=pathlib.Path(self.req['inputs']['snapshot']['path']);s=json.loads(p.read_text());s['source']='local-preview-not-neon';p.write_text(json.dumps(s));self.req['inputs']['snapshot']=pin(p);self.path.write_text(json.dumps(self.req))
  with patch.dict(seed_producer.TRUSTED_CODE,{'closure_checker':self.req['inputs']['closure_checker']['sha256']}):
   with self.assertRaisesRegex(ValueError,'selected Neon'):run(self.path,self.work,self.output,lambda:None)
  self.assertFalse(self.output.exists())
if __name__=='__main__':unittest.main()
