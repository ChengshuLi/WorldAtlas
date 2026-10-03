#!/usr/bin/env python3
"""Rebuild issue #616 source identity, scope, census crosswalk, and geometry evidence.
Run from the repository root. All generated files stay beside this script.
"""
from __future__ import annotations
import csv, hashlib, io, json, pathlib, sys, zipfile, unicodedata
from collections import Counter, defaultdict
from datetime import date
import shapefile
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform, unary_union

ROOT = pathlib.Path(__file__).resolve().parents[3]
PACKET = pathlib.Path(__file__).resolve().parent
IDS = ['ASM-4998','ASM-4999','ASM-5000','ASM-5001','ASM-5002','WLF-4995','WLF-4996','WLF-4997']
BASELINE = 'f592b3d8b72f40036218803d2c70c733112e4d37'
ROUND = lambda x: round(float(x), 8)
SHA = lambda b: hashlib.sha256(b).hexdigest()

def dump(name, data):
    (PACKET/name).write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)+'\n')
def load_json(path): return json.loads(path.read_text())

def verify_raw_sources():
    v=(PACKET/'sources/natural-earth/ne_10m_admin_1_states_provinces.VERSION.txt').read_text().strip()
    if v != '5.1.1': raise SystemExit('unexpected pinned Natural Earth layer version')
    r=shapefile.Reader(str(PACKET/'sources/natural-earth/ne_10m_admin_1_states_provinces.shp'), encoding='utf-8')
    fields=[x[0] for x in r.fields[1:]]
    records={}
    for sr in r.iterShapeRecords():
        row=dict(zip(fields,sr.record)); code=row.get('adm1_code')
        if code in IDS:
            records[code]={'attributes':row,'geometry':sr.shape.__geo_interface__}
    if set(records)!=set(IDS): raise SystemExit(f'Natural Earth ID mismatch: {set(IDS)-set(records)}')
    return records

def build_scope(ne):
    ix=load_json(ROOT/'data/world-index.json')
    features={}; containing={}
    for part in ix['parts']:
        full='data/'+part
        for f in load_json(ROOT/'data'/part)['features']:
            if f['id'] in IDS:
                if f['id'] in features: raise SystemExit('duplicate scoped feature '+f['id'])
                features[f['id']]=f; containing[f['id']]=full
    if set(features)!=set(IDS): raise SystemExit('not all eight location IDs found in index')
    hrows=load_json(ROOT/'data/hierarchy.json'); hierarchy={x['id']:x for x in hrows}
    def ancestors(pid):
        out=[];seen=set();cur=pid
        while cur:
            if cur in seen: raise SystemExit('parent cycle '+cur)
            seen.add(cur)
            row=hierarchy.get(cur)
            if row is None: raise SystemExit('missing parent '+cur)
            out.append(row);cur=row.get('parent_id')
        return out
    locations=[]; province_rows=[]; area_ids=set(); region_ids=set()
    for id in IDS:
        f=features[id]; props=f['properties']; chain=ancestors(props['parent_id'])
        if [x.get('level') for x in chain] != ['province','area','region','subcontinent','continent']:
            raise SystemExit(f'incomplete/unexpected chain for {id}')
        province=chain[0]; area=chain[1]; region=chain[2]
        area_ids.add(area['id']);region_ids.add(region['id'])
        locations.append({'id':id,'name':props['name'],'parent_id':props['parent_id'],'containing_file':containing[id],
          'geometry_type':f['geometry']['type'],'component_count':len(f['geometry'].get('coordinates',[])),
          'current_metadata':props.get('metadata',{}),'parent_chain':[{'id':x['id'],'name':x['name'],'level':x['level']} for x in chain]})
        province_rows.append({'id':province['id'],'name':province['name'],'parent_id':province['parent_id'],'child_location_id':id,
          'metadata':province.get('metadata',{})})
    memberships={a:[] for a in area_ids}; all_features={}
    for part in ix['parts']:
        for f in load_json(ROOT/'data'/part)['features']:
            all_features[f['id']]=f
            chain=ancestors(f['properties']['parent_id'])
            for node in chain:
                if node['id'] in memberships: memberships[node['id']].append(f['id'])
    areas=[]
    for a in sorted(area_ids):
        row=hierarchy[a]
        areas.append({'id':a,'name':row['name'],'parent_id':row['parent_id'],'current_full_member_ids':sorted(memberships[a]),'reviewed_issue_subject_ids':sorted(set(memberships[a]) & set(IDS)),'metadata':row.get('metadata',{})})
    scope={'issue':616,'baseline_commit':BASELINE,'retrieved_on':'2026-10-03','scope_source':'GitHub issue #616; dependency #134 closed',
      'member_location_ids':IDS,'location_count':8,'locations':locations,'province_count':8,'province_wrappers':province_rows,
      'areas':areas,'neighboring_region_ids':sorted(region_ids)}
    dump('issue-scope.json',scope)
    return features,hierarchy,scope

