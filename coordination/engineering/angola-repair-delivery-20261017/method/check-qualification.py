import json,pathlib,subprocess,collections,gzip,hashlib,sys
import numpy as np
import shapely
from shapely.geometry import shape
assert len(sys.argv)==3, 'Supply read-only repository and fresh output file'
W=pathlib.Path(sys.argv[1]).absolute();out=pathlib.Path(sys.argv[2]).absolute()
assert W.is_dir() and out.parent.is_dir() and not out.exists()
assert all(not p.is_symlink() for root in (W,out) for p in (root,*root.parents))
P=W/'coordination/engineering/angola-repair-delivery-20261017';H='579c2850ab0eb4bbcc1a6f41f8eb0563791208fe';pins=[]
def raw(p):
 b=subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'show',H+':'+p]);pins.append({'path':p,'commit':H,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()});return b
original=[r for f in sorted((P/'frozen-queue').glob('block-*.gz')) for r in json.loads(gzip.decompress(f.read_bytes()))];patch=json.load(open(P/'source-stage/native-patch.json'));diag=json.load(open(P/'native-diagnostic-001/native-diagnostic.json'));stages=json.load(open(P/'source-stage/original-stage-inputs.json'));physical=json.load(open(P/'physical-001/whole-target-support.json'));assessment=json.load(open(P/'source-stage/source-scope-assessment.json'))
def cells(rows,kind=False):
 d={}
 for r in rows:
  for a,z,o,*rest in r['runs']:
   for x in range(a,z):
    k=(r['y'],x);assert k not in d;d[k]=(o,rest[0]) if kind else o
 return d
request=cells(patch['rows']);support=cells(diag['supported_rows']);decisions=cells(diag['decision_rows'],True);assert request==support;assert {k:(v,'assigned_cells') for k,v in request.items()}==decisions;assert not diag['held_rows'] and diag['held_cells']==0;assert len(request)==170526
frozen={}
for y,a,z,owners,_,c in original:
 assert c in ('land','inland-water') and len(owners)==1
 for x in range(a,z):assert (y,x) not in frozen;frozen[(y,x)]=owners[0]
assert frozen==request;assert {s['target'] for s in stages}=={x['target'] for x in physical['results']};assert assessment['complete_source_feature_count']==241 and sum(x['original_bytes'] for x in assessment['complete_sources'])==3618885
sel=json.loads(raw('data/ownership-selection.json'));m=json.loads(raw(sel['manifest_path']));latpin=m['native_latitudes'];b=subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'show',latpin['commit']+':'+latpin['path']]);assert hashlib.sha256(b).hexdigest()==latpin['sha256'];lat=np.frombuffer(gzip.decompress(b),dtype='<f8');keys=sorted(request);points=shapely.points([((x+.5)/262166*360-180,float(lat[y])) for y,x in keys]);ids={x['id']:x['pixelIndex'] for x in assessment['target_checks']};own=np.array([request[k] for k in keys]);whole=[]
for r in physical['results']:
 for issue in r['issues']:
  g=shape(issue['geometry']);hits=np.flatnonzero(shapely.covers(g,points));target_hits=[int(i) for i in hits if own[i]==ids[r['target']]];whole.append({'target':r['target'],'reason':issue['reason'],'geometry_type':g.geom_type,'area_square_degrees':g.area,'any_requested_centres':len(hits),'target_requested_centres':len(target_hits),'interpretation':'Original whole-feature physical issue retained without deletion or reclassification. Exact requested-centre native diagnostic independently reports all qualified.'})
assert not any(r['target_requested_centres'] for r in whole)
historical=[]
for issue,path in [(1268,'research/geography/gap-source-namibia-angola-20261006/inputs/original-components.geojson'),(1243,'research/geography/gap-source-angola-drc-shared-seams-20261006/inputs/component-features.geojson'),(1423,'coordination/engineering/angola-original-envelope-20261007/vintages/final-focused-one/original-components.geojson')]:
 j=json.loads(raw(path));found=set();rows=[]
 for f in j['features']:
  g=shape(f['geometry']);hits=np.flatnonzero(shapely.covers(g,points));found.update(int(i) for i in hits);rows.append({'id':f.get('id',f['properties'].get('id')),'requested_centres':len(hits),'owners':dict(sorted(collections.Counter(int(own[i]) for i in hits).items())),'properties':f['properties']})
 historical.append({'issue':issue,'source':pins[-1],'features':len(rows),'unique_requested_centres':len(found),'rows':rows,'interpretation':'Historical geometry overlap is a scope intersection, not a settled physical or current international boundary result. Original findings remain unchanged.'})
report={'kind':'complete-original-angola-qualification-accounting','baseline_commit':H,'original_cells':len(frozen),'original_segments':len(original),'requested_cells':len(request),'supported_cells':len(support),'held_cells':diag['held_cells'],'requested_per_owner':dict(sorted(collections.Counter(request.values()).items())),'full_source_features':241,'full_source_decoded_bytes':3618885,'original_physical_issues':whole,'historical_intersections':historical,'historical_input_pins':pins,'limits':['Exact 2018 source-relative municipal qualification only. No current-law equivalence or authoritative international boundary, physical-status or whole-feature semantic approval.','No source-conflict or physical-interpretation companion cell is proposed.','Original #1046/#896 source-date and Cabinda successors, #1243 seam/water and #1268/#1397 Namibia-water questions remain unresolved.','Current owner-zero and final emitted-map consumer verification remain separate gates.']}
assert out.parent.is_dir() and not out.exists() and all(not p.is_symlink() for p in (out,*out.parents))
with out.open('x') as f:json.dump(report,f,sort_keys=True,separators=(',',':'));f.write('\n')
print(json.dumps({'requested':len(request),'supported':len(support),'physical_issues':len(whole),'candidate_issue_hits':sum(x['target_requested_centres'] for x in whole),'historical':[{k:x[k] for k in ['issue','features','unique_requested_centres']} for x in historical]}))
