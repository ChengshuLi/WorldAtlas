import ast,pathlib,subprocess,os,signal,time,types,tempfile,json,hashlib
D=pathlib.Path('/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/8c86b01772c1c827/8f37144f48568734be4c4d84e67e369ea25708759c9cd4f3ba8016200850ca79/work/.cache/selected-continuous-actual417-20261009');p=D/'supervise.py';tree=ast.parse(p.read_bytes());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['cleanup_launch','own_launch']];with_node=next(n for n in tree.body if isinstance(n,ast.With) and any(isinstance(x,ast.Try) for x in n.body));results=[]
for branch in ['missing_initial_snapshot','sampler_snapshot_failure','sampler_ps_failure']:
 with tempfile.TemporaryDirectory(prefix='1627-owned-launch-control-') as tmp:
  count=[0];children=[]
  def launch(*a,**kw):
   child=subprocess.Popen(*a,**kw);children.append(child);time.sleep(.08);return child
  def snap():
   count[0]+=1
   if branch=='missing_initial_snapshot':return {}
   if branch=='sampler_snapshot_failure' and count[0]==2:raise OSError('injected sampler snapshot failure')
   return {children[0].pid:{'pgid':children[0].pid,'started':'tiny-control'}}
  def ps(*a,**k):raise OSError('injected sampler ps failure')
  scope={'os':os,'signal':signal,'time':time,'m':types.SimpleNamespace(snapshot=snap),'D':pathlib.Path(tmp),'subprocess':types.SimpleNamespace(Popen=launch,check_output=ps),'R':tmp,'env':dict(os.environ),'cmd':['/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12','-c','import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(20)'],'reason':None,'observed':{},'samples':[],'events':[],'tick':time.monotonic()}
  exec(compile(ast.fix_missing_locations(ast.Module(body=nodes+[with_node],type_ignores=[])),str(p),'exec'),scope)
  child=children[0];assert child.poll() is not None and scope['reason'].startswith('Owned launch/sampling exception:')
  try:os.killpg(child.pid,0)
  except ProcessLookupError:pass
  else:raise AssertionError('owned group remains')
  results.append({'branch':branch,'exit_code':child.returncode,'stop_reason':scope['reason'],'owned_group_absent':True})
r={'supervisor_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'actual_extracted_supervisor_blocks':True,'controls':results,'scientific_execution':False};(D/'launch-guard-controls.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