def census_sources():
    base=PACKET/'sources/census-as'; groups={'010':'Eastern District','020':"Manu'a District",'030':'Rose Island','040':'Swains Island','050':'Western District'}
    def zipped_shape(prefix):
        z=zipfile.ZipFile(next(base.glob(prefix+'*.zip'))); stem=next(n[:-4] for n in z.namelist() if n.endswith('.shp'))
        return z,shapefile.Reader(shp=io.BytesIO(z.read(stem+'.shp')),shx=io.BytesIO(z.read(stem+'.shx')),dbf=io.BytesIO(z.read(stem+'.dbf')),encoding='utf-8')
    zc,cr=zipped_shape('tl_2020_60_cousub'); cfields=[f[0] for f in cr.fields[1:]]; cousubs=[]
    for sr in cr.iterShapeRecords():
        d=dict(zip(cfields,sr.record)); d['territory_location_id']={'010':'ASM-4998','020':'ASM-4999','030':'ASM-5000','040':'ASM-5001','050':'ASM-5002'}[d['COUNTYFP']]
        d['parent_geography_group']=groups[d['COUNTYFP']];d['geometry']=sr.shape.__geo_interface__;cousubs.append(d)
    zp,pr=zipped_shape('tl_2020_60_place'); pfields=[f[0] for f in pr.fields[1:]]; places=[]
    for sr in pr.iterShapeRecords():
        d=dict(zip(pfields,sr.record));d['geometry']=sr.shape.__geo_interface__;places.append(d)
    # Quantitatively crosswalk each Census place polygon to the 2020 Census county-subdivision geometry with the greatest overlap.
    project=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform
    cgeoms=[(c['GEOID'],c['territory_location_id'],transform(project,shape(c['geometry']))) for c in cousubs]
    crosswalk=[]
    for p in places:
        pg=transform(project,shape(p['geometry'])); hits=[]
        for geoid,location,g in cgeoms:
            area=pg.intersection(g).area
            if area>0: hits.append((area,geoid,location))
        hits.sort(reverse=True)
        denom=pg.area or 1
        crosswalk.append({'place_geoid':p['GEOID'],'name':p['NAME'],'statistical_class':p['CLASSFP'],'geoid_county_subdivision':hits[0][1] if hits else None,
          'location_id':hits[0][2] if hits else None,'largest_overlap_fraction':ROUND(hits[0][0]/denom) if hits else 0,
          'next_overlap_fraction':ROUND(hits[1][0]/denom) if len(hits)>1 else 0,'all_county_subdivision_overlaps':[{'geoid':x[1],'location_id':x[2],'fraction_of_place_area':ROUND(x[0]/denom)} for x in hits]})
    summaries=[]
    for id in IDS[:5]:
        pl=[x for x in crosswalk if x['location_id']==id]
        cs=[x for x in cousubs if x['territory_location_id']==id]
        summaries.append({'location_id':id,'census_county_equivalent_group':groups[next((x['COUNTYFP'] for x in cousubs if x['territory_location_id']==id),{'ASM-5000':'030','ASM-5001':'040'}.get(id,''))] if cs else groups[{'ASM-5000':'030','ASM-5001':'040'}.get(id,'')],
          'county_subdivision_count':len(cs),'county_subdivision_names':sorted(x['NAME'] for x in cs),'place_feature_count':len(pl),'place_names':sorted(x['name'] for x in pl),
          'all_place_geometries_have_at_least_99pct_in_one_county_subdivision':bool(pl) and all(x['largest_overlap_fraction']>=.99 for x in pl)})
    report={'source':'U.S. Census Bureau, 2020 Census, TIGER/Line 2020, American Samoa',
      'county_equivalent_codes':groups,'tiger_cousub_feature_count':len(cousubs),'tiger_cousub_features':[{k:v for k,v in x.items() if k!='geometry'} for x in cousubs],
      'tiger_place_feature_count':len(places),'tiger_place_to_cousub_crosswalk':crosswalk,'place_names_by_scope_location':summaries,
      'interpretation':'Census statistical geographies only: GARM states boundaries/designations are for census collection/tabulation and do not determine jurisdiction, ownership or legal title. TIGER village/place records do not prove every inhabited settlement or dwellings; statutory lists, Census place universe and village counts are distinct source concepts.'}
    dump('american-samoa-census-inventory.json',report)
    return cousubs,places,crosswalk

