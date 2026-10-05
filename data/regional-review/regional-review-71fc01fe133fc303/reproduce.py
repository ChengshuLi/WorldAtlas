#!/usr/bin/env python3
"""Reproduce the exact 228-subject Turkey district review for issue #73.

Reads retained sources and immutable Atlas blobs from the pinned fresh-main
baseline. Writes only inside this issue's declared ownership directory.
Comparative geometry measures are diagnostic screens, not legal certificates.
"""
from __future__ import annotations
import collections, gzip, hashlib, json, re, subprocess, sys, unicodedata
from pathlib import Path
from shapely import union_all
from shapely.affinity import translate
from shapely.geometry import shape
ROOT = Path(__file__).resolve().parents[3]
OWNED = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence.geometry import VERSION, canonical_land, land_area_m2
BASELINE = 'ec5c642f2986d0671488e5d2134e73b62f1de906'
SCOPE = OWNED / 'scope.json'
RECEIPTS = OWNED / 'source-receipts.json'
OUTPUT = OWNED / 'district-assessments.json'
SOURCE_ROOT = 'data/regional-review/regional-review-c24563b50d8731b3/sources/geoboundaries-9469f09'
GENERIC = {'unknown','unnamed','remainder','remaining','unassigned','other','none','n/a','merkez'}
MARKER = re.compile(r'(?:\bmerkez\b|\bunknown\b|\bunnamed\b|\bremainder\b|\bremaining\b|\bunassigned\b|\bother\b|\bnon[- ]?existent\b)', re.I)

