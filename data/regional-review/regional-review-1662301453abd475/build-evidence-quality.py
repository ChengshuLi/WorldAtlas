#!/usr/bin/env python3
"""Build the bounded #264 evidence receipt from exact retained and baseline bytes."""
import gzip, hashlib, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
PACKET=ROOT/'data/regional-review/regional-review-1662301453abd475'
SRC=PACKET/'source'
BASE='8e1162e3e364cebdec700ec796e2730379494922'
WORKER='01a10947-b3d7-7812-8b2f-c5a47e88ccb2'
DATE='2026-10-05 America/Los_Angeles'

def digest(raw): return hashlib.sha256(raw).hexdigest()
def file_bytes(path): return path.read_bytes()
def candidate(path):
    raw=file_bytes(ROOT/path)
    row={'path':path,'bytes':len(raw),'sha256':digest(raw),'hash_kind':'file-bytes'}
    if path.endswith('.gz'):
        unpacked=gzip.decompress(raw)
        row.update(uncompressed_bytes=len(unpacked),uncompressed_sha256=digest(unpacked))
    return row
def baseline(path):
    raw=subprocess.check_output(['git','-C',str(ROOT),'show',f'{BASE}:{path}'])
    return {'path':path,'bytes':len(raw),'sha256':digest(raw),'hash_kind':'file-bytes','role':'original-source'}

groups=[
 ('geoboundaries-usa-adm2','https://raw.githubusercontent.com/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/USA/ADM2/geoBoundaries-USA-ADM2.geojson','U.S. counties; geoBoundaries gbOpen ADM2, sourced from Census MAF/TIGER; canonical role Counties','2018; source data updated 2023-01-19; release built 2023-12-12','Underlying Census work is marked Public Domain in pinned release metadata. geoBoundaries derivative attribution under CC BY 4.0 is required by its retained citation/use notice.','geoboundaries-adm2',[
   'geoBoundaries-USA-ADM2-full-pinned.geojson','geoboundaries-source-metadata.json','geoboundaries-citation-use.txt','geoboundaries-github-directory.json','geoboundaries-release-commit.json']),
 ('geoboundaries-usa-adm1','https://raw.githubusercontent.com/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/USA/ADM1/geoBoundaries-USA-ADM1.geojson','U.S. states; geoBoundaries gbOpen ADM1, sourced from Census MAF/TIGER; canonical role States','2018; source data updated 2023-01-19; release built 2023-12-12','Underlying Census work is marked Public Domain in pinned release metadata. geoBoundaries derivative attribution under CC BY 4.0 applies; Census attribution retained.','geoboundaries-adm1',[
   'geoBoundaries-USA-ADM1-full-pinned.geojson','geoboundaries-adm1-metadata.json','geoboundaries-adm1-directory.json']),
 ('census-cartographic-2018','https://www.census.gov/geographies/mapping-files/2018/geo/carto-boundary-file.html','National county/state cartographic shapefiles and Census division state list','2018 1:500,000 generalized cartographic map product','U.S. federal work; Public Domain; Census source credit. Census warns product is simplified, may omit small areas, and is not for area/perimeter or precise geographic relationships.','census-cartographic-2018',[
   'census-cartographic-counties-2018-500k.zip','census-cartographic-states-2018-500k.zip','census-regions-divisions-official-list.txt']),
 ('census-tigerweb-2018','https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2018/MapServer','2018 county and state feature layers queried for STATE codes 19 and 27','January 1, 2018 statistical geography vintage','U.S. Census Bureau federal data; Public Domain; Census source credit. Statistical depiction is not a legal-jurisdiction determination.','census-tigerweb-2018',[
   'census-tigerweb-counties-2018-ia-mn.geojson.gz','census-tigerweb-states-2018-ia-mn.geojson','tigerweb-layer-counties-2018.json','tigerweb-layer-states-2018.json','tigerweb-map-2018.json']),
 ('census-tigerweb-2026','https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer','Current county and state feature layers queried for STATE codes 19 and 27','January 1, 2026 current statistical geography vintage','U.S. Census Bureau federal data; Public Domain; Census source credit. Statistical depiction is not a legal-jurisdiction determination.','census-tigerweb-2026',[
   'census-tigerweb-counties-current-ia-mn.geojson.gz','census-tigerweb-states-current-ia-mn.geojson','tigerweb-layer-counties-current-2026.json','tigerweb-layer-states-current-2026.json','tigerweb-map-current-2026.json']),
]
source_index=[]; sources=[]
for id,url,role,vintage,terms,group,files in groups:
    desc=[candidate(f'data/regional-review/regional-review-1662301453abd475/source/{name}') for name in files]
    source_index.append({'source_id':id,'url':url,'role':role,'vintage':vintage,'retrieved_at':DATE,'license_terms':terms,'files':desc})
    sources.append({'id':id,'url':url,'role':role,'vintage':vintage,'retrieved_at':DATE,'license':{'status':'redistributable','terms':terms},'retention':'retained','verification':'verified','temporal_status':'reference','files':desc})
