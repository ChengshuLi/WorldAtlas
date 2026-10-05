#!/usr/bin/env python3
"""Reproduce exact source-ID/name/parent and contemporary GSS comparisons for #471."""
import csv,gzip,hashlib,json,math,struct,sys,zipfile
from pathlib import Path
import unicodedata
from pyproj import Transformer
from shapely.geometry import shape,Polygon,MultiPolygon,GeometryCollection
from shapely import make_valid
from shapely.ops import transform,unary_union
from shapely.strtree import STRtree

OWN=Path(__file__).resolve().parent
BASE=OWN.parents[2]
EQUAL_AREA=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform

def readjson(path): return json.loads(Path(path).read_text())
def raw_source(stem): return json.load(gzip.open(OWN/'sources'/f'{stem}.geojson.gz','rt',encoding='utf-8'))
def norm(s):
    s=unicodedata.normalize('NFKD',s or '')
    s=''.join(c for c in s if not unicodedata.combining(c)).lower()
    return ''.join(c for c in s if c.isalnum())
def pct(a,b): return a.intersection(b).area/b.area if b.area else 0

def parse_dbf(raw):
    count=struct.unpack_from('<I',raw,4)[0]; header,record=struct.unpack_from('<HH',raw,8)
    fields=[]
    for i in range(32,header-1,32):
        if raw[i]==13: break
        d=raw[i:i+32]; fields.append((d[:11].split(b'\0')[0].decode('ascii'),chr(d[11]),d[16]))
    rows=[]; pos=header
    for _ in range(count):
        rec=raw[pos:pos+record]; pos+=record
        if len(rec)!=record: raise ValueError('truncated DBF')
        off=1; row={}
        for name,typ,size in fields:
            value=rec[off:off+size]; off+=size
            row[name]=value.decode('utf-8',errors='replace').strip().strip('\x00') if typ=='C' else value
        if rec[0]!=42: rows.append(row)
    return rows,fields

def parse_polygon_shp(raw):
    if len(raw)<100 or struct.unpack_from('<i',raw,32)[0]!=5: raise ValueError('expected Polygon shapefile')
    pos=100; out=[]
    while pos<len(raw):
        if pos+8>len(raw): raise ValueError('truncated SHP record header')
        number,words=struct.unpack_from('>ii',raw,pos); n=words*2; body=raw[pos+8:pos+8+n]; pos+=8+n
        stype=struct.unpack_from('<i',body,0)[0]
        if stype==0: out.append(None); continue
        if stype!=5: raise ValueError(f'unexpected per-record shape {stype}')
        nparts,npoints=struct.unpack_from('<ii',body,36)
        starts=list(struct.unpack_from('<'+'i'*nparts,body,44))
        pointoff=44+4*nparts
        pts=[struct.unpack_from('<dd',body,pointoff+16*i) for i in range(npoints)]
        rings=[]
        for j,start in enumerate(starts): rings.append(pts[start:starts[j+1] if j+1<nparts else npoints])
        # ESRI Polygon convention: clockwise exterior, counterclockwise holes.
        shells=[]; holes=[]
        for ring in rings:
            signed=sum(ring[i][0]*ring[i+1][1]-ring[i+1][0]*ring[i][1] for i in range(len(ring)-1))/2
            (shells if signed<0 else holes).append(ring)
        polys=[Polygon(shell,[h for h in holes if Polygon(shell).covers(Polygon(h).representative_point())]) for shell in shells]
        geom=polys[0] if len(polys)==1 else MultiPolygon(polys)
        out.append(geom)
    return out

def gss_records(zip_path):
    z=zipfile.ZipFile(zip_path)
    nested=z.read('Geo FIles/Districts_261.zip')
    inner=zipfile.ZipFile(__import__('io').BytesIO(nested))
    stem='District_261'
    attrs,fields=parse_dbf(inner.read(stem+'.dbf'))
    geoms=parse_polygon_shp(inner.read(stem+'.shp'))
    if len(attrs)!=261 or len(geoms)!=261: raise ValueError('GSS 261 expected 261 records')
    rows=[]
    for i,(a,g) in enumerate(zip(attrs,geoms)):
        was_valid=g.is_valid
        diagnostic=make_valid(g) if not was_valid else g
        if isinstance(diagnostic,GeometryCollection):
            diagnostic=unary_union([part for part in diagnostic.geoms if part.geom_type in ('Polygon','MultiPolygon')])
        rows.append({'record':i+1,'name':a['Label'],'region':a['Region'],'district_field':a['District'],'source_geometry_valid':was_valid,'diagnostic_geometry':not was_valid,'geometry':transform(EQUAL_AREA,diagnostic)})
    return rows,hashlib.sha256(Path(zip_path).read_bytes()).hexdigest(),len(Path(zip_path).read_bytes()),hashlib.sha256(nested).hexdigest(),len(nested),fields

