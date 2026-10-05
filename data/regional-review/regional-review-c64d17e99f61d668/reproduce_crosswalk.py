#!/usr/bin/env python3
"""Reproduce identity and admin-level crosswalks from retained packet inputs.

Croatia source reconstruction: the exact ATOM URL, archive/member hashes and
size are retained in dgu-scoped-unit-crosswalk.json. The 199 MiB source archive
was not committed. The small, attributed scoped name/code/parent extract is
retained and is the offline input to this script. Re-download the exact archive
from the DGU ATOM entry to independently repeat the original streaming extraction.
"""
import csv, hashlib, json, pathlib, re, unicodedata
ROOT=pathlib.Path(__file__).resolve().parent
SCOPE=json.loads((ROOT/'scope.json').read_text())
IDS=set(SCOPE['member_location_ids'])
source_manifest=json.loads((ROOT/'source-manifest.json').read_text())
for descriptor in source_manifest['retained_source_files']:
    path=ROOT/descriptor['path']
    raw=path.read_bytes()
    if len(raw)!=descriptor['bytes'] or hashlib.sha256(raw).hexdigest()!=descriptor['sha256']:
        raise SystemExit(f"Retained source differs from exact manifest pin: {descriptor['path']}")
COUNTY={
 'framework:province:pozega-slavonia:9c0b252675e1':'Požeško-slavonska županija',
 'framework:province:virovitica-podravina:05b25891ba1e':'Virovitičko-podravska županija',
 'framework:province:brod-posavina:ed1f1a57cc5b':'Brodsko-posavska županija',
 'framework:province:osijek-baranja:150cf19feca3':'Osječko-baranjska županija',
 'framework:province:vukovar-syrmia:063bde629720':'Vukovarsko-srijemska županija'}
PROVINCE={x['id']:x['name'] for x in SCOPE['province_scopes']}
AREA_BY_COUNTRY={'gb:GRC':'framework:area:greece:e5489fc04cd7','gb:HRV':'framework:area:yugoslavia:cff5e9ba6c8e'}
def county_norm(s): return re.sub(r'^[ivxlcdm]+\s+','',norm(s).replace(' zupanija',''))

def norm(s):
    s=unicodedata.normalize('NFKD',s or '')
    return ''.join(c for c in s if not unicodedata.combining(c)).casefold().replace('opcina ','').replace('grad ','').strip()

# Exact scoped source IDs and retained atlas metadata.
atlas={}
rendered_hash={}
for part in (ROOT.parents[2]/'data'/'geography').glob('part-*.json'):
    for feature in json.loads(part.read_text())['features']:
        props=feature.get('properties',{}); key=props.get('id')
        if key in IDS:
            atlas[key]=props
            rendered_hash[key]=hashlib.sha256(json.dumps(feature.get('geometry'),sort_keys=True).encode()).hexdigest()
if set(atlas)!=IDS: raise SystemExit(f'atlas scope mismatch: {len(atlas)}/{len(IDS)}')
source={}
for code,adm in [('GRC','ADM3'),('HRV','ADM2')]:
    path=ROOT/'source'/'geoboundaries-9469f09'/code/adm/f'geoBoundaries-{code}-{adm}.geojson'
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    data=json.loads(path.read_text())
    for ft in data['features']:
        p=ft['properties']; key=f"gb:{code}:{adm}:{p['shapeID']}"
        if key in IDS:
            geom=ft['geometry']; coords=geom['coordinates']; polys=coords if geom['type']=='MultiPolygon' else [coords]
            def vertices(v):
                if isinstance(v,list) and v and isinstance(v[0],(int,float)): return 1
                return sum(vertices(x) for x in v) if isinstance(v,list) else 0
            source[key]={'name':p['shapeName'],'source_id':p['shapeID'],'geometry_hash':hashlib.sha256(json.dumps(geom,sort_keys=True).encode()).hexdigest(),'geometry_type':geom['type'],'geometry_parts':len(polys),'geometry_holes':sum(max(0,len(poly)-1) for poly in polys),'geometry_vertices':vertices(coords)}
if set(source)!=IDS: raise SystemExit(f'source scope mismatch: {len(source)}/{len(IDS)}')

# The large DGU archive is not committed. The exact scoped extract is retained
# with required attribution/modification notice and hashes; it was produced by
# streaming the source archive and includes only target municipality/city rows.
dgu=json.loads((ROOT/'source/official-croatia/dgu-scoped-unit-crosswalk.json').read_text())
if hashlib.sha256((ROOT/'source/official-croatia/dgu-scoped-unit-crosswalk.json').read_bytes()).hexdigest()!='d517293f593593160fd9fdffede8a64e559a54e533176034fbd392266d29bbac':
    raise SystemExit('Retained DGU scoped extract hash changed; re-review source evidence')
