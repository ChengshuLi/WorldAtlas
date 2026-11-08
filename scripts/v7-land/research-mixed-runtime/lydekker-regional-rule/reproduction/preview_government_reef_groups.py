"""Read-only official-name reef groups and direct nearest-anchor convention."""
import hashlib,importlib.util,json,sys
from pathlib import Path
R=Path.cwd();D=R/'regional-lydekker-rule-work';sys.path.insert(0,str(D))
from component_scan import scan,collect_runs,component_at
from regional_rule import Line
from regional_workflow import buffered_bounds
from regional_group_convention import apply_groups
from replay_adapter import resolve_with_mixed_replay
from satellite_geodesic import apply_satellites

def H(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def J(p):return json.loads(Path(p).read_bytes())
p=D/'current-selected170-combined-groups-preview.json';assert H(p)=='ca7de75cc5b6c075d6e855059b1382e72c8ecf53093c316eb5b0b21bb35dc136';out=J(p)
for k in ('proposals','review','competitor_targets','replayed_claims','satellites'):out[k]={int(r):v for r,v in out[k].items()}
oldgroups={int(r):v for r,v in out['regional_group_proposals'].items()};oldstats=out['regional_group_diagnostics'];oldsat=out['satellites'];oldnear={int(r):v for r,v in out['nearest_unanchored'].items()}
big=R/'tanimbar-tandula-research-20261105/big-readback.pdf';assert H(big)=='5ecdc47a0a59cad5ba7aa4f1f57c748334b3ea804f229841184aac914d24aa18'
source=R/'regional-fast-comparison-20261105/residual-unnamed-feature-preview.json';assert H(source)=='d904832f70d8e8da3492d7f165b64a37705d86f923c9d7d7a0e9674866d98821';v=J(source)
a=R/'lydekker-regional-coverage-20261105/report.json';assert H(a)=='7a82beeab97bfe0874bff5c88b85210996e67b9ee889abdf129770c97b116133';totals={z['root']:z['cells_global'] for z in J(a)['components']}
rows={'path':str(R/'fresh-components-output-20261104/rows.u32le'),'sha256':'4beda178bfc7beeb2d30cbdfa5901a48f9a41bb82c69e534d4c8cddfdb09aea7'};runs={'path':str(R/'fresh-components-output-20261104/runs.u32le'),'sha256':'18d7f36fa22c5728662cdd40487bf684108da030c074fec6d22ac378d0df0961'};grid=out['grid'];windows=[];newanchors={}
# BIG Gazette 2021 directly locates Meaterialam and Metutun; NGA Pub.164
# §§4.76–4.77 place these on the Meatiy and Luang reef groups respectively.
# Exact source coordinate selects a complete physical root, also independently
# checked against the whole source-polygon component intersection preview.
names=[('meaterialam',128+24/60+20.99/3600,-(8+11/60+26.99/3600),'4.76'),('metutun',128+35/60+13.99/3600,-(8+9/60+54/3600),'4.77')]
for name,lon,lat,section in names:
 r=component_at(rows,runs,grid,lon,lat);hits=[h for h in v['grid_center_hits'] if h['root']==r];assert len(hits)==1 and len(hits[0]['containing_feature_ids'])==1;fid=hits[0]['containing_feature_ids'][0];inter=[i for i in v['intersection'] if i['feature_id']==fid];assert len(inter)==1 and 'failure' not in inter[0]; inside=inter[0]['intersection']['per_feature_root_inside_cells'];assert len(inside)==1; components={}
 for root,n in inside[0].items():
  root=int(root);assert totals[root]==n;components[root]={'total':n,'in_scope':n}
 assert r in components
 spec={'group_id':name,'code':18,'components':components,'source':{'gazette_url':'https://sinar.big.go.id/assets/document/gazeter/gazeter_1643095453.pdf','gazette_record':name,'gazette_point_lon_lat':[lon,lat],'nga_section':section,'nga_source_sha256':'f71a16ba2095e200a51edfc4a7ea8c029f284f56380f99f58bd65f6272f9d903','osm_feature_id':fid,'feature_preview_sha256':H(source)}};windows.append(spec)
 newanchors[r]={'code':18,'source_id':'indonesia-big-national-gazetteer','source_feature_id':name,'source_version':'2021-5ecdc47a0a59-official','source_sha256':'5ecdc47a0a59cad5ba7aa4f1f57c748334b3ea804f229841184aac914d24aa18','main_island_evidence':'Official gazette point and NGA Pub.164 section '+section+' identify source-named reef island.'}
out=apply_groups(out,windows);out['regional_group_proposals']={**oldgroups,**out['regional_group_proposals']};out['regional_group_diagnostics']={**oldstats,**out['regional_group_diagnostics']};assert all(out['proposals'].get(r,{}).get('code')==18 for r in newanchors)
linefile=R/'boo-boundary-broader-20261105/boo-east-candidate.json';assert H(linefile)=='bb7a9c4621646c98d25c4cc4685346fbb6bc468db6015f2d7a3926780c27a02e';line=Line({'type':'LineString','coordinates':J(linefile)['coordinates']});bounds=out['regional_bounds'];print('Scanning full candidate frame',flush=True);region=scan(rows,runs,grid,bounds,line);buffer=scan(rows,runs,grid,buffered_bounds(bounds,5000.00001),line)
rec=D/'reconstructed-current-selected170.json';assert H(rec)=='1f4a21b9468b7434813648ae8dc6b8784d8b0858ab23af2f57c461ac5ef043cd';replay=J(rec);mp=R/'aegean-archive-containment-integrated-20261105/group-label-multipolygon-prototype/mixed_claims.py';assert H(mp)=='1800e87cc53f597ed4f6e58be41ba8b35f7370e2408f30b5856146c6e24264bc';sp=importlib.util.spec_from_file_location('mixed_reef',mp);mixed=importlib.util.module_from_spec(sp);sp.loader.exec_module(mixed);buf=resolve_with_mixed_replay(buffer,replay['compiled'],J(R/'shared-regional-replay-20261105/snapshot170.raw.json'),replay['reports'],set(replay['protected_roots']),mixed)
out['proposals'].update({r:v for r,v in buf['proposals'].items() if r not in region});out['competitor_targets']={r:c[0]['code'] for r,c in buf['replayed_claims'].items() if r not in buf['pending_source_claims']}
rootruns=collect_runs(rows,runs,grid,{r:v['total'] for r,v in buffer.items()});pairpath=R/'pr4-mixed-runtime-preserve-20261105/scripts/v7-land/research-mixed-runtime/stage2-geodesic-20261104';sys.path.insert(0,str(pairpath));from run_pair import run_pair
held={r for r in region if out['review'].get(r)=='outside_line_latitude'};print('Evaluating all',len(held),'held roots against independently named reef islands',flush=True)
result=apply_satellites(out,buffer,rootruns,newanchors,run_pair,width=grid['width'],north=grid['north'],max_satellite_cells=20,max_gap_m=5000,candidate_roots=held,allow_unanchored_nearest=True)
result['proposals']={r:p for r,p in result['proposals'].items() if r in region};result['review']={r:p for r,p in result['review'].items() if r in region};result['satellites']={**oldsat,**result['satellites']};result['nearest_unanchored']={**oldnear,**result['nearest_unanchored']};result['reef_source_anchors']=newanchors;result['status']='provisional-official-name-reef-group-preview-not-selection';result['limitations'].append('Official gazette point identity and NGA reef association support named components; exact source polygon association and 5 km nearby-islet grouping remain interpreted. No complete pending-group set was supplied.')
dest=D/'current-selected170-reef-groups-preview.json';assert not dest.exists();dest.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print('wrote',dest,'sha',H(dest),flush=True)
