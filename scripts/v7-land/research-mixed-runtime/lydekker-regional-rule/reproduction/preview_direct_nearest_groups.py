"""Broad direct nearest-anchored-island sensitivity preview; no map build."""
import hashlib,importlib.util,json,sys
from pathlib import Path
R=Path.cwd();D=R/'regional-lydekker-rule-work';sys.path.insert(0,str(D))
from component_scan import scan,collect_runs
from regional_rule import Line
from regional_workflow import buffered_bounds
from replay_adapter import resolve_with_mixed_replay
from satellite_geodesic import apply_satellites

def H(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def J(p):return json.loads(Path(p).read_bytes())
p=D/'current-selected170-source-groups-preview.json';assert H(p)=='3ad592e67477fe24a7d35f90d3ee3c4490069b519f7af3b6f6e08d0e89ce2072';out=J(p)
for k in ('proposals','review','source_anchors','replayed_claims','competitor_targets'):out[k]={int(r):v for r,v in out[k].items()}
rec=D/'reconstructed-current-selected170.json';assert H(rec)=='1f4a21b9468b7434813648ae8dc6b8784d8b0858ab23af2f57c461ac5ef043cd';replay=J(rec);snap=J(R/'shared-regional-replay-20261105/snapshot170.raw.json')
mp=R/'aegean-archive-containment-integrated-20261105/group-label-multipolygon-prototype/mixed_claims.py';assert H(mp)=='1800e87cc53f597ed4f6e58be41ba8b35f7370e2408f30b5856146c6e24264bc';sp=importlib.util.spec_from_file_location('mixed_direct_preview',mp);mixed=importlib.util.module_from_spec(sp);sp.loader.exec_module(mixed)
linefile=R/'boo-boundary-broader-20261105/boo-east-candidate.json';assert H(linefile)=='bb7a9c4621646c98d25c4cc4685346fbb6bc468db6015f2d7a3926780c27a02e';line=Line({'type':'LineString','coordinates':J(linefile)['coordinates']})
rows={'path':str(R/'fresh-components-output-20261104/rows.u32le'),'sha256':'4beda178bfc7beeb2d30cbdfa5901a48f9a41bb82c69e534d4c8cddfdb09aea7'};runs={'path':str(R/'fresh-components-output-20261104/runs.u32le'),'sha256':'18d7f36fa22c5728662cdd40487bf684108da030c074fec6d22ac378d0df0961'};grid=out['grid'];bounds=out['regional_bounds']
print('Scanning region and competitors',flush=True);region=scan(rows,runs,grid,bounds,line);buffer=scan(rows,runs,grid,buffered_bounds(bounds,5000.00001),line)
buf=resolve_with_mixed_replay(buffer,replay['compiled'],snap,replay['reports'],set(replay['protected_roots']),mixed)
out['proposals'].update({r:v for r,v in buf['proposals'].items() if r not in region});out['competitor_targets']={r:c[0]['code'] for r,c in buf['replayed_claims'].items() if r not in buf['pending_source_claims']}
anchors=out['source_anchors'];preview=R/'regional-fast-comparison-20261105/residual-source-feature-preview.json';assert H(preview)=='2c59d23ef0fe52eee2d4e78e719a585257784926f8432ce4883243c196a4fbe3';hits=J(preview)['point_hits'];names={'1643043':'NGA Pub.164 §1.3 Intata','1642074':'NGA Pub.164 §1.3 Kakolotan','1636642':'NGA Pub.164 §1.3 Malo','1635266':'NGA Pub.164 §4.76 Meatiy Miarang'}
for hit in hits:
 if hit['geonames_id'] not in names:continue
 r=hit['root'];assert out['proposals'].get(r,{}).get('code')==18
 anchors[r]={'code':18,'source_id':'geonames-country-id','source_feature_id':hit['geonames_id'],'source_version':'2026-11-05-2a1966f22f1e','source_sha256':'2a1966f22f1eda5b099270b8382b93fe347a81b3f858b891349da7d4c9fe3718','main_island_evidence':names[hit['geonames_id']]+'; complete source polygon and point link verified in bounded preview'}
assert all(r in buffer for r in anchors)
rootruns=collect_runs(rows,runs,grid,{r:v['total'] for r,v in buffer.items()});pairpath=R/'pr4-mixed-runtime-preserve-20261105/scripts/v7-land/research-mixed-runtime/stage2-geodesic-20261104';sys.path.insert(0,str(pairpath));from run_pair import run_pair
print('Evaluating direct named-island distances',flush=True)
result=apply_satellites(out,buffer,rootruns,anchors,run_pair,width=grid['width'],north=grid['north'],max_satellite_cells=20,max_gap_m=5000,candidate_roots=set(region),allow_unanchored_nearest=True)
result['proposals']={r:p for r,p in result['proposals'].items() if r in region};result['review']={r:p for r,p in result['review'].items() if r in region};result['status']='provisional-direct-nearest-anchor-group-preview-not-selection';result['satellite_policy']=dict(result['satellite_policy'],unknown_nearer_land='recorded; does not block a direct named anchor within 5 km; no inferred anchor chaining');result['limitations'].append('Direct proximity to a named island within 5 km is an operational geographic convention, not proof of group membership; nearer unknown land is recorded, and known conflicting targets block the proposal.')
dest=D/'current-selected170-direct-nearest-preview.json';assert not dest.exists();dest.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print('wrote',dest,'sha',H(dest),flush=True)