scope=readjson(OWN/'issue-scope-pinned.json')
features=json.load(gzip.open(OWN/'baseline-members.geojson.gz','rt',encoding='utf-8'))['features']
lineage={x['id']:x for x in readjson(OWN/'baseline-source-lineage.json')['subjects']}
expected=set(scope['member_location_ids'])
if {f.get('id') or f['properties']['id'] for f in features}!=expected: raise SystemExit('pinned subject mismatch')
configs={
 'gb:GMB:ADM2':('gambia-gbopen-2020-adm2','gambia-gbopen-2020-adm1','GMB-ADM2','GMB-ADM1'),
 'gb:GHA:ADM2':('ghana-gbopen-2019-adm2','ghana-gbopen-2019-adm1','GHA-ADM2','GHA-ADM1'),
 'gb:CIV:ADM3':('civ-gbopen-2021-adm3','civ-gbopen-2021-adm2','CIV-ADM3','CIV-ADM2'),
}
source_sets={}; source_equal_sets={}; parent_sets={}; transforms={}
for sid,(childstem,parentstem,childmd,parentmd) in configs.items():
    ch=raw_source(childstem)['features']; pa=raw_source(parentstem)['features']
    source_sets[sid]={f['properties']['shapeID']:f for f in ch}
    source_equal_sets[sid]={f['properties']['shapeID']:transform(EQUAL_AREA,shape(f['geometry'])) for f in ch}
    parent_sets[sid]=[(f['properties']['shapeName'],f['properties']['shapeID'],transform(EQUAL_AREA,shape(f['geometry']))) for f in pa]
    transforms[sid]=childstem

# Retained Natural Earth 10m admin-1 reference for the source record Atlas calls Banjul.
ne_dir=OWN/'sources/natural-earth-10m-admin1'
ne_dbf=gzip.open(ne_dir/'ne_10m_admin_1_states_provinces.dbf.gz','rb').read()
ne_shp=gzip.open(ne_dir/'ne_10m_admin_1_states_provinces.shp.gz','rb').read()
ne_attrs,ne_fields=parse_dbf(ne_dbf); ne_geoms=parse_polygon_shp(ne_shp)
if len(ne_attrs)!=4596 or len(ne_geoms)!=4596: raise SystemExit('Natural Earth expected aligned 4596 DBF/SHP records')
ne_matches=[i for i,a in enumerate(ne_attrs) if a.get('adm0_a3')=='GMB' and a.get('adm1_code')=='GMB-2153']
if len(ne_matches)!=1: raise SystemExit(f'Natural Earth exact GMB-2153 record count {len(ne_matches)}')
ne_index=ne_matches[0]; ne_attrs_target=ne_attrs[ne_index]; ne_geom_target=ne_geoms[ne_index]
if ne_attrs_target.get('name')!='Banjul' or ne_attrs_target.get('type_en')!='Independent City': raise SystemExit('Natural Earth target semantic attributes changed')
ne_target_eq=transform(EQUAL_AREA,ne_geom_target)
city_id='atlas:city:GMB-2153'
city_feature=next(f for f in features if (f.get('id') or f['properties']['id'])==city_id)
city_eq=transform(EQUAL_AREA,shape(city_feature['geometry']))
city_members=city_feature['properties']['metadata']['source_member_ids']
gmb_source_by_id={f['properties']['shapeID']:f for f in raw_source('gambia-gbopen-2020-adm2')['features']}
member_union_eq=transform(EQUAL_AREA,unary_union([shape(gmb_source_by_id[x.rsplit(':',1)[-1]]['geometry']) for x in city_members]))
def overlap(a,b):
    a=make_valid(a) if not a.is_valid else a; b=make_valid(b) if not b.is_valid else b
    inter=a.intersection(b).area; union=a.union(b).area
    return {'iou':inter/union if union else None,'first_geometry_area_fraction':inter/a.area if a.area else None,'second_geometry_area_fraction':inter/b.area if b.area else None}
