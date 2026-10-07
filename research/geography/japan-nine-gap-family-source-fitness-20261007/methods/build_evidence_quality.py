"""Build the bounded issue-1316 evidence manifest from pinned packet files."""
import hashlib, json, pathlib, subprocess

ROOT=pathlib.Path(__file__).resolve().parents[1]
REPO=ROOT.parents[2]
PREFIX='research/geography/japan-nine-gap-family-source-fitness-20261007/'
def sha(raw): return hashlib.sha256(raw).hexdigest()
def desc(path, role=None):
    raw=(REPO/path).read_bytes()
    row={'path':path,'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'}
    if role: row['role']=role
    if path.endswith('.gz'):
        import gzip
        body=gzip.decompress(raw)
        row.update(uncompressed_bytes=len(body),uncompressed_sha256=sha(body))
    return row

freeze=json.loads((ROOT/'inputs/runtime-freeze.json').read_bytes())
scope=json.loads((ROOT/'inputs/immutable-scope-and-inputs.json').read_bytes())
claim=json.loads((ROOT/'inputs/claim-receipt.json').read_bytes())
proposal=json.loads((ROOT/'inputs/root-proposal-proof.json').read_bytes())
issue=json.loads((ROOT/'inputs/issue-snapshot.json').read_bytes())
subjects=sorted(scope['contacts'])
source_files={
 'geoboundaries-jpn-adm2-full':[
  PREFIX+'sources/geoboundaries/full-product.geojson',
  PREFIX+'sources/geoboundaries/full-product.pointer',
  PREFIX+'sources/geoboundaries/metadata.json',
  PREFIX+'sources/geoboundaries/CITATION-AND-USE-geoBoundaries.txt'],
 'geoboundaries-jpn-adm2-atlas-simplified':[
  PREFIX+'sources/geoboundaries/simplified-product.geojson.gz',
  PREFIX+'sources/geoboundaries/simplified-product.pointer']}
retained_paths={p for group in source_files.values() for p in group}
candidate=[]
for p in sorted(ROOT.rglob('*')):
    if not p.is_file(): continue
    rel=PREFIX+p.relative_to(ROOT).as_posix()
    if rel.endswith('/evidence-quality.json') or rel in retained_paths: continue
    candidate.append(desc(rel,'research-output'))

pin_files={
 'audited_world_index':'data/world-index.json',
 'delivered_routing_report':'coordination/engineering/global-actionability-routing-20261007/results/report.json',
 'delivered_routing_input_config':'coordination/engineering/global-actionability-routing-20261007/input-config.json',
 'scoped_part_11':'data/geography/part-11.json',
 'scoped_part_12':'data/geography/part-12.json'}
baseline_files=freeze['baseline_inputs']
pins={key:next(x['sha256'] for x in baseline_files if x['path']==path) for key,path in pin_files.items()}
subject_files={}
for path in ('data/geography/part-11.json','data/geography/part-12.json'):
    raw=subprocess.check_output(['git','-C',str(REPO),'show',f"{freeze['data_baseline_commit']}:{path}"])
    ids={f.get('id',f.get('properties',{}).get('id')) for f in json.loads(raw).get('features',[])}
    for sid in subjects:
        if sid in ids:
            if sid in subject_files: raise ValueError('contact appears in both pinned containing parts')
            subject_files[sid]=path
if set(subject_files)!=set(subjects): raise ValueError('pinned contact inventory does not cover exact reviewed subjects')
def source(id,url,role,vintage,retrieved,license_status,license_terms,retention,verification,temporal,**extra):
    row={'id':id,'url':url,'role':role,'vintage':vintage,'retrieved_at':retrieved,
         'license':{'status':license_status,'terms':license_terms},'retention':retention,
         'verification':verification,'temporal_status':temporal}
    if id in source_files: row['files']=[desc(p,'source-product') for p in source_files[id]]
    row.update(extra); return row
