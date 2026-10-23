import json, gzip, hashlib, subprocess, collections
from pathlib import Path
from shapely.geometry import shape, Point
import shapely
ROOT=Path('/Users/chengshuli/Documents/Codex/2026-10-20/task')
HERE=Path(__file__).resolve().parent
SCOPE=HERE.parent
ob=json.loads((ROOT/'inventory/bdi-selected-owner-observation.json').read_text())
join=json.loads((ROOT/'inventory/bdi-source-property-identity-join.json').read_text())
pins=json.loads((ROOT/'inventory/bdi-exact-input-acquisition.json').read_text())['items']
physical=json.loads((SCOPE/'physical-001/whole-target-support.json').read_text())
contacts=join['candidate_contacts']; target_by_owner={r['owner_indices'][0]:r['source_id'] for r in contacts if r['family_index']==20}
index_by_id={r['source_id']:r['source_index'] for r in contacts}
products=[];validity=[]
for pin in pins:
 raw=subprocess.check_output(['git','--no-lazy-fetch','cat-file','blob',pin['blob']]);assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256']
 decoded=gzip.decompress(raw);assert hashlib.sha256(decoded).hexdigest()==pin['decoded_sha256']
 product=json.loads(decoded)
 for f in product['features']:
  props=f['properties'];ident='gb:'+props['shapeGroup']+':'+props['shapeType']+':'+props['shapeID'];g=shape(f['geometry']);products.append((ident,g));validity.append({'id':ident,'valid':bool(g.is_valid)})
assert all(v['valid'] for v in validity), 'Invalid source geometry; no implicit repair allowed'
phys={r['target']:r for r in physical['results']}
rows=[]; original={}
for block in ob['original_intervals']:
 for y,start,end,owners,sources,kind in block['rows']:
  assert len(owners)==1
  for x in range(start,end):
   assert (x,y) not in original
   original[x,y]=(owners[0],sources,kind)
assert len(original)==len(ob['keys'])==583
for k in ob['keys']:
 x,y=k['x'],k['y'];owner,stored,kind=original[x,y];target=target_by_owner[owner]
 # Literal native-grid center formula, same 262166-column grid as the retained observation.
 lon=(360*x+180-180*262166)/262166; point=Point(lon,k['latitude'])
 hit_ids=[ident for ident,g in products if g.covers(point)]
 actual_indices=sorted(index_by_id[i] for i in hit_ids if i in index_by_id)
 noncontact_hits=[i for i in hit_ids if i not in index_by_id]
 p=phys[target];expected='mapped_land_support' if kind=='land' else 'mapped_inland_water_support'
 issues=[i['reason'] for i in p['issues'] if 'geometry' in i and shape(i['geometry']).covers(point)]
 rows.append({'x':x,'y':y,'latitude':k['latitude'],'longitude':lon,'owner':owner,'target':target,'class':kind,'stored_source_indices':stored,'actual_source_indices':actual_indices,'unlisted_contact_hits':noncontact_hits,'source_ids':hit_ids,'direct_target_hit':target in hit_ids,'foreign_source_ids':[i for i in hit_ids if not i.startswith('gb:BDI:')],'physical_expected_class_covered':bool(shape(p['support'][expected]).covers(point)),'adverse_physical_reasons':issues})
report={'kind':'BDI-original-source-and-physical-native-center-comparison','runtime':{'shapely':shapely.__version__,'geos':shapely.geos_version_string},'source_pins':pins,'observation_commit':ob['commit'],'observation_query_sha256':ob['query_sha256'],'physical_support_sha256':hashlib.sha256((SCOPE/'physical-001/whole-target-support.json').read_bytes()).hexdigest(),'complete_source_feature_count':len(products),'source_validity':validity,'counts':{'original_keys':len(rows),'classes':dict(collections.Counter(r['class'] for r in rows)),'direct_target_hit':sum(r['direct_target_hit'] for r in rows),'source_roster_mismatch':sum(r['stored_source_indices']!=r['actual_source_indices'] or bool(r['unlisted_contact_hits']) for r in rows),'foreign_contact_keys':sum(bool(r['foreign_source_ids']) for r in rows),'expected_physical_class_covered':sum(r['physical_expected_class_covered'] for r in rows),'adverse_physical_keys':sum(bool(r['adverse_physical_reasons']) for r in rows)},'rows':rows,'limits':['Bounded comparison of original 583 native centers with four complete retained source families and genuine whole-target physical outputs; no new selected-owner observation.','Same-target source membership, physical support and absent local conflicts do not establish temporal/administrative applicability or complete competitor qualification.','Whole-target adverse geometries and all original water keys remain preserved.','Longitude formula applied here; this analysis did not execute native-grid.js. Latitude values came from the unchanged retained observation.']}
out=HERE/'bdi-source-physical-native-center-comparison.json'
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(report['counts'],indent=2))
