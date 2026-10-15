"""Whole ordinary execution custody only; no scientific implementation."""
import pathlib,os,hashlib,json,subprocess

def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def digest(body):return hashlib.sha256(body).hexdigest()
def stat_pin(pin):
 p=pathlib.Path(pin['path']);assert p.is_absolute() and '..' not in p.parts
 for a in [p,*p.parents]:assert not a.is_symlink()
 s=p.stat();assert p.is_file() and s.st_size==pin['bytes'] and s.st_mode&0o777==pin['mode']
 assert type(pin['bytes']) is int and 0<=pin['bytes']<=9007199254740991 and len(pin['sha256'])==64
 return s

def authenticate_file(pin):
 # Literal accepted pre/post ordinary-file mechanics: stat before exact-length
 # O_NOFOLLOW stream, exact EOF/hash, held-FD AND pathname identity afterwards.
 before=stat_pin(pin);p=pathlib.Path(pin['path']);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  h=hashlib.sha256();remaining=pin['bytes']
  while remaining:
   b=os.read(fd,min(1048576,remaining));assert b;remaining-=len(b);h.update(b)
  assert not os.read(fd,1) and h.hexdigest()==pin['sha256']
  held=os.fstat(fd);after=p.stat()
  for k in ('st_dev','st_ino','st_size','st_mode','st_mtime_ns','st_ctime_ns'):assert getattr(before,k)==getattr(held,k)==getattr(after,k)
  stat_pin(pin)
 finally:os.close(fd)
 return {k:pin[k] for k in ('path','bytes','sha256','mode')}

def capture(root,head,pre,plan_bytes=None):
 assert [p['path'] for p in pre['code']]==json.loads((pathlib.Path(__file__).parent/'execution-code-paths.json').read_bytes()),'Complete ordered current code roster required'
 git=next(p['path'] for p in pre['runtime'] if p['role']=='git')
 assert subprocess.check_output([git,'-C',str(root),'rev-parse','HEAD'],text=True).strip()==head
 assert not subprocess.check_output([git,'-C',str(root),'status','--porcelain'],text=True).strip(),'Require frozen clean executing checkout'
 pins=[*pre['runtime'],pre['entry'],pre['supervisor']]
 if plan_bytes is None:pins.append(pre['plan'])
 else:
  # The issuer authenticates a derived in-memory plan before creating its fresh
  # file. The supervisor always reopens/authenticates that actual file at launch.
  assert isinstance(plan_bytes,bytes) and len(plan_bytes)==pre['plan']['bytes'] and digest(plan_bytes)==pre['plan']['sha256']

 code=[]
 for p in pre['code']:
  assert set(p)=={'path','bytes','sha256'} and type(p['bytes']) is int and p['bytes']>0 and not pathlib.Path(p['path']).is_absolute() and '..' not in pathlib.Path(p['path']).parts
  q=root/p['path'];code.append({**p,'path':str(q),'mode':0o644})
 for p in [*pins,*code]:authenticate_file(p)
 for p in pre['code']:
  row=subprocess.check_output([git,'-C',str(root),'ls-tree','-z',head,'--',p['path']]).decode();assert row.startswith('100644 blob ') and row.endswith('\t'+p['path']+'\0')
  body=subprocess.check_output([git,'-C',str(root),'show',head+':'+p['path']]);assert len(body)==p['bytes'] and digest(body)==p['sha256']
 return pre
