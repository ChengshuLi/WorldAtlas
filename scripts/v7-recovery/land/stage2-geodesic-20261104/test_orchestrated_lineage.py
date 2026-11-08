import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import verify_physical_lineage as v


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,obj):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,sort_keys=True)+'\n');return {'path':str(path),'sha256':sha(path)}
def blob(path,data=b'x'):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);return {'path':str(path),'sha256':sha(path)}


class OrchestratedLineageTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.r=Path(self.tmp.name)
  self.grid={'width':8,'height':4,'west':-180,'north':90,'step':45};self.rev='r';self.snapshot={'decision_revision':{'id':self.rev},'sources':[],'source_lineage_assets':[],'source_lineage_dependencies':[],'stage1_source_inputs':[]}
  self.code_root=self.r/'code';names=['build_physical.py','build.py','rasterize_land.py','overture/rasterize_water_shard.py','overture/aggregate_compare.py','compose_physical.py'];code={n:blob(self.code_root/n,n.encode())['sha256'] for n in names}
  self.osmsha=hashlib.sha256(b'archive').hexdigest();landsrc={'source_id':'osm','version':'v','sha256':self.osmsha,'r2_bucket':'b','r2_key':'osm.zip','size_bytes':7};self.snapshot['sources'].append(landsrc);self.snapshot['source_lineage_assets'].append({**landsrc,'kind':'raw','source_uri':'https://example.test/osm','provenance':{}})
  self.snapshot['stage1_source_inputs'].append({'decision_revision':'r','role':'physical_land','ordinal':0,'source_id':'osm','source_version':'v','execution_status':'selected_for_research'})
  live=[{'revision':'r','role':'physical_land','ordinal':0,'execution_status':'selected_for_research',**landsrc}];member=[];pins=[]
  for name in ('land.shp','land.shx','land.dbf','land.prj','land.cpg'):
   p=blob(self.r/'input'/name,name.encode());pins.append(p);member.append({'member':'archive/'+name,'match':True,'archive_sha256':p['sha256'],'local_sha256':p['sha256'],'config_sha256':p['sha256']})
  landcfg={'grid':self.grid,'land':[{'files':pins}]};lc=write(self.r/'input'/'land.json',landcfg)
  watercfg={'grid':self.grid,'policy':{'method':'x'},'batch_size':8};wc=write(self.r/'input'/'water.json',watercfg)
  osm={'status':'matched','r2_bucket':'b','r2_key':'osm.zip','r2_stream':{'sha256':self.osmsha,'bytes':7},'local_archive':{'sha256':self.osmsha,'bytes':7},'members':member}
  osm_pin=write(self.r/'osm.json',osm);old=[];res=[];files=[];shards=[];part18=None
  for i in range(32):
   sid=f'water-{i:02d}';source_sha=hashlib.sha256(sid.encode()).hexdigest();name=f'part-{i:05d}-x.zstd.parquet';key='water/'+name;size=10+i
   src={'source_id':sid,'version':'v','sha256':source_sha,'r2_bucket':'b','r2_key':key,'size_bytes':size};self.snapshot['sources'].append(src);self.snapshot['source_lineage_assets'].append({**src,'kind':'raw','source_uri':'https://example.test/water','provenance':{}})
   self.snapshot['stage1_source_inputs'].append({'decision_revision':'r','role':'inland_water','ordinal':i,'source_id':sid,'source_version':'v','execution_status':'selected_for_research'});live.append({'revision':'r','role':'inland_water','ordinal':i,'execution_status':'selected_for_research',**src})
   files.append({'path':'raw/'+name,'source_id':sid,'sha256':source_sha,'size':size,'r2_bucket':'b','r2_key':key})
   od=self.r/'output'/'shards'/f'{i:05d}';tif=blob(od/'water.tif',sid.encode());report={'status':'candidate-only','source':'/raw/'+name,'source_sha256':source_sha,'configuration_sha256':wc['sha256'],'script_sha256':code['overture/rasterize_water_shard.py'],'grid':self.grid,'policy':watercfg['policy'],'batch_size':8,'output_sha256':tif['sha256']};rp=write(od/'report.json',report);shards.append({**tif,'status':'candidate-only','report':rp})
   if i<18:
    old.append({'event':'shard_complete','source_id':sid,'source':'/raw/'+name,'sha256':source_sha,'size':size,'output_sha256':tif['sha256']});res.append({'event':'reused_shard_checkpoint','source_id':sid,'source_sha256':source_sha,'output_sha256':tif['sha256'],'report_sha256':rp['sha256']})
   else:
    res.append({'source_id':sid,'sha256':source_sha,'size':size,'downloaded':i!=18})
    if i==18:part18={'source_id':sid,'source_sha256':source_sha,'bytes':size,'r2_key':key,'r2_bucket':'b','shard_report_sha256':rp['sha256'],'output_sha256':tif['sha256'],'r2_readback':'verified in this run'}
  man=write(self.r/'input'/'manifest.json',{'source':'Overture Maps Foundation','theme':'base','type':'water','file_count':32,'total_bytes':sum(x['size'] for x in files),'files':files})
  pipeline={'land_config':lc,'water_config':wc,'source_manifest':man};pc=write(self.r/'output'/'pipeline-config.json',pipeline)
  ld=self.r/'output'/'land';lp=blob(ld/'land.tif',b'land');(ld/'config.json').write_bytes(Path(lc['path']).read_bytes());lr=write(ld/'report.json',{'status':'candidate-only','grid':self.grid,'configuration_sha256':lc['sha256'],'land_sha256':lp['sha256']})
  ud=self.r/'output'/'union';uw=blob(ud/'water-union.tif',b'union');uc=write(ud/'config.json',{'source_manifest':man,'shard_count':32,'shards':shards});ur=write(ud/'report.json',{'status':'candidate-only','grid':self.grid,'configuration_sha256':uc['sha256'],'source_manifest':man,'shard_count':32,'shards':shards,'union_sha256':uw['sha256']})
  pd=self.r/'output'/'physical';out={n:blob(pd/n,n.encode())['sha256'] for n in ('physical-dry.tif','rows.u32le','runs.u32le')};fc=write(pd/'config.json',{'land':lp,'water':uw});pr=write(pd/'report.json',{'status':'candidate-only','grid':self.grid,'configuration_sha256':fc['sha256'],'inputs':{'land':lp,'water':uw},'output_sha256':out});self.pr=pr;self.out=out
  pipeline_report={'status':'candidate-only','grid':self.grid,'shard_count':32,'script_sha256':code,'configuration_sha256':pc['sha256'],'land_config':lc,'water_config':wc,'source_manifest':man,'water_batch_size':8,'stage_reports':{'land':lr,'union':ur,'physical':pr},'physical_output_sha256':out};pp=write(self.r/'output'/'report.json',pipeline_report)
  neo=write(self.r/'neon.json',{'schema':'worldatlas-neon-stage1-selection-readback-v1','revision':'r','rows':live});part=write(self.r/'part18.json',part18)
  def jsonl(path,rows):path.write_text(''.join(json.dumps(x)+'\n' for x in rows));return {'path':str(path),'sha256':sha(path)}
  self.inputs={'pipeline_report':pp,'osm_receipt':osm_pin,'neon_selection':neo,'initial_events':jsonl(self.r/'old.jsonl',old),'resume_events':jsonl(self.r/'resume.jsonl',res),'part18_receipt':part};self.req={'schema':'stage1-orchestrated-lineage-request-v1','inputs':self.inputs,'code_root':str(self.code_root)};self.reqpath=self.r/'request.json';write(self.reqpath,self.req)
 def check(self):return v.validate_combined(self.snapshot,'a'*64,str(self.reqpath),self.pr['sha256'],self.out['rows.u32le'],self.out['runs.u32le'],self.grid)
 def use_raw_physical_contract(self):
  self.req={'schema':'stage1-raw-physical-lineage-request-v1','inputs':{k:self.inputs[k] for k in ('pipeline_report','osm_receipt','neon_selection')},'code_root':str(self.code_root)};write(self.reqpath,self.req)
 def use_native_kernel(self,wrong_source=False,method='hybrid'):
  self.use_raw_physical_contract();pp=self.r/'output'/'report.json';pipe=json.loads(pp.read_text())
  for name in ('overture/water_native.py','overture/water_native.cpp'):
   pipe['script_sha256'][name]=blob(self.code_root/name,name.encode())['sha256']
  ucp=self.r/'output'/'union'/'config.json';uc=json.loads(ucp.read_text())
  for i,shard in enumerate(uc['shards']):
   path=Path(shard['report']['path']);report=json.loads(path.read_text());binary=blob(path.parent/'water-native.so',b'native')
   report.update({'rasterizer':'native','native_kernel':{'method':method,'source_sha256':pipe['script_sha256']['overture/water_native.cpp'],
     'binding_sha256':pipe['script_sha256']['overture/water_native.py'],'binary_sha256':binary['sha256']}})
   if wrong_source and i==5:report['native_kernel']['source_sha256']='0'*64
   shard['report']=write(path,report)
  ucpin=write(ucp,uc);urp=self.r/'output'/'union'/'report.json';union=json.loads(urp.read_text())
  union.update({'configuration_sha256':ucpin['sha256'],'shards':uc['shards']});pipe['stage_reports']['union']=write(urp,union)
  self.req['inputs']['pipeline_report']=write(pp,pipe);write(self.reqpath,self.req)
 def use_gdal_kernel(self,implementation='python-gdal-api-v2',wrong_binding=False):
  self.use_raw_physical_contract();pp=self.r/'output'/'report.json';pipe=json.loads(pp.read_text())
  name='overture/water_batch.py';pipe['script_sha256'][name]=blob(self.code_root/name,name.encode())['sha256']
  ucp=self.r/'output'/'union'/'config.json';uc=json.loads(ucp.read_text())
  for i,shard in enumerate(uc['shards']):
   path=Path(shard['report']['path']);report=json.loads(path.read_text())
   report.update({'rasterizer':'gdal','gdal_kernel':{'implementation':implementation,'method':'hybrid','binding_sha256':pipe['script_sha256'][name]}})
   if wrong_binding and i==5:report['gdal_kernel']['binding_sha256']='0'*64
   shard['report']=write(path,report)
  ucpin=write(ucp,uc);urp=self.r/'output'/'union'/'report.json';union=json.loads(urp.read_text())
  union.update({'configuration_sha256':ucpin['sha256'],'shards':uc['shards']});pipe['stage_reports']['union']=write(urp,union)
  self.req['inputs']['pipeline_report']=write(pp,pipe);write(self.reqpath,self.req)
 def test_python_api_kernel_report_chain(self):
  self.use_gdal_kernel();self.assertEqual(self.check()['method'],'raw-physical-report-chain-v1')
 def test_historical_gdal_kernel_report_chain_is_readable(self):
  self.use_gdal_kernel(implementation='python-gdal-c-api-v1');self.assertEqual(self.check()['method'],'raw-physical-report-chain-v1')
 def test_python_api_kernel_wrong_binding_rejected(self):
  self.use_gdal_kernel(wrong_binding=True)
  with self.assertRaisesRegex(ValueError,'GDAL water kernel mismatch'):self.check()
 def test_unknown_gdal_kernel_implementation_rejected(self):
  self.use_gdal_kernel(implementation='unknown')
  with self.assertRaisesRegex(ValueError,'GDAL water kernel mismatch'):self.check()
 def test_native_kernel_report_chain_and_binary_tamper(self):
  self.use_native_kernel();self.assertEqual(self.check()['method'],'raw-physical-report-chain-v1')
  (self.r/'output'/'shards'/'00005'/'water-native.so').write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'native water kernel mismatch'):self.check()
 def test_native_kernel_rehashed_wrong_source_rejected(self):
  self.use_native_kernel(wrong_source=True)
  with self.assertRaisesRegex(ValueError,'native water kernel mismatch'):self.check()
 def test_native_kernel_method_must_match_pinned_water_config(self):
  self.use_native_kernel(method='vector')
  with self.assertRaisesRegex(ValueError,'native water kernel mismatch'):self.check()
 def test_raw_physical_valid_without_historical_checkpoint_events(self):
  self.use_raw_physical_contract();result=self.check()
  self.assertEqual(result['method'],'raw-physical-report-chain-v1');self.assertEqual(len(result['shard_report_sha256']),32)
  self.assertFalse(any('18 shards' in x for x in result['limitations']))
 def test_raw_physical_rejects_changed_shard(self):
  self.use_raw_physical_contract();(self.r/'output'/'shards'/'00005'/'water.tif').write_bytes(b'changed')
  with self.assertRaises(ValueError):self.check()
 def test_raw_physical_rejects_changed_code(self):
  self.use_raw_physical_contract();(self.code_root/'build.py').write_bytes(b'changed')
  with self.assertRaises(ValueError):self.check()
 def test_raw_physical_rejects_changed_selection(self):
  self.use_raw_physical_contract();self.snapshot['stage1_source_inputs'][3]['source_id']='other'
  with self.assertRaises(ValueError):self.check()
 def test_raw_physical_rejects_changed_source_evidence(self):
  self.use_raw_physical_contract();p=Path(self.req['inputs']['neon_selection']['path']);doc=json.loads(p.read_text());doc['rows'][5]['sha256']='0'*64
  self.req['inputs']['neon_selection']=write(p,doc);write(self.reqpath,self.req)
  with self.assertRaises(ValueError):self.check()
 def test_raw_physical_rejects_rehashed_wrong_filter_policy(self):
  self.use_raw_physical_contract();srpath=self.r/'output'/'shards'/'00005'/'report.json';sr=json.loads(srpath.read_text());sr['policy']={'method':'wrong'};srpin=write(srpath,sr)
  ucp=self.r/'output'/'union'/'config.json';uc=json.loads(ucp.read_text());uc['shards'][5]['report']=srpin;ucpin=write(ucp,uc)
  urp=self.r/'output'/'union'/'report.json';ur=json.loads(urp.read_text());ur['configuration_sha256']=ucpin['sha256'];ur['shards']=uc['shards'];urpin=write(urp,ur)
  pp=self.r/'output'/'report.json';report=json.loads(pp.read_text());report['stage_reports']['union']=urpin;self.req['inputs']['pipeline_report']=write(pp,report);write(self.reqpath,self.req)
  with self.assertRaisesRegex(ValueError,'shard report/output mismatch'):self.check()
 def test_raw_physical_rejects_unexpected_input(self):
  self.use_raw_physical_contract();self.req['inputs']['initial_events']=self.inputs['initial_events'];write(self.reqpath,self.req)
  with self.assertRaisesRegex(ValueError,'invalid orchestrated input set'):self.check()
 def test_valid(self):self.assertEqual(self.check()['method'],'orchestrated-report-chain-v1')
 def test_shard_tamper_rejected(self):
  (self.r/'output'/'shards'/'00005'/'water.tif').write_bytes(b'changed')
  with self.assertRaises(ValueError):self.check()
 def test_code_tamper_rejected(self):
  (self.code_root/'build.py').write_bytes(b'changed')
  with self.assertRaises(ValueError):self.check()
 def test_derived_selected_source_rejected(self):
  self.snapshot['source_lineage_assets'][3]['kind']='derived'
  with self.assertRaises(ValueError):self.check()
 def test_source_dependency_child_rejected(self):
  a=self.snapshot['source_lineage_assets'][3];self.snapshot['source_lineage_dependencies'].append({'source_id':a['source_id'],'version':a['version']})
  with self.assertRaises(ValueError):self.check()
 def test_snapshot_selection_tamper_rejected(self):
  self.snapshot['stage1_source_inputs'][3]['source_id']='other'
  with self.assertRaises(ValueError):self.check()
 def test_duplicate_completion_event_rejected(self):
  p=Path(self.inputs['initial_events']['path']);rows=p.read_text();p.write_text(rows+rows.splitlines()[0]+'\n');self.req['inputs']['initial_events']['sha256']=sha(p);write(self.reqpath,self.req)
  with self.assertRaises(ValueError):self.check()
 def test_part18_receipt_tamper_rejected(self):
  p=Path(self.inputs['part18_receipt']['path']);d=json.loads(p.read_text());d['r2_readback']='unknown';self.req['inputs']['part18_receipt']=write(p,d);write(self.reqpath,self.req)
  with self.assertRaises(ValueError):self.check()
 def test_expected_output_pin_tamper_rejected(self):
  with self.assertRaises(ValueError):v.validate_combined(self.snapshot,'a'*64,str(self.reqpath),self.pr['sha256'],'0'*64,self.out['runs.u32le'],self.grid)

if __name__=='__main__':unittest.main()