def insee_source():
    wb=PACKET/'sources/insee-wf/wetf-2018.xlsx'
    import openpyxl
    book=openpyxl.load_workbook(wb,data_only=True,read_only=True)
    sheets={}
    for tab in ['Circonscriptions','Districts','Villages']:
        s=book[tab]; rows=list(s.iter_rows(values_only=True)); headers=[str(x).strip() if x is not None else '' for x in rows[0]]
        data=[]; last={}
        for row in rows[1:]:
            obj={h:v for h,v in zip(headers,row) if h}
            if not any(v is not None for v in obj.values()):continue
            for h in headers:
                if h in ('Circonscription','District') and obj.get(h):last[h]=obj[h]
                elif h in ('Circonscription','District') and h in last:obj[h]=last[h]
            data.append(obj)
        sheets[tab]=data
    villages=[x for x in sheets['Villages'] if x.get('Village') and x['Village']!='Ensemble du Territoire']
    dump('wallis-futuna-insee-inventory.json',{'source':'INSEE legal populations for Wallis and Futuna, 2018 reference','sheet_row_counts':{k:len(v) for k,v in sheets.items()},
      'circonscription_rows':[x for x in sheets['Circonscriptions'] if x.get('Circonscription') and not str(x.get('Circonscription')).startswith(('Total',' Ensemble'))],
      'district_rows':[x for x in sheets['Districts'] if x.get('District') and not str(x.get('District')).startswith(('Total',' Ensemble'))],
      'village_count':len(villages),'village_rows':villages,
      'settlement_count_by_natural_earth_unit':{'WLF-4996':21,'WLF-4997':9,'WLF-4995':6},
      'limit':'Statistical/census settlements and legal-population tables do not provide authoritative boundaries or determine a district/circonscription legal status; distinguish INSEE statistical “Districts” worksheet categories from the Territorial Assembly’s current local-government organization. Workbook contains an apparently stale “Population totale 2008” column header in reference 2018 workbook; do not use that column as 2018 support.'})
    return villages

