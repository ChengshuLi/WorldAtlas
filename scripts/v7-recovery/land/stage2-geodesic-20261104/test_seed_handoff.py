import copy,hashlib,json,tempfile,unittest
from pathlib import Path
import orchestrate_stage2 as o
class SeedHandoffTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.d=Path(self.t.name);self.grid={'width':8,'height':4,'west':-180,'north':90,'step':45};self.inputs={}
  for k in o.BASE_INPUTS:self.inputs[k]=self.write(k,{'k':k})
  self.inputs['closure_contract']=self.write('closure_contract',{'resources':{'memory_floor_kib':1887437}})
  self.code={'seed-producer/'+n:format(i+1,'064x') for i,n in enumerate(o.SEED_NAMES)};self.code['seed-producer/seed_worker.py']='a'*64
  seedcode={n:self.code['seed-producer/'+n] for n in o.SEED_NAMES};seedcode.update({'rasterizer':self.inputs['seed_builder']['sha256'],'rasterizer_kernel':self.inputs['seed_kernel']['sha256']})
  def code(name):return self.write(name,{'code':name})
  self.h={k:code(k) for k in ('seed_watchdog_code','seed_guardian_code','witness_watchdog_code','witness_guardian_code','component_watchdog_code','component_guardian_code','component_driver_code','witness_driver_code')}
  self.h['component_config']=self.write('component_config',{'controls':{'minimum_memory_kib':1730151}});self.h['witness_config']=self.write('witness_config',{'controls':{'minimum_memory_kib':1730151}})
  cr={'schema':'fresh-physical-components-report-v1','status':'research-awaiting-monitor','publishable':False,'manifest_sha256':self.inputs['component_manifest']['sha256'],'component_rows_sha256':self.inputs['component_rows']['sha256'],'component_runs_sha256':self.inputs['component_runs']['sha256'],'input_sha256':{k:self.inputs[k]['sha256'] for k in ('physical_rows','physical_runs','physical_report','component_source')},'driver_sha256':self.h['component_driver_code']['sha256'],'config_sha256':self.h['component_config']['sha256']};self.h['component_report']=self.write('component_report',cr)
  def monitor(schema,report,driver,config,watchdog,guardian):return {'schema':schema,'status':'sampled-complete','report_sha256':report['sha256'],'driver_sha256':driver['sha256'],'config_sha256':config['sha256'],'watchdog_sha256':watchdog['sha256'],'guardian_sha256':guardian['sha256'],'samples':2,'minimum_memory_kib':1730151,'minimum_available_kib':2000000,'peak_process_group_rss_kib':100000,'maximum_process_group_rss_kib':400000,'sample_interval_seconds':.05}
  cm=monitor('fresh-physical-components-watchdog-v1',self.h['component_report'],self.h['component_driver_code'],self.h['component_config'],self.h['component_watchdog_code'],self.h['component_guardian_code']);self.h['component_monitor']=self.write('component_monitor',cm)
  resolution=self.write('resolution',{'schema':'resolution'});wr={'schema':'fresh-mainland-witness-report-v1','status':'research-awaiting-monitor','publishable':False,'resolution_sha256':resolution['sha256'],'request_sha256':self.inputs['resolution_request']['sha256'],'component_report_sha256':self.h['component_report']['sha256'],'component_monitor_sha256':self.h['component_monitor']['sha256'],'driver_sha256':self.h['witness_driver_code']['sha256'],'config_sha256':self.h['witness_config']['sha256']};self.h['witness_report']=self.write('witness_report',wr)
  wm=monitor('fresh-mainland-witness-watchdog-v1',self.h['witness_report'],self.h['witness_driver_code'],self.h['witness_config'],self.h['witness_watchdog_code'],self.h['witness_guardian_code']);self.h['witness_monitor']=self.write('witness_monitor',wm)
  mappings=(('snapshot','decision_snapshot'),('physical_rows','physical_rows'),('physical_runs','physical_runs'),('physical_report','physical_report'),('component_rows','component_rows'),('component_runs','component_runs'),('component_manifest','component_manifest'),('closure_checker','closure_checker'),('terminal_checker','terminal_checker'),('closure_contract','closure_contract'),('seed_builder','seed_builder'),('seed_kernel','seed_kernel'));qi={a:self.inputs[b] for a,b in mappings};qi['resolution']=resolution
  sc={'timeout_seconds':1800,'strip_rows':8,'max_group_rss_kib':786432};q={'schema':'worldatlas-stage2-seed-request-v1','grid':self.grid,'inputs':qi,'controls':{'memory_floor_kib':1730151,'disk_reserve_bytes':2147483648,**sc}};qp=self.write('seed_request',q);rows=self.write('rows',{'r':1});runs=self.write('runs',{'s':1});report={'schema':'worldatlas-stage2-mainland-seed-report-v1','status':'diagnostic-seed-pending-independent-provenance','publishable':False,'request_sha256':qp['sha256'],'input_sha256':{k:v['sha256'] for k,v in qi.items()},'seed_rows_sha256':rows['sha256'],'seed_runs_sha256':runs['sha256'],'code_sha256':seedcode};rp=self.write('seed_report',report)
  mon={'schema':'sampled-process-group-watchdog-v1','status':'complete','watchdog_sha256':self.h['seed_watchdog_code']['sha256'],'guardian_sha256':self.h['seed_guardian_code']['sha256'],'memory_floor_kib':1730151,'disk_floor_bytes':2147483648,'group_rss_limit_kib':786432,'samples':5,'minimum_available_kib':2000000,'peak_group_rss_kib':100000,'sample_interval_seconds':.05};mp=self.write('seed_monitor',mon)
  self.att={'schema':'stage2-seed-readback-attestation-v1','status':'sampled-complete','request':qp,'monitor':mp,'report':rp,'seed_rows':rows,'seed_runs':runs,'seed_worker_sha256':self.code['seed-producer/seed_worker.py'],'producer_code_sha256':seedcode,'snapshot_sha256':self.inputs['decision_snapshot']['sha256'],'resolution_sha256':resolution['sha256'],'component_manifest_sha256':self.inputs['component_manifest']['sha256']};self.h['attestation']=self.write('attestation',self.att);self.cfg={'grid':self.grid,'inputs':self.inputs,'seed_controls':sc,'seed_handoff':self.h}
 def write(self,name,obj):
  p=self.d/name;p.write_text(json.dumps(obj,sort_keys=True));return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 def check(self):return o.validate_seed_handoff(self.cfg,self.code,lambda:None)
 def test_valid(self):self.assertEqual(self.check()[0]['status'],'sampled-complete')
 def test_seed_monitor_below_closure_floor(self):
  mon=json.loads((self.d/'seed_monitor').read_text());mon['minimum_available_kib']=1887436;self.att['monitor']=self.write('seed_monitor',mon);self.h['attestation']=self.write('attestation',self.att)
  with self.assertRaisesRegex(ValueError,'below selected closure floor'):self.check()
 def test_witness_driver_and_config_forgery(self):
  for field in ('driver_sha256','config_sha256'):
   original=json.loads((self.d/'witness_monitor').read_text());bad={**original,field:'0'*64};self.h['witness_monitor']=self.write('witness_monitor',bad)
   with self.assertRaisesRegex(ValueError,'witness monitor mismatch'):self.check()
   self.h['witness_monitor']=self.write('witness_monitor',original)
 def test_component_resource_failure(self):
  for field,value in (('minimum_available_kib',1),('peak_process_group_rss_kib',400001),('sample_interval_seconds',.2)):
   original=json.loads((self.d/'component_monitor').read_text());bad={**original,field:value};self.h['component_monitor']=self.write('component_monitor',bad)
   # Update witness's reference so the component monitor itself is examined.
   wr=json.loads((self.d/'witness_report').read_text());wr['component_monitor_sha256']=self.h['component_monitor']['sha256'];self.h['witness_report']=self.write('witness_report',wr);wm=json.loads((self.d/'witness_monitor').read_text());wm['report_sha256']=self.h['witness_report']['sha256'];self.h['witness_monitor']=self.write('witness_monitor',wm)
   with self.assertRaisesRegex(ValueError,'component monitor mismatch'):self.check()
   self.h['component_monitor']=self.write('component_monitor',original);wr['component_monitor_sha256']=self.h['component_monitor']['sha256'];self.h['witness_report']=self.write('witness_report',wr);wm['report_sha256']=self.h['witness_report']['sha256'];self.h['witness_monitor']=self.write('witness_monitor',wm)
if __name__=='__main__':unittest.main()
