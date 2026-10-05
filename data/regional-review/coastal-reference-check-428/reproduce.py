#!/usr/bin/env python3
"""Compare the eight #980 county geometries in exact retained Census vintages."""
import hashlib,json,subprocess,sys
from pathlib import Path
from shapely.geometry import shape
from shapely import make_valid
from shapely.ops import transform
from shapely.validation import explain_validity
from pyproj import Transformer
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/"scripts"))
from evidence.geometry import VERSION as SHARED_GEOMETRY_VERSION, transform_point
ROOT=Path(__file__).resolve().parent
BASELINE='5391a5a2cc5bc3386d30e8c816de3f9388e70d99'
IDS={
'13051':'gb:USA:ADM2:52423323B68249799438553','13127':'gb:USA:ADM2:52423323B35006791438696','13191':'gb:USA:ADM2:52423323B58673559392327','13039':'gb:USA:ADM2:52423323B71362647483761','13179':'gb:USA:ADM2:52423323B31615661575159','13249':'gb:USA:ADM2:52423323B40186233786127','13231':'gb:USA:ADM2:52423323B93853380479562','13273':'gb:USA:ADM2:52423323B62158301450735'}
NAMES={'13051':'Chatham','13127':'Glynn','13191':'McIntosh','13039':'Camden','13179':'Liberty','13249':'Schley','13231':'Pike','13273':'Terrell'}
PROJECT=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform
def load(path): return json.loads(Path(path).read_bytes())
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def fcmap(fc,key): return {str(f['properties'][key]):f for f in fc['features']}
def projected(g): return transform(PROJECT,g)
def iou(a,b):
 u=a.union(b).area
 return 1. if not u else a.intersection(b).area/u
root=Path.cwd();parent=root/'data/regional-review/regional-review-528e53393a4376b4/source'
fc18=fcmap(load(parent/'census-2018/georgia-kentucky-counties.geojson'),'GEOID');fc25=fcmap(load(parent/'census-2025/georgia-kentucky-counties.geojson'),'GEOID');fc26=fcmap(load(ROOT/'source/census-2026/eight-counties.geojson'),'GEOID')
world=json.loads(subprocess.check_output(['git','show',f'{BASELINE}:data/world-index.json'],cwd=root));atlas={}
for part in world['parts']:
 data=json.loads(subprocess.check_output(['git','show',f'{BASELINE}:data/{part}'],cwd=root))
 for f in data['features']:
  if f.get('properties',{}).get('id') in IDS.values(): atlas[f['properties']['id']]=f