ne_city_comparison={'upstream_commit':'ca96624a56bd078437bca8184e78163e5039ad19','upstream_layer':'10m_cultural/ne_10m_admin_1_states_provinces','feature_index_zero_based':ne_index,'feature_count':len(ne_attrs),'target_attributes':{k:((v.decode('ascii').strip() or None) if isinstance((v:=ne_attrs_target.get(k)),bytes) else v) for k in ('adm1_code','adm0_a3','name','name_long','type','type_en','admin','ne_id')},'dbf_fields':[{'name':x[0],'type':x[1],'width':x[2]} for x in ne_fields],'natural_earth_vs_atlas_city':overlap(ne_target_eq,city_eq),'natural_earth_vs_nine_geoBoundaries_member_union':overlap(ne_target_eq,member_union_eq),'limits':['Natural Earth is an undated modern reference and not an authoritative statutory city delimitation.','Its broad admin-1 city feature is a comparative source record; it does not establish which LGA or statutory parent Atlas should encode.']}

# Optional comparison to the openly downloadable GSS 2021 district bundle. We retain its hash and
# row-level crosswalk only; no GSS source bytes/geometries are copied into the packet because a
# redistribution license was not exposed on StatsBank and its stated agreement URL returned 404.
gss_path=Path('/tmp/gss-geofiles-2021.zip')
gss=[]; gss_receipt=None; gss_fields=None
if gss_path.exists():
    gss,zhash,zbytes,inner_hash,inner_bytes,gss_fields=gss_records(gss_path)
    gss_receipt={'url':'https://statsbank.statsghana.gov.gh/assets/geofiles.zip','outer_sha256':zhash,'outer_bytes':zbytes,'inner_path':'Geo FIles/Districts_261.zip','inner_sha256':inner_hash,'inner_bytes':inner_bytes,'official_unit_count':len(gss)}