found={r['atlas_location_id']:r['official_matches'] for r in dgu['scope_rows'] if r['official_matches']}
near=dgu.get('near_name_candidates',{})
hrv={k:v for k,v in source.items() if k.startswith('gb:HRV:')}
ministry_rows=[]
ministry_csv=ROOT/'source/official-croatia/ministry-local-government-list-2013.csv'
ministry_xls=ROOT/'source/official-croatia/ministry-local-government-list.xls'
expected_ministry_hashes={
    ministry_xls:'1f60a60b90e875cf59dd69de2fff64a1550a699165251ff665ed039fa67a3ac0',
    ministry_csv:'13dc42e534606c785be49008746e16eb7c553999b1675058bdaac0612262ea71',
}
for path, expected in expected_ministry_hashes.items():
    actual=hashlib.sha256(path.read_bytes()).hexdigest()
    if actual!=expected: raise SystemExit(f'Croatian ministry evidence hash changed: {path.name}')
with ministry_csv.open(encoding='utf-8',newline='') as f:
    ministry_rows=list(csv.DictReader(f))
if len(ministry_rows)!=556: raise SystemExit(f'Historic Croatian roster row count changed: {len(ministry_rows)}')
ministry_matches={}
for key,row in hrv.items():
    props=atlas[key]; county=county_norm(COUNTY.get(props.get('parent_id'),'')); name=norm(row['name'])
    unit_type='Grad' if row['name'].casefold().startswith('grad ') else 'Općina'
    ministry_matches[key]=[x for x in ministry_rows if county_norm(x['county'])==county and norm(x['official_name'])==name and norm(x['unit_type'])==norm(unit_type)]
ministry_near={key:[x for x in ministry_rows if county_norm(x['county'])==county_norm(COUNTY.get(atlas[key].get('parent_id'),'')) and norm(x['official_name']) in {norm(c['official_name']) for c in near.get(key,[])} and norm(x['unit_type'])==norm('Grad' if source[key]['name'].casefold().startswith('grad ') else 'Općina')] for key in hrv if near.get(key)}

rows=[]
for key in sorted(IDS):
    p=atlas[key]; s=source[key]; meta=p.get('metadata',{})
    row={'id':key,'issue_area':'Greece' if key.startswith('gb:GRC') else 'Yugoslavia','atlas_name':p.get('name'),
         'atlas_parent_id':p.get('parent_id'),'atlas_parent_province':PROVINCE.get(p.get('parent_id'),p.get('parent_id')),'atlas_area_id':AREA_BY_COUNTRY['gb:'+key.split(':')[1]],'atlas_region_id':SCOPE['region_id'],'reference_owner':p.get('reference_owner'),'reference_owner_id':meta.get('reference_owner_id'),
         'source_id':s['source_id'],'source_name':s['name'],'source_geometry_type':s['geometry_type'],
         'source_geometry_parts':s['geometry_parts'],'source_geometry_holes':s['geometry_holes'],'source_geometry_vertices':s['geometry_vertices'],'source_geometry_hash':s['geometry_hash'],'current_atlas_geometry_hash':rendered_hash[key],'source_geometry_same_as_current':s['geometry_hash']==rendered_hash[key],'source_geometry_matches_original_metadata':s['geometry_hash']==meta.get('original_geometry_sha256') if meta.get('original_geometry_sha256') else None,'source_license':meta.get('license'),'source_vintage':meta.get('reference_year'),
         'source_role':meta.get('source_role'),'source_parent_level':meta.get('parent_source_level'),'hierarchy_source':meta.get('hierarchy_source'),'hierarchy_overlap':meta.get('hierarchy_overlap'),'geographic_area_code':meta.get('geographic_area_code'),'geographic_region_code':meta.get('geographic_region_code'),'geographic_overlap':meta.get('geographic_overlap'),'selection_reason':meta.get('selection_reason'),'topology_reconciled':meta.get('topology_reconciled'),'topology_conflicts':meta.get('topology_conflicts'),'topology_note':meta.get('topology_note'),'original_geometry_sha256':meta.get('original_geometry_sha256'),'status':'insufficient-evidence','classification':'insufficient-evidence','identity_assessment':'No authoritative same-vintage unit and boundary crosswalk established.','boundary_assessment':'Exact footprint, multipart completeness, enclaves/islands, and neighboring-edge equivalence remain unverified.'}
    if key.startswith('gb:HRV:'):
        hits=found.get(key,[])
        row['official_dgu_matches']=hits
        row['official_ministry_2013_matches']=ministry_matches[key]
        row['official_ministry_2013_near_matches']=ministry_near.get(key,[])
        row['identity_classification']='justified' if len(hits)==1 and len(ministry_matches[key])==1 else 'correction-needed' if bool(near.get(key)) and bool(ministry_near.get(key)) else 'insufficient-evidence'
        if row['identity_classification']=='correction-needed': row['classification']='correction-needed'
        row['identity_assessment']=('Unique normalized name + parent-county match to current DGU INSPIRE 3rdOrder municipality/city unit; identity/role supported, but not the 2021 boundary.' if len(hits)==1 else 'No exact name match; a same-county close spelling candidate requires source-label follow-up.' if row['identity_classification']=='correction-needed' else 'Current DGU identity crosswalk is ambiguous or absent.')
    rows.append(row)
