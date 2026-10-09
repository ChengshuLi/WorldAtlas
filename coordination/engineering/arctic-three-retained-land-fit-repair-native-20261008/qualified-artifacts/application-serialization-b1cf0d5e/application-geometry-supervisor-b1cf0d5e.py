"""Owned serial proposal pair; existing reviewed descendant termination, measured limits."""
import pathlib,subprocess,os,time,json,datetime,hashlib,importlib.util,re
W=pathlib.Path('/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/8c86b01772c1c827/13630faa807843641a6abb3484134a94a87e5c38c2665c17f5c9742c84749ddf/work')
R=pathlib.Path('/Users/chengshuli/world-atlas-workspace/.cache/arctic-three-repair-1520-20261008')
HEAD='b1cf0d5efa6943c1c1a991aaec8ead3d83bf5511'
PYTHON='/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python'
HELPER=pathlib.Path('/Users/chengshuli/world-atlas-workspace/.cache/1295-normal-consumer-materialization-20261008/final-author-cache-preserved-94495073/1295-owned-child-termination.py')
assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='00c6028d814eabb67fd1986c7e7b0473836823dcfc81072d2b6563b0a5151c61'
spec=importlib.util.spec_from_file_location('owned_termination',HELPER);termination=importlib.util.module_from_spec(spec);spec.loader.exec_module(termination)
assert hashlib.sha256((R/'owned-group.py').read_bytes()).hexdigest()=='9ac8aeca9c721968bf33e69e219dbfb103875263b994dff1bd2e94402d0750ce'
spec2=importlib.util.spec_from_file_location('owned_group',R/'owned-group.py');owned_group=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(owned_group)
STOP=384*1024*1024; CEILING=512*1024*1024; WALL=1200; GROWTH=16*1024*1024

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def usage(group):
 rows=[]
 for line in subprocess.check_output(['ps','-axo','pid=,ppid=,pgid=,rss=,command='],text=True).splitlines():
  fields=line.split(None,4)
  if len(fields)==5 and int(fields[2])==group:rows.append({'pid':int(fields[0]),'ppid':int(fields[1]),'rss_bytes':int(fields[3])*1024,'command':fields[4]})
 return rows

def retained():
 roots=[R/'application-geometry-publication-b1cf0d5e',W/'.cache'/'application-geometry-publication-b1cf0d5e']
 return sum(p.stat().st_size for root in roots if root.exists() for p in root.rglob('*') if p.is_file())


EXECUTABLE='/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
ENTRY='/Users/chengshuli/world-atlas-workspace/.cache/arctic-three-repair-1520-20261008/application-geometry-entry-b1cf0d5e.mjs'
PROOF=pathlib.Path('/Users/chengshuli/world-atlas-workspace/.cache/arctic-three-repair-1520-20261008/application-geometry-code-source-b1cf0d5e.json')
PROOF_BYTES=2026
PROOF_SHA='ec0b2122731af717b61ec80cf5e063a52fc1ce6b9e7bc298712e323ccfd535b9'
assert PROOF.stat().st_size==PROOF_BYTES and hashlib.sha256(PROOF.read_bytes()).hexdigest()==PROOF_SHA
CODE_PROOF=json.loads(PROOF.read_bytes());assert CODE_PROOF["head"]==HEAD and CODE_PROOF["root"]==str(W)
PLANS=[{'path': '/Users/chengshuli/world-atlas-workspace/.cache/arctic-three-repair-1520-20261008/application-geometry-plan-b1cf0d5e.json', 'bytes': 3283, 'sha': 'cfa347b2d38c6b957ddd5cd841c9b7582420c125d6cb2a751b519e510c185f98'}]