gss_tree=STRtree([x['geometry'] for x in gss]) if gss else None
rows=[]
for f in features:
    p=f.get('properties') or {}; m=p.get('metadata') or {}; id=p.get('id') or f.get('id')
    source_id=m.get('source_id'); rec={'id':id,'name':p.get('name'),'atlas_parent_id':p.get('parent_id'),'area_id':next((a['id'] for a in lineage[id]['ancestry'] if a['level']=='area'),None),'province_id':next((a['id'] for a in lineage[id]['ancestry'] if a['level']=='province'),None),'province_name':next((a['name'] for a in lineage[id]['ancestry'] if a['level']=='province'),None),'source_id':source_id,'source_role_atlas':m.get('source_role'),'source_vintage_atlas':m.get('reference_year'),'atlas_license':m.get('license'),'source_name_atlas':m.get('source_name'),'source_url_atlas':m.get('source_url'),'atlas_geometry_type':(f.get('geometry') or {}).get('type')}
    if source_id in configs:
        childstem,parentstem,childmd,parentmd=configs[source_id]
        original=m.get('original_id'); source=source_sets[source_id].get(original)
        if not source: raise SystemExit(f'missing exact source original_id {id} {original}')
        sp=source['properties']; cg=shape(source['geometry']); ag=shape(f['geometry'])
        child=source_equal_sets[source_id][original]; atlas_eq=transform(EQUAL_AREA,ag)
        atlas_diag=not atlas_eq.is_valid; child_diag=not child.is_valid
        if atlas_diag: atlas_eq=make_valid(atlas_eq)
        if child_diag: child=make_valid(child)
        share=atlas_eq.intersection(child).area; union=atlas_eq.area+child.area-share
        rec.update({'source_shape_id':sp.get('shapeID'),'source_shape_name':sp.get('shapeName'),'source_shape_iso':sp.get('shapeISO'),'source_shape_type':sp.get('shapeType'),'source_identity_match':sp.get('shapeID')==original,'source_name_exact':sp.get('shapeName')==p.get('name'),'geometry_exact_coordinates':ag.equals_exact(cg,0),'geometry_topologically_equal':ag.equals(cg),'atlas_feature_valid':ag.is_valid,'source_feature_valid':cg.is_valid,'atlas_source_atlas_area_fraction':share/atlas_eq.area if atlas_eq.area else None,'atlas_source_reference_area_fraction':share/child.area if child.area else None,'atlas_source_iou':share/union if union else None,'atlas_source_diagnostic_make_valid':atlas_diag or child_diag})
        cand=sorted(((pct(pargeom,child),name,pid) for name,pid,pargeom in parent_sets[source_id]),reverse=True)
        rec.update({'source_parent_name_candidate':cand[0][1] if cand else None,'source_parent_id_candidate':cand[0][2] if cand else None,'source_parent_area_coverage':cand[0][0] if cand else None,'atlas_parent_name_norm_matches_source_candidate':norm(rec['province_name'])==norm(cand[0][1]) if cand else False})
        if source_id=='gb:GHA:ADM2' and gss:
            name_candidates=[x for x in gss if norm(x['name'])==norm(sp['shapeName']) and norm(x['region']).removesuffix('region')==norm(rec['province_name']).removesuffix('region')]
            named_result={'gss2021_named_match_name':None,'gss2021_named_match_region':None,'gss2021_named_match_district_field':None,'gss2021_named_match_record':None,'gss2021_named_match_iou':None,'gss2021_named_match_source_fraction':None,'gss2021_named_match_reference_fraction':None}
            if len(name_candidates)==1:
                n=name_candidates[0]; inter=child.intersection(n['geometry']).area; union_area=child.area+n['geometry'].area-inter
                named_result={'gss2021_named_match_name':n['name'],'gss2021_named_match_region':n['region'],'gss2021_named_match_district_field':n['district_field'],'gss2021_named_match_record':n['record'],'gss2021_named_match_iou':inter/union_area if union_area else None,'gss2021_named_match_source_fraction':inter/child.area if child.area else None,'gss2021_named_match_reference_fraction':inter/n['geometry'].area if n['geometry'].area else None}
            nearby=gss_tree.query(child)
            gmatches=[]
            for ix in nearby:
                z=gss[int(ix)]; gg=z['geometry']; inter=child.intersection(gg).area; union=child.area+gg.area-inter
                gmatches.append((inter/union if union else 0,inter/child.area if child.area else 0,inter/gg.area if gg.area else 0,z))
            gmatches.sort(key=lambda x:(x[0],x[1]),reverse=True)
            # Keep all substantial overlays as a candidate list. Their union is not an
            # accuracy score: selecting every intersecting unit can make the source
            # coverage look complete by construction, especially for partition changes.
            substantial=[entry for entry in gmatches if entry[1]>=0.01 or entry[2]>=0.01]
            if gmatches:
                iou,sfrac,rfrac,z=gmatches[0]
                rec.update({'gss2021_name_match_count':len(name_candidates),'gss2021_spatial_match_name':z['name'],'gss2021_spatial_match_region':z['region'],'gss2021_district_field':z['district_field'],'gss2021_spatial_record':z['record'],'gss2021_source_fraction':sfrac,'gss2021_reference_fraction':rfrac,'gss2021_iou':iou,'gss2021_substantial_overlay_names':[e[3]['name'] for e in substantial],'gss2021_substantial_overlay_count':len(substantial),'gss2021_source_geometry_valid':z['source_geometry_valid'],'gss2021_diagnostic_make_valid':z['diagnostic_geometry'],**named_result})
            else: rec.update({'gss2021_name_match_count':len(name_candidates),'gss2021_spatial_match_name':None,'gss2021_spatial_match_region':None,'gss2021_district_field':None,'gss2021_spatial_record':None,'gss2021_source_fraction':None,'gss2021_reference_fraction':None,'gss2021_iou':None,'gss2021_substantial_overlay_names':[],'gss2021_substantial_overlay_count':0,'gss2021_source_geometry_valid':None,'gss2021_diagnostic_make_valid':None,**named_result})
        else: rec.update({'gss2021_name_match_count':None,'gss2021_spatial_match_name':None,'gss2021_spatial_match_region':None,'gss2021_district_field':None,'gss2021_spatial_record':None,'gss2021_source_fraction':None,'gss2021_reference_fraction':None,'gss2021_iou':None,'gss2021_substantial_overlay_names':[],'gss2021_substantial_overlay_count':0,'gss2021_source_geometry_valid':None,'gss2021_diagnostic_make_valid':None,'gss2021_named_match_name':None,'gss2021_named_match_region':None,'gss2021_named_match_district_field':None,'gss2021_named_match_record':None,'gss2021_named_match_iou':None,'gss2021_named_match_source_fraction':None,'gss2021_named_match_reference_fraction':None})
    elif source_id=='atlas:city:GMB-2153':
        rec.update({'source_shape_id':None,'source_shape_name':None,'source_shape_iso':None,'source_shape_type':None,'source_identity_match':None,'source_name_exact':None,'geometry_exact_coordinates':None,'geometry_topologically_equal':None,'atlas_feature_valid':shape(f['geometry']).is_valid,'source_feature_valid':None,'atlas_source_atlas_area_fraction':None,'atlas_source_reference_area_fraction':None,'atlas_source_iou':None,'atlas_source_diagnostic_make_valid':None,'source_parent_name_candidate':None,'source_parent_id_candidate':None,'source_parent_area_coverage':None,'atlas_parent_name_norm_matches_source_candidate':None,'gss2021_name_match_count':None,'gss2021_spatial_match_name':None,'gss2021_spatial_match_region':None,'gss2021_district_field':None,'gss2021_source_fraction':None,'gss2021_reference_fraction':None,'gss2021_iou':None,'gss2021_substantial_overlay_names':[],'gss2021_substantial_overlay_count':None,'gss2021_source_geometry_valid':None,'gss2021_diagnostic_make_valid':None})
    else: raise SystemExit('unmapped source '+str(source_id))
    rows.append(rec)
