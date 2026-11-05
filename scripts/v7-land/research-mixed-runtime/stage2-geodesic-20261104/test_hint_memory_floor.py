import importlib.util, json, os, signal, sys, tempfile, types, unittest
from pathlib import Path
from unittest import mock
import contracts
from test_contracts_qualified import ContractsTests

BASE=Path(__file__).parent/'hint-producer'
if not BASE.is_dir():
 BASE=Path(__file__).parent.parents[2]/'v7-recovery'/'land'/'stage2-geodesic-20261104'/'hint-producer'
def load(name):
 spec=importlib.util.spec_from_file_location(name,BASE/(name+'.py'))
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

class HintMemoryFloor(unittest.TestCase):
 def test_contract_accepts_zero_floor_but_checks_measurements(self):
  t=ContractsTests();t.setUp();args=(t.hints,t.monitor,t.grid,t.pins,'d','e',t.metric,[7],{'hints.py':'b'*64,'run_diagnostic.py':'c'*64},'d'*64)
  t.monitor['minimum_memory_kib']=0;t.monitor['minimum_available_kib']=12
  self.assertEqual(contracts.hints_report(*args),3)
  for field,value in [('minimum_memory_kib',-1),('minimum_available_kib',-1),('peak_child_rss_kib',0),('samples',0)]:
   old=t.monitor[field];t.monitor[field]=value
   with self.assertRaisesRegex(ValueError,'watchdog'):contracts.hints_report(*args)
   t.monitor[field]=old
 def test_runner_zero_floor_still_reads_memory_and_checks_disk(self):
  import builtins, io
  stubs={name:types.ModuleType(name) for name in ('numpy','pyproj','scipy','hints')}
  stubs['hints'].__file__=str(BASE/'hints.py')
  with mock.patch.dict(sys.modules,stubs):r=load('run_diagnostic')
  with tempfile.TemporaryDirectory() as temp:
   d=Path(temp);inputs=d/'inputs';inputs.mkdir();source=inputs/'data';source.write_text('x');cfg=inputs/'request.json'
   request={'schema':'source-only-hints-diagnostic-request-v1','grid':{},'codes':[],'inputs':{k:{'path':str(source),'sha256':'a'*64} for k in r.NAMES},'decision_revision':'d','entity_revision':'e','policy_id':'p','policy_version':'1','minimum_memory_kib':0,'minimum_free_bytes':1}
   cfg.write_text(json.dumps(request));real_open=builtins.open
   def opened(path,*args,**kwargs):
    if str(path)=='/proc/meminfo':return io.StringIO('MemAvailable: 55 kB\n')
    return real_open(path,*args,**kwargs)
   with mock.patch('builtins.open',side_effect=opened), mock.patch.object(r.shutil,'disk_usage',side_effect=RuntimeError('disk checked')):
    with self.assertRaisesRegex(RuntimeError,'disk checked'):r.run(cfg,d/'out')
   request['minimum_memory_kib']=-1;cfg.write_text(json.dumps(request))
   with self.assertRaisesRegex(ValueError,'resource floors'):r.run(cfg,d/'out')
 def test_runner_reads_bounded_representatives_without_extra_floor(self):
  import builtins, io
  stubs={name:types.ModuleType(name) for name in ('numpy','pyproj','scipy','hints')};stubs['hints'].__file__=str(BASE/'hints.py');stubs['hints'].seed_roots_from_resolution=lambda *a,**k:[7]
  stubs['numpy'].frombuffer=mock.Mock(side_effect=RuntimeError('representatives reached'))
  with mock.patch.dict(sys.modules,stubs):r=load('run_diagnostic')
  with tempfile.TemporaryDirectory() as temp:
   d=Path(temp);ins=d/'inputs';ins.mkdir();paths={k:ins/k for k in r.NAMES}
   for path in paths.values():path.write_text('{}')
   metric={'policy_id':'p','version':'1','execution_status':'selected_for_research','decision_revision':'d','algorithm':'wgs84_ellipsoidal_geodesic_inverse','units':'metres','semi_major_axis_m':'6378137','inverse_flattening':'298.257223563'}
   snap={'schema':'worldatlas-geography-decision-draft-evidence-v1','source':'neon-export','decision_revision':{'id':'d','entity_revision':'e','status':'draft'},'entity_revision':{'id':'e','status':'draft'},'distance_policies':[metric],'category_bindings':[{'physical_class':'land','code':17}]}
   paths['decision_snapshot'].write_text(json.dumps(snap));paths['tile_manifest'].write_text('0 0 1 1 '+'a'*64+'\n');paths['representatives'].write_bytes(b'\0'*20)
   request={'schema':'source-only-hints-diagnostic-request-v1','grid':{'width':8,'height':4,'step':45,'west':-180,'north':90},'codes':[17],'inputs':{k:{'path':str(v),'sha256':'a'*64} for k,v in paths.items()},'decision_revision':'d','entity_revision':'e','policy_id':'p','policy_version':'1','minimum_memory_kib':0,'minimum_free_bytes':1};cfg=ins/'request';cfg.write_text(json.dumps(request));real_open=builtins.open
   def opened(path,*args,**kwargs):
    if str(path)=='/proc/meminfo':return io.StringIO('MemAvailable: 1 kB\n')
    return real_open(path,*args,**kwargs)
   with mock.patch('builtins.open',side_effect=opened), mock.patch.object(r.shutil,'disk_usage',return_value=types.SimpleNamespace(free=100)), mock.patch.object(r,'digest',return_value='a'*64):
    with self.assertRaisesRegex(RuntimeError,'representatives reached'):r.run(cfg,d/'out')
   stubs['numpy'].frombuffer.assert_called_once()
 def test_watch_records_observed_memory_with_zero_floor(self):
  w=load('watch_diagnostic')
  with tempfile.TemporaryDirectory() as temp:
   d=Path(temp);out=d/'out';out.mkdir();(out/'report.json').write_text('{}');cfg=d/'request.json';cfg.write_text(json.dumps({'minimum_memory_kib':0,'minimum_free_bytes':1}))
   proc=mock.Mock(pid=123);proc.poll.side_effect=[None,0];proc.wait.return_value=0
   with mock.patch.object(w.os,'pidfd_open',lambda pid:os.open('/dev/null',os.O_RDONLY),create=True), mock.patch.object(w.signal,'pidfd_send_signal',create=True), mock.patch.object(w.subprocess,'Popen',return_value=proc), mock.patch.object(w,'memavailable',side_effect=[123,45,67]), mock.patch.object(w,'rss',return_value=7), mock.patch.object(w.time,'sleep'):
    result=w.run(cfg,out,10)
   self.assertEqual((result['minimum_memory_kib'],result['minimum_available_kib'],result['peak_child_rss_kib'],result['samples']),(0,45,7,1))
   self.assertEqual(json.loads((out/'monitor.json').read_text()),result)
 def test_watch_still_rejects_rss_limit_with_zero_floor(self):
  w=load('watch_diagnostic')
  with tempfile.TemporaryDirectory() as temp:
   d=Path(temp);cfg=d/'request';cfg.write_text(json.dumps({'minimum_memory_kib':0,'minimum_free_bytes':1}));proc=mock.Mock(pid=123);proc.poll.return_value=None;proc.wait.return_value=0
   with mock.patch.object(w.os,'pidfd_open',lambda pid:os.open('/dev/null',os.O_RDONLY),create=True), mock.patch.object(w.signal,'pidfd_send_signal',create=True) as kill, mock.patch.object(w.subprocess,'Popen',return_value=proc), mock.patch.object(w,'memavailable',return_value=40), mock.patch.object(w,'rss',return_value=11):
    with self.assertRaisesRegex(RuntimeError,'child RSS limit'):w.run(cfg,d/'out',10)
    kill.assert_called_once()
 def test_watch_rejects_negative_floor(self):
  w=load('watch_diagnostic')
  with tempfile.TemporaryDirectory() as temp:
   cfg=Path(temp)/'request';cfg.write_text(json.dumps({'minimum_memory_kib':-1}))
   with self.assertRaisesRegex(ValueError,'invalid watchdog limits'):w.run(cfg,Path(temp)/'out',10)
if __name__=='__main__':unittest.main()