sources=[
 source('geoboundaries-jpn-adm2-full','https://github.com/wmgeolab/geoBoundaries/blob/9469f09/releaseData/gbOpen/JPN/ADM2/geoBoundaries-JPN-ADM2.geojson','Full unsimplified Japan ADM2 reference product; metadata says 2017, source updated 2023-01-19 and built 2023-12-12.','2017 claimed; source/build 2023','2026-10-06T23:40:00Z','redistributable','CC BY 4.0 product terms with attribution/per-feature citation; underlying OpenStreetMap/Wambacher source recorded CC BY-SA 2.0. Retained citation file governs reuse.','retained','verified','reference',limit='Represented year is not verified effective geometry date; no positional-accuracy or legal-authority proof.'),
 source('geoboundaries-jpn-adm2-atlas-simplified','https://github.com/wmgeolab/geoBoundaries/blob/9469f09/releaseData/gbOpen/JPN/ADM2/geoBoundaries-JPN-ADM2_simplified.geojson','Exact simplified product consumed by the pinned Atlas administrative pipeline.','2017 claimed; source/build 2023','2026-10-06T23:40:00Z','redistributable','CC BY 4.0 product terms with attribution/per-feature citation; underlying OpenStreetMap/Wambacher source recorded CC BY-SA 2.0. Retained citation file governs reuse.','retained','verified','reference',limit='Same date, positional accuracy and legal-authority limits as full product; simplification is material for three scoped candidate comparisons.'),
 source('mlit-n03-2017','https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2017/N03-170101_GML.zip','Nationwide Japanese administrative/coastline polygons; complete archive restored and byte-verified locally.','2017-01-01','2026-10-07T06:54:39Z','redistributable','Commercial-use-permitted release; official terms allow copying/redistribution with attribution and retain limitations. See retained official terms and source manifest.', 'restoration-only','verified','reference',restoration='python methods/restore_mlit_source.py --download; restore the complete official ZIP and verify exact 242211059-byte length and SHA256 a649b4099c1b0df80a6fb9ed087b594ed75ae9a92e9511cecdb6463d1480c6fb',limit='Archive exceeds 33,554,432-byte source-file bound. Administrative/coastline product does not establish physical land/water truth, legal title, positional accuracy or cause.'),
 source('gsi-fundamental-geospatial-information-service','https://service.gsi.go.jp/kiban/app/','Official source-access research; request returned HTTP 403 in this environment.','Current service page; no geometry retrieved','2026-10-07T06:54:39Z','unknown','No source-body reuse terms verified because no geometry/data body was retrieved.','restoration-only','unverified','unknown',restoration='Retry the official GSI service or retrieve an authorized exact geometry body with provenance and terms; no captured data payload is available to restore.',limit='HTTP 403 is only this environment access result; no finite candidate-scale applicability was verified.'),
 source('gsi-digital-map-200000','https://www.gsi.go.jp/kibanjoho/kibanjoho40082.html','Official 1:200,000 Digital Map context page; no geometry used.','Current page; no geometry retrieved','2026-10-07T06:54:39Z','unknown','No source-body reuse terms verified for candidate-scale geometry.','restoration-only','unverified','unknown',restoration='Obtain an exact candidate-scale source body and terms from the responsible official service; no geometry payload is available to restore.',limit='The documented scale is too coarse to establish finite applicability to these candidates.'),
 source('gshhg-existing-accepted-comparison','https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-bin-2.3.7.zip','Previously accepted complete source-relative physical-comparison output from issue #1261; 28 existing whole rows reused, detector not rerun.','GSHHG 2.3.7 released 2017-06-15; underlying dates heterogeneous','2026-10-07T06:54:39Z','unknown','Inherited COPYING/README wording conflicts between LGPL v3-or-later and v3-or-earlier; no resolution attempted.','restoration-only','unverified','reference',restoration='Consult the retained #1261 source archive/custody; this packet reuses committed result rows and does not reconstruct its full source archive.',limit='Prior rows are a heterogeneous-vintage diagnostic with shoreline registration and narrow-channel limits; they do not establish current physical truth or authority.')]

