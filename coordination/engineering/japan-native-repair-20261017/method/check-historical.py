"""Bound exact original cells to preserved Japan historical source questions.
Usage: python check-historical.py READ_ONLY_REPO STAGE_COMMIT FRESH_OUTPUT
"""
import collections,gzip,hashlib,json,os,pathlib,subprocess,sys
import numpy as np,shapely
from shapely.geometry import shape
W=pathlib.Path(sys.argv[1]).absolute();H=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();assert len(H)==40 and O.parent.is_dir() and not O.exists();assert all(not p.is_symlink() for p in (O,*O.parents));P='coordination/engineering/japan-native-repair-20261017/';OLD='research/geography/japan-nine-gap-family-source-fitness-20261007/';inputs=[]
env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'}
def read(p):
 b=subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'show',H+':'+p],env=env);assert len(b)<=32*1024*1024;inputs.append({'path':p,'commit':H,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()});return b
js=lambda p:json.loads(read(p))
def unique(rows,key,n):
 assert len(rows)==n and len({r[key] for r in rows})==n;return {r[key]:r for r in rows}
a=js(P+'source-stage/source-scope-assessment.json');scope=js(OLD+'inputs/immutable-scope-and-inputs.json');overlay=js(OLD+'results/source-overlays.json');physical=js(OLD+'inputs/existing-physical-row-scope.json')
candidates=unique(scope['full_candidate_features'],'id',28);routes=unique(scope['routing_rows'],'component',28);families=unique(scope['families_full_records'],'id',9) if 'id' in scope['families_full_records'][0] else unique(scope['families_full_records'],'family',9)
assert set(routes)==set(candidates);print('physical keys',list(physical),'source summary first',str(overlay['source_summaries'][0])[:350],flush=True)
# Independent raw uniqueness checks do not adopt #1633's dictionary-collapse behavior.
assert len(physical['selected_whole_rows'])==28 and len({r['component_id'] for r in physical['selected_whole_rows']})==28
summaries=overlay['source_summaries'];assert len(summaries)==3
summary_key=next(k for k in ['source_product'] if k in summaries[0]);assert len({r[summary_key] for r in summaries})==3
full=js(OLD+'sources/geoboundaries/full-product.geojson');simplified=json.loads(gzip.decompress(read(OLD+'sources/geoboundaries/simplified-product.geojson.gz')));ff=unique(full['features'],'id',1742) if 'id' in full['features'][0] else {f['properties']['shapeID']:f for f in full['features']};sf={f['properties']['shapeID']:f for f in simplified['features']};assert len(ff)==len(sf)==1742 and len(full['features'])==len(simplified['features'])==1742 and set(ff)==set(sf)
sel=js('data/ownership-selection.json');native=js(sel['manifest_path']);lp=native['native_latitudes'];lb=subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'show',lp['commit']+':'+lp['path']],env=env);assert hashlib.sha256(lb).hexdigest()==lp['sha256'];lat=np.frombuffer(gzip.decompress(lb),dtype='<f8');byowner={r['pixelIndex']:r for r in a['target_checks']};rows=[]
for old in a['prior_candidate_overlap']:
 if not old['candidate_cells']:continue
 cells=old['native_cells'];pts=shapely.points([[(x+.5)/262166*360-180,lat[y]] for x,y,o in cells]);full_hits=[[] for _ in cells];simplified_hits=[[] for _ in cells]
 for shapeid,f in ff.items():
  for i in np.flatnonzero(shapely.covers(shape(f['geometry']),pts)):full_hits[i].append('gb:JPN:ADM2:'+shapeid)
 for shapeid,f in sf.items():
  for i in np.flatnonzero(shapely.covers(shape(f['geometry']),pts)):simplified_hits[i].append('gb:JPN:ADM2:'+shapeid)
 for i,(x,y,o) in enumerate(cells):assert set(simplified_hits[i]).intersection(byowner[o]['source_atoms'])
 rows.append({'component':old['component'],'original_whole_candidate_disposition':routes[old['component']]['next_prerequisite'],'original_whole_candidate_physical_status':routes[old['component']]['physical_status'],'original_whole_candidate_authority':routes[old['component']]['physical_authority'],'cells':[{'x':x,'y':y,'owner':o,'target_id':byowner[o]['id'],'full_original_source_hits':full_hits[i],'consumed_simplified_source_hits':simplified_hits[i]} for i,(x,y,o) in enumerate(cells)],'whole_candidate_unknown_preserved':True})
assert sum(len(r['cells']) for r in rows)==9
result={'original_repair_cells':106333,'whole_historical_candidates':28,'whole_historical_families':9,'whole_historical_contacts':21,'raw_reference_cardinalities':{'routing_rows':28,'selected_whole_rows':28,'families_full_records':9,'source_summaries':3},'raw_reference_uniqueness_checked':True,'overlap_cells':9,'overlap_candidates':3,'overlap':rows,'inputs':inputs,'limits':['No MLIT archive restoration, GSI retrieval, new legal/physical classification or 2017-effective geometry claim.','The full original and exact consumed simplified source point tests here are a finite comparison on the nine overlapping repair centres, not a whole-candidate source approval.','All original whole-candidate unknowns remain unchanged; later native qualification must establish individual support for these exact cells.','#1633 remains open for its actual report-validator defect. Independent raw uniqueness checks here do not fix or approve that validator.']}
b=(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n').encode();assert len(b)<=32*1024*1024;assert not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
with (O/'historical-applicability.json').open('xb') as f:f.write(b)
with (O/'preparation.json').open('x') as f:json.dump({'complete':True,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()},f);f.write('\n')
print(json.dumps({'complete':True,'overlap_cells':9,'overlap_candidates':3,'full_simplified_point_differences':sum(c['full_original_source_hits']!=c['consumed_simplified_source_hits'] for r in rows for c in r['cells'])}))
