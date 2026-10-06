#!/usr/bin/env python3
"""Reproduce bounded Minnesota county/source comparisons for issue #1079."""
from __future__ import annotations
import hashlib, json, sys
from collections import Counter
from pathlib import Path
from shapely.geometry import shape
from shapely import union_all
ROOT=Path(__file__).resolve().parents[3]
PACKET=ROOT/'data/regional-review/minnesota-lake-superior-boundaries-20261006'
SRC=PACKET/'source'
sys.path.insert(0,str(ROOT/'scripts'))
from evidence.geometry import canonical_land, land_area_m2, METHOD, VERSION

def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def area(g): return land_area_m2(g)
def ratio(a,b):
    a,b=canonical_land(a),canonical_land(b)
    overlap=a.intersection(b); polys=[]; pending=[overlap]
    while pending:
        x=pending.pop()
        if x.geom_type=='Polygon' and not x.is_empty and x.area>0: polys.append(x)
        elif hasattr(x,'geoms'): pending.extend(x.geoms)
    inter=area(union_all(polys)) if polys else 0.0
    aa,bb=area(a),area(b)
    return {'intersection_over_atlas':inter/aa,'intersection_over_reference':inter/bb,'jaccard':inter/(aa+bb-inter),'atlas_area_m2':aa,'reference_area_m2':bb,'intersection_area_m2':inter}
def feature_map(path,key):
    rows={}
    for f in read(path)['features']:
        props=f['properties']; k=props[key]
        if k in rows: raise ValueError(f'duplicate {key} {k}: {path}')
        rows[k]=f
    return rows

def find_atlas(ids):
    rows={}
    for n in (25,26,27):
        for f in read(ROOT/f'data/geography/part-{n}.json')['features']:
            if f['properties']['id'] in ids:
                k=f['properties']['id']
                if k in rows: raise ValueError('duplicate Atlas id '+k)
                rows[k]=f
    if set(rows)!=set(ids): raise ValueError(f'Atlas subject mismatch: missing={set(ids)-set(rows)} extra={set(rows)-set(ids)}')
    return rows

ids={'gb:USA:ADM2:52423323B35428884505626','gb:USA:ADM2:52423323B21927262007954','gb:USA:ADM2:52423323B71326746759120'}
atlas_subjects=find_atlas(ids)
all_atlas={}
for n in (25,26,27):
    for f in read(ROOT/f'data/geography/part-{n}.json')['features']:
        p=f['properties']
        if p.get('parent_id')=='framework:province:minnesota:bf75ad975e19':
            if p['id'] in all_atlas: raise ValueError('duplicate county id '+p['id'])
            all_atlas[p['id']]=f