result={'version':1,'retrieved_at':'2026-10-05','scope_count':len(IDS),'source_hashes':{},'official_croatia_archive_sha256':dgu['archive_sha256'],
        'official_croatia_archive_bytes':dgu['archive_bytes'],'official_croatia_gml_member':dgu['gml_member_name'],
        'official_croatia_gml_member_sha256':dgu['gml_member_sha256'],'official_croatia_gml_member_bytes':dgu['gml_member_bytes'],
        'official_croatia_features_returned':dgu['gml_features_returned'],'official_croatia_features_matched':dgu['gml_features_matched'],'official_croatia_number_returned_declared':dgu['gml_declared_number_returned'],'official_croatia_return_count_consistent':dgu['gml_return_count_consistent'],'official_croatia_next_page_url':dgu['gml_next_page_url'],
        'croatia_unique_name_county_matches':sum(len(found.get(k,[]))==1 for k in hrv),'croatia_unmatched_or_ambiguous':{k:found.get(k,[]) for k in hrv if not found.get(k)},
        'official_dgu_3rd_order_count_in_returned_page':dgu['gml_3rd_order_in_returned_page'],
        'croatia_near_name_candidates':near,'croatia_ministry_2013_exact_matches':sum(len(v)==1 for v in ministry_matches.values()),'croatia_ministry_2013_roster_rows':len(ministry_rows),
        'geometry_hash_comparison':{code:{'source_equals_current':sum(source[k]['geometry_hash']==rendered_hash[k] for k in source if k.startswith(f'gb:{code}:')),'different':sum(source[k]['geometry_hash']!=rendered_hash[k] for k in source if k.startswith(f'gb:{code}:')),'topology_reconciled_count':sum(atlas[k].get('metadata',{}).get('topology_reconciled') is True for k in source if k.startswith(f'gb:{code}:')),'topology_conflict_counts':{str(n):sum(atlas[k].get('metadata',{}).get('topology_conflicts')==n for k in source if k.startswith(f'gb:{code}:')) for n in (1,2,3,4)}} for code in ('GRC','HRV')},
        'geometry_triage':{code:{'multipolygon_units':sum(source[k]['geometry_type']=='MultiPolygon' for k in source if k.startswith(f'gb:{code}:')),'multipart_units':sum(source[k]['geometry_parts']>1 for k in source if k.startswith(f'gb:{code}:')),'units_with_holes':sum(source[k]['geometry_holes']>0 for k in source if k.startswith(f'gb:{code}:')),'highest_vertex_counts':sorted([{'id':k,'name':source[k]['name'],'vertices':source[k]['geometry_vertices']} for k in source if k.startswith(f'gb:{code}:')],key=lambda x:-x['vertices'])[:5]} for code in ('GRC','HRV')},
        'greece_source_duplicate_names':[{'name':n,'ids':[f"gb:GRC:ADM3:{x['properties']['shapeID']}" for x in json.loads((ROOT/'source/geoboundaries-9469f09/GRC/ADM3/geoBoundaries-GRC-ADM3.geojson').read_text())['features'] if x['properties']['shapeName'].casefold().strip()==n]} for n,count in __import__('collections').Counter(f['properties']['shapeName'].casefold().strip() for f in json.loads((ROOT/'source/geoboundaries-9469f09/GRC/ADM3/geoBoundaries-GRC-ADM3.geojson').read_text())['features']).items() if count>1],
        'croatia_scoped_future_begin_lifespan':{k:found[k][0]['valid_from'] for k in found if found[k][0].get('valid_from','')[:10]>'2026-10-04'},
        'rows':rows,
        'province_inventory':[{ 'id':q['id'],'name':q['name'],'scoped_count':sum(atlas[k].get('parent_id')==q['id'] for k in IDS),'full_scope':not q.get('partial',False)} for q in SCOPE['province_scopes']],
        'ministry_2013_source_sha256':hashlib.sha256(ministry_xls.read_bytes()).hexdigest(),'ministry_2013_csv_sha256':hashlib.sha256(ministry_csv.read_bytes()).hexdigest(),
        'interpretation':'Per-location boundary classifications remain insufficient-evidence pending source-vintage polygon comparison. Croatian identity/role is crosswalked by DGU 3rdOrder name and county; this does not validate the 2021 polygons. Greek identity/count sources do not establish the 80 exact boundaries. All 207 current Atlas coordinate sequences differ from their archived geoBoundaries source coordinates; serialized differences are a warning only, not a measured territorial discrepancy.'}
for code,adm in [('GRC','ADM3'),('HRV','ADM2')]:
 path=ROOT/'source'/'geoboundaries-9469f09'/code/adm/f'geoBoundaries-{code}-{adm}.geojson'
 result['source_hashes'][f'{code}-{adm}']=hashlib.sha256(path.read_bytes()).hexdigest()
out=ROOT/'crosswalk.json'; out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False,indent=2))
print('row_count',len(rows),'croatia_unique_name_county_matches',sum(len(found.get(k,[]))==1 for k in hrv),'official_dgu_3rd_order_count',dgu['gml_3rd_order_in_returned_page'])