def census_geometry_check(ne, features):
    base=PACKET/'sources/census-as/tl_2020_60_cousub.zip'
    z=zipfile.ZipFile(base);stem=next(n[:-4] for n in z.namelist() if n.endswith('.shp'))
    r=shapefile.Reader(shp=io.BytesIO(z.read(stem+'.shp')),shx=io.BytesIO(z.read(stem+'.shx')),dbf=io.BytesIO(z.read(stem+'.dbf')),encoding='utf-8')
    fields=[f[0] for f in r.fields[1:]]; by_code=defaultdict(list); by_names=defaultdict(list)
    for sr in r.iterShapeRecords():
        row=dict(zip(fields,sr.record));by_code[row['COUNTYFP']].append(shape(sr.shape.__geo_interface__));by_names[row['COUNTYFP']].append(row['NAME'])
    groups={'010':'ASM-4998','020':'ASM-4999','030':'ASM-5000','040':'ASM-5001','050':'ASM-5002'}
    project=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform;out=[]
    for code,id in groups.items():
        count_geoms=by_code.get(code,[]); census=transform(project,unary_union(count_geoms)) if count_geoms else None
        negeom=transform(project,shape(ne[id]['geometry']));current=transform(project,shape(features[id]['geometry']))
        row={'countyfp':code,'location_id':id,'census_name':{'010':'Eastern District','020':"Manu'a District",'030':'Rose Island','040':'Swains Island','050':'Western District'}[code],
          'census_county_subdivision_count':len(count_geoms),'census_county_subdivision_names':sorted(by_names.get(code,[])),
          'census_geometry_union_available':bool(count_geoms),'exploratory_ne_vs_census_union':None,'exploratory_current_vs_census_union':None,
          'area_comparability_limit':'These Census polygons include extensive statistical water and are not comparable with land-only or different-water-scope naturalearth polygons by whole area; percentages are descriptive diagnostics only, not boundary match weights.',
          'scope_gap':'The TIGER 2020 COUSUB inventory contains 14 statutory county records plus Swains Island but no Rose Island/Atoll COUSUB record. Rose Island is mapped in the Census GARM as a county-equivalent island; no authoritative digital census county outline was retained for it.'}
        if census:
            def cmp(a,b):
                it=a.intersection(b).area
                return {'census_union_area_km2':ROUND(b.area/1e6),'feature_area_km2':ROUND(a.area/1e6),'feature_area_in_census_union_pct':ROUND(100*it/a.area) if a.area else None,'census_union_area_in_feature_pct':ROUND(100*it/b.area) if b.area else None,'sym_difference_pct_of_feature':ROUND(100*a.symmetric_difference(b).area/a.area) if a.area else None}
            row['exploratory_ne_vs_census_union']=cmp(negeom,census);row['exploratory_current_vs_census_union']=cmp(current,census)
        out.append(row)
    dump('american-samoa-census-geometry-comparison.json',{'baseline_commit':BASELINE,'method':{'source':'2020 TIGER/Line county-subdivision polygons','crs':'EPSG:6933','note':'2020 Census map states its boundaries support census collection/tabulation and do not determine jurisdiction/ownership. TIGER polygons include extensive water. Whole-area overlaps are descriptive only and must not be interpreted as administrative boundary accuracy.'},'units':out})

