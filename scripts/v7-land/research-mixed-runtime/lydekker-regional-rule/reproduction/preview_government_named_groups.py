"""Extend full source polygons by independently documented group witnesses."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'regional-lydekker-rule-work')
from regional_group_convention import apply_groups
R=Path.cwd();D=R/'regional-lydekker-rule-work'
def H(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=D/'current-selected170-direct-nearest-preview.json';assert H(p)=='5c20f5970465bfbbc7e61bc2a79c3197a05919e35aaba82a79e0afb0f09dbc9c';out=json.loads(p.read_bytes())
for k in ('proposals','review'):out[k]={int(r):v for r,v in out[k].items()}
s=R/'regional-fast-comparison-20261105/residual-source-feature-preview.json';assert H(s)=='2c59d23ef0fe52eee2d4e78e719a585257784926f8432ce4883243c196a4fbe3';v=json.loads(s.read_bytes())
a=R/'lydekker-regional-coverage-20261105/report.json';assert H(a)=='7a82beeab97bfe0874bff5c88b85210996e67b9ee889abdf129770c97b116133';totals={x['root']:x['cells_global'] for x in json.loads(a.read_bytes())['components']}
# Indonesian Ministry of Education research records Garat among Nanusa islands;
# Indonesian Geospatial Information Agency 2021 gazette identifies Kore at
# 07°50'51 S, 131°27'07.99 E in the Tanimbar regency. Kore also lies 606 m
# from a currently selected source group Tanimbar component; administrative
# association by itself is not a proof of physical archipelago membership.
rosters=[('nenusa-garat','1644151','https://repositori.kemendikdasmen.go.id/30252/1/STUDI%20KASUS%20MASYARAKAT%20PULAU%20MARORE%20KABUPATEN%20KEPULAUAN%20SANGIHE.pdf','printed pp.113-114: Garat listed among Nanusa islands'),('tanimbar-kore','1890696','https://sinar.big.go.id/assets/document/gazeter/gazeter_1643095453.pdf','2021 Gazette p.467: Kore at 07°50′51″S 131°27′07.99″E in Tanimbar regency; nearby selected Tanimbar source component')];windows=[]
for group,gid,url,evidence in rosters:
 hits=[x for x in v['point_hits'] if x['geonames_id']==gid];assert len(hits)==1 and len(hits[0]['containing_feature_ids'])==1;fid=hits[0]['containing_feature_ids'][0]; matches=[x for x in v['intersection'] if x['feature_id']==fid];assert len(matches)==1 and 'failure' not in matches[0];items=matches[0]['intersection']['per_feature_root_inside_cells'];assert len(items)==1;components={}
 for root,n in items[0].items():
  r=int(root);assert r in totals and totals[r]==n;components[r]={'total':n,'in_scope':n}
 windows.append({'group_id':group,'code':18,'components':components,'source':{'source_url':url,'evidence':evidence,'archived_corroboration':({'source_id':'detik-talaud-mangupun','version':'2019-598a4211a216','sha256':'598a4211a2166a66b7e699dbc05c8d323009f26968eb3a69aff0bc8b276ebe90'} if group=='nenusa-garat' else {'source_id':'indonesia-big-national-gazetteer','version':'2021-5ecdc47a0a59-official','sha256':'5ecdc47a0a59cad5ba7aa4f1f57c748334b3ea804f229841184aac914d24aa18'}),'geonames_id':gid,'osm_feature_id':fid,'feature_preview_sha256':H(s)}})
oldgroup={int(k):v for k,v in out.get('regional_group_proposals',{}).items()};oldstats=out['regional_group_diagnostics'];out=apply_groups(out,windows);out['regional_group_proposals']={**oldgroup,**out['regional_group_proposals']};out['regional_group_diagnostics']={**oldstats,**out['regional_group_diagnostics']};out['government_group_evidence']=[{'group_id':w['group_id'],'source':w['source'],'roots_current_generation_only':sorted(w['components'])} for w in windows];out['status']='provisional-government-named-feature-group-preview-not-selection';out['limitations'].append('Garat group name and Kore administrative association are documented in government publications; GeoNames-to-unnamed-OSM-polygon identification is interpreted. Tanimbar administration alone is not proof of physical group membership.')
dest=D/'current-selected170-combined-groups-preview.json';assert not dest.exists();dest.write_text(json.dumps(out,sort_keys=True,indent=2)+'\n');print(json.dumps(out['regional_group_diagnostics']),H(dest))
