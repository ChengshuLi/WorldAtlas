import subprocess,json,os,collections,hashlib,pathlib,bisect
R='/workspace/scratch/127991fc8b8e/worldatlas-primary';E=dict(os.environ,GIT_NO_LAZY_FETCH='1');H='eb06af616eb876b612fd433d81d632981642799b';S='a1a8c3060a97cfc0648a7412c1662e19fde83f76';B='282d14b4682f738fed6a0e6f3ee0d0e4b775d611'
def raw(c,p):return subprocess.check_output(['git','-C',R,'show',c+':'+p],env=E)
def j(c,p):return json.loads(raw(c,p))
x=j(H,'coordination/engineering/germany-original-repair-20261017/source-stage-001/original-native-patch.json');ours={r['y']:r['runs'] for r in x['rows']};assert sum(b-a for rs in ours.values() for a,b,*_ in rs)==27555
selector=j(B,'data/ownership-selection.json');side=j(B,selector['additive_release']['path']);d=side['logical_asset_map']['patch'];b=raw(d['commit'],d['path']);assert len(b)==d['bytes'] and hashlib.sha256(b).hexdigest()==d['sha256']
spec=[('actual_accepted_selector_patch',json.loads(b),d),('all_sweden_originals',j(S,'coordination/engineering/sweden-original-repair-20261017/source-stage-001/original-native-patch.json'),dict(commit=S)),('pending_sweden_selected',j('daad9f06','coordination/engineering/sweden-selected-delivery-20261017/composition-001/patch.json'),dict(commit='daad9f06d4ce85a90bb1a94142ae0a62a951ca11'))];out=[]
for label,v,pin in spec:
 overlaps=[]
 for row in v['rows']:
  rs=ours.get(row['y'],[]);ends=[r[1] for r in rs]
  for a,b,*_ in row['runs']:
   i=bisect.bisect_right(ends,a)
   while i<len(rs) and rs[i][0]<b:
    overlaps.append([row['y'],max(a,rs[i][0]),min(b,rs[i][1])]);i+=1
 assert not overlaps,label
 out.append(dict(role=label,pin=pin,cells=sum(b-a for r in v['rows'] for a,b,*_ in r['runs']),overlap_cells=0))
r=dict(head=H,original_cells=27555,comparisons=out);pathlib.Path('/workspace/shared/worldatlas-recovery/germany-independent-review/overlap-check.json').write_text(json.dumps(r,indent=2)+'\n');print([(r['role'],r['cells'],r['overlap_cells']) for r in out])
