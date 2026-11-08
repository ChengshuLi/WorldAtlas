"""Read-only whole-feature group preview, not a decision selection."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'regional-lydekker-rule-work')
from regional_group_convention import apply_groups
R=Path.cwd();D=R/'regional-lydekker-rule-work'
def H(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=D/'current-selected170-endpoint-groups-preview.json';assert H(p)=='aacfc57f15c3568f6d4f17f0a5612dc2e481b247052da90e4af6754700990439';out=json.loads(p.read_bytes())
for k in ('proposals','review'):out[k]={int(r):v for r,v in out[k].items()}
s=R/'regional-fast-comparison-20261105/residual-source-feature-preview.json';assert H(s)=='2c59d23ef0fe52eee2d4e78e719a585257784926f8432ce4883243c196a4fbe3';v=json.loads(s.read_bytes())
a=R/'lydekker-regional-coverage-20261105/report.json';assert H(a)=='7a82beeab97bfe0874bff5c88b85210996e67b9ee889abdf129770c97b116133';totals={x['root']:x['cells_global'] for x in json.loads(a.read_bytes())['components']}
# Source names are stated in NGA Pub.164 §§1.3 and 4.76. Exact point-to-
# polygon associations are interpreted; every complete source polygon is
# applied as a whole, including any unnamed roots it contains.
groups=[('nenusa',{'1643043','1642074','1636642'},'1.3'),('meatiy-miarang',{'1635266'},'4.76')];windows=[]
for group,ids,section in groups:
 hits=[x for x in v['point_hits'] if x['geonames_id'] in ids];assert {x['geonames_id'] for x in hits}==ids and all(len(x['containing_feature_ids'])==1 for x in hits)
 features={x['containing_feature_ids'][0] for x in hits}; components={}; attest=[]
 for item in v['intersection']:
  if item['feature_id'] not in features:continue
  assert 'failure' not in item and len(item['intersection']['per_feature_root_inside_cells'])==1
  inside=item['intersection']['per_feature_root_inside_cells'][0]
  for root,count in inside.items():
   r=int(root);assert r in totals and count==totals[r];components[r]={'total':totals[r],'in_scope':count}
  attest.append(item['feature_id'])
 assert set(attest)==features and components
 windows.append({'group_id':group,'code':18,'components':components,'source':{'source_id':'nga-sailing-directions-pub164-project-copy','source_version':'2009-f71a16ba2095-official','section':section,'source_sha256':'f71a16ba2095e200a51edfc4a7ea8c029f284f56380f99f58bd65f6272f9d903','geonames_ids':sorted(ids),'osm_feature_ids':sorted(features),'feature_preview_sha256':H(s)}})
oldgroup={int(k):v for k,v in out.get('regional_group_proposals',{}).items()};oldstats=out.get('regional_group_diagnostics',{})
out=apply_groups(out,windows);out['regional_group_proposals']={**oldgroup,**out['regional_group_proposals']};out['regional_group_diagnostics']={**oldstats,**out['regional_group_diagnostics']};out['status']='provisional-source-named-feature-group-preview-not-selection';out['limitations'].append('OSM polygons are unnamed: GeoNames point-to-polygon identity is interpreted, and a shared source lineage may exist. Feature selection here is a bounded preview, not an exhaustive group roster.')
dest=D/'current-selected170-source-groups-preview.json';assert not dest.exists();dest.write_text(json.dumps(out,sort_keys=True,indent=2)+'\n');print('stats',json.dumps(out['regional_group_diagnostics']),'sha',H(dest))