def legal_review(cousubs, places):
    groups={'010':('American Samoa Code §5.0101/5.0102','Eastern District'), '020':('American Samoa Code §5.0101/5.0102',"Manu'a District"),
      '050':('American Samoa Code §5.0101/5.0102','Western District')}
    statute={'010':['Ituau','Ma’oputasi','Sa’ole','Sua','Vaifanua'],'050':['Lealataua','Leasina','Tualatai','Tualauta'],'020':['Ta’u','Faleasao','Fitiuta','Ofu','Olosega']}
    observed={k:sorted(x['NAME'] for x in cousubs if x['COUNTYFP']==k) for k in ['010','020','030','040','050']}
    def norm(s):
        s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
        return ''.join(c for c in s if c.isalnum())
    assembly={'WLF-4996_Uvea':{'Hihifo':['Malae','Alele','Vaitupu','Vailala','Tufuone'],'Hahake':['Liku','Akaaka',"Mata’Utu",'Ahoa','Falaleu','Haafuasia'],'Mua':['Lavegahau','Tepa','Haatofo','Gahi','Utufua','Malaefoon','Teesi','Kolopopo','Halalo','Vaimalau']},
      'WLF-4997_Alo':['Malae','Taoa','Ono','Kolia','Alofi','Poï','Vele','Tamana','Tuatafa'],
      'WLF-4995_Sigave':['Leava','Nuku','Vaisei','Fiua','Toloke','Tavai']}
    insee=json.loads((PACKET/'wallis-futuna-insee-inventory.json').read_text())
    wb_rows=insee['village_rows']
    insee_by={'WLF-4996_Uvea':[x['Village'] for x in wb_rows if x.get('Circonscription')=='Uvea'],
      'WLF-4997_Alo':[x['Village'] for x in wb_rows if x.get('Circonscription')=='Alo'],
      'WLF-4995_Sigave':[x['Village'] for x in wb_rows if x.get('Circonscription')=='Sigave']}
    wlf_crosswalk={}
    for key,official in assembly.items():
        if isinstance(official,dict):official=[name for names in official.values() for name in names]
        tsv=insee_by[key]; on={norm(x):x for x in official};tn={norm(x):x for x in tsv}
        wlf_crosswalk[key]={'official_assembly_count':len(official),'insee_2018_count':len(tsv),'normalized_exact_matches':[{'assembly':on[n],'insee':tn[n]} for n in sorted(set(on)&set(tn))],
          'assembly_only_or_spelling_unresolved':[on[n] for n in sorted(set(on)-set(tn))],'insee_only_or_spelling_unresolved':[tn[n] for n in sorted(set(tn)-set(on))]}
    report={'AmericanSamoa':{'source':'American Samoa Code Annotated §§5.0101–5.0102 (published online by American Samoa Bar Association; PL 7-28 (1962) cited as history)',
      'access':'Direct host returned HTTP 403 in this session; source text inspected through text-access proxy. Preserve the original URLs and verify against local public-law/code originals before a legal implementation.',
      'administrative_districts':{'count':3,'source_names':{'010':'Eastern District','020':"Manu'a District",'050':'Western District'},
      'statutory_county_lists':statute,'statute_vs_2020_TIGER_counties':{k:{'statute_county_names':v,'TIGER_2020_county_subdivision_names':observed[k],'normalized_name_set_match':{norm(x) for x in v}=={norm(x) for x in observed[k]},'statute_only':sorted({norm(x):x for x in v}.keys()-{norm(x) for x in observed[k]}),'tiger_only':sorted({norm(x):x for x in observed[k]}.keys()-{norm(x) for x in v})} for k,v in statute.items()},
      'Swains_Island':'§5.0101 explicitly excludes Swains Island from the three districts and places its administration directly under the Governor. Census 2020 separately maps Swains Island as a county-equivalent and TIGER includes a Swains Island county-subdivision and place. These are legal text/Census roles, not a source-demarcation of title.',
      'Rose_Atoll':'Rose Island/Atoll is a Census county-equivalent map feature and 2020 TIGER county group (COUNTYFP 030), but not in the statutory 14-county list or §5.0101 three districts. Exact current statutory/admin jurisdiction remains unresolved; absence from those county lists is not proof it lacks any authority/management.',
      'settlements':'§5.0102 enumerates villages/settlements per the 14 counties; 2020 TIGER PLACE provides 77 statistical village features. Treat these as differing date and purpose inventories, not equal rosters.'}},
      'WallisFutuna':{'source':'Official Assemblée Territoriale de Wallis et Futuna, “Organisation Institutionnelle”; INSEE legal populations (2018 reference) by circonscription, district and village.',
      'official_structure':'The assembly reports three circonscriptions corresponding to three customary kingdoms, Uvéa, Alo and Sigave, with civil-registry/roads competences, autonomous budgets, customary institutions and each king presiding over the council. It reports 21 Wallis villages across Hihifo, Hahake and Mua districts, plus 15 Futuna villages: 9 Alo (including Alofi) and 6 Sigave.',
      'counts':{'circonscriptions':3,'wallis_districts':3,'futuna_customary_kingdom_units':2,'villages':36,'WLF-4996_Uvea':21,'WLF-4997_Alo':9,'WLF-4995_Sigave':6},'assembly_to_insee_village_crosswalk':wlf_crosswalk,
      'source_tier_limit':'INSEE has a “Districts” table with Hahake, Hihifo, Mua, Alo and Sigave; the official Territorial Assembly calls only the three Wallis subdivisions districts, and describes Alo/Sigave as Futuna kingdoms/circonscriptions. Do not make the table label an assertion of a shared legal tier. Neither INSEE statistics nor the assembly page supplies authoritative digital boundaries.'}}
    dump('administrative-role-review.json',report)

