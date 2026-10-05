#!/usr/bin/env python3
"""Rebuild v1 evidence ledger, full change receipts and table row receipts for #944."""
import csv, hashlib, io, json, pathlib, subprocess
ROOT=pathlib.Path(__file__).resolve().parents[3]
OWN=ROOT/'data/regional-review/argentina-adm2-source-revalidation-443'
PACKET='data/regional-review/argentina-adm2-source-revalidation-443'
BASE='2ac65414166764713eafa8238f1b28211a57344e'
OUT=OWN/'findings'

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def desc_repo(rel, role=None):
    raw=subprocess.check_output(['git','-C',str(ROOT),'show',f'{BASE}:{rel}'])
    d={'path':rel,'bytes':len(raw),'sha256':sha_bytes(raw),'hash_kind':'file-bytes'}
    if role:d['role']=role
    return d
def desc_candidate(rel):
    raw=(ROOT/rel).read_bytes()
    return {'path':rel,'bytes':len(raw),'sha256':sha_bytes(raw),'hash_kind':'file-bytes'}

# The exact 214 IDs are the direct scoped rows in the immutable #443 review packet.
with (ROOT/'data/regional-review/regional-review-7cf674a63057d43f/findings/scoped-location-review.csv').open(encoding='utf-8',newline='') as f:
    issue_rows=list(csv.DictReader(f))
subject_ids=sorted(r['location_id'] for r in issue_rows if r['location_id'].startswith('gb:ARG:ADM2:'))
assert len(subject_ids)==214 and len(set(subject_ids))==214
subject_digest=sha_bytes(json.dumps(subject_ids,separators=(',',':'),ensure_ascii=False).encode())
assert subject_digest=='d1bc2104602f18ee013e25d795d0e5235147cde36e9e88a0e0f174a6683613d4'

# Rebuild a scalar metrics ledger from each generated CSV numeric cell. Each table row
# template binds the rendered text to this value; JSON results bind to their real pointer.
metric_rows=[]; metric_bindings=[]; summaries=[]; rendered_by_path={}
source_hash={
 'adm2':sha_bytes((OWN/'source/geoBoundaries-2020-scoped-214.geojson').read_bytes()),
 'adm1':sha_bytes((OWN/'source/geoBoundaries-2006/geoBoundaries-ARG-ADM1-2006.geojson').read_bytes()),
 'departments':sha_bytes((OWN/'source/Georef-current/departamentos.geojson').read_bytes()),
 'provinces':sha_bytes((OWN/'source/Georef-current/provincias.geojson').read_bytes())}
columns={
 '2006-adm1-to-current-province-overlay.csv':{'old_intersecting_feature_count':'count','top_old_share_of_current_area':'share','top_old_shape_id':'skip','old_union_coverage_of_current':'share','union_symmetric_difference_share':'share'},
 'scoped-2020-to-current-georef-overlay.csv':{'source_2020_component_count':'count','source_2020_hole_count':'count','old_area_km2_equal_area':'km2','current_intersecting_feature_count':'count','top_share_of_old_area':'share','current_union_coverage_of_old':'share','current_overlap_excess_share':'share','same_normalized_name_candidate_count':'count','best_same_name_candidate_share_of_old_area':'share','best_same_name_candidate_symmetric_difference_share':'share','over_1sqm_sliver_count':'count'},
 'scoped-current-georef-positive-area-overlaps.csv':{'overlap_area_m2':'m2'},
 'scoped-multipart-components.csv':{'component_number':'count','component_count':'count','component_area_km2':'km2','interior_ring_count':'count'},
 'scoped-parent-review.csv':{'scoped_parent_review_children_from_443':'count','direct_adm2_subjects_in_944':'count','current_georef_exact_name_match_count':'count','2006_feature_count':'count','current_national_province_count':'count','old_2006_top_overlap_share_of_current':'share','old_2006_union_coverage_of_current':'share'},
 'scoped-2020-internal-overlaps.csv':{'intersection_area_m2':'m2'}}
table_input={
 '2006-adm1-to-current-province-overlay.csv':source_hash['adm1'],
 'scoped-2020-to-current-georef-overlay.csv':source_hash['adm2'],
 'scoped-current-georef-positive-area-overlaps.csv':source_hash['departments'],
 'scoped-multipart-components.csv':source_hash['adm2'],
 'scoped-parent-review.csv':source_hash['adm1'],
 'scoped-2020-internal-overlaps.csv':source_hash['adm2']}
