#!/usr/bin/env python3
"""Rebuild the exact issue 492 assessment from pinned current data and retained sources."""
import gzip,hashlib,json,pathlib,unicodedata
HERE=pathlib.Path(__file__).resolve().parent; ROOT=HERE.parents[2]
scope=json.loads((HERE/'scope.json').read_text()); ids=set(scope['member_location_ids'])
hier={x['id']:x for x in json.loads((ROOT/'data/hierarchy.json').read_text())}
index=json.loads((ROOT/'data/world-index.json').read_text()); features={}; allprops={}
for fn in index['parts']:
 for f in json.loads((ROOT/'data'/fn).read_text())['features']:
  p=f['properties']; allprops[p['id']]=p
  if p['id'] in ids: features[p['id']]=f
if ids!=set(features):raise SystemExit(f'scope feature mismatch: missing {ids-set(features)}')
sourcepath=HERE/'sources/geoboundaries-COL-ADM2-2020.geojson.gz'
raw=gzip.decompress(sourcepath.read_bytes()); source_doc=json.loads(raw)
meta=json.loads((HERE/'sources/geoboundaries-COL-ADM2-metadata.json').read_text())
if hashlib.sha256(raw).hexdigest()!='fe715854fc3383d2fd39e8692f3df0c60bd12208cb2cd36ef1ec2220ea8972fe':raise SystemExit('ADM2 source hash mismatch')
if len(source_doc['features'])!=1122 or len(source_doc['features'])!=int(meta['admUnitCount']):raise SystemExit('ADM2 source feature count mismatch')
byid={f['properties']['shapeID']:f for f in source_doc['features']}
if len(byid)!=1122:raise SystemExit('upstream shape IDs are not unique')
# Parent candidate crosswalk is for hierarchy continuity only; its OSM source is not official DANE.
adm1path=HERE/'sources/geoboundaries-COL-ADM1-2017.geojson.gz'; adm1raw=gzip.decompress(adm1path.read_bytes()); adm1=json.loads(adm1raw)
adm1meta=json.loads((HERE/'sources/geoboundaries-COL-ADM1-metadata.json').read_text())
if len(adm1['features'])!=33 or len(adm1['features'])!=int(adm1meta['admUnitCount']):raise SystemExit('ADM1 parent source count mismatch')
parent_source={f['properties']['shapeName']:f for f in adm1['features']}
def ring_area(r):
 area=0.0
 for i,(lon,lat) in enumerate(r):
  lon2,lat2=r[(i+1)%len(r)]
  area+=__import__('math').radians(lon2-lon)*(2+__import__('math').sin(__import__('math').radians(lat))+__import__('math').sin(__import__('math').radians(lat2)))
 return abs(area)*(6371.0088**2)/2

def geom(g):
 c=g['coordinates']; ps=[c] if g['type']=='Polygon' else c
 pts=[pt for poly in ps for ring in poly for pt in ring]
 areas=[max(0,ring_area(poly[0])-sum(ring_area(h) for h in poly[1:])) for poly in ps]
 return {'type':g['type'],'components':len(ps),'rings':sum(len(poly) for poly in ps),'interior_rings':sum(max(0,len(poly)-1) for poly in ps),'vertices':sum(len(r) for poly in ps for r in poly),'bbox':[min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)],'spherical_area_km2_screen_only':round(sum(areas),2)}
def chain(f):
 out=[]; pid=f['properties'].get('parent_id'); seen=set()
 while pid and pid not in seen:
  seen.add(pid); p=allprops.get(pid) or hier.get(pid)
  if not p:out.append({'id':pid,'missing':True});break
  out.append({'id':pid,'name':p.get('name'),'level':p.get('level'),'parent_id':p.get('parent_id'),'metadata':p.get('metadata',{})})
  pid=p.get('parent_id')
 return out
def norm(s):
 return ''.join(c for c in unicodedata.normalize('NFKD',str(s or '')).casefold() if not unicodedata.combining(c) and c.isalnum())
