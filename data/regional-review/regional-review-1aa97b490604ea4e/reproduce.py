#!/usr/bin/env python3
"""Reproduce bounded subject identity and screening checks for issue #454.

Geometry overlays use only the explicitly diagnostic New Caledonia repair clone;
source bytes are never modified. This does not certify any geography.
"""
from __future__ import annotations
import csv, hashlib, json
from pathlib import Path
import sys
import re
import subprocess
sys.path[:0] = [str(Path(__file__).resolve().parents[3] / 'scripts'), str(Path(__file__).resolve().parents[3] / 'scripts' / 'evidence')]
from pyproj import Transformer
from shapely.geometry import shape, Polygon, MultiPolygon, GeometryCollection
from shapely.ops import transform
from shapely import make_valid
from shapely.validation import explain_validity
from geometry import canonical_land, land_area_m2, METHOD as GEOMETRY_METHOD

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
BASELINE_COMMIT = '5f6ab02338a07fd4b3d1cf82d58b96bc84b70312'
SCOPE = json.loads((ROOT / 'scope.json').read_text())
ISSUE = json.loads((ROOT / 'issue-scope-pinned.json').read_text())
assert ISSUE['number'] == 454 and ISSUE['state'] == 'open'
marker=ISSUE['body'].find('Machine-readable exact workload scope')
scope_match=re.search(r'```json\s*\n([\s\S]*?)\n```',ISSUE['body'][marker:])
assert scope_match and json.loads(scope_match.group(1)) == SCOPE, 'packet scope differs from issue exact scope'
work_match=re.search(r'<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->',ISSUE['body'])
assert work_match and json.loads(work_match.group(1))['owned_paths'] == [str(ROOT.relative_to(REPO))+'/']
assert SCOPE['release']['id'] == 'geography:review:df86cbaeaf2e18f16ddf2906ef089768baac22f4428e28ed0a4724296cbb413e'
def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def baseline_blob(relative):
    return subprocess.run(['git','-C',str(REPO),'show',f'{BASELINE_COMMIT}:{relative}'],check=True,stdout=subprocess.PIPE).stdout
def canonical_ids(ids): return '\n'.join(ids).encode()
def polygon_components(g):
    if isinstance(g, Polygon): return 1
    if isinstance(g, MultiPolygon): return len(g.geoms)
    if isinstance(g, GeometryCollection): return sum(polygon_components(part) for part in g.geoms)
    return 0
def checked_land(g):
    try: return canonical_land(g), None
    except ValueError as e: return None, str(e)
assert len(SCOPE['member_location_ids']) == SCOPE['location_count'] == 25
assert hashlib.sha256(canonical_ids(SCOPE['member_location_ids'])).hexdigest() == SCOPE['member_location_ids_sha256']