if set(atlas)!=set(IDS.values()) or any(not set(IDS).issubset(m) for m in [fc18,fc25]) or set(fc26)!=set(IDS): raise SystemExit('Exact scoped roster missing or duplicated')
rows=[]
axis_control=transform_point(10,45,'EPSG:3857')
if abs(axis_control[0]-1113194.9079)>1 or abs(axis_control[1]-5621521.4862)>1: raise SystemExit('Shared helper longitude/latitude control failed')
for geoid,sid in IDS.items():
 feats={'atlas':atlas[sid],**{f'tiger_{year}':fc[geoid] for year,fc in [(2018,fc18),(2025,fc25),(2026,fc26)]}}
 ap=feats['atlas']['properties'];meta=ap.get('metadata',{})
 if ap.get('name')!=NAMES[geoid] or ap.get('parent_id')!='framework:province:georgia:99c5fb82481b': raise SystemExit(f'Atlas county name/Georgia parent mismatch: {sid}')
 if meta.get('source_id')!='gb:USA:ADM2' or meta.get('administrative_level')!='ADM2' or meta.get('source_role')!='Counties' or meta.get('reference_year')!='2018' or meta.get('original_id')!=sid.rsplit(':',1)[-1]: raise SystemExit(f'Atlas source identity/tier mismatch: {sid}')
 for layer,f in feats.items():
  if layer.startswith('tiger_'):
   p=f['properties']
   if p.get('STATE')!='13' or p.get('GEOID')!=geoid or p.get('BASENAME')!=NAMES[geoid] or p.get('LSADC')!='06': raise SystemExit(f'Census identity/tier mismatch: {layer}/{geoid}')
 geoms={k:shape(v['geometry']) for k,v in feats.items()}; validity={k:{'valid':g.is_valid,'reason':explain_validity(g)} for k,g in geoms.items()}
 repaired={k:(g if g.is_valid else make_valid(g)) for k,g in geoms.items()}
 pg={k:projected(g) for k,g in repaired.items()}
 row={'geoid':geoid,'subject_id':sid,'name':NAMES[geoid],'atlas_attributes':{'name':ap.get('name'),'parent_id':ap.get('parent_id'),'source_id':meta.get('source_id'),'source_role':meta.get('source_role'),'administrative_level':meta.get('administrative_level'),'reference_year':meta.get('reference_year'),'source_shape_id':meta.get('original_id')},'source_attributes':{k:{x:v['properties'].get(x) for x in ['GEOID','STATE','COUNTY','NAME','BASENAME','LSADC','FUNCSTAT','COUNTYNS','AREALAND','AREAWATER']} for k,v in feats.items() if k.startswith('tiger_')},'validity':validity,'components':{k:len(g.geoms) if g.geom_type=='MultiPolygon' else (1 if g.geom_type=='Polygon' else 0) for k,g in geoms.items()},'equal_area_area_km2':{k:round(v.area/1e6,3) for k,v in pg.items()},'atlas_2018_2026_difference_km2':{'atlas_minus_tiger_2026':round(pg['atlas'].difference(pg['tiger_2026']).area/1e6,3),'tiger_minus_atlas':round(pg['tiger_2026'].difference(pg['atlas']).area/1e6,3),'tiger_minus_atlas_as_share_of_census_areawater':round(pg['tiger_2026'].difference(pg['atlas']).area/feats['tiger_2026']['properties']['AREAWATER'],6)},'iou':{f'{a}_to_{b}':round(iou(pg[a],pg[b]),9) for a,b in [('atlas','tiger_2018'),('atlas','tiger_2025'),('atlas','tiger_2026'),('tiger_2018','tiger_2025'),('tiger_2025','tiger_2026')]},'interpretation':'IoU is a repeatable statistical geometry screen only; repaired geometries exist in memory only; neither validates legal lines or proves coastal completeness.'}
 rows.append(row)
method_id='census-eight-county-equal-area-screen'
coastal=['Chatham','Glynn','McIntosh','Camden','Liberty']
positive_values={r['name']:r['iou']['tiger_2025_to_tiger_2026'] for r in rows if r['name'] in coastal}
if set(positive_values)!=set(coastal) or any(v!=1.0 for v in positive_values.values()): raise SystemExit('Positive control failed: 2025/2026 coastal geometries must be identical')
positive={'method_id':method_id,'kind':'positive-control','outcome':'passed','description':'The five coastal Census 2025-to-2026 identical geometry comparisons return IoU 1.0.','observed_iou':positive_values}
wrong_axis=PROJECT(45,10);right_axis=PROJECT(10,45)
axis_delta=((wrong_axis[0]-right_axis[0])**2+(wrong_axis[1]-right_axis[1])**2)**0.5
if axis_delta<1_000_000: raise SystemExit('Negative control failed: swapped lon/lat was not detected')
negative={'method_id':method_id,'kind':'negative-control','outcome':'passed','description':'Deliberately swapped the known lon/lat control coordinates before EPSG:6933 transformation; the result must differ from correct order by more than 1,000,000 m.','correct_xy_m':[round(v,6) for v in right_axis],'swapped_xy_m':[round(v,6) for v in wrong_axis],'separation_m':round(axis_delta,3)}
(ROOT/'runs/positive-control.json').write_text(json.dumps(positive,indent=2)+'\n')
(ROOT/'runs/negative-control.json').write_text(json.dumps(negative,indent=2)+'\n')
out=ROOT/'runs/eight-county-comparison.json';out.write_text(json.dumps({'baseline':BASELINE,'projection':'EPSG:6933; always_xy; lon/lat source','shared_helper_version':SHARED_GEOMETRY_VERSION,'shared_helper_axis_control_EPSG3857_lon10_lat45_m':list(axis_control),'scope_count':len(rows),'source_hashes':{str(p.relative_to(root)):digest(p) for p in [parent/'census-2018/georgia-kentucky-counties.geojson',parent/'census-2025/georgia-kentucky-counties.geojson',ROOT/'source/census-2026/eight-counties.geojson']},'rows':rows},indent=2)+'\n')
print(json.dumps([{k:r[k] for k in ['geoid','name','validity','iou']} for r in rows],indent=2))