locs=[]; parent_counts={}
for id in sorted(ids):
 f=features[id];p=f['properties'];m=p['metadata']; sid=m['original_id']; sf=byid.get(sid)
 if sf is None:raise SystemExit(f'original shape id missing: {id}/{sid}')
 parents=chain(f); province=next((q for q in parents if q.get('level')=='province'),None)
 if not province:raise SystemExit(f'no province parent: {id}')
 parent_counts[province['id']]=parent_counts.get(province['id'],0)+1
 parent_name=province['name']; dep=[x for x in adm1['features'] if norm(x['properties']['shapeName'])==norm(parent_name)]; parent_area=geom(dep[0]['geometry'])['spherical_area_km2_screen_only'] if len(dep)==1 else None
 locs.append({'location_id':id,'name':p['name'],'full_parent_chain':parents,'province_candidate_crosswalk':{'atlas_parent':parent_name,'atlas_parent_source':province.get('metadata',{}).get('source'),'osm_2017_department_source_candidate_count':len(dep),'osm_2017_department_source_candidate_id':dep[0]['properties']['shapeID'] if len(dep)==1 else None,'official_DANE_2024_parent_row_crosswalk':'not performed; official service item found but source rows unavailable','interpretation':'OSM-derived ADM1 candidate supports name/identity continuity only; it is not an independent official DANE crosswalk.'},'source_identity':{'source_id':m.get('source_id'),'original_id':sid,'geoBoundaries_shape_id':sf['properties']['shapeID'],'shape_name':sf['properties']['shapeName'],'shape_type':sf['properties']['shapeType'],'name_exact':p['name']==sf['properties']['shapeName'],'parent_disambiguated':True,'source_country':'COL','source_vintage':meta['boundaryYear'],'license':meta['boundaryLicense']},'source_geometry':geom(sf['geometry']),'current_atlas_geometry':geom(f['geometry']),'province_physical_scale_screen':{'osm_department_reference_area_km2':parent_area,'source_location_share_of_department_area':round(geom(sf['geometry'])['spherical_area_km2_screen_only']/parent_area,5) if parent_area else None,'warning':'Approximate spherical area from OSM-derived 2017 department and 2020 DANE-declared municipality polygons; not an official DANE area and not a tier quota.'},'settlement_review':'unresolved: DANE Centros Poblados DIVIPOLA 2013I public item metadata was retained, but source point rows and license were not obtainable; it cannot establish current settlement completeness. DANE DIVIPOLA MGN 2024 item is a municipality/source candidate, but its rows were also inaccessible.','disconnected_land_review':'unresolved: source and current connected-component/ring counts are recorded; no complete official island, enclave, hydrography, or physical-territory register was reconciled.','decision':'insufficient_evidence','unresolved':'DANE 2024 official municipality/department rows and reuse terms; current named settlement inventory; physical land/island/hydrography completeness; source-to-current boundary precision/topology and neighbor-edge comparison. Administrative identity is crosswalked by exact DANE-declared source shape ID, not by name alone.'})
province_records=[]
for item in scope['province_scopes']:
 pid=item['id']; p=allprops.get(pid) or hier.get(pid); name=item['name']; cand=[x for x in adm1['features'] if norm(x['properties']['shapeName'])==norm(name)]
 province_records.append({'id':pid,'name':name,'parent_area':p.get('parent_id') if p else None,'issue_full_province_count':item.get('full_province_locations'),'issue_assigned_province_count':item.get('owned_member_location_count'), 'assigned_in_scope':parent_counts.get(pid,0),'current_declared_role':(p or {}).get('metadata',{}).get('basis'),'current_source':(p or {}).get('metadata',{}).get('source'),'osm_2017_department_source_candidate_count':len(cand),'osm_2017_department_area_km2_screen_only':geom(cand[0]['geometry'])['spherical_area_km2_screen_only'] if len(cand)==1 else None,'dane_2024_mgn_official_row_crosswalk':'not performed; item metadata retained, service rows inaccessible','decision':'insufficient_evidence','unresolved':'Confirm DANE 2024 department role and row identity from authoritative service data; assess full footprint, all sibling memberships, relative scale/purpose and neighbors.'})