def geometry_evidence(ne, features):
    project=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform; rows=[]
    for id in IDS:
        s=shape(ne[id]['geometry']); c=shape(features[id]['geometry'])
        sm=transform(project,s);cm=transform(project,c)
        inter=sm.intersection(cm).area
        rows.append({'id':id,'name':features[id]['properties']['name'],'source_geometry_type':s.geom_type,'source_polygon_components':len(s.geoms) if s.geom_type=='MultiPolygon' else 1,
          'current_geometry_type':c.geom_type,'current_polygon_components':len(c.geoms) if c.geom_type=='MultiPolygon' else 1,
          'source_area_km2':ROUND(sm.area/1e6),'current_area_km2':ROUND(cm.area/1e6),'intersection_km2':ROUND(inter/1e6),
          'source_area_covered_by_current_pct':ROUND(100*inter/sm.area) if sm.area else None,'current_area_covered_by_source_pct':ROUND(100*inter/cm.area) if cm.area else None,
          'sym_difference_pct_of_current':ROUND(100*sm.symmetric_difference(cm).area/cm.area) if cm.area else None,
          'source_valid':bool(s.is_valid),'current_valid':bool(c.is_valid),'source_bounds_lonlat':list(map(ROUND,s.bounds)),'current_bounds_lonlat':list(map(ROUND,c.bounds))})
    dump('natural-earth-current-geometry-comparison.json',{'baseline_commit':BASELINE,'method':{'axis_order':'longitude-latitude','crs':'EPSG:6933','area':'Planar equal-area EPSG:6933; coverage percentages denominated by stated whole feature area.','geometry_repair':'No source/current geometry was altered or repaired.','meaning':'Overlay diagnostic only; no linework source is an authoritative local legal demarcation.'},'units':rows})

def main():
    ne=verify_raw_sources();features,hierarchy,scope=build_scope(ne);cousubs,places,crosswalk=census_sources(); villages=insee_source();geometry_evidence(ne,features);census_geometry_check(ne,features);legal_review(cousubs,places)
    fields_to_keep=['adm1_code','featurecla','scalerank','iso_3166_2','adm0_a3','admin','geonunit','name','name_alt','type','type_en','code_local','adm0_label','gn_id','gn_name','gn_level','gn_region','gn_a1_code','woe_name','region_sub','area_sqkm','ne_id','latitude','longitude']
    profiles=[]
    for id in IDS:
        a=ne[id]['attributes']; g=ne[id]['geometry']; loc=next(x for x in scope['locations'] if x['id']==id); province=next(x for x in scope['province_wrappers'] if x['child_location_id']==id)
        profiles.append({'location_id':id,'current_name':loc['name'],'natural_earth_identity':{k:a.get(k) for k in fields_to_keep},
          'source_geometry':g,'source_geometry_type':g['type'],'source_component_count':len(g['coordinates']),'province_wrapper_id':province['id'],'parent_chain':loc['parent_chain']})
    dump('natural-earth-source-profiles.json',{'source':'Natural Earth Version 5.1.1 ne_10m_admin_1_states_provinces, exact commit ca96624a56bd078437bca8184e78163e5039ad19 dated 2022-06-02',
      'match_method':'Exact `adm1_code` match to the eight scoped WorldAtlas IDs; raw world shapefile sidecars retained unchanged.','field_warning':'Natural Earth feature class is Admin-1 states/provinces, but for the eight rows `type` and `type_en` are blank; selected `adm1_code`, GeoNames and alternate attributes need semantic review. The dataset is cartographic reference, not legal boundary authority.','records':profiles})
    print(json.dumps({'locations':len(scope['locations']),'provinces':len(scope['province_wrappers']),'areas':len(scope['areas']),'tiger_counties':len(cousubs),'tiger_places':len(places),'insee_villages':len(villages)},indent=2))
if __name__=='__main__':main()