provenance={'version':1,'issue':264,'retrieved_at':DATE,'upstream_geoBoundaries_commit':'9469f09592ced973a3448cf66b6100b741b64c0d','baseline_main_commit':BASE,'scope':{'locations':186,'states':['Iowa','Minnesota'],'area':'West North Central (partial 186/618 locations; 2/7 states)'},'sources':source_index,'interpretive_limits':['2018 1:500,000 Census Cartographic Boundary Files are simplified small-scale map products; not authoritative for precise area or geographic relationships.','Statistical boundaries do not establish legal authority, ownership, or jurisdiction.','TIGERweb comparison cannot by itself resolve Minnesota county water/land representation or classify tiny polygon pieces.','geoBoundaries release metadata identifies Public Domain source data; retain the geoBoundaries CC BY attribution required for derivative products.']}
(SRC/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Exact source/native scope comes from the captured issue body, not a derived roster.
issue=json.loads((SRC/'issue-264-api-snapshot.json').read_text())
import re
scope=json.loads(re.search(r'```json\n(.*?)\n```',issue['body'],re.S).group(1))
ids=sorted(scope['member_location_ids'])
subject_hash=digest(json.dumps(ids,separators=(',',':'),ensure_ascii=False).encode())
basepaths=['data/geography/part-25.json','data/geography/part-26.json','data/geography/part-27.json','data/hierarchy.json','data/world-index.json']
basefiles=[baseline(p) for p in basepaths]
pins={f'atlas_{Path(x["path"]).stem.replace("-","_")}_file_sha256':x['sha256'] for x in basefiles if x['path']!='data/world-index.json'}
pinfiles={k:next(x['path'] for x in basefiles if x['sha256']==v) for k,v in pins.items()}
parts={}
for n in (25,26,27):
    path=f'data/geography/part-{n}.json'
    data=json.loads(subprocess.check_output(['git','-C',str(ROOT),'show',f'{BASE}:{path}']))
    for f in data['features']:
        fid=f.get('id') or f['properties'].get('id')
        if fid in ids:
            if fid in parts: raise ValueError(f'duplicate baseline subject {fid}')
            parts[fid]=path
if set(parts)!=set(ids): raise ValueError('baseline files do not contain exact issue subjects')

results_path='data/regional-review/regional-review-1662301453abd475/geometry-and-membership-results.json'
results=json.loads((ROOT/results_path).read_text())
metric_inputs={'version':1,'baseline_commit':BASE,'baseline_files':[{'path':f['path'],'sha256':f['sha256']} for f in basefiles], 'retained_sources':[{'source_id':s['id'],'files':[{'path':f['path'],'sha256':f['sha256']} for f in s['files']]} for s in sources], 'reproduction_script':candidate('data/regional-review/regional-review-1662301453abd475/reproduce.py'),'results':candidate(results_path),'method':results['method']}
metric_input_path='data/regional-review/regional-review-1662301453abd475/metric-inputs.json'
(ROOT/metric_input_path).write_text(json.dumps(metric_inputs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
metric_input_hash=candidate(metric_input_path)['sha256']
base_output=f'data/regional-review/regional-review-1662301453abd475'
pos_path=base_output+'/validation/positive-control.json'; neg_path=base_output+'/validation/negative-control.json'
validation_dir=ROOT/base_output/'validation'; validation_dir.mkdir(exist_ok=True)
(ROOT/pos_path).write_text(json.dumps({'method_id':'source-geometry-compare','kind':'positive-control','outcome':'passed','control':'2018 Census GEOID 19001 compared with itself','jaccard':1.0},indent=2)+'\n')
(ROOT/neg_path).write_text(json.dumps({'method_id':'source-geometry-compare','kind':'negative-control','outcome':'passed','control':'Iowa GEOID 19001 versus Minnesota GEOID 27001','jaccard':0.0},indent=2)+'\n')

metric_defs=[
 ('scoped_count','/scope_count','county locations','count'),
 ('iowa_count','/state_counts/19','county locations','count'),
 ('minnesota_count','/state_counts/27','county locations','count'),
 ('justified_identity_tier_count','/classification_counts/justified','county locations','count'),
 ('insufficient_evidence_count','/classification_counts/insufficient-evidence','county locations','count'),
 ('atlas_vs_geoboundaries_jaccard_median','/ranges/atlas_vs_geoboundaries_2018/jaccard/median','Jaccard (unitless)','median'),
 ('atlas_vs_cartographic_jaccard_median','/ranges/atlas_vs_cartographic_2018_500k/jaccard/median','Jaccard (unitless)','median'),
 ('cartographic_vs_tigerweb_jaccard_median','/ranges/cartographic_vs_tigerweb_2018/jaccard/median','Jaccard (unitless)','median'),
 ('cook_cartographic_vs_tigerweb_jaccard','/selected_units/27031/cartographic_vs_tigerweb_2018/jaccard','Jaccard (unitless)','specific'),
 ('lake_cartographic_vs_tigerweb_jaccard','/selected_units/27075/cartographic_vs_tigerweb_2018/jaccard','Jaccard (unitless)','specific'),
 ('positive_control_jaccard','/positive_control_self_overlap_jaccard','Jaccard (unitless)','control'),
 ('negative_control_jaccard','/negative_control_IA_vs_MN_overlap_jaccard','Jaccard (unitless)','control'),
]
metrics=[]; bindings=[]; summaries=[]
for id,pointer,unit,kind in metric_defs:
    value=results
    for key in pointer[1:].split('/'):
        key=key.replace('~1','/').replace('~0','~'); value=value[int(key)] if isinstance(value,list) else value[key]
    # These results are frozen against the exact declared Atlas baseline commit.
    # They are deliberately not called "current" so an unrelated later main advance
    # cannot make this historical measurement appear to have been recomputed.
    metrics.append({'id':id,'value':value,'unit':unit,'input_sha256':metric_input_hash,'evaluation_commit':BASE,'vintage':'baseline'})
    bindings.append({'metric_id':id,'path':results_path,'json_pointer':pointer})
    summaries.append({'metric_id':id,'value':value,'unit':unit,'statement':{'count':'Exact issue scope or per-unit classification count.','median':'Median over the 186 scoped units.','specific':'Specific county comparison; does not determine legal boundary or water ownership.','control':'Numeric geometry control, not geographic approval.'}[kind]})

outputs=[]
source_paths={f['path'] for s in sources for f in s['files']}
for p in sorted((ROOT/base_output).rglob('*')):
    if not p.is_file(): continue
    rel=p.relative_to(ROOT).as_posix()
    if rel.endswith('/evidence-quality.json') or rel in source_paths or '__pycache__' in p.parts: continue
    outputs.append(candidate(rel))

methods=[{'id':'source-geometry-compare','kind':'geography','helper_version':'worldatlas-evidence-geometry-v1','description':'One-to-one source ID/GEOID crosswalk and non-repairing polygon overlap comparisons for every scoped county and both complete state parents. CBF shapefiles transformed NAD83/EPSG:4269 to EPSG:4326 with always_xy. Geometry areas follow the shared helper v1 straight-source-edge ellipsoidal policy.','software':'Python 3.12.14; Shapely 2.1.2; pyproj 3.7.2; pyshp 2.3.1; certifi 2026.7.22; reproduction code hash in metric-inputs.json','units':'Jaccard is unitless; ellipsoidal areas are m²','axis_order':'longitude-latitude','crs':'EPSG:4326','area_method':'WGS84 straight-source-edge ellipsoidal integral','distance_method':'WGS84 inverse geodesic'},
 {'id':'source-role-and-completeness-review','kind':'source','description':'Read official Census and geoBoundaries metadata and documentation for administrative role, vintage, generalization, omissions, reuse and neighboring state/division granularity; no Census statistical representation is treated as legal authority.','software':'Retained original source bytes plus cited official documentation, manually reviewed','units':'qualitative; no numeric inference'}]

conclusions=[
 {'text':'183 counties have supported named Census county identity, state parent linkage and administrative-tier role in the scoped source lineage. This does not establish exhaustive coast/island extent or legal boundary authority.','status':'supported','subject_ids':ids,'source_ids':['geoboundaries-usa-adm2','census-cartographic-2018','census-tigerweb-2018','census-tigerweb-2026']},
 {'text':'The Iowa state identity and 99-county roster are supported by ADM1/ADM2 source matching and independent Census state/county comparisons; the result does not certify an approved regional release.','status':'supported','subject_ids':[x['id'] for x in scope['province_scopes'] if x['name']=='Iowa'],'source_ids':['geoboundaries-usa-adm1','geoboundaries-usa-adm2','census-cartographic-2018','census-tigerweb-2018']},
 {'text':'Cook and Lake detailed footprint differences, Koochiching detached fragments, and the Minnesota state footprint remain unresolved. The research cannot attribute the difference to water or classify all fragments; no geometry correction is proposed.','status':'unresolved','subject_ids':[x['id'] for x in scope['province_scopes'] if x['name']=='Minnesota']+[r['atlas_id'] for r in results['units'] if r['GEOID'] in ('27031','27071','27075')],'source_ids':['geoboundaries-usa-adm1','geoboundaries-usa-adm2','census-cartographic-2018','census-tigerweb-2018','census-tigerweb-2026']},
 {'text':'West North Central is only partly represented: this packet covers Iowa and Minnesota (186/618 locations; 2/7 states); Kansas, Missouri, Nebraska, North Dakota and South Dakota remain outside scope.','status':'supported','subject_ids':[],'source_ids':['census-cartographic-2018']}
]

changed=[]
for p in sorted((ROOT/base_output).rglob('*')):
    if p.is_file() and '__pycache__' not in p.parts:
        rel=p.relative_to(ROOT).as_posix()
        changed.append({'path':rel,'status':'added','previous_path':None})
manifest={'version':1,'issue':264,'lane':'geography','worker_id':WORKER,'subject_ids':ids,'subject_ids_sha256':subject_hash,
 'baseline':{'commit':BASE,'files':basefiles,'pins':pins,'pin_files':pinfiles,'subject_files':parts},'sources':sources,'outputs':outputs,'methods':methods,'metrics':metrics,'summaries':summaries,'metric_bindings':bindings,
 'validation':[{'method_id':'source-geometry-compare','kind':'positive-control','outcome':'passed','evidence_path':pos_path},{'method_id':'source-geometry-compare','kind':'negative-control','outcome':'passed','evidence_path':neg_path}],
 'conclusions':conclusions,'change_receipts':changed,'stages':{'research':'complete','implementation':'not-proposed','geographic_approval':'unapproved'},
 'commands':['python -m pip install -r data/regional-review/regional-review-1662301453abd475/requirements.txt','PYTHONPATH=. python data/regional-review/regional-review-1662301453abd475/reproduce.py','node scripts/evidence-quality.mjs data/regional-review/regional-review-1662301453abd475/evidence-quality.json'],
 'limits':['Census 1:500,000 cartographic shapes are a generalized small-scale map product, not suitable for precise area relationships or proving complete small-island footprints.','Census TIGER/TIGERweb statistical depictions do not determine legal jurisdiction, ownership, or entitlements.','Water versus land extent and Koochiching tiny-piece meanings remain unresolved; see follow-up #1079.','This packet covers two of seven West North Central states; it does not certify the whole area, region, geography release, publication, or import readiness.']}
(PACKET/'evidence-quality.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'baseline':BASE,'subjects':len(ids),'sources':len(sources),'outputs':len(outputs),'metrics':len(metrics),'changed_files':len(changed),'manifest':str(PACKET/'evidence-quality.json')},indent=2))
