import subprocess,pathlib,time,json,re,importlib.util,hashlib,os
root=pathlib.Path.cwd();d=root/'.cache/selected-prevention/coordinate-hook-e7b0';helper=pathlib.Path('/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/8c86b01772c1c827/3d62cf18b0b42e3ae3cd26d42f5e7ac90b65e45ead741649cedd79762724f9e7/work/.cache/1394-physical-continuation-e9b03/owned-child-termination-00c6028d.py')
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='00c6028d814eabb67fd1986c7e7b0473836823dcfc81072d2b6563b0a5151c61'
spec=importlib.util.spec_from_file_location('owned',helper);owned=importlib.util.module_from_spec(spec);spec.loader.exec_module(owned)
node='/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node';entry=root/'coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs';destination=d/'current-v8-coordinate-hook-e7b0';assert not destination.exists()
command=['/usr/bin/time','-l',node,'--expose-gc',str(entry),'coordinate',str(root),'e7b0c388914b8f6650cfeacf1e9cd9e338c2dd5b','4f1639082dc1e9c54fd11e06a9530a7ce78d4f12',str(destination)]
env=dict(os.environ);env.pop('NODE_OPTIONS',None);env.pop('NODE_PATH',None)
start=time.monotonic();samples=[];refusal=None;events=[];cap=536870912;wall=1200
with (d/'coordinate.stdout').open('xb') as out,(d/'coordinate.stderr').open('xb') as err:
 p=subprocess.Popen(command,stdout=out,stderr=err,env=env,start_new_session=True)
 identity=owned.snapshot().get(p.pid);assert identity and identity['pgid']==p.pid
 while p.poll() is None:
  group=[]
  for line in subprocess.check_output(['ps','-axo','pid=,pgid=,rss=']).decode().splitlines():
   fields=line.split()
   if len(fields)==3 and int(fields[1])==p.pid:group.append({'pid':int(fields[0]),'rss_bytes':int(fields[2])*1024})
  sample={'elapsed':time.monotonic()-start,'group':group,'rss_bytes':sum(r['rss_bytes'] for r in group)};samples.append(sample)
  if sample['rss_bytes']>cap or sample['elapsed']>wall:
   refusal='sample_rss' if sample['rss_bytes']>cap else 'wall';events=owned.terminate_owned(p,identity);break
  time.sleep(.5)
 code=p.wait()
text=(d/'coordinate.stderr').read_text();match=re.search(r'(\d+)\s+maximum resident set size',text);lifetime=int(match.group(1)) if match else None
remaining=[{'pid':pid,**row} for pid,row in owned.snapshot().items() if row['pgid']==p.pid]
qualified=code==0 and refusal is None and lifetime is not None and lifetime<=cap and not remaining
receipt={'version':1,'kind':'selected-coordinate-operating-v1','command':command,'head':'e7b0c388914b8f6650cfeacf1e9cd9e338c2dd5b','input_commit':'4f1639082dc1e9c54fd11e06a9530a7ce78d4f12','limits':{'rss_bytes':cap,'wall_seconds':wall,'sample_seconds':.5},'elapsed':time.monotonic()-start,'root_identity':identity,'exit_code':code,'refusal':refusal,'lifetime_rss_bytes':lifetime,'sample_peak_bytes':max((r['rss_bytes'] for r in samples),default=0),'owned_processes_remaining':remaining,'termination_events':events,'qualified':qualified,'publication_exists':(destination/'publication.json').exists(),'supervisor_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'helper_sha256':'00c6028d814eabb67fd1986c7e7b0473836823dcfc81072d2b6563b0a5151c61'}
(d/'coordinate-samples.json').write_text(json.dumps(samples)+'\n');(d/'coordinate-operating-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));raise SystemExit(0 if qualified else 1)