# Independent positive and negative identity controls against exact pinned IDs.
all_features = {}
containing_files = {}
baselines = {}
index_bytes=baseline_blob('data/world-index.json')
world_index=json.loads(index_bytes)
baselines['data/world-index.json']={'sha256':hashlib.sha256(index_bytes).hexdigest(),'bytes':len(index_bytes)}
registry_bytes=baseline_blob('data/administrative-sources.json')
baselines['data/administrative-sources.json']={'sha256':hashlib.sha256(registry_bytes).hexdigest(),'bytes':len(registry_bytes)}
for path in ['data/validation/macro-publication-v5.json','data/macro-foundation/macro-certificate.json','data/hierarchy.json','data/macro-foundation/regional-handoffs.json.gz','data/macro-foundation/current-membership-inventory.json.gz']:
    content=baseline_blob(path)
    baselines[path]={'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content)}
release_record=json.loads(baseline_blob('data/validation/macro-publication-v5.json'))
assert release_record['release']['id']==SCOPE['release']['id']
assert release_record['release']['hierarchy_sha256']==SCOPE['release']['hierarchy_sha256']
assert release_record['release']['footprints_sha256']==SCOPE['release']['footprints_sha256']
assert release_record['macro_certificate_sha256']==SCOPE['macro_certificate_sha256']
for relative in world_index['parts']:
    path='data/'+relative
    content=baseline_blob(path)
    doc = json.loads(content)
    matched=[]
    for f in doc['features']:
        ident = f.get('properties', {}).get('id')
        if ident in SCOPE['member_location_ids']:
            assert ident not in all_features
            all_features[ident] = f
            containing_files[ident]=path
            matched.append(ident)
    if matched: baselines[path] = {'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)}
assert set(all_features) == set(SCOPE['member_location_ids'])
assert 'not-a-real-location-id' not in all_features

source_cfg = {
 'FJI': ('sources/fiji-2007-census-province.geojson','shapeID'),
 'SLB': ('sources/solomon-islands-natural-earth-adm1.geojson','shapeID'),
 'VUT': ('sources/vanuatu-2017-adm1.geojson','shapeID'),
}
source_ledger=json.loads((ROOT/'sources.json').read_text())
retained={row['path']:row for row in source_ledger['files']}
actual={p.relative_to(ROOT).as_posix() for p in (ROOT/'sources').rglob('*') if p.is_file()}
assert actual == set(retained), 'retained source inventory/path set changed'
for relative,row in retained.items():
    path=ROOT/relative
    assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], f'source bytes changed: {relative}'
acquisition=json.loads((ROOT/'source-acquisition.json').read_text())
for row in acquisition:
    if row.get('path'):
        path=ROOT/row['path']
        assert row['path'] in retained and sha(path)==row['sha256'] and path.stat().st_size==row['bytes'], f'acquisition receipt mismatch: {row["source_id"]}'
    for part in row.get('partition_files',[]):
        path=ROOT/part['path']
        assert part['path'] in retained and sha(path)==part['sha256'] and path.stat().st_size==part['bytes'], f'partition receipt mismatch: {row["source_id"]}'
source_features = {}
for code, (relative, key) in source_cfg.items():
    doc=json.loads((ROOT/relative).read_text()); source_features[code]={f['properties'][key]:f for f in doc['features']}
ncl_dir=ROOT/'sources/new-caledonia-province-parts'
ncl_features=[json.loads(p.read_text())['features'][0] for p in sorted(ncl_dir.glob('*.geojson'))]
assert len(ncl_features)==3 and {f['properties']['nom_fichier'] for f in ncl_features}=={'PROVINCE_NORD','PROVINCE_DES_ILES','PROVINCE_SUD'}
def match_native_feature(collection, native_id, expected_name):
    feature=collection.get(native_id)
    return feature if feature and feature['properties'].get('shapeName','').casefold()==expected_name.casefold() else None
assert match_native_feature(source_features['FJI'],'__deliberately_absent__','Ba') is None
fixture=next(f for f in source_features['FJI'].values() if f['properties']['shapeName']=='Ba')
assert match_native_feature(source_features['FJI'],fixture['properties']['shapeID'],'wrong name') is None

rows=[]
for ident in SCOPE['member_location_ids']:
    atlas=all_features[ident]; p=atlas['properties']; code=ident.split(':')[1] if ident.startswith('gb:') else 'NCL'
    source=None; match='official feature matched by reviewed province name' if code=='NCL' else 'native source shapeID equals atlas ID suffix'
    if code in source_cfg:
        native=ident.rsplit(':',1)[-1]
        source=match_native_feature(source_features[code],native,p['name'])
        assert source is not None, f'missing native source identity: {ident}'
        name=source['properties'].get('shapeName','')
    elif code=='NCL':
        names={'NCL-559':'PROVINCE_NORD','NCL-1258':'PROVINCE_DES_ILES','NCL-1259':'PROVINCE_SUD'}
        name=names[ident]
        source=next(f for f in ncl_features if f['properties'].get('nom_fichier')==name)
        match='official GeoReP province feature mapped from source attributes; raw geometry invalid'
    else: raise AssertionError(code)
    finding = 'insufficient-evidence'
    boundary_note = 'Identity and tier corroborated; exact current footprint, completeness and official current boundary authority remain unproven.'
    if ident == 'gb:FJI:ADM2:14151628B71764118664060':
        finding = 'correction-needed'
        boundary_note = 'Official Fiji Prime Minister source describes Rotuma as administratively incorporated as a dependency under the Rotuma Act; census/geoboundaries source labels it with the ADM2 province roster. The atlas province parent is a semantic/hierarchy mismatch to resolve.'
    if p['name'] == 'Lau':
        finding = 'correction-needed'
        boundary_note = 'The retained GeoBoundaries layer uses the same source identity as the Atlas record but a WGS84 source-edge screening comparison finds material footprint disagreement. Due unresolved 2007/2020 vintage and retained-byte hash mismatch, neither version can be accepted as authoritative; verify provenance and boundary source before correction.'
    if code == 'NCL':
        finding = 'correction-needed'
        boundary_note = 'Current official open GeoReP province source matches province role/names, but all source polygons are topologically invalid and diagnostic overlays materially diverge from the Natural Earth fallback. No repair or replacement is safe without source-owner clarification and engineering review.'
    atlas_geom=shape(atlas['geometry']); source_geom=shape(source['geometry'])
    if source_geom.is_valid:
        ga,err_a=checked_land(atlas_geom); gs,err_s=checked_land(source_geom)
        if ga is not None and gs is not None:
            overlap=land_area_m2(ga.intersection(gs)); union=land_area_m2(ga.union(gs))
            jaccard=overlap/union if union else None; symmetric_difference=land_area_m2(ga.symmetric_difference(gs))/1e6
            skip_reason=None
        else:
            jaccard=None; symmetric_difference=None; skip_reason=f'helper rejected input: {err_s or err_a}'
    else:
        jaccard=None; symmetric_difference=None; skip_reason='source geometry invalid; overlay not attempted'
    rows.append({'location_id':ident,'name':p['name'],'baseline_containing_file':containing_files[ident],'administrative_level':p.get('metadata',{}).get('administrative_level'),
      'source_identity':match,'source_name':name,'parent_id':p.get('parent_id'),
      'source_geometry_type':source_geom.geom_type,'source_polygon_components':polygon_components(source_geom),
      'source_vertex_count':sum(len(r.coords) for poly in ([source_geom] if isinstance(source_geom,Polygon) else source_geom.geoms if isinstance(source_geom,MultiPolygon) else []) for r in [poly.exterior,*poly.interiors]),
      'source_geometry_valid':source_geom.is_valid,'atlas_vs_source_jaccard':jaccard,
      'atlas_vs_source_symmetric_difference_km2':symmetric_difference,'overlay_screen_skip_reason':skip_reason,
      'finding':finding,'boundary_note':boundary_note})

# Cohort screens expose tier and fragmentation signals without treating a
# feature count, union, or absence of overlap as a completeness certificate.
cohorts=[]
for code, (relative, key) in source_cfg.items():
    doc=json.loads((ROOT/relative).read_text())
    ids=[ident for ident in SCOPE['member_location_ids'] if ident.startswith('gb:'+code+':')]
    geoms=[shape(f['geometry']) for f in doc['features']]
    projected=[checked_land(g) for g in geoms]
    intersections=[]
    for i,(a,err_a) in enumerate(projected):
        for j,(b,err_b) in enumerate(projected[i+1:],i+1):
            if a is None or b is None: continue
            intersection=a.intersection(b) if a.intersects(b) else None
            area=land_area_m2(intersection) if intersection is not None and not intersection.is_empty and intersection.geom_type in ('Polygon','MultiPolygon') else 0
            if area>1: intersections.append({'feature_a':doc['features'][i]['properties'].get('shapeName'), 'feature_b':doc['features'][j]['properties'].get('shapeName'), 'overlap_m2':area})
    cohorts.append({'source_code':code,'source_path':relative,'source_feature_count':len(doc['features']),
      'scoped_feature_count':len(ids),'out_of_scope_sibling_count':len(doc['features'])-len(ids),
      'multipolygon_feature_count':sum(g.geom_type=='MultiPolygon' for g in geoms),
      'invalid_feature_count':sum(not g.is_valid for g in geoms),'helper_method_rejected_features':[{'name':doc['features'][i]['properties'].get('shapeName'),'reason':e} for i,(_,e) in enumerate(projected) if e],
      'pairwise_overlap_pairs_over_1m2':intersections,
      'completeness_limit':'Cohort counts and internal overlap screening cannot identify omitted islands or gaps against an authoritative territory boundary.'})

# Official NCL source validity and overlay screen. MakeValid is a disposable
# analytical clone, never a candidate replacement or silent correction.
transformer=Transformer.from_crs('EPSG:4326','EPSG:3163',always_xy=True)
def projected(g): return transform(transformer.transform,g)
raw={'features':ncl_features}
by_id={'NCL-559':'PROVINCE_NORD','NCL-1258':'PROVINCE_DES_ILES','NCL-1259':'PROVINCE_SUD'}
ncl_results=[]
for ident, source_name in by_id.items():
    atlas=shape(all_features[ident]['geometry']); src=next(f for f in raw['features'] if source_name in json.dumps(f['properties'],ensure_ascii=False))
    original=shape(src['geometry']); fixed=make_valid(original)
    a=projected(atlas); b=projected(fixed)
    inter=a.intersection(b).area; union=a.union(b).area
    ncl_results.append({'location_id':ident,'source_feature':source_name,'source_valid':original.is_valid,
      'source_validity_reason':explain_validity(original),
      'source_repair_used_only_for_diagnostic':True,'atlas_area_km2':a.area/1e6,'diagnostic_source_area_km2':b.area/1e6,
      'atlas_coverage':inter/a.area,'source_coverage':inter/b.area,'jaccard':inter/union,'symmetric_difference_km2':a.symmetric_difference(b).area/1e6,
      'interpretation':'Large disagreement is a review signal only; invalid-source repair semantics and source boundary generalization prevent deciding which footprint is correct.'})

out={'issue':454,'retrieved_at':'2026-10-05','baseline_commit':BASELINE_COMMIT,'scope_id_count':len(SCOPE['member_location_ids']),
 'scope_member_ids_sha256':SCOPE['member_location_ids_sha256'],'positive_control':'all 25 pinned scope IDs found exactly once in pinned baseline partitions and source native IDs/name identity reproduced',
 'pinned_release_record':{'release':release_record['release'],'macro_certificate_sha256':release_record['macro_certificate_sha256'],'issue_scope_matches':True},
 'negative_controls':[{'control':'absent scope location ID','passed':'not-a-real-location-id' not in all_features},{'control':'absent native source ID','passed':match_native_feature(source_features['FJI'],'__deliberately_absent__','Ba') is None},{'control':'wrong native-source display name','passed':match_native_feature(source_features['FJI'],fixture['properties']['shapeID'],'wrong name') is None}],
 'baseline_files':baselines,'subjects':rows,'source_cohort_screens':cohorts,'new_caledonia_diagnostic_overlays':ncl_results,
 'runtime':{'python':sys.version.split()[0],'shapely':__import__('shapely').__version__,'pyproj':__import__('pyproj').__version__,'proj':__import__('pyproj').proj_version_str},
 'geometry_method':GEOMETRY_METHOD,
 'ncl_diagnostic_method':'Unofficial diagnostic only: Shapely make_valid clone; project source and atlas coordinates EPSG:4326 to EPSG:3163 with pyproj Transformer(always_xy=True); calculate planar area/intersection in m2. Source GeoJSON retrieved using maxAllowableOffset=0.00005 and geometryPrecision=6. Original source bytes remain unchanged; these outputs do not assert legal boundary correctness.',
 'limitations':['Source identity and unit counts do not establish boundary correctness.','Fiji 2007 census layer and 2017 statistical province labels establish roster, not exact official contemporary footprints; geoBoundaries catalog says 2020, source underlying census says 2007.','Vanuatu OSM-derived 2017/2018 province layer has ODbL obligations and no consulted legally authoritative province boundary dataset; government profiles/maps corroborate names and island groupings at generalized scale only.','Solomon Islands Temotu source is Natural Earth 2021 generalized public-domain ADM1; official source confirms administrative role and broad geography, not its precise boundary.','New Caledonia official GeoReP geometry is invalid; MakeValid clone is diagnostic only; overlays are not authoritative adjudication.','No official neighboring granularity dataset was used to assert comprehensive sub-province islands or coastal/islet coverage.']}
(ROOT/'reproduction.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
with (ROOT/'unit-review.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys(),lineterminator='\n');w.writeheader();w.writerows(rows)
print(json.dumps({'subjects':len(rows),'all_identity_controls':'passed','baseline_files':baselines,'ncl':ncl_results},indent=2))
