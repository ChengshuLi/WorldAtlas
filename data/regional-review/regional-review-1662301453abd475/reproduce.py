#!/usr/bin/env python3
"""Reproduce #264 roster joins and geometry diagnostics from retained source files."""
from __future__ import annotations
import gzip, hashlib, json, re
from io import BytesIO
from collections import Counter
from pathlib import Path
from zipfile import ZipFile
import shapefile
from shapely.geometry import shape
from shapely.ops import transform as transform_geom
from shapely import union_all
from shapely.strtree import STRtree
from pyproj import Transformer
import sys
ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / 'data/regional-review/regional-review-1662301453abd475'
SOURCE = PACKET / 'source'
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence.geometry import canonical_land, land_area_m2, METHOD, VERSION
NAD83_TO_WGS84=Transformer.from_crs('EPSG:4269','EPSG:4326',always_xy=True)

def read(path):
    return json.load(open(path, encoding='utf-8'))
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def input_descriptor(path):
    raw=path.read_bytes()
    d={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    if path.suffix=='.gz':
        unpacked=gzip.decompress(raw)
        d.update({'uncompressed_sha256':hashlib.sha256(unpacked).hexdigest(),'uncompressed_bytes':len(unpacked)})
    return d
def area(g):
    return land_area_m2(g)
def ratio(a,b):
    a,b=canonical_land(a),canonical_land(b)
    overlap=a.intersection(b)
    # Overlay may return a GeometryCollection containing polygon interiors and
    # shared boundary lines. Retain only its positive-area polygon components.
    polys=[]
    pending=[overlap]
    while pending:
        part=pending.pop()
        if part.geom_type=='Polygon' and not part.is_empty and part.area>0: polys.append(part)
        elif hasattr(part,'geoms'): pending.extend(part.geoms)
    inter=area(union_all(polys)) if polys else 0.0
    return {'intersection_over_atlas': inter/area(a), 'intersection_over_reference': inter/area(b), 'jaccard': inter/(area(a)+area(b)-inter), 'atlas_area_m2':area(a), 'reference_area_m2':area(b)}
def polygon_parts(g, reference):
    parts=sorted(list(g.geoms) if g.geom_type=='MultiPolygon' else [g],key=lambda p:-p.area)
    result=[]
    for i,p in enumerate(parts,1):
        overlap=p.intersection(reference)
        polys=[]; pending=[overlap]
        while pending:
            item=pending.pop()
            if item.geom_type=='Polygon' and not item.is_empty and item.area>0: polys.append(item)
            elif hasattr(item,'geoms'): pending.extend(item.geoms)
        overlap_area=area(union_all(polys)) if polys else 0.0
        result.append({'part':i,'area_m2':area(p),'bounds_lonlat':list(p.bounds),'reference_overlap_fraction':overlap_area/area(p)})
    return result
issue=read(SOURCE/'issue-264-api-snapshot.json')
body=issue['body']
scope=json.loads(re.search(r'```json\n(.*?)\n```',body,re.S).group(1))
ids=scope['member_location_ids']
assert len(ids)==len(set(ids))==186
hierarchy={x['id']:x for x in read(ROOT/'data/hierarchy.json')}
division_id='framework:area:west-north-central:2e29334b977b'
division=hierarchy[division_id]
division_children=sorted((x['name'],x['id']) for x in hierarchy.values() if x.get('parent_id')==division_id and x.get('level')=='province')
assert division['name']=='West North Central' and division['metadata']['child_count']==7 and len(division_children)==7
official_divisions=(SOURCE/'census-regions-divisions-official-list.txt').read_text(encoding='utf-8')
division_names=[name for name,_ in division_children]
assert all(re.search(rf'^{re.escape(name)}\s+\(\d+\)\s*$',official_divisions,re.M) for name in division_names)
assert {x['name'] for x in scope['province_scopes']}=={'Iowa','Minnesota'}
assert all(hierarchy[x['id']]['parent_id']==division_id for x in scope['province_scopes'])
atlas={}
for n in (25,26,27):
    for f in read(ROOT/f'data/geography/part-{n}.json')['features']:
        if f['properties']['id'] in ids:
            assert f['properties']['id'] not in atlas
            atlas[f['properties']['id']]=f
assert set(atlas)==set(ids)

def census(path):
    with gzip.open(path,'rt',encoding='utf-8') as f: o=json.load(f)
    rows={f['properties']['GEOID']:f for f in o['features']}
    assert len(rows)==len(o['features'])
    return rows
def cartographic(path, internal_stem, wanted):
    with ZipFile(path) as z:
        r=shapefile.Reader(shp=BytesIO(z.read(internal_stem+'.shp')),
                           shx=BytesIO(z.read(internal_stem+'.shx')),
                           dbf=BytesIO(z.read(internal_stem+'.dbf')))
        rows={}
        for sr in r.iterShapeRecords():
            record=sr.record.as_dict()
            key=record['GEOID']
            if key in wanted:
                rows[key]={'properties':record,'geometry':transform_geom(NAD83_TO_WGS84.transform,shape(sr.shape.__geo_interface__))}
        return rows
v18=census(SOURCE/'census-tigerweb-counties-2018-ia-mn.geojson.gz')
cur=census(SOURCE/'census-tigerweb-counties-current-ia-mn.geojson.gz')
assert len(v18)==len(cur)==186
assert set(v18)==set(cur)
assert Counter(k[:2] for k in v18)=={'19':99,'27':87}
carto18=cartographic(SOURCE/'census-cartographic-counties-2018-500k.zip','cb_2018_us_county_500k',set(v18))
assert set(carto18)==set(v18)

gbraw=read(SOURCE/'geoBoundaries-USA-ADM2-full-pinned.geojson')
gb={f['properties']['shapeID']:f for f in gbraw['features']}
gb1raw=read(SOURCE/'geoBoundaries-USA-ADM1-full-pinned.geojson')
gb1={f['properties']['shapeName']:f for f in gb1raw['features']}
with open(SOURCE/'census-tigerweb-states-2018-ia-mn.geojson',encoding='utf-8') as f: states18={x['properties']['STATE']:x for x in json.load(f)['features']}
with open(SOURCE/'census-tigerweb-states-current-ia-mn.geojson',encoding='utf-8') as f: states_now={x['properties']['STATE']:x for x in json.load(f)['features']}
carto_states=cartographic(SOURCE/'census-cartographic-states-2018-500k.zip','cb_2018_us_state_500k',{'19','27'})
assert set(states18)==set(states_now)=={'19','27'} and len(gb1)==len(gb1raw['features'])
assert set(carto_states)=={'19','27'}
ids_by_shape={x.rsplit(':',1)[-1]:x for x in ids}
assert len(ids_by_shape)==186 and set(ids_by_shape)<=set(gb)

# Join each source shape to one Census GEOID by maximum geometric overlap, then
# enforce a strict one-to-one crosswalk and inspect the resulting overlap ratio.
tiger_geoms=[shape(f['geometry']) for _,f in sorted(v18.items())]
tiger_geoids=sorted(v18)
tree=STRtree(tiger_geoms)
crosswalk={}
for shape_id in sorted(ids_by_shape):
    g=shape(gb[shape_id]['geometry'])
    candidates=tree.query(g)
    ranked=sorted(((g.intersection(tiger_geoms[int(i)]).area,tiger_geoids[int(i)]) for i in candidates),reverse=True)
    assert ranked and ranked[0][0]>0
    assert len(ranked)==1 or ranked[0][0]>ranked[1][0]*1.000001
    crosswalk[shape_id]=ranked[0][1]
assert len(set(crosswalk.values()))==186
rows=[]
for gbid, geoid in sorted(crosswalk.items()):
    tf=v18[geoid]
    # Explicit joins: Atlas source original_id ↔ geoBoundaries shapeID, then
    # polygon-overlap crosswalk ↔ Census 2018 five-character GEOID.
    gid=ids_by_shape[gbid]
    ag=shape(atlas[gid]['geometry']); tg=shape(tf['geometry']); gg=shape(gb[gbid]['geometry'])
    now=shape(cur[geoid]['geometry'])
    cg=carto18[geoid]['geometry']
    ap=atlas[gid]['properties']; tp=tf['properties']; gp=gb[gbid]['properties']
    expected_parent=next(x['id'] for x in scope['province_scopes'] if (tp['STATE']=='19' and x['name']=='Iowa') or (tp['STATE']=='27' and x['name']=='Minnesota'))
    status='insufficient-evidence' if geoid in ('27031','27075','27071') else 'justified'
    if geoid in ('27031','27075'):
        reason='Substantive unresolved county-water extent difference: Atlas and geoBoundaries reproduce Census 2018 1:500,000 cartographic representation, while detailed TIGERweb contains materially more area. Census warns the cartographic product is not for area/precise-relationship analysis; exact land/water and complete-unit extent need a focused source review.'
    elif geoid=='27071':
        reason='County identity and main footprint are supported, but Atlas geometry has six additional detached polygon pieces beyond the single polygon in the pinned cartographic source. Their clustered tiny components may be topology artefacts or land fragments; current retained evidence cannot classify them.'
    else:
        reason='Named Census county (LSADC 06) maps one-to-one to the pinned 2018 geoBoundaries/cartographic source shape and same-name Atlas location; parent state and independent 2018/current Census county identity agree. This justifies the county-tier identity only, not exhaustive small-island or analytical-boundary completeness.'
    assert ap['name']==gp['shapeName']
    rows.append({'atlas_id':gid,'source_shapeID':gbid,'GEOID':geoid,'state':tp['STATE'],'census_name':tp['NAME'],'atlas_name':ap['name'],'geoBoundaries_name':gp['shapeName'],'atlas_parent_id':ap['parent_id'],'expected_parent_id':expected_parent,'atlas_parent_matches_state':ap['parent_id']==expected_parent,'census_lsad_code':tp['LSADC'],'classification':status,'classification_basis':reason,'atlas_vs_geoboundaries_2018':ratio(ag,gg),'atlas_vs_cartographic_2018_500k':ratio(ag,cg),'cartographic_vs_tigerweb_2018':ratio(cg,tg),'geoboundaries_vs_2018_tiger':ratio(gg,tg),'atlas_vs_2018_tiger':ratio(ag,tg),'atlas_vs_current_tiger':ratio(ag,now),'current_vs_2018_tiger':ratio(now,tg),'atlas_polygon_parts':len(ag.geoms) if ag.geom_type=='MultiPolygon' else 1,'source_polygon_parts':len(gg.geoms) if gg.geom_type=='MultiPolygon' else 1,'tiger_polygon_parts':len(tg.geoms) if tg.geom_type=='MultiPolygon' else 1,'atlas_parts_detail':polygon_parts(ag,gg) if ag.geom_type=='MultiPolygon' else []})
state_names={'19':'Iowa','27':'Minnesota'}
state_ids={x['name']:x['id'] for x in scope['province_scopes']}
state_rows=[]
for st,name in state_names.items():
    state_atlas=[shape(atlas[x['atlas_id']]['geometry']) for x in rows if x['state']==st]
    state_tiger_counties=[shape(v18[x['GEOID']]['geometry']) for x in rows if x['state']==st]
    ag=shape(gb1[name]['geometry']); t18=shape(states18[st]['geometry']); now=shape(states_now[st]['geometry'])
    cs=carto_states[st]['geometry']
    state_status='insufficient-evidence' if st=='27' else 'justified'
    state_rows.append({'province_id':state_ids[name],'name':name,'classification':state_status,'classification_basis':('The state identity and complete 87-county roster are supported, but its Atlas/county-union land geometry has a material unresolved difference from Census TIGER state extent (including the Cook/Lake county water-boundary issue); do not certify statewide footprint completeness.' if state_status=='insufficient-evidence' else 'The state identity is an ADM1 named state; its complete 99-county roster matches the pinned source, and county union / independent state geometries agree closely across 2018 and current Census sources.'),'county_count':len(state_atlas),'geoBoundaries_shapeID':gb1[name]['properties']['shapeID'],'atlas_county_union_vs_2018_geoBoundaries_state':ratio(union_all(state_atlas),ag),'census_county_union_vs_2018_tiger_state':ratio(union_all(state_tiger_counties),t18),'atlas_county_union_vs_2018_tiger_state':ratio(union_all(state_atlas),t18),'2018_geoBoundaries_state_vs_tiger_state':ratio(ag,t18),'cartographic_state_vs_tigerweb_2018':ratio(cs,t18),'atlas_county_union_vs_cartographic_state':ratio(union_all(state_atlas),cs),'current_vs_2018_tiger_state':ratio(now,t18),'atlas_parent_matches_state':all(r['atlas_parent_matches_state'] for r in rows if r['state']==st)})
related_specs={261:(119,{'North Dakota','South Dakota'}),263:(198,{'Kansas','Nebraska'}),265:(115,{'Missouri'})}
related_scopes=[]
for number,(expected_owned,expected_states) in related_specs.items():
    item=read(SOURCE/f'issue-{number}-api-snapshot.json')
    item_scope=json.loads(re.search(r'```json\n(.*?)\n```',item['body'],re.S).group(1))
    target=next(x for x in item_scope['area_scopes'] if x['id']==division_id)
    all_division_state_ids={state_id for _,state_id in division_children}
    covered_states={x['name'] for x in item_scope['province_scopes'] if x['id'] in all_division_state_ids}
    assert item['state']=='open' and target['full_area_location_count']==618
    assert target['owned_member_location_count']==expected_owned and covered_states==expected_states
    related_scopes.append({'issue':number,'title':item['title'],'url':item['html_url'],'area_owned_location_count':expected_owned,'covered_states':sorted(covered_states)})
assert sum(x['area_owned_location_count'] for x in related_scopes)+len(ids)==618
assert {s for x in related_scopes for s in x['covered_states']}==set(division_names)-{'Iowa','Minnesota'}
positive=ratio(shape(v18['19001']['geometry']),shape(v18['19001']['geometry']))
negative=ratio(shape(v18['19001']['geometry']),shape(v18['27001']['geometry']))
assert positive['jaccard']==1 and negative['jaccard']==0
assert all(r['atlas_parent_matches_state'] for r in rows)
# provenance.json is generated by build-evidence-quality.py after this run; it
# is an output, not a reproduction input. Excluding it keeps repeated runs stable.
descriptors={p.name:input_descriptor(p) for p in sorted(SOURCE.iterdir()) if p.is_file() and p.name!='provenance.json'}
summary={'method':METHOD,'helper_version':VERSION,'issue':264,'retrieved_date':'2026-10-05 America/Los_Angeles','scope_count':len(ids),'state_counts':dict(Counter(f['properties']['STATE'] for f in v18.values())),'geoBoundaries_total_features':len(gbraw['features']),'geoBoundaries_scope_features':len(ids_by_shape),'geoBoundaries_state_features':len(gb1raw['features']),'census_2018_count':len(v18),'census_current_count':len(cur),'cartographic_500k_counties_scope_count':len(carto18),'cartographic_500k_state_scope_count':len(carto_states),'all_current_vintage_geoids_match':set(v18)==set(cur),'area_context':{'area_id':division_id,'area_name':division['name'],'area_full_location_count':scope['area_scopes'][0]['full_area_location_count'],'area_owned_location_count':len(ids),'area_partial':scope['area_scopes'][0]['partial'],'area_state_children':division_children,'official_census_division_list_all_seven_match':True,'other_peer_states_outside_this_packet':sorted(set(division_names)-{'Iowa','Minnesota'}),'other_work_item_scopes':related_scopes,'work_item_scope_counts_partition_full_area':True},'positive_control_self_overlap_jaccard':positive['jaccard'],'negative_control_IA_vs_MN_overlap_jaccard':negative['jaccard'],'sources':descriptors,'geometry_crosswalk':crosswalk,'states':state_rows,'units':rows}
summary['classification_counts']=dict(Counter(r['classification'] for r in rows))
summary['selected_units']={r['GEOID']:r for r in rows if r['GEOID'] in {'27031','27071','27075'}}
# The original IDs and exact retained sources are matched one-to-one; every ratio stays visible.
summary['ranges']={}
for key in ('atlas_vs_geoboundaries_2018','atlas_vs_cartographic_2018_500k','cartographic_vs_tigerweb_2018','atlas_vs_2018_tiger','geoboundaries_vs_2018_tiger','atlas_vs_current_tiger','current_vs_2018_tiger'):
    summary['ranges'][key]={metric:{'min':min(r[key][metric] for r in rows),'median':sorted(r[key][metric] for r in rows)[len(rows)//2],'max':max(r[key][metric] for r in rows)} for metric in ('intersection_over_atlas','intersection_over_reference','jaccard')}
out=PACKET/'geometry-and-membership-results.json'
out.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'counts':[len(ids),len(v18),len(cur),len(ids_by_shape)],'state_counts':dict(Counter(f['properties']['STATE'] for f in v18.values())),'ranges':summary['ranges'],'output_sha256':sha(out)},indent=2))