assert len(all_atlas)==87, len(all_atlas)
# Source file maps; every source identifies complete 87-county MN layer.
mndot_raw=feature_map(SRC/'mndot-counties.json','county_name')
dnr_raw=feature_map(SRC/'dnr-counties.json','name')
census_raw=feature_map(SRC/'census-2026-mn-counties.json','GEOID')
assert len(mndot_raw)==len(dnr_raw)==len(census_raw)==87
def canon(n): return n.replace('Saint Louis','St. Louis')
mndot_by_name={canon(k):v for k,v in mndot_raw.items()}
dnr_by_name={canon(k):v for k,v in dnr_raw.items()}
census_by_name={f['properties']['BASENAME']:f for f in census_raw.values()}
assert len(mndot_by_name)==len(dnr_by_name)==len(census_by_name)==87
assert set(mndot_by_name)==set(dnr_by_name)==set(census_by_name)
# One-to-one Atlas match by authoritative Census 5-digit GEOID recorded in each ID.
ids_by_geoid={}
# Join Atlas features to source named units only after checking same-state and unique name.
atlas_by_name={canon(f['properties']['name']):f for f in all_atlas.values()}
assert len(atlas_by_name)==87 and set(atlas_by_name)==set(census_by_name)
# Compare each of the three exact issue-subjects against Census, MnDOT and DNR.
focus={'Cook':'27031','Lake':'27075','Koochiching':'27071'}
unit_rows=[]
for name,geoid in focus.items():
    af=atlas_by_name[name]; cf=census_raw[geoid]; mf=mndot_by_name[name]; df=dnr_by_name[name]
    assert cf['properties']['BASENAME']==name
    a=shape(af['geometry']); c=shape(cf['geometry']); m=shape(mf['geometry']); d=shape(df['geometry'])
    unit_rows.append({
      'atlas_id':af['properties']['id'],'name':name,'GEOID':geoid,'parent_id':af['properties']['parent_id'],
      'census_area_attributes_m2':{'land':cf['properties']['AREALAND'],'water':cf['properties']['AREAWATER'],'total':cf['properties']['AREALAND']+cf['properties']['AREAWATER']},
      'source_identity':{'census':cf['properties']['NAME'],'mndot':mf['properties']['county_name'],'mndot_county_code':mf['properties']['county_code'],'mndot_fips55_gnis':mf['properties']['county_fips55_code'],'dnr':df['properties']['name'],'dnr_county_code':df['properties']['fips'],'atlas_parts':len(a.geoms) if a.geom_type=='MultiPolygon' else 1,'census_parts':len(c.geoms) if c.geom_type=='MultiPolygon' else 1,'mndot_parts':len(m.geoms) if m.geom_type=='MultiPolygon' else 1,'dnr_parts':len(d.geoms) if d.geom_type=='MultiPolygon' else 1},
      'areas_m2':{'atlas':area(a),'census_2026':area(c),'mndot_2022':area(m),'dnr_open_data_layer_1993_lineage':area(d)},
      'atlas_components': [{'rank_by_area':i+1,'area_m2':area(piece),'bounds_lonlat':list(piece.bounds),'census_2026_overlap_fraction':ratio(piece,c)['intersection_over_atlas'],'mndot_2022_overlap_fraction':ratio(piece,m)['intersection_over_atlas'],'dnr_overlap_fraction':ratio(piece,d)['intersection_over_atlas']} for i,piece in enumerate(sorted(list(a.geoms) if a.geom_type=='MultiPolygon' else [a],key=lambda g:-area(g)))],
      'atlas_vs_census_2026':ratio(a,c),'atlas_vs_mndot_2022':ratio(a,m),'atlas_vs_dnr':ratio(a,d),'mndot_2022_vs_dnr':ratio(m,d),
      'classification':'insufficient-evidence',
      'classification_basis':({'Cook':'Identity, state parent and land-oriented reference outline are strongly corroborated; Census 2026 includes materially more mapped water area and no inspected survey/legal source establishes the county’s line through Lake Superior.','Lake':'Identity, state parent and land-oriented reference outline are strongly corroborated; Census 2026 includes materially more mapped water area and no inspected survey/legal source establishes the county’s line through Lake Superior.','Koochiching':'Identity and main footprint are corroborated, but the Atlas has one 2,129 m² component shared by all references, a 205 m² component absent from all three and four degenerate slivers; their physical/survey status is unresolved.'}[name])
    })