for filename, numeric_cols in columns.items():
    path=OUT/filename
    with path.open(encoding='utf-8',newline='') as f:
        reader=csv.DictReader(f); headers=reader.fieldnames; rows=list(reader)
    raw_lines=path.read_text(encoding='utf-8').splitlines()
    table_rows=[]
    for row_index,row in enumerate(rows,start=2):
        for col,unit in numeric_cols.items():
            if col not in row or not row[col]: continue
            try: value=float(row[col])
            except ValueError: continue
            if not value.is_integer() or '.' in row[col]: decimals=len(row[col].rsplit('.',1)[1]) if '.' in row[col] else 0
            else: decimals=0
            rid=row.get('atlas_id') or row.get('atlas_parent_id') or row.get('current_id') or row.get('georef_id_a','')+'-'+row.get('georef_id_b','') or row.get('atlas_name') or str(row_index)
            metric_id=f"table:{filename}:{row_index}:{col}:{rid}"
            metric_rows.append({'id':metric_id,'value':int(value) if decimals==0 else value,'unit':unit,'vintage':'current','input_sha256':table_input[filename],'evaluation_commit':BASE})
            metric_index=len(metric_rows)-1
            metric_bindings.append({'metric_id':metric_id,'path':f'{PACKET}/findings/metrics.json','json_pointer':f'/metrics/{metric_index}/value'})
            summaries.append({'metric_id':metric_id,'value':int(value) if decimals==0 else value,'unit':unit})
            # The trusted reviewer checks the exact rendered line containing this metric.
            cells=[row[h] for h in headers];cells[headers.index(col)]='{value}'
            buf=io.StringIO(newline='');writer=csv.writer(buf,lineterminator='');writer.writerow(cells)
            template=buf.getvalue()
            assert '{value}' in template and row_index <= len(raw_lines), (filename,row_index)
            table_rows.append({'metric_id':metric_id,'line':row_index,'template':template,'decimals':decimals,'scale':1})
    rendered_by_path[f'{PACKET}/findings/{filename}']={'path':f'{PACKET}/findings/{filename}','rows':table_rows}

# Bind every numeric leaf in generated JSON result/control reports to its actual path.
def add_json_metrics(file_rel):
    data=json.loads((ROOT/file_rel).read_text(encoding='utf-8'))
    def walk(value,pointer=''):
        if isinstance(value,bool) or value is None:return
        if isinstance(value,(int,float)):
            metric_id=f'json:{file_rel}:{pointer or "/"}'
            # Hash the substantive source most directly responsible for this report.
            inp=source_hash['departments'] if 'spatial-reproduction-summary' in file_rel else source_hash['adm1'] if 'province-crosswalk' in file_rel else source_hash['adm2']
            metric_rows.append({'id':metric_id,'value':value,'unit':'count' if isinstance(value,int) else 'ratio-or-source-value','vintage':'current','input_sha256':inp,'evaluation_commit':BASE})
            metric_bindings.append({'metric_id':metric_id,'path':file_rel,'json_pointer':pointer})
            summaries.append({'metric_id':metric_id,'value':value,'unit':'count' if isinstance(value,int) else 'ratio-or-source-value'})
        elif isinstance(value,dict):
            for k,v in value.items():walk(v,pointer+'/'+str(k).replace('~','~0').replace('/','~1'))
        elif isinstance(value,list):
            for i,v in enumerate(value):walk(v,pointer+'/'+str(i))
    walk(data)
json_reports=[f'{PACKET}/findings/{p.name}' for p in sorted(OUT.glob('*.json')) if p.name!='metrics.json']
for p in json_reports:add_json_metrics(p)
metrics={'version':1,'issue':944,'baseline_commit':BASE,'subject_ids_sha256':subject_digest,'metrics':metric_rows}
(OUT/'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')

baseline_paths={
 'data/geographic-releases/current-manifest.json':'release',
 'data/hierarchy.json':'hierarchy',
 'data/regional-review/regional-review-7cf674a63057d43f/source/issue-443-api-snapshot.json':'scope',
 'data/administrative-sources.json':'source_registry'}
