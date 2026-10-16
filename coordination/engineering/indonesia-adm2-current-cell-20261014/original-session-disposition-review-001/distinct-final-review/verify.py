import json,gzip,hashlib,pathlib,subprocess,os,collections,zipfile,io
D=pathlib.Path(__file__).resolve().parent
W=pathlib.Path('/workspace/scratch/127991fc8b8e/.worldatlas-workspaces/a7d1c19eff225d01/0f0bb6420b8a7acb9fec7eb313216e39d9b15a0c1f51234aa558b7f5aa812c31/work')
P=W/'.cloud-work/original-session-completion-review-001'; G=W/'.cloud-work/physical.git'
H='7f95faac8e729a3f199d28ae30cf317570c65ab9'; BASE='e7a47b0f3ccb08565b7bd7c9e219ac5500e8f338'; PREFIX='coordination/engineering/indonesia-adm2-current-cell-20261014/original-session-disposition-review-001/'
def git(*a): return subprocess.check_output(['git','-c','protocol.allow=never','--git-dir='+str(G),*a],env={**os.environ,'GIT_NO_LAZY_FETCH':'1'})
def sha(b): return hashlib.sha256(b).hexdigest()
def oid(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def js(p): return json.loads(pathlib.Path(p).read_bytes())
def jl(p):
 b=pathlib.Path(p).read_bytes(); b=gzip.decompress(b) if str(p).endswith('.gz') else b; return [json.loads(l) for l in b.splitlines()]
def key(x):
 k=x.get('original_key',x);return tuple(k[n] for n in ('owner','y','x'))
def checkpin(b,p):
 assert len(b)==p['bytes']; assert sha(b)==p['sha256'];
 if 'git_blob_oid'in p: assert oid(b)==p['git_blob_oid']
 if 'decoded_sha256'in p:
  d=gzip.decompress(b);assert sha(d)==p['decoded_sha256'];assert len(d)==p['decoded_bytes']
manifest=js(P/'publication-inventory.json'); tree={}
for line in git('ls-tree','-rz',H,'--',PREFIX).split(b'\0'):
 if not line:continue
 h,path=line.split(b'\t');mode,kind,o=h.decode().split();tree[path.decode()[len(PREFIX):]]=(mode,o)
files=manifest['files'];assert len(files)==316 and len(tree)==317
assert set(tree)=={f['path'] for f in files}|{'publication-inventory.json'}
for f in files:
 b=(P/f['path']).read_bytes();checkpin(b,f);assert tree[f['path']]==('100644',oid(b))
assert tree['publication-inventory.json']==('100644',oid((P/'publication-inventory.json').read_bytes()))
diff=git('diff','--name-status',BASE,H).decode().splitlines();assert len(diff)==317 and all(l.startswith('A\t'+PREFIX)for l in diff)
assert git('rev-parse',H+'^').decode().strip()==BASE
c=js(P/'input-custody-and-actual-vintages.json');pins=0
for pin in c['frozen_public_custody_pins']:
 rel=pin['path'].split('/consumed-inputs/')[1]
 local=P/'original-acceptance'/('frozen-extraction/'+rel[len('extraction/'):] if rel.startswith('extraction/') else 'original-initial-current-accounting-receipt.json')
 b=local.read_bytes();checkpin(b,pin);assert git('ls-tree',pin['commit'],'--',pin['path']).decode().split()[2]==oid(b);pins+=1
for name in ['original_complete778_questions','original_complete778_firstdated_records','actual_current_snapshot','quality33_whole_proposal','quality33_actual_custody','repair106_assessment','malaysian35_identity_review']:
 pin=c[name];checkpin(pathlib.Path(pin['file']).read_bytes(),pin)
for pin in c['actually_available_immutable_public_prior_question_firstdated_and_accounting_pins']:
 assert git('ls-tree',pin['commit'],'--',pin['path']).decode().split()[2]==pin['git_blob_oid'];pins+=1
F={};rows={}
for cat in ['physical','repair','conflict']:
 r=[]
 for p in sorted((P/'original-acceptance/frozen-extraction'/cat).glob('block-*.json.gz')):r+=json.loads(gzip.decompress(p.read_bytes()))
 m={}
 for i,row in enumerate(r):
  y,a,b,owners,sids,kind=row
  for x in range(a,b):
   for owner in owners:
    k=(owner,y,x);assert k not in m;m[k]=(i,row)
 F[cat]=m;rows[cat]=r
A={}
for f in (P/'accounting').glob('*.gz'):
 a=jl(f);s=set(map(tuple,a));assert len(s)==len(a);A[f.name]=s
ph=F['physical'];rep=F['repair'];conf=F['conflict'];pa=A['accepted-interpreted133434-owner-y-x.jsonl.gz'];held=A['still-map-unresolved412-owner-y-x.jsonl.gz'];ra=A['current-repair190743-accepted-native-including2794-start-overlap.jsonl.gz'];rh=A['current-repair106-unaccepted-owner-y-x.jsonl.gz']
assert set(ph)==A['original-physical133846-owner-y-x.jsonl.gz']==pa|held and not pa&held
assert set(rep)==A['original-repair190849-owner-y-x.jsonl.gz']==ra|rh and not ra&rh
assert [len(ph),len(pa),len(held),len(rep),len(ra),len(rh)]==[133846,133434,412,190849,190743,106]
origq={key(x):x for x in jl(c['original_complete778_questions']['file'])};origd={key(x):x for x in jl(c['original_complete778_firstdated_records']['file'])};records=jl(P/'physical412-complete-original-questions-evidence-and-proposed-dispositions.jsonl.gz')
assert len(records)==412 and {key(x)for x in records}==held
for x in records:
 k=key(x); f=x['original_frozen_interval']; assert f['original_interval']==ph[k][1] and f['interval_ordinal_in_ordered_four_blocks']==ph[k][0]
 assert x['original_published_complete_question_unchanged']==origq[k];assert x['original_firstdated_complete_scientific_record_unchanged']==origd[k]
 d=x['proposed_original_package_review_disposition']; assert d['actual_source_reason'] and d['remaining_question'] and d['next_action'];assert d['new_positive_answer_or_native_credit']==0
r106=jl(P/'native106-remaining-original-requests-with62prepared44-exceptions.jsonl.gz');r44=jl(P/'native44-documented-exceptions-only.jsonl.gz');assert len(r106)==106 and {key(x)for x in r106}==rh
assert len(r44)==44 and {key(x)for x in r44}<rh
for x in r106: assert x['original_frozen_interval']==rep[key(x)][1]
for x in r44: assert x in r106 and x['original_package_review_disposition']['accepted_new_repair_credit']==0
patchpin=c['actual_current_accepted_native_patch'];patchbody=git('cat-file','blob',patchpin['git_blob_oid']);checkpin(patchbody,patchpin);patch=json.loads(patchbody); native={}
for row in patch['rows']:
 for start,end,owner in row['runs']:
  for x in range(start,end):
   k=(row['y'],x);assert k not in native;native[k]=owner
assert {(o,y,x)for (o,y,x)in rep if native.get((y,x))==o}==ra
r27=jl(P/'source-conflict27-complete-competing-evidence-and-dispositions.jsonl.gz');assert len(r27)==27
assert {tuple(x['native_key'])for x in r27}=={(y,x)for o,y,x in conf}
for x in r27:
 y,z=x['native_key']; assert x['all_original_competing_owners']==x['original_interval'][3]; assert all(conf[(o,y,z)][1]==x['original_interval']for o in x['all_original_competing_owners']);assert native.get((y,z))==x['current_accepted_native_owner']
initial=js(P/'original-acceptance/original-initial-current-accounting-receipt.json');print('initial repair',initial['categories']['repair'])
# Whole new native-array members; exact retained value/mask centres and 3x3 neighborhoods.
import numpy as np
Q=P/'source-quality33';cust=js(Q/'actual-observation-custody-verification.json'); arrays={};decoded=0
for r in cust['native_arrays']:
 b=(Q/r['path']).read_bytes();checkpin(b,r)
 with zipfile.ZipFile(io.BytesIO(b))as z:
  assert set(z.namelist())=={v['path']for v in r['decoded_members']}
  for v in r['decoded_members']:checkpin(z.read(v['path']),v)
 with np.load(io.BytesIO(b),allow_pickle=False)as z: arrays[r['path']]={k:z[k].copy()for k in z.files}
 decoded+=sum(a.nbytes for a in arrays[r['path']].values())
obs=[];centres=[]
for f in (Q/'next-distinct-raw-native-observation-001').glob('*/point-observations.jsonl'):obs+=jl(f)
assert len(obs)==33
for x in obs:
 for asset,r in x['assets'].items():
  a=arrays[r['containing_array']['file']]; row,col=r['native_containing_pixel']; height,width=a['values'].shape;rr=row%height;cc=col%width
  assert int(a['values'][rr,cc])==r['raw_value']; assert int(a['mask'][rr,cc])==r['native_valid_mask']
  assert a['values'][rr-1:rr+2,cc-1:cc+2].tolist()==r['actual_raw3x3'];assert a['mask'][rr-1:rr+2,cc-1:cc+2].tolist()==r['actual_mask3x3']
 centres.append({'key':x['original_key'],'point_index':x['point_index'],'item':x['item_id'],'baseline':x['processing_baseline'],'values':{a:r['raw_value']for a,r in x['assets'].items()},'masks':{a:r['native_valid_mask']for a,r in x['assets'].items()}})
assert decoded==196608000
result={'head':H,'tree':git('rev-parse',H+'^{tree}').decode().strip(),'files':317,'inventory_payload_bytes':sum(f['bytes']for f in files),'authenticated_frozen_and_public_pin_count':pins,'physical_intervals':len(rows['physical']),'physical_keys':len(ph),'accepted_interpreted':len(pa),'explicit_pending_disposition_keys':len(held),'held_owner_counts':dict(collections.Counter(k[0]for k in held)),'repair_intervals':len(rows['repair']),'repair_keys':len(rep),'actually_accepted_repair_keys_including_start_overlap':len(ra),'repair_pending':len(rh),'documented_exceptions':len(r44),'conflict_coordinates':len(r27),'original_competitors':len(conf),'accepted_conflicts':sum(x['accepted_original_source_conflict_credit']for x in r27),'new_quality_arrays':len(arrays),'new_quality_decoded_value_mask_bytes':decoded,'new_quality_centres':centres,'all_assertions_passed':True}
(D/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='new_quality_centres'},indent=2))