def authenticate_file(file,size,mode,digest):
 file=pathlib.Path(file)
 assert file.is_absolute() and '..' not in file.parts
 for ancestor in [file,*file.parents]:assert not ancestor.is_symlink()
 before=file.stat();assert file.is_file() and before.st_size==size and before.st_mode&0o777==mode
 fd=os.open(file,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  h=hashlib.sha256();remaining=size
  while remaining:
   body=os.read(fd,min(1048576,remaining));assert body;remaining-=len(body);h.update(body)
  assert not os.read(fd,1) and h.hexdigest()==digest
  held=os.fstat(fd);after=file.stat()
  for field in ('st_dev','st_ino','st_size','st_mode','st_mtime_ns','st_ctime_ns'):
   assert getattr(before,field)==getattr(held,field)==getattr(after,field)
  for ancestor in [file,*file.parents]:assert not ancestor.is_symlink()
 finally:os.close(fd)
def admit_declared_phase():
 raw=pathlib.Path(PLANS[0]['path']).read_bytes()
 assert len(raw)==PLANS[0]['bytes'] and hashlib.sha256(raw).hexdigest()==PLANS[0]['sha']
 plan=json.loads(raw);assert plan['head']==HEAD
 pins=[*plan['sources'],*plan['code'],plan['runtime']]
 assert len(pins)<=512 and len({pin['path'] for pin in pins})==len(pins)
 total=plan['outputReserve']+plan['metadataBytes']
 for pin in pins:
  file=pathlib.Path(pin['path']);assert file.is_absolute() and '..' not in file.parts
  for ancestor in [file,*file.parents]:assert not ancestor.is_symlink()
  stat=file.stat();assert file.is_file() and stat.st_size==pin['bytes'] and stat.st_mode&0o777==pin['mode']
  if pin is not plan['runtime']:assert pin['bytes']<=32*1024*1024
  assert pin.get('decoded_bytes',0)<=32*1024*1024
  total+=pin['bytes']+pin.get('decoded_bytes',0)
 assert total<=256*1024*1024

def verify_code():
 admit_declared_phase()
 authenticate_file(PROOF,PROOF_BYTES,0o644,PROOF_SHA)
 for plan in PLANS:authenticate_file(plan['path'],plan['bytes'],0o644,plan['sha'])
 for pin in [*CODE_PROOF['whole_code'],*CODE_PROOF['whole_runtime']]:authenticate_file(pin['path'],pin['bytes'],pin['mode'],pin['sha256'])
def log_bounds(files):
 return all(not file.exists() or file.stat().st_size<=32*1024*1024 for file in files)
def metadata_bytes():
 fixed=[pathlib.Path(__file__),pathlib.Path(ENTRY),PROOF,pathlib.Path(PLANS[0]['path']),HELPER,R/'owned-group.py']
 root=R/'application-geometry-publication-b1cf0d5e'
 return sum(file.stat().st_size for file in fixed)+sum(file.stat().st_size for file in root.rglob('*') if file.is_file()) if root.exists() else sum(file.stat().st_size for file in fixed)

def run():
 assert subprocess.check_output(['/Library/Developer/CommandLineTools/usr/bin/git','rev-parse','HEAD'],cwd=W,text=True).strip()==HEAD
 assert not subprocess.check_output(['/Library/Developer/CommandLineTools/usr/bin/git','status','--porcelain'],cwd=W,text=True).strip()
 D=R/'application-geometry-publication-b1cf0d5e';D.mkdir(exist_ok=False)
 results=[]
 for number in (1,):
  for ordinal in range(1):
   key=f'run-{number}-chunk-{ordinal:02d}'
   O=W/'.cache'/'application-geometry-publication-b1cf0d5e'
   assert not O.exists()
   assert '..' not in O.parts and O.is_relative_to(W/'.cache')
   for ancestor in O.parents:
    if ancestor.exists() or ancestor.is_symlink():assert not ancestor.is_symlink() and ancestor.is_dir()
   O.parent.mkdir(parents=True,exist_ok=True)
   verify_code() # Independent original Git proof before ANY child imports.
   assert metadata_bytes()+16384<=131072,'Complete external metadata reservation before launch'
   cmd=['/usr/bin/time','-l',EXECUTABLE,ENTRY,PLANS[ordinal]['path'],str(O)]
   start=now();tick=time.monotonic();peak=0;reason=None;events=[]
   stdout=D/f'{key}.stdout.json';stderr=D/f'{key}.stderr.log'
   with stdout.open('xb') as out,stderr.open('xb') as err,(D/f'{key}.samples.jsonl').open('x') as samples:
    env={k:v for k,v in os.environ.items() if k not in ('NODE_OPTIONS','NODE_PATH','PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','PYTHONINSPECT','PYTHONUSERBASE','__PYVENV_LAUNCHER__')}
    env.update(WORLDATLAS_SELECTED_NATIVE_HEAD=HEAD,WORLDATLAS_SELECTED_NATIVE_PLAN_RAW_SHA256=PLANS[ordinal]['sha'])
    p=subprocess.Popen(cmd,cwd=W,env=env,stdout=out,stderr=err,start_new_session=True)
    identity=termination.snapshot().get(p.pid);assert identity and identity['pgid']==p.pid
    authority=owned_group.OwnedGroup(p,identity)
    (D/f'{key}.launch.json').write_text(json.dumps({'pid':p.pid,'identity':identity,'command':cmd,'started_at':start,'head':HEAD,'output':str(O)})+'\n')
    print(json.dumps({'run':number,'ordinal':ordinal,'pid':p.pid,'command':cmd}),flush=True)
    while p.poll() is None:
     rows=usage(p.pid);total=sum(row['rss_bytes'] for row in rows);peak=max(peak,total)
     samples.write(json.dumps({'at':now(),'elapsed':time.monotonic()-tick,'rss_bytes':total,'processes':rows})+'\n');samples.flush()
     if metadata_bytes()+16384>131072:reason='Complete external metadata128KiB cap'
     elif not log_bounds([stdout,stderr,D/f'{key}.samples.jsonl']):reason='Ordinary log/sample cap exceeded32MiB'
     elif total>STOP:reason='sampled process-tree RSS exceeds384MiB'
     elif time.monotonic()-tick>WALL:reason='chunk walltime exceeds1200s'
     elif retained()>GROWTH:reason='complete retained output/log growth exceeds16MiB'
     if reason:events=authority.cleanup();break
     time.sleep(.25)
    exit_code=p.wait()
   survivors=[{'pid':pid,**row} for pid,row in termination.snapshot().items() if row['pgid']==p.pid]
   if survivors:
    events+=authority.cleanup();reason=reason or 'Natural exit retained owned descendants; cleaned/unqualified'
    survivors=[{'pid':pid,**row} for pid,row in termination.snapshot().items() if row['pgid']==p.pid]
   assert log_bounds([stdout,stderr,D/f'{key}.samples.jsonl']),'Terminal ordinary log/sample cap'
   verify_code()
   match=re.search(r'^\s*(\d+)\s+maximum resident set size',stderr.read_text(),re.M)
   lifetime=int(match.group(1)) if match else None
   qualified=exit_code==0 and reason is None and not survivors and lifetime is not None and lifetime<=CEILING
   receipt={'run':number,'ordinal':ordinal,'head':HEAD,'command':cmd,'started_at':start,'ended_at':now(),'elapsed_seconds':time.monotonic()-tick,'exit_code':exit_code,'qualified':qualified,'guard_reason':reason,'sampled_group_peak_bytes':peak,'time_l_lifetime_max_rss_bytes':lifetime,'owned_group_survivors':survivors,'termination_events':events,'sampled_stop_bytes':STOP,'lifetime_ceiling_bytes':CEILING,'wall_limit_seconds':WALL,'growth_bytes':retained(),'growth_limit':GROWTH,'preimport_code_source_sha256':'ec0b2122731af717b61ec80cf5e063a52fc1ce6b9e7bc298712e323ccfd535b9','sampling_limit':'Sampled simultaneous group and per-process lifetime differ; neither is a kernel memory guarantee.'}
   terminal_body=json.dumps(receipt,indent=2)+'\n'
   assert metadata_bytes()+len(terminal_body.encode())<=131072,'Terminal metadata reservation'
   (D/f'{key}.terminal.json').write_text(terminal_body);results.append(receipt)
   print(json.dumps({'run':number,'ordinal':ordinal,'exit_code':exit_code,'qualified':qualified,'lifetime':lifetime}),flush=True)
   assert retained()<=GROWTH,'Terminal receipt exceeds growth reserve'
   assert qualified,'Unqualified actual acquisition; no automatic retry'
run()