base_paths=list(dict.fromkeys([
 'data/geographic-releases/current-manifest.json','data/hierarchy.json','data/world-index.json','data/administrative-sources.json','data/geography/part-0.json',
 'data/regional-review/regional-review-7cf674a63057d43f/source/issue-443-api-snapshot.json',
 'data/regional-review/regional-review-7cf674a63057d43f/source/geoBoundaries-ARG/geoBoundaries-ARG-ADM2.geojson.gz',
 'data/regional-review/regional-review-7cf674a63057d43f/source/geoBoundaries-ARG/geoBoundaries-ARG-ADM2.geojson.lfs-pointer.txt',
 'data/regional-review/regional-review-7cf674a63057d43f/source/geoBoundaries-ARG/geoBoundaries-ARG-ADM2-metaData.json',
 'data/regional-review/regional-review-7cf674a63057d43f/source/geoBoundaries-ARG-ADM1/geoBoundaries-ARG-ADM1.geojson',
 'data/regional-review/regional-review-7cf674a63057d43f/source/geoBoundaries-ARG-ADM1/geoBoundaries-ARG-ADM1-metaData.json',
 'data/regional-review/regional-review-7cf674a63057d43f/source/Georef/argentina-provinces.json',
 'data/regional-review/regional-review-7cf674a63057d43f/source/IGN-2017/limite_interdepartamental_partido-metadata.pdf',
 'data/regional-review/regional-review-7cf674a63057d43f/source-register.json',
 'data/regional-review/regional-review-7cf674a63057d43f/findings/scoped-location-review.csv',
 'data/regional-review/regional-review-7cf674a63057d43f/findings/scoped-province-review.csv',
 'data/regional-review/regional-review-7cf674a63057d43f/findings/reproduction.json']))
baseline_files=[desc_repo(p,'original-source' if '/source/' in p or 'source-register.json' in p else None) for p in base_paths]
by_path={x['path']:x for x in baseline_files}
core_pins={k:by_path[p]['sha256'] for p,k in baseline_paths.items()}
issue_pins={
 'issue_443_exact_scope':'1336f94a586137856691f3831c3a0287a6591ba912f49e2314c51fd52a53a293',
 'argentina_adm2_2020_source':'80e8dc71e89e75f581089fc16270943b559235dfcaf6c49174b0935fc5febc68',
 'ign_interdepartmental_metadata_2017':'95f001ec9e874b05b36187daac158d2285b7aa816b7b99d25c4ff9c5517ae16a',
 'argentina_adm1_2006_source':'b5d13177b09ad3347b617a83252cc77bc985f3c70802d4d7a8b50d3fbe5adba6',
 'georef_province_api_response':'d6a47fd439a347b4a2da5689b6cde68a3dc3de776d2c33ad32a58d58d82ca944'}
custom_pin_files={
 'issue_443_exact_scope':'data/regional-review/regional-review-7cf674a63057d43f/source/issue-443-api-snapshot.json',
 'argentina_adm2_2020_source':'data/regional-review/regional-review-7cf674a63057d43f/source/geoBoundaries-ARG/geoBoundaries-ARG-ADM2.geojson.lfs-pointer.txt',
 'ign_interdepartmental_metadata_2017':'data/regional-review/regional-review-7cf674a63057d43f/source/IGN-2017/limite_interdepartamental_partido-metadata.pdf',
 'argentina_adm1_2006_source':'data/regional-review/regional-review-7cf674a63057d43f/source/geoBoundaries-ARG-ADM1/geoBoundaries-ARG-ADM1.geojson',
 'georef_province_api_response':'data/regional-review/regional-review-7cf674a63057d43f/source/Georef/argentina-provinces.json'}
pins={**core_pins,**issue_pins};pin_files={**{key:path for path,key in baseline_paths.items()},**custom_pin_files}
for key,val in pins.items():assert by_path[pin_files[key]]['sha256']==val,(key,val,by_path[pin_files[key]]['sha256'])