# State parent is framework-only: compare its child county union to complete state outlines.
atlas_state=union_all([shape(f['geometry']) for f in all_atlas.values()])
mndot_state=union_all([shape(f['geometry']) for f in mndot_by_name.values()])
dnr_state=union_all([shape(f['geometry']) for f in dnr_by_name.values()])
census_state_features=feature_map(ROOT/'data/regional-review/regional-review-1662301453abd475/source/census-tigerweb-states-current-ia-mn.geojson','STATE')
census_state=shape(census_state_features['27']['geometry'])
state_rows={'parent_id':'framework:province:minnesota:bf75ad975e19','classification':'insufficient-evidence','classification_basis':'The hierarchy record has 87 county children but no independent geometry feature. County-union area is close to land-oriented references yet materially smaller than the current Census state footprint; official Minnesota state area includes a Lake Superior jurisdictional portion, but this does not resolve exact county/state water geometry.','hierarchy_record':{k:v for k,v in next(x for x in read(ROOT/'data/hierarchy.json') if x['id']=='framework:province:minnesota:bf75ad975e19').items() if k in ('id','level','name','parent_id','metadata')},'child_count':len(all_atlas),'complete_source_counts':{'atlas_children':len(all_atlas),'mndot_2022':len(mndot_raw),'dnr_open_data_layer':len(dnr_raw),'census_tigerweb_2026':len(census_raw)},'atlas_county_union_vs_census_tigerweb_state_2026':ratio(atlas_state,census_state),'mndot_2022_county_union_vs_census_tigerweb_state_2026':ratio(mndot_state,census_state),'dnr_county_union_vs_census_tigerweb_state_2026':ratio(dnr_state,census_state),'atlas_county_union_vs_mndot_county_union':ratio(atlas_state,mndot_state),'mndot_county_union_vs_dnr_county_union':ratio(mndot_state,dnr_state),'census_county_union_vs_census_tigerweb_state':ratio(union_all([shape(f['geometry']) for f in census_raw.values()]),census_state)}
# Topology / containment checks are diagnostics only, with no implicit repair.
topology={}
for label,rows in [('atlas',all_atlas),('mndot_2022',mndot_raw),('dnr',dnr_raw),('census_2026',census_raw)]:
    gs={k:shape(v['geometry']) for k,v in rows.items()}
    state_counts={'features':len(gs),'invalid':sum(not g.is_valid for g in gs.values()),'empty':sum(g.is_empty for g in gs.values()),'multipart':sum(g.geom_type=='MultiPolygon' for g in gs.values())}
    names=list(gs); overlap_pairs=[]; overlaps=[]
    # Pairwise positive area overlap among counties after respecting shared edges.
    for i,k in enumerate(names):
        for j in range(i+1,len(names)):
            z=gs[k].intersection(gs[names[j]])
            if z.area>0:
                overlaps.append((k,names[j],z.area))
    state_counts['positive_area_overlap_pairs']=len(overlaps)
    state_counts['max_planar_overlap_square_degrees']=max((x[2] for x in overlaps),default=0)
    topology[label]=state_counts
# Neighbor memberships compare complete same-state layers; contact length is deliberately not used as a distance measure.
def neighbor_names(rows, key_name):
    geoms={key_name(k):shape(v['geometry']) for k,v in rows.items()}
    return {name:sorted(other for other,g in geoms.items() if other!=name and geoms[name].boundary.intersection(g.boundary).length>0) for name in focus}
neighboring={
 'atlas':neighbor_names(atlas_by_name,lambda n:n),
 'mndot_2022':neighbor_names(mndot_by_name,lambda n:n),
 'dnr_1993_lineage':neighbor_names(dnr_by_name,lambda n:n),
 'census_tigerweb_2026':neighbor_names(census_by_name,lambda n:n)
}
# Components are preserved individually for the three exact features; tiny degenerate parts can be rejected by the scientific land-area helper and are marked unmeasurable.
def component_inventory(geom,reference):
    parts=sorted(list(geom.geoms) if geom.geom_type=='MultiPolygon' else [geom],key=lambda z:-z.area)
    rows=[]
    for i,piece in enumerate(parts,1):
        try:
            size=area(piece); frac=ratio(piece,reference)['intersection_over_atlas'] if size>0 else None; quality='measured'
        except ValueError:
            size=0.0;frac=None;quality='unmeasurable-degenerate'
        rows.append({'rank_by_planar_size':i,'area_m2_shared_helper':size,'area_status':quality,'bounds_lonlat':list(piece.bounds),'atlas_overlap_fraction':frac})
    return rows
