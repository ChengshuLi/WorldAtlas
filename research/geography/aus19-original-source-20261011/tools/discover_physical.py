"""Bounded delivered physical-row discovery, without original inverse or GIS."""
import base64,collections,gzip,hashlib,json,os,pathlib,resource,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[4]
OUT=ROOT/'.cache/aus19/physical-discovery';OUT.mkdir(exist_ok=False)
BASE='6a99a7606b9c2d11ac8cd093610653d4cd5d1382';PRE='coordination/engineering/global-physical-comparison-20261006/results/'
CAP=128*1024**2;started=time.monotonic();sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a],stderr=subprocess.PIPE)
def canon(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()
def body(name):
 row=git('ls-tree','-z',BASE,'--',name).decode().rstrip('\0');fields,path=row.split('\t');mode,kind,oid=fields.split();assert(mode,kind,path)==('100644','blob',name)
 raw=git('cat-file','blob',oid);return raw,{'path':name,'git_blob_oid':oid,'bytes':len(raw),'sha256':sha(raw)}
raw,tp=body(PRE+'transport-map.json');transport=json.loads(raw);parts=[p for p in transport['entries'] if p['kind']=='components'];assert len(parts)==71 and transport['complete_components']==95173
raw,rp=body(PRE+'report.json');report=json.loads(raw);assert report['execution_commit']==transport['scientific_execution'] and report['component_count']==95173
roster=json.loads((ROOT/'research/geography/aus19-original-source-20261011/roster.json').read_bytes());want=[r['component_id'] for r in roster['members']];assert len(want)==len(set(want))==19
rows=git('ls-tree','-r',BASE,'--',PRE).decode().splitlines();oids={r.split('\t')[1]:r.split()[2] for r in rows};found={};ranges={};phases=[];phase=[];used=0;downloaded=[]
fixed=tp['bytes']+rp['bytes']+len(canon(roster))+pathlib.Path(__file__).stat().st_size+4*1024**2

def closephase():
 global phase,used
 if phase:phases.append({'ordinal':len(phases),'whole_products':phase,'logical_bytes':used,'retained_selected_row_bytes':len(canon(found))});phase=[];used=0

def read(i):
 global used
 if i in ranges:return ranges[i]
 entry=parts[i];d=entry['delivered'];path=PRE+d['path'];oid=oids[path];charge=d['bytes']+d['uncompressed_bytes']
 carry=len(canon(found))+len(canon(ranges))+fixed
 if phase and used+charge+carry>CAP:closephase()
 if not phase:used=carry
 assert used+charge<=CAP;used+=charge
 proc=subprocess.run(['git','-C',str(ROOT),'cat-file','-e',oid],capture_output=True)
 if proc.returncode==0:raw=git('cat-file','blob',oid)
 else:
  api=json.loads(subprocess.check_output(['gh','api','repos/ChengshuLi/WorldAtlas/git/blobs/'+oid]));assert api['sha']==oid and api['encoding']=='base64';raw=base64.b64decode(api['content']);downloaded.append(oid)
 assert len(raw)==d['bytes'] and sha(raw)==d['sha256'] and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid
 with (OUT/(oid+'.bin')).open('xb') as f:f.write(raw)
 dec=gzip.decompress(raw);assert len(dec)==d['uncompressed_bytes'] and sha(dec)==d['uncompressed_sha256'];records=[json.loads(line) for line in dec.splitlines()];ids=[r['component_id'] for r in records];assert ids==sorted(set(ids)) and ids
 meta={'index':i,'first_id':ids[0],'last_id':ids[-1],'rows':len(records),'entry':entry,'path':path,'blob':oid};ranges[i]=meta;phase.append({'path':path,'oid':oid,'encoded_bytes':len(raw),'decoded_bytes':len(dec)})
 for ordinal,r in enumerate(records):
  if r['component_id'] in want:assert r['component_id'] not in found;found[r['component_id']]={'row':r,'ordinal':ordinal,'product':meta}
 assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<256*1024**2
 print(json.dumps({'part':i,'found':len(found),'phase':len(phases),'logical_bytes':used}),flush=True)
 return meta
for cid in want:
 if cid in found:continue
 i=min(70,int(int(cid.split(':')[1][:8],16)/2**32*71))
 while cid not in found:
  r=read(i)
  if cid in found:break
  j=i-1 if cid<r['first_id'] else i+1
  if j<0 or j>=len(parts) or r['first_id']<=cid<=r['last_id']:raise ValueError('Missing exact ID in authenticated sorted range')
  i=j
closephase();assert set(found)==set(want)
result={'baseline':BASE,'scope':want,'rows':[found[x] for x in want],'products':list(ranges.values()),'phases':phases,'downloaded_oids':downloaded,'metadata_inputs':[tp,rp],'elapsed_seconds':time.monotonic()-started,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'limits':['Delivered metadata aliases only; whole original product inverse still required.','No physical/GIS scientific acceptance.']}
with(OUT/'discovery.json').open('xb')as f:f.write(canon(result))
print(json.dumps({'found':len(found),'products':len(ranges),'phases':len(phases),'elapsed_seconds':result['elapsed_seconds'],'peak_rss_bytes':result['peak_rss_bytes'],'statuses':dict(collections.Counter(r['row']['status'] for r in found.values()))}))