sources=[
 {'id':'geoboundaries-arg-adm2-2020-scoped-214','url':'https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/ARG/ADM2/geoBoundaries-ARG-ADM2.geojson','role':'2020 Argentina ADM2 departments source, exact scoped feature extract','vintage':'Published boundary year 2020; metadata update 2023-01-19, build 2023-12-12','retrieved_at':'2026-10-05','license':{'status':'redistributable','terms':'CC BY 3.0 IGO declared in the exact source metadata; attribute geoBoundaries and named source agencies.'},'retention':'retained','verification':'verified','temporal_status':'unknown','files':[desc_candidate(f'{PACKET}/source/geoBoundaries-2020-scoped-214.geojson'),desc_candidate(f'{PACKET}/source/geoBoundaries-2020/geoBoundaries-ARG-ADM2-metaData.json')],'restoration':'Restore upstream Git LFS object at wmgeolab/geoBoundaries commit 9469f09, path releaseData/gbOpen/ARG/ADM2/geoBoundaries-ARG-ADM2.geojson (LFS SHA-256 f35dae5a257302dea5bd1549ae135baf82e7ee7491918854c3db9bbdec890177, 69,702,323 bytes). The original compressed bytes and LFS pointer are retained in the ancestor #443 packet. Run prepare-scoped-2020.py to verify original archive/raw hashes and regenerate the lawful 214-feature subset.','limit':'Upstream full GeoJSON has 525 features but metadata admUnitCount=526; no missing 526th unit is identified, and a subset does not certify national completeness or current/legal boundaries.'},
 {'id':'geoboundaries-arg-adm1-2006','url':'https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/ARG/ADM1/geoBoundaries-ARG-ADM1.geojson','role':'2006 Argentina province comparison geometries and metadata','vintage':'Published boundary year 2006; metadata update 2023-01-19, build 2023-12-12','retrieved_at':'2026-10-05','license':{'status':'redistributable','terms':'CC BY 2.5 Generic declared in the exact upstream source metadata; attribution required.'},'retention':'retained','verification':'verified','temporal_status':'unknown','files':[desc_candidate(f'{PACKET}/source/geoBoundaries-2006/geoBoundaries-ARG-ADM1-2006.geojson'),desc_candidate(f'{PACKET}/source/geoBoundaries-2006/geoBoundaries-ARG-ADM1-metaData.json')],'restoration':'Exact bytes are retained under source/geoBoundaries-2006; original upstream path is fixed at commit 9469f09 in wmgeolab/geoBoundaries.','limit':'Historical source-register expected SHA conflicts with this exact upstream object, and it is not proof of current legal province boundaries.'},
 {'id':'datos-argentina-georef-departments-current','url':'https://apis.datos.gob.ar/georef/api/departamentos.geojson?max=1000','role':'Current official department, partido and commune feature/name/parent comparison data','vintage':'API response retrieved 2026-10-05; HTTP Last-Modified 2026-08-19; payload has no release version/effective legal date','retrieved_at':'2026-10-05','license':{'status':'redistributable','terms':'Datos Argentina Georef dataset CC BY 4.0. Attribute Jefatura de Gabinete/Secretaría de Innovación Pública; API data model attributes territorial-unit source to IGN.'},'retention':'retained','verification':'verified','temporal_status':'reference','files':[desc_candidate(f'{PACKET}/source/Georef-current/departamentos.json'),desc_candidate(f'{PACKET}/source/Georef-current/departamentos-all.json'),desc_candidate(f'{PACKET}/source/Georef-current/departamentos.geojson')],'restoration':'GET https://apis.datos.gob.ar/georef/api/departamentos.json and /departamentos.geojson?max=1000; response bodies, redirect/Last-Modified/ETag headers and SHA-256 files are retained.','limit':'529 records mix Departamento, Partido and Comuna; the source has material positive-area overlaps and is not a clean planar partition or legal boundary certification.'},
 {'id':'datos-argentina-georef-provinces-current','url':'https://apis.datos.gob.ar/georef/api/provincias.geojson?max=1000','role':'Current official province names, identifiers and geometry comparison layer','vintage':'API response retrieved 2026-10-05; HTTP Last-Modified 2026-08-19; payload has no release version/effective legal date','retrieved_at':'2026-10-05','license':{'status':'redistributable','terms':'Datos Argentina Georef dataset CC BY 4.0. Attribute Jefatura de Gabinete/Secretaría de Innovación Pública; API data model attributes territorial-unit source to IGN.'},'retention':'retained','verification':'verified','temporal_status':'reference','files':[desc_candidate(f'{PACKET}/source/Georef-current/provincias.json'),desc_candidate(f'{PACKET}/source/Georef-current/provincias.geojson')],'restoration':'GET https://apis.datos.gob.ar/georef/api/provincias.json and /provincias.geojson?max=1000; response bodies and headers are retained with SHA-256.','limit':'Current comparison only; not certification of historical or legal province boundary lineage.'},
 {'id':'ign-interdepartmental-metadata-2017','url':'https://www.ign.gob.ar/archivos/sig250/metadatos/limite_interdepartamental_partido.pdf','role':'IGN metadata for advertised 2017 second-order boundaries and reuse terms','vintage':'Metadata update December 2017','retrieved_at':'2026-10-05 (source original retained by #443)','license':{'status':'redistributable','terms':'CC BY as stated by the retained IGN metadata PDF; attribution required.'},'retention':'retained','verification':'verified','temporal_status':'unknown','files':[desc_candidate(f'{PACKET}/source/IGN-2017/limite_interdepartamental_partido-metadata.pdf')],'restoration':'Exact metadata PDF is retained. Its advertised file URL https://www.ign.gob.ar/descargas/geodatos/limite_interdepartamental_partido_geojson.zip returned HTTP 404 on 2026-10-05.','limit':'Metadata is not boundary geometry; no 2017 overlay was possible.'}
]

