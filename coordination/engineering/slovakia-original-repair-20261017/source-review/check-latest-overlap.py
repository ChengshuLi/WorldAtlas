import json,gzip,pathlib,subprocess,hashlib,bisect
R='/workspace/scratch/127991fc8b8e/worldatlas-primary';H='1330b938687e1c8255ae0e80bf4ad854e44c6d5e';P=pathlib.Path(__file__).parent;inputs=[]
def read(c,p):
 b=subprocess.check_output(['git','--no-lazy-fetch','-C',R,'show',c+':'+p]);inputs.append(dict(commit=c,path=p,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()));return json.loads(gzip.decompress(b) if p.endswith('.gz') else b)
rows=[]
for p in sorted((P/'original-intervals-001').glob('block-*.json.gz')):
 b=p.read_bytes();inputs.append(dict(path=p.name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()));rows.extend(json.loads(gzip.decompress(b)))
assert len(rows)==700 and sum(z-a for y,a,z,*_ in rows)==1811
keys={(y,x) for y,a,z,*_ in rows for x in range(a,z)};assert len(keys)==1811
selector=read(H,'data/ownership-selection.json');sidecar=read(H,selector['additive_release']['path']);pin=sidecar['logical_asset_map']['patch'];accepted=read(pin['commit'],pin['path']);assert inputs[-1]['bytes']==pin['bytes'] and inputs[-1]['sha256']==pin['sha256']
refs=[('actual_accepted_additive',accepted),('entire_Sweden_original',read('a1a8c3060a97cfc0648a7412c1662e19fde83f76','coordination/engineering/sweden-original-repair-20261017/source-stage-001/original-native-patch.json')),('entire_Germany_original',read('9ebe37b375b46b06f2eed17302c746582e80a2aa','coordination/engineering/germany-original-repair-20261017/source-stage-001/original-native-patch.json')),('entire_Spain_original',read('c1a507348cd1ade4167f548a1f9fe384da8fe7c2','coordination/engineering/spain-original-repair-20261017/source-stage-001/original-native-patch.json')),('entire_Poland_original',read('d6017783b1154a59386ea8701b1a729749806741','coordination/engineering/poland-original-repair-20261017/source-stage-001/original-native-patch.json')),('entire_Czechia_original',read('cb333f83bd9996cc1f685a36c87872b8aea21a16','coordination/engineering/czechia-original-repair-20261017/source-stage-001/original-native-patch.json'))];results=[]
for name,p in refs:
 by={r['y']:r['runs'] for r in p['rows']};starts={y:[r[0] for r in runs] for y,runs in by.items()};over=[]
 for y,x in keys:
  rr=by.get(y,[]);i=bisect.bisect_right(starts.get(y,[]),x)-1
  if i>=0 and x<rr[i][1]:over.append([y,x])
 results.append(dict(reference=name,cells=sum(z-a for r in p['rows'] for a,z,o in r['runs']),overlap_cells=len(over),overlap_keys=sorted(over)));assert not over
result=dict(kind='Slovakia-complete-original-spatial-overlap-screen',accepted_main=H,original_cells=1811,original_intervals=700,original_owners=len({oo[0] for y,a,z,oo,*_ in rows}),comparisons=results,inputs=inputs,limitations=['Spatial keys are compared irrespective of owner; complete pending originals conservatively cover their proposed supported subsets.','This does not replace genuine native-base owner-zero or final selected-output conservation.','Slovakia remains unclaimed and outside active denominators.']);(P/'latest-original-overlap-screen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['original_cells','original_intervals','original_owners','comparisons']}))