def sha(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()
def git_blob(path: str) -> bytes: return subprocess.check_output(['git','show',f'{BASELINE}:{path}'],cwd=ROOT)
def j(path: Path): return json.loads(path.read_text(encoding='utf-8'))
def norm(value: str) -> str: return unicodedata.normalize('NFKC',value).casefold().strip()
def parts(g): return len(g.geoms) if g.geom_type=='MultiPolygon' else (1 if g.geom_type=='Polygon' else 0)
def polygonal_area(g):
    if g.is_empty: return 0.0
    if g.geom_type=='Polygon': return land_area_m2(g)
    if g.geom_type=='MultiPolygon': return land_area_m2(g)
    if g.geom_type=='GeometryCollection':
        vals=[p for p in g.geoms if p.geom_type in ('Polygon','MultiPolygon')]
        return land_area_m2(union_all(vals)) if vals else 0.0
    return 0.0

def main():
    scope_raw=SCOPE.read_bytes(); scope=json.loads(scope_raw)
    ids=scope['member_location_ids']; wanted=set(ids)
    contract=j(OWNED/'issue-contract.json'); receipt_doc=j(RECEIPTS)
    if contract['baseline_commit']!=BASELINE: raise SystemExit('Baseline commit does not match the recorded fresh main.')
    if sha(scope_raw)!=contract['scope_sha256']: raise SystemExit('Issue scope bytes differ from recorded API snapshot.')
    if len(ids)!=228 or len(wanted)!=228 or scope['location_count']!=228: raise SystemExit('Expected exactly 228 unique issue subjects.')
    if hashlib.sha256('\n'.join(sorted(ids)).encode()).hexdigest()!=scope['member_location_ids_sha256']: raise SystemExit('Issue subject list hash mismatch.')
    if len(scope['province_scopes'])!=20: raise SystemExit('Expected the 20 pinned province scopes.')
    province={x['id']:x for x in scope['province_scopes']}
    for row in scope['province_scopes']:
        owned_ids=row.get('owned_location_ids',[])
        if len(owned_ids)!=row['full_province_locations'] or row['partial'] or not set(owned_ids)<=wanted:
            raise SystemExit('Province scope is not a complete owned group: '+row['name'])
    if sum(x['full_province_locations'] for x in scope['province_scopes'])!=228: raise SystemExit('Province groups do not sum to issue scope.')

    source_receipts={x['path']:x for x in receipt_doc['retained_source_files']}
    for rel,record in source_receipts.items():
        raw=git_blob(rel)
        if sha(raw)!=record['sha256'] or len(raw)!=record['bytes']: raise SystemExit('Retained source hash/length mismatch: '+rel)
    source_path=SOURCE_ROOT+'/geoBoundaries-TUR-ADM2.geojson'
    source_meta_path=SOURCE_ROOT+'/geoBoundaries-TUR-ADM2-metaData.json'
    adm1_path=SOURCE_ROOT+'/ADM1/geoBoundaries-TUR-ADM1.geojson'
    source_doc=json.loads(git_blob(source_path)); source_features=source_doc['features']; source_meta=json.loads(git_blob(source_meta_path))
    adm1_doc=json.loads(git_blob(adm1_path)); adm1_features=adm1_doc['features']
    if len(source_features)!=973 or len(adm1_features)!=81: raise SystemExit('Pinned source feature count changed.')
    source={}
    for f in source_features:
        p=f['properties']; key='gb:TUR:ADM2:'+p['shapeID']
        if key in source: raise SystemExit('Duplicate source ID: '+key)
        source[key]=f
    if not wanted<=set(source): raise SystemExit('Issue scope missing source IDs.')

    index_raw=git_blob('data/world-index.json'); hierarchy_raw=git_blob('data/hierarchy.json')
    granularity_raw=git_blob('data/granularity-review-evidence.json')
    handoffs_raw=git_blob('data/macro-foundation/regional-handoffs.json.gz')
    membership_raw=git_blob('data/macro-foundation/current-membership-inventory.json.gz')
    macro=json.loads(gzip.decompress(handoffs_raw)); region=next(x for x in macro['regions'] if x['region_id']==scope['region_id'])
    if region['envelope']['geometry_sha256']!=scope['frozen_region_geometry_sha256'] or region['envelope']['member_location_ids_sha256']!=scope['frozen_region_member_ids_sha256']:
        raise SystemExit('Macro envelope pins mismatch.')
    if region['regional_interiors_approved'] or region['location_attribute_imports_ready'] or not region['own_boundary_approved']:
        raise SystemExit('Unexpected macro geography approval gate state.')
    index=json.loads(index_raw); hierarchy={x['id']:x for x in json.loads(hierarchy_raw)}
    atlas={}; atlas_path={}; index_part_hashes={}
    for rel in index['parts']:
        raw=git_blob('data/'+rel); index_part_hashes['data/'+rel]=sha(raw)
        for f in json.loads(raw)['features']:
            key=f.get('properties',{}).get('id')
            if key in wanted:
                if key in atlas: raise SystemExit('Duplicate Atlas identity: '+key)
                atlas[key]=f; atlas_path[key]='data/'+rel
    if set(atlas)!=wanted: raise SystemExit('Atlas subject IDs differ from issue scope.')

    parents=[]
    for f in adm1_features:
        p=f['properties']; parents.append({'name':p['shapeName'],'geometry':canonical_land(shape(f['geometry'])),'id':p.get('shapeID')})
    flags_doc=json.loads(granularity_raw)
    turkey=next(x for x in flags_doc['territories'] if x['reference_iso']=='TUR')
    prior_flags={x['id']:x for x in turkey['flagged_locations']}
    source_name_counts=collections.Counter(norm(f['properties']['shapeName']) for f in source_features)
    rows=[]
    for identity in sorted(ids):
        af=atlas[identity]; ap=af['properties']; meta=ap.get('metadata',{})
        sf=source[identity]; sp=sf['properties']
        sg=canonical_land(shape(sf['geometry'])); ag=canonical_land(shape(af['geometry']))
        sa=land_area_m2(sg); aa=land_area_m2(ag)
        inter=polygonal_area(ag.intersection(sg)); union=aa+sa-inter
        iou=inter/union if union else 0.0
        overlaps=[]
        for par in parents:
            area=polygonal_area(sg.intersection(par['geometry']))
            if area>0: overlaps.append((area,par))
        overlaps.sort(key=lambda x:(-x[0],norm(x[1]['name'])))
        if not overlaps: raise SystemExit('No ADM1 overlap: '+identity)
        declared_id=ap.get('parent_id'); declared=hierarchy.get(declared_id,{})
        top_area,top=overlaps[0]; second_area,second=overlaps[1] if len(overlaps)>1 else (0,None)
        name=sp['shapeName']; key=norm(name); prior=prior_flags.get(identity,{})
        source_component_count=parts(sg); atlas_component_count=parts(ag)
        rows.append({
            'id':identity,'atlas_name':ap['name'],'source_shape_id':sp['shapeID'],'source_name':name,
            'atlas_source_name_exact_match':ap['name']==name,'atlas_source_name_normalized_match':norm(ap['name'])==key,
            'source_shape_type':sp.get('shapeType'),'source_shape_group':sp.get('shapeGroup'),
            'source_has_named_parent_id':any(k.casefold() in {'parent','parentid','parent_id','adm1_id'} for k in sp),
            'atlas_declared_parent_id':declared_id,'atlas_declared_parent_name':declared.get('name'),
            'parent_id_in_issue_province_scopes':declared_id in province,
            'atlas_source_role':meta.get('source_role'),'atlas_administrative_level':meta.get('administrative_level'),
            'source_components':source_component_count,'atlas_components':atlas_component_count,
            'source_name_is_generic_label':key in GENERIC,'source_name_remainder_or_city_centre_marker':bool(MARKER.search(name)),
            'source_name_has_merkez_marker':'merkez' in key,'source_name_is_standalone_merkez':key=='merkez',
            'source_name_repeated_nationally':source_name_counts[key]>1,
            'source_name_equals_declared_parent':key==norm(str(declared.get('name',''))),
            'source_area_km2':round(sa/1e6,6),'atlas_source_iou':round(iou,9),
            'atlas_area_covered_by_source':round(inter/aa,9) if aa else 0,
            'source_area_covered_by_atlas':round(inter/sa,9) if sa else 0,
            'source_adm1_top_overlap_name':top['name'],'source_adm1_top_overlap_share':round(top_area/sa,9) if sa else 0,
            'source_adm1_runner_up_name':second['name'] if second else None,'source_adm1_runner_up_share':round(second_area/sa,9) if sa else 0,
            'source_adm1_top_name_matches_declared_parent':norm(top['name'])==norm(str(declared.get('name',''))),
            'source_adm1_parent_area_share':round(sa/land_area_m2(top['geometry']),9),
            'prior_screen_flags':prior.get('reasons',[]),'prior_screen_parent_overlap':prior.get('parent_overlap'),'prior_screen_components':prior.get('components'),
            'baseline_containing_file':atlas_path[identity],
            'classification':'insufficient-evidence',
            'reason':'The 2021-claimed OSM-derived source identifies a district-like unit, but no authoritative, same-vintage official ID/name/parent and boundary crosswalk was retained for this row. Name/identity match and 2021 ADM1 spatial overlap are corroborative screens only; neither proves legal status, exact parent, completeness, or boundary truth.'
        })

    province_summary=[]
    for pid,p in sorted(province.items(),key=lambda x:norm(x[1]['name'])):
        members=[r for r in rows if r['atlas_declared_parent_id']==pid]
        matches=[f for f in adm1_features if norm(f['properties']['shapeName'])==norm(p['name'])]
        province_summary.append({'province_id':pid,'name':p['name'],'scope_member_count':len(p['owned_location_ids']),'atlas_children_count':len(members),'adm1_source_name_match_count':len(matches),'adm1_source_boundary_ids':[x['properties']['shapeID'] for x in matches]})
    # Geometry control on a small real polygon and a deliberately translated clone.
    g=canonical_land(shape(source_features[0]['geometry'])); control_inter=polygonal_area(g.intersection(g)); control_iou=control_inter/(2*land_area_m2(g)-control_inter)
    shifted=translate(g,xoff=10.0); ni=polygonal_area(g.intersection(shifted)); nu=land_area_m2(g)+land_area_m2(shifted)-ni; negative_iou=ni/nu
    if abs(control_iou-1)>1e-12 or negative_iou>1e-8: raise SystemExit('Geometry controls failed.')
    count={
        'exact_issue_ids':len(ids),'unique_atlas_features':len(atlas),'unique_source_features':len(source),
        'source_geojson_feature_count':len(source_features),'source_metadata_declared_count':int(source_meta['admUnitCount']),
        'source_metadata_file_count_difference':int(source_meta['admUnitCount'])-len(source_features),
        'complete_province_scopes':len(province),'province_parent_id_membership_pass':sum(r['parent_id_in_issue_province_scopes'] for r in rows),
        'atlas_source_name_exact_matches':sum(r['atlas_source_name_exact_match'] for r in rows),
        'declared_parent_equals_2021_ADM1_top_overlap_name':sum(r['source_adm1_top_name_matches_declared_parent'] for r in rows),
        'top_ADM1_source_overlap_at_least_95pct':sum(r['source_adm1_top_overlap_share']>=.95 for r in rows),
        'source_multipart':sum(r['source_components']>1 for r in rows),'atlas_multipart':sum(r['atlas_components']>1 for r in rows),
        'source_multipart_atlas_singlepart':sum(r['source_components']>1 and r['atlas_components']==1 for r in rows),
        'possible_merkez_names':sum(r['source_name_has_merkez_marker'] for r in rows),'standalone_merkez_names':sum(r['source_name_is_standalone_merkez'] for r in rows),
        'generic_names':sum(r['source_name_is_generic_label'] for r in rows),'remainder_or_centre_marker_names':sum(r['source_name_remainder_or_city_centre_marker'] for r in rows),
        'repeated_source_names_nationally':sum(r['source_name_repeated_nationally'] for r in rows),
        'same_name_collision_groups_in_scope':sum(1 for _,n in collections.Counter(norm(r['source_name']) for r in rows).items() if n>1),
        'subjects_in_scope_name_collisions':sum(n for n in collections.Counter(norm(r['source_name']) for r in rows).values() if n>1),
        'atlas_source_iou_below_0_90':sum(r['atlas_source_iou']<.90 for r in rows),
        'source_name_equals_declared_parent':sum(r['source_name_equals_declared_parent'] for r in rows),
        'children_over_half_source_parent_area':sum(r['source_adm1_parent_area_share']>.5 for r in rows),
        'minimum_atlas_source_iou':min(r['atlas_source_iou'] for r in rows),'maximum_atlas_source_iou':max(r['atlas_source_iou'] for r in rows),
        'minimum_source_in_declared_top_ADM1_share':min(r['source_adm1_top_overlap_share'] for r in rows),
        'minimum_atlas_area_covered_by_source':min(r['atlas_area_covered_by_source'] for r in rows),
        'maximum_atlas_area_covered_by_source':max(r['atlas_area_covered_by_source'] for r in rows),
        'minimum_source_area_covered_by_atlas':min(r['source_area_covered_by_atlas'] for r in rows),
        'maximum_source_area_covered_by_atlas':max(r['source_area_covered_by_atlas'] for r in rows),
        'prior_weak_parent_flags':sum('weak-source-parent-match' in r['prior_screen_flags'] for r in rows),
        'prior_multipart_flags':sum('multipart-footprint' in r['prior_screen_flags'] for r in rows),
        'rows_insufficient_evidence':sum(r['classification']=='insufficient-evidence' for r in rows)
    }
    basefiles={x['path']:x['sha256'] for x in receipt_doc['baseline_files']}
    inputs={'scope_sha256':sha(scope_raw),'source_files':{k:v['sha256'] for k,v in sorted(source_receipts.items())},'baseline_files':basefiles,'atlas_index_part_hashes':dict(sorted(index_part_hashes.items()))}
    report={'version':1,'issue_number':73,'baseline_commit':BASELINE,'region_id':scope['region_id'],'fixed_macro_envelope':{'geometry_sha256':region['envelope']['geometry_sha256'],'member_location_ids_sha256':region['envelope']['member_location_ids_sha256'],'own_boundary_approved':region['own_boundary_approved'],'regional_interiors_approved':region['regional_interiors_approved'],'location_attribute_imports_ready':region['location_attribute_imports_ready']},'scope':{'area_scopes':scope['area_scopes'],'subject_ids_sha256':scope['member_location_ids_sha256'],'subject_count':len(ids),'province_scopes':province_summary,'owned_path':scope['owned_evidence_path']},'inputs':inputs,'counts':count,'geometry_method':{'helper_version':VERSION,'method':'WGS84 straight-source-edge ellipsoidal area via scripts/evidence/geometry.py; canonical longitude-first EPSG:4326 polygons','controls':{'identical_geometry_iou':control_iou,'translated_geometry_iou':negative_iou},'interpretation':'Comparative source/Atlas and source/ADM1 screens; no legal boundary or administrative-parent proof.'},'source_metadata':{'boundary_year':source_meta['boundaryYear'],'source':source_meta['boundarySource'],'canonical_role':source_meta['boundaryCanonical'],'license':source_meta['boundaryLicense'],'source_data_update':source_meta['sourceDataUpdateDate'],'build_date':source_meta['buildDate'],'declared_feature_count':int(source_meta['admUnitCount']),'actual_feature_count':len(source_features)},'findings':rows,'limits':['Only 228 of the 911 Atlas members in the Turkey area are in this packet; the area is partial.','The 228 subjects comprise 20 full province groups, but do not constitute a whole-country or whole-region review.','The OSM-derived source contains no named province-parent ID; source/ADM1 overlay uses an ADM1 layer from the same geoBoundaries release, not official legal parent evidence.','No official 2021 exact ID/name/immediate-parent roster or authoritative 2021 district boundaries were retained; all per-row legal and boundary status remains insufficient-evidence.','The source metadata reports 999 units while its retained raw ADM2 file has 973 features. TurkStat 2021 reports 922 districts excluding central districts; numeric relationships do not establish exact roster equivalence or completeness.','Current HGM boundaries are explicitly indicative and not official; their current vintage cannot settle 2021 status.','Review of inherited weak-parent, multipart, central-district, coastline/island, and cross-border boundary findings is diagnostic and incomplete where official source comparison is unavailable.','No regional interior approval, geography correction, production data change, publication, or import authorization is claimed.']}
    raw=(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode(); OUTPUT.write_bytes(raw)
    print(json.dumps({'output':str(OUTPUT.relative_to(ROOT)),'sha256':sha(raw),'counts':count,'parent_provinces':len(province_summary)},ensure_ascii=False,sort_keys=True))
if __name__=='__main__': main()