assessment={'issue':492,'date':'2026-10-03','scope':{'member_count':len(ids),'ids_sha256':scope['member_location_ids_sha256'],'area_scopes':scope['area_scopes'],'source_id':'gb:COL:ADM2','source_counts':{'in_scope':len(locs),'full_source':len(source_doc['features'])}},'release_pins':scope['release'],'sources_registry':'sources.json','counts':{'assessed':len(locs),'source_ID_matches':sum(x['source_identity']['geoBoundaries_shape_id']==x['source_identity']['original_id'] for x in locs),'exact_source_name_matches':sum(x['source_identity']['name_exact'] for x in locs),'justified':0,'correction_needed':0,'insufficient_evidence':len(locs)},'scale_screen':{'method':'Approximate spherical-area calculation over source rings, checked against matched OSM/Wambacher 2017 department polygons only as relative scale context.','per_province':{p['name']:{'assigned_locations':sum(1 for x in locs if any(a.get('name')==p['name'] and a.get('level')=='province' for a in x['full_parent_chain'])),'osm_department_area_km2_screen_only':p['osm_2017_department_area_km2_screen_only'],'largest_location_department_share':max((x['province_physical_scale_screen']['source_location_share_of_department_area'] or 0 for x in locs if any(a.get('name')==p['name'] and a.get('level')=='province' for a in x['full_parent_chain'])),default=0)} for p in province_records}},'source_review':{'actual_source_role':'Pinned ADM2 metadata names DANE as source, sets boundary year 2020, source update 2023-01-19, CC BY 4.0, declares 1,122 units; feature shapes are all marked shapeType ADM2 and all 194 assigned shape IDs match uniquely. Metadata canonical field is empty. DANE DIVIPOLA/MGN 2024 official public item identifies an updated source family but service rows are inaccessible and not crosswalked. ADM2 code alone is not used as semantic proof.','assigned_names':'All 194 Atlas names exactly match their pinned source shape names. Valparaíso, La Unión, and San Pedro each occur twice; exact source IDs and province chain are required for disambiguation.','coverage':'This issue owns 194/1,122 Colombia source features. Other Colombian locations are in sibling packets; this partial packet makes no whole-country coverage conclusion.','parent_source':'The four current parent names are compared to the 2017 OSM/Wambacher ADM1 `Departments` reference. It is only an identity/continuity candidate and does not independently establish DANE parent coverage.','settlement_source':'A public DANE 2013I centros poblados service was identified from official attribution metadata; its rows/license are not retained or inspected. It is dated and cannot alone prove current completeness.','physical_review':'All 194 current/source polygon counts and rings are recorded. No authoritative complete named island, coastline, inland water, or disconnected-territory reference was reconciled.','neighbors':'No shared-boundary inconsistency is established. Exact cross-region edge audit remains open; if later detected, coordinate with #489 and the affected owner.'},'locations':locs,'provinces':province_records,'area':{'id':scope['area_scopes'][0]['id'],'name':'Colombia','owned_location_count':194,'full_location_count':scope['area_scopes'][0]['full_area_location_count'],'partial':True,'role_decision':'insufficient_evidence','unresolved':'Colombia area has named national administrative/statistical meaning; this partial location batch does not establish full source coverage or physical land domain.'},'follow_up':'Continue with official DANE 2024 MGN and centros-poblados data restoration, complete settlement and physical-land screening, and neighboring boundary review. Findings remain source evidence/proposals only.'}
(HERE/'assessment.json').write_text(json.dumps(assessment,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(assessment['counts'],indent=2));print('provinces',[(x['name'],x['assigned_in_scope']) for x in province_records])