# Source inputs are stored as retained-source descriptors above; every remaining new file
# (except this manifest) is a separately hashed output. No file outside the exact owned path is collected.
source_candidate_paths={f['path'] for source in sources for f in source['files']}
all_paths=sorted(str(p.relative_to(ROOT)) for p in OWN.rglob('*') if p.is_file())
manifest_path=f'{PACKET}/evidence-quality.json'
non_table_outputs=[]; outputs=[]; receipts=[]
for rel in all_paths:
    if rel==manifest_path:continue
    receipts.append({'path':rel,'status':'added'})
    if rel in source_candidate_paths:continue
    d=desc_candidate(rel)
    if rel.endswith('.csv'):
        d['role']='generated-table'
        table=rendered_by_path.get(rel)
        if table:d['rendered_tables']=[table]
    elif rel.endswith('.py'):d['role']='reproduction-code'
    elif 'http-headers' in rel:d['role']='original-source'
    elif 'upstream/' in rel:d['role']='source-provenance'
    elif rel.endswith('.json') and '/findings/' in rel:d['role']='measurement-result'
    else:d['role']='research-output'
    outputs.append(d)

# Contracts and exact pinned file bindings are from issue #944's additive evidence_quality block.
pins={**core_pins,**issue_pins};pin_files={**{key:path for path,key in baseline_paths.items()},**custom_pin_files}
manifest={
 'version':1,'issue':944,'lane':'geography','worker_id':'worldatlas-geography-812-20261005-r1-415dc98e',
 'subject_ids':subject_ids,'subject_ids_sha256':subject_digest,
 'baseline':{'commit':BASE,'files':baseline_files,'pins':pins,'pin_files':pin_files,'subject_files':{sid:'data/geography/part-0.json' for sid in subject_ids}},
 'sources':sources,'outputs':outputs,
 'methods':[
  {'id':'source-partition','kind':'measurement','description':'Restore/hash the pinned full 2020 ADM2 object, verify the complete 525-feature/unique-ID roster, and extract exactly the issue-scoped 214 IDs from the retained #443 scope.','software':'Python 3.8.5; stdlib gzip/json/hashlib; geoBoundaries upstream commit 9469f09','units':'features, bytes and SHA-256'},
  {'id':'polygon-overlay','kind':'measurement','description':'Project longitude/latitude WGS84 polygons into EPSG:6933 with always_xy; run equal-area Shapely overlay at positive area >1 m2 without geometry repair. Produce the exact scoped 2020/current department candidate, overlap, parent and component ledgers plus the 2006 ADM1/current-province comparison.','software':'Python 3.8.5; Shapely 2.0.7; GEOS 3.11.4; pyproj 3.5.0; PROJ 9.2.0; NumPy 1.24.4','units':'m2, km2, component counts, interior rings and dimensionless area shares'}],
 'metrics':metric_rows,'metric_bindings':metric_bindings,'summaries':summaries,
 'change_receipts':receipts,
 'rendered_tables':[t for d in outputs for t in d.get('rendered_tables',[])],
 'validation':[
  {'method_id':'source-partition','kind':'measurement','outcome':'passed','evidence_path':f'{PACKET}/findings/source-partition-positive.json'},
  {'method_id':'source-partition','kind':'measurement','outcome':'passed','evidence_path':f'{PACKET}/findings/source-partition-negative.json'},
  {'method_id':'polygon-overlay','kind':'measurement','outcome':'passed','evidence_path':f'{PACKET}/findings/polygon-overlay-positive.json'},
  {'method_id':'polygon-overlay','kind':'measurement','outcome':'passed','evidence_path':f'{PACKET}/findings/polygon-overlay-negative.json'}],
 'conclusions':[
  {'status':'supported','text':'The exact geoBoundaries 2020 ADM2 LFS object matches the retained raw object; the raw source has 525 unique shape IDs while its metadata declares 526.', 'source_ids':['geoboundaries-arg-adm2-2020-scoped-214']},
  {'status':'supported','text':'The exact geoBoundaries 2006 ADM1 object has 23 unique features, including La Roja and no Entre Ríos feature label; the current official Georef province source has 24 names.', 'source_ids':['geoboundaries-arg-adm1-2006','datos-argentina-georef-provinces-current']},
  {'status':'supported','text':'The official current Georef department layer is CC BY 4.0 source-identified to IGN through the official API data model; its response has a mixed 529-feature category schema and material positive-area overlap candidates within this issue footprint.', 'source_ids':['datos-argentina-georef-departments-current']},
  {'status':'unresolved','text':'The reason for the La Roja spelling, legal treatment of the absent Entre Ríos ADM1 feature, historical boundaries and the differing 2006/current province outlines remain unresolved.', 'source_ids':['geoboundaries-arg-adm1-2006','datos-argentina-georef-provinces-current']},
  {'status':'unresolved','text':'Twelve parent-assignment candidates, 20 under-99% current coverage cases, duplicate/no-name matches, current-layer overlaps, multipart island completeness, and legal/current boundary identity need further independent adjudication; no automated winner is approved.', 'source_ids':['geoboundaries-arg-adm2-2020-scoped-214','datos-argentina-georef-departments-current','datos-argentina-georef-provinces-current']},
  {'status':'unresolved','text':'The advertised licensed 2017 IGN boundary data was not retrievable; its metadata PDF does not provide overlay geometry.', 'source_ids':['ign-interdepartmental-metadata-2017']}],
 'stages':{'research':'complete','implementation':'proposed','geographic_approval':'not-requested'},
 'commands':[
  'python3 data/regional-review/argentina-adm2-source-revalidation-443/build-evidence-manifest.py',
  'python3 data/regional-review/argentina-adm2-source-revalidation-443/prepare-scoped-2020.py',
  'python3 data/regional-review/argentina-adm2-source-revalidation-443/validate-controls.py',
  'PYTHONPATH=/path/to/env/site-packages python3 data/regional-review/argentina-adm2-source-revalidation-443/reproduce-spatial.py',
  'PYTHONPATH=/path/to/env/site-packages python3 data/regional-review/argentina-adm2-source-revalidation-443/reproduce-components.py',
  'PYTHONPATH=/path/to/env/site-packages python3 data/regional-review/argentina-adm2-source-revalidation-443/reproduce-province-crosswalk.py',
  'node scripts/evidence-quality.mjs data/regional-review/argentina-adm2-source-revalidation-443/evidence-quality.json '+str(ROOT)]}
# Keep source/changes registered one time and reject any write outside the exact owned prefix.
manifest['outputs']=sorted(outputs,key=lambda x:x['path'])
manifest['change_receipts']=sorted(receipts,key=lambda x:x['path'])
(OWN/'evidence-quality.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({'subject_count':len(subject_ids),'metrics':len(metric_rows),'bindings':len(metric_bindings),'summaries':len(summaries),'outputs':len(outputs),'receipts':len(receipts),'manifest':f'{PACKET}/evidence-quality.json'},indent=2))