# Source totals and area-level counts are context only, never an accuracy pass.
control=Polygon([(0,0),(1,0),(1,1),(0,0)])
positive=pct(transform(EQUAL_AREA,control),transform(EQUAL_AREA,control))
disjoint=pct(transform(EQUAL_AREA,Polygon([(2,2),(3,2),(3,3),(2,2)])),transform(EQUAL_AREA,control))
if abs(positive-1)>1e-12 or abs(disjoint)>1e-12: raise SystemExit('positive/negative polygon controls failed')
summary={'version':1,'issue':471,'baseline_commit':readjson(OWN/'baseline-receipt.json')['baseline_commit'],'subject_count':len(rows),'source_totals':{sid:{'source_features':len(source_sets[sid]),'scoped_features':sum(r['source_id']==sid for r in rows),'source_parent_features':len(parent_sets[sid])} for sid in configs},'gss2021':gss_receipt,'gss_dbf_fields':[{'name':x[0],'type':x[1],'width':x[2]} for x in gss_fields] if gss_fields else None,'natural_earth_gambia_city':ne_city_comparison,'geometry_method':{'crs_input':'RFC 7946 longitude/latitude GeoJSON; Natural Earth shapefile uses its retained PRJ','area_crs':'EPSG:6933 World Cylindrical Equal Area','method':'source-child versus exact geoBoundaries-source-parent polygon intersection. For GSS, compute equal-area IoU and both asymmetric area shares for the unique normalized name+region candidate, if any, and separately report the nearest spatial candidate; substantial overlays are a candidate list only, never a union accuracy score. Natural Earth 10m GMB-2153 is matched by exact adm0_a3+adm1_code attributes, then compared to Atlas and the nine declared geoBoundaries members. Invalid GSS records get a local Shapely make_valid diagnostic clone while source bytes remain unchanged.','software':{'python':sys.version.split()[0],'shapely':__import__('shapely').__version__,'pyproj':__import__('pyproj').__version__},'controls':{'identical_triangle_overlap':positive,'disjoint_triangle_overlap':disjoint,'passed':True},'gss_diagnostic_invalid_count':sum(not x['source_geometry_valid'] for x in gss),'limits':['Source and GSS layers are not a legal boundary survey.','GSS 2021 geofiles are inspected as restoration-only because no redistributable license was located.','Natural Earth is public domain per its published terms, but remains an undated generalized reference.','Area overlap is a within-source/temporal comparator, not proof of local statutory status or complete shoreline representation.']}}
(OWN/'source-crosswalk.json').write_text(json.dumps({'summary':summary,'members':rows},ensure_ascii=False,sort_keys=True,indent=2)+'\n')
(OWN/'source-crosswalk.csv').write_text('')
with open(OWN/'source-crosswalk.csv','w',newline='') as out:
    cols=[k for k in rows[0] if k not in ('geometry_exact_coordinates','atlas_feature_valid','source_feature_valid')]
    w=csv.DictWriter(out,fieldnames=cols);w.writeheader();w.writerows({k:r.get(k) for k in cols} for r in rows)
print(json.dumps({'members':len(rows),'source_totals':summary['source_totals'],'exact_id':sum(r.get('source_identity_match') is True for r in rows),'exact_name':sum(r.get('source_name_exact') is True for r in rows),'exact_geom':sum(r.get('geometry_exact_coordinates') is True for r in rows),'topo_equal':sum(r.get('geometry_topologically_equal') is True for r in rows),'parent_name_match':sum(r.get('atlas_parent_name_norm_matches_source_candidate') is True for r in rows),'parent_overlap_min':min((r['source_parent_area_coverage'] for r in rows if r['source_parent_area_coverage'] is not None),default=None),'atlas_source_iou_min':min((r['atlas_source_iou'] for r in rows if r['atlas_source_iou'] is not None),default=None),'gss2021':gss_receipt,'gss_name_candidates':sum((r.get('gss2021_name_match_count') or 0)==1 for r in rows),'gss_spatial_matches':sum(r.get('gss2021_spatial_match_name') is not None for r in rows),'gss_iou_ge_0_99':sum((r.get('gss2021_iou') or 0)>=.99 for r in rows)},indent=2))