source_components={}
for name in focus:
    source_components[name]={}
    for layer,feature in [('mndot_2022',mndot_by_name[name]),('dnr_1993_lineage',dnr_by_name[name]),('census_tigerweb_2026',census_by_name[name])]:
        source_components[name][layer]=component_inventory(shape(feature['geometry']),shape(atlas_by_name[name]['geometry']))
# Federal American Indian Reservation overlay is a separate 2020 Census geography, included only to identify intersecting governance layers; it is not evidence for county geometry.
tribal_rows=feature_map(SRC/'tribal-reservations-2020-mn.geojson','GEOID')
tribal_intersections=[]
for county,geoid in focus.items():
    cg=shape(atlas_by_name[county]['geometry'])
    for tf in tribal_rows.values():
        tg=shape(tf['geometry']); x=cg.intersection(tg)
        if not x.is_empty and x.area>0:
            tribal_intersections.append({'county':county,'reservation':tf['properties']['NAME'],'GEOID':tf['properties']['GEOID'],'census_vintage':'2020-01-01','intersection_planar_square_degrees':x.area})
# Controls using independent Iowa and state pieces from the parent #264 collection.
# Positive: an exact retained county compared with itself; negative: Cook v Kittson (remote county).
cook=shape(atlas_by_name['Cook']['geometry']); control_positive=ratio(cook,cook)
kittson=shape(atlas_by_name['Kittson']['geometry']); control_negative=ratio(cook,kittson)
assert control_positive['jaccard']==1 and control_negative['intersection_area_m2']==0
assert all(x['parent_id']=='framework:province:minnesota:bf75ad975e19' for x in unit_rows)

prior_results=read(ROOT/'data/regional-review/regional-review-1662301453abd475/geometry-and-membership-results.json')
prior_carto={row['GEOID']:{'atlas_vs_census_cartographic_2018_500k':row['atlas_vs_cartographic_2018_500k'],'cartographic_2018_vs_tigerweb_2018':row['cartographic_vs_tigerweb_2018']} for row in prior_results['selected_units'].values()}
assert set(prior_carto)=={'27031','27071','27075'}
result={'prior_issue_264_cartographic_reproduction':{'baseline_commit':'897fdd0fbac0e16e675a56a15883c22f533b51a3','results_path':'data/regional-review/regional-review-1662301453abd475/geometry-and-membership-results.json','results_sha256':sha(ROOT/'data/regional-review/regional-review-1662301453abd475/geometry-and-membership-results.json'),'source_sha256':prior_results['sources']['census-cartographic-counties-2018-500k.zip']['sha256'],'prior_selected_counties':prior_carto},'issue':1079,'baseline_commit':'00664f04790641a9e0c0b29535823076ed243b93','helper_version':VERSION,'method':METHOD,'units':unit_rows,'state_parent':state_rows,'neighboring_counties':neighboring,'source_components':source_components,'tribal_context':{'source_vintage':'Census federal American Indian Reservation geography, 2020-01-01','geographies_are_separate_from_counties':True,'county_intersections':tribal_intersections},'topology':topology,'controls':{'positive_cook_self':control_positive,'negative_cook_vs_kittson':control_negative},'scope_count':4,'classifications':{'framework:province:minnesota:bf75ad975e19':'insufficient-evidence','gb:USA:ADM2:52423323B21927262007954':'insufficient-evidence','gb:USA:ADM2:52423323B35428884505626':'insufficient-evidence','gb:USA:ADM2:52423323B71326746759120':'insufficient-evidence'},'source_files':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(SRC.iterdir()) if p.is_file() and p.name not in ('provenance.json','geometry-and-membership-results.json')}}
out=PACKET/'geometry-results.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'state':{k:v for k,v in state_rows.items() if k.endswith('2026') or k=='complete_source_counts'},'units':[{x['name']:x['atlas_vs_census_2026']['jaccard'] for x in unit_rows}],'topology':topology,'result_sha256':sha(out)},indent=2))