manifest={'version':1,'issue':1316,'lane':'geography','worker_id':claim['claim']['worker_id'],
 'subject_ids':subjects,'subject_ids_sha256':hashlib.sha256(json.dumps(subjects,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),
 'baseline':{'commit':freeze['data_baseline_commit'],'files':baseline_files,'pins':pins,'pin_files':pin_files,'subject_files':subject_files},
 'sources':sources,'outputs':candidate,
 'methods':[
  {'id':'complete-source-relative-vector-overlay','kind':'geography','description':'Exact Shapely polygon intersections/coverage over complete pinned geoBoundaries full and Atlas-simplified features and bbox-selected native MLIT N03 polygons; all 28 whole candidates and 21 whole contacts retained. No repairs, dissolve, raster, or detector rerun.','software':'Frozen Python 3.12.14; Shapely 2.1.2 / GEOS 3.13.1; pyproj 3.7.2 / PROJ 9.5.1; NumPy 2.3.5; runtime file hashes in inputs/runtime-freeze.json.','units':'Square degrees only for angular-coordinate polygon areas; categorical exact predicates and source-record counts.','axis_order':'longitude-latitude','crs':'GeoJSON RFC 7946 WGS84 longitude/latitude; MLIT native EPSG:6668 JGD2011 geographic after always_xy transformation.','area_method':'Planar Shapely intersection in each stated geographic coordinate space; degree-squared output only, never square metres.','distance_method':'No distances calculated.'},
  {'id':'native-n03-record-reader','kind':'source','description':'Scanned complete native SHP/DBF record sequence and applied original SHP envelope query before exact Shapely predicates; rings were not repaired or edited.','software':'Frozen Python 3.12.14; packet native reader and exact dependency/runtime closure.','units':'Original SHP record ordinal, DBF attributes, and exact overlay predicates.'}],
 'metrics':[],'metric_bindings':[],'summaries':[],
 'conclusions':[
  {'text':'The Atlas-consumed simplified geoBoundaries body matches the pinned administrative source registry and exact upstream simplified LFS product; it is not interchangeable with the full body for all scoped overlays.','status':'supported','source_ids':['geoboundaries-jpn-adm2-atlas-simplified','geoboundaries-jpn-adm2-full']},
  {'text':'Three of 28 candidates have differing full-versus-simplified intersection/coverage outcomes in the source-relative comparison; this does not establish which geometry is physically or legally correct.','status':'supported','source_ids':['geoboundaries-jpn-adm2-atlas-simplified','geoboundaries-jpn-adm2-full']},
  {'text':'The official 2017 N03 administrative/coastline product intersects candidate and contact polygons in the recorded CRS, but it does not independently establish physical land/water, title, accuracy, historical cause or a repair.','status':'supported','source_ids':['mlit-n03-2017']},
  {'text':'Physical truth, historical geometry, source positional accuracy and legal authority for the candidates remain unresolved; retain all 28 dispositions and all unknowns.','status':'unresolved','source_ids':['geoboundaries-jpn-adm2-full','geoboundaries-jpn-adm2-atlas-simplified','mlit-n03-2017','gshhg-existing-accepted-comparison']},
  {'text':'No finite candidate-scale high-resolution GSI geometry or independent hydrography was retrieved, so mixed coastal/water contexts remain unclassified.','status':'unresolved','source_ids':['gsi-fundamental-geospatial-information-service','gsi-digital-map-200000']}],
 'stages':{'research':'complete','implementation':'proposed','geographic_approval':'not-requested'},
 'commands':[
  'python methods/restore_mlit_source.py --download',
  'python methods/producer_controls.py',
  'python methods/run_once.py --execution 4ca1eaf014e3c2e38953812090aa6078ec960ae0 --run one --output research/geography/japan-nine-gap-family-source-fitness-20261007/results/source-overlays.json --receipt research/geography/japan-nine-gap-family-source-fitness-20261007/runs/run-one-attempt-2.json --log research/geography/japan-nine-gap-family-source-fitness-20261007/runs/run-one-attempt-2.log',
  'python methods/run_once.py --execution 4ca1eaf014e3c2e38953812090aa6078ec960ae0 --run two --output .cache/japan-nine-gap-run-two/source-overlays.json --receipt research/geography/japan-nine-gap-family-source-fitness-20261007/runs/run-two.json --log research/geography/japan-nine-gap-family-source-fitness-20261007/runs/run-two.log',
  'python methods/build_source_fitness_table.py',
  'node scripts/evidence-quality.mjs research/geography/japan-nine-gap-family-source-fitness-20261007/evidence-quality.json'],
 'change_receipts':[{'path':PREFIX+p.relative_to(ROOT).as_posix(),'status':'added','previous_path':None}
  for p in sorted(ROOT.rglob('*')) if p.is_file()]}
(ROOT/'evidence-quality.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'baseline_files':len(baseline_files),'sources':len(sources),'outputs':len(candidate),'source_files':sum(len(x.get('files',[])) for x in sources),'evidence_quality_bytes':(ROOT/'evidence-quality.json').stat().st_size},ensure_ascii=False))
