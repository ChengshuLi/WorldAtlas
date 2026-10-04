#!/usr/bin/env python3
"""Build the packet's exact-head source/output inventory (manifest excludes its own hash)."""
import gzip, hashlib, json, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / 'data/regional-review/regional-review-4254da254d94f450'
REL = 'data/regional-review/bc-admin-vintage-crosswalk-followup-2026'
MANIFEST = 'evidence-manifest.json'
WORKER = 'codex-20261004-bc-csd-xwalk-607-ecb3053c-65c0-46a4-ac59-5701e3dc9ae4'
COMMIT = subprocess.check_output(['git','-C',str(ROOT),'rev-parse','origin/main'],text=True).strip()

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''): h.update(chunk)
    return h.hexdigest()

def describe(path, role=None):
    p=ROOT/path
    obj={'path':path,'bytes':p.stat().st_size,'sha256':digest(p),'hash_kind':'file-bytes'}
    if path.endswith(('.csv.gz','.html.gz')):
        with gzip.open(p,'rb') as f: raw=f.read()
        obj['uncompressed_bytes']=len(raw)
        obj['uncompressed_sha256']=hashlib.sha256(raw).hexdigest()
    if role: obj['role']=role
    return obj

def candidate(relative, role=None): return describe(f'{REL}/{relative}',role)

all_paths=sorted(p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file() and p.name!=MANIFEST)
raw_sources={
 'sources/statistics-canada-2016-census-subdivisions-digital-boundary.zip',
 'sources/statistics-canada-2016-2021-csd-changes.csv.gz',
 'sources/statistics-canada-2016-census-dictionary-census-subdivision.html.gz'
}
sources=[
 {'id':'statcan-2016-csd-digital-boundary','url':'https://open.canada.ca/data/en/dataset/dee563be-383f-4c6a-91c6-d08ca6638c7c','role':'authoritative 2016 CSD identity and geometry','vintage':'2016 Census','retrieved_at':'2026-10-04','license':{'status':'redistributable','terms':'Open Government Licence – Canada'},'retention':'retained','verification':'verified','restoration':'Restore the official archive from the canonical dataset page and compare whole-file digest.','limit':'Statistical CSD digital boundary; not cadastral or political ownership evidence.','temporal_status':'historical','supported_interval':{'from':2016,'to':2017},'files':[candidate('sources/statistics-canada-2016-census-subdivisions-digital-boundary.zip','original-source')]},
 {'id':'statcan-2016-2021-csd-changes-table-1','url':'https://www150.statcan.gc.ca/n1/pub/92f0009x/2021001/tbl/tbl01-eng.htm','role':'official CSD transition and successor events','vintage':'Effective dates 2016-01-02 through 2021-01-01','retrieved_at':'2026-10-04','license':{'status':'redistributable','terms':'Statistics Canada Open Licence'},'retention':'retained','verification':'verified','restoration':'Download CSV from the canonical table page; signed URLs are transient.','limit':'Table warns it may omit changes and has no polygon areas.','temporal_status':'historical','supported_interval':{'from':2016,'to':2022},'files':[candidate('sources/statistics-canada-2016-2021-csd-changes.csv.gz','original-source')]},
 {'id':'statcan-2016-census-dictionary-csd','url':'https://www12.statcan.gc.ca/census-recensement/2016/ref/dict/geo012-eng.cfm','role':'official definition of Census Subdivision and type','vintage':'2016 Census','retrieved_at':'2026-10-04','license':{'status':'redistributable','terms':'Statistics Canada Open Licence'},'retention':'retained','verification':'verified','restoration':'Retrieve canonical dictionary page and compare digest.','limit':'Statistical definition does not support sovereignty or political-ownership conclusions.','temporal_status':'historical','supported_interval':{'from':2016,'to':2017},'files':[candidate('sources/statistics-canada-2016-census-dictionary-census-subdivision.html.gz','original-source')]},
 {'id':'geoboundaries-canada-adm3-2016','url':'https://github.com/wmgeolab/geoBoundaries/releases/tag/9469f09','role':'assigned 2016 local-unit source membership and name','vintage':'2016 boundary vintage; metadata updated 2023-01-19','retrieved_at':'2026-10-04','license':{'status':'unknown','terms':'API says ODbL 1.0; licenseDetail cites Statistics Canada Open License; discrepancy preserved.'},'retention':'restoration-only','verification':'unverified','restoration':'Restore the geoBoundaries 9469f09 original and verify hash in the ancestor source manifest; assigned ID extracts are retained in outputs.','limit':'Secondary administrative boundary source; license discrepancy and legal lineage/ownership remain unresolved.','temporal_status':'historical','supported_interval':{'from':2016,'to':2017}},
 {'id':'statcan-2021-census-subdivisions-bc','url':'https://www.arcgis.com/home/item.html?id=594124f0380d42b7a4b450574dd9630c','role':'official 2021 target IDs, names and 33 low-overlap target geometries','vintage':'2021 Census','retrieved_at':'2026-10-04','license':{'status':'redistributable','terms':'Statistics Canada Open Licence'},'retention':'restoration-only','verification':'verified','restoration':'Restore the retained #485 Statistics Canada item response from the ancestor commit; compare item ID, query, and hash documented in source-receipts.json.','limit':'Full source response is >32 MB and retained in ancestor packet; candidate retains only all target properties and needed low-overlap geometries.','temporal_status':'historical','supported_interval':{'from':2021,'to':2022}}
]
baseline_paths=['data/regional-review/regional-review-4254da254d94f450/assessment.json','data/regional-review/regional-review-4254da254d94f450/sources-manifest.json','data/regional-review/regional-review-4254da254d94f450/evidence-artifacts-manifest.json','data/regional-review/regional-review-4254da254d94f450/sources/geoboundaries-CAN-ADM3-2016.geojson','data/regional-review/regional-review-4254da254d94f450/sources/statistics-canada-bc-census-subdivisions-2021.geojson.gz']
baseline=[describe(p,'original-source' if '/sources/' in p else None) for p in baseline_paths]
outputs=[candidate(p) for p in all_paths if p not in raw_sources]
files=[]
for path in all_paths+[MANIFEST]: files.append({'path':f'{REL}/{path}','status':'added','previous_path':None})
summary=json.loads((HERE/'results-summary.json').read_text())
source_hash=digest(HERE/'sources/statistics-canada-2016-census-subdivisions-digital-boundary.zip')
prior_hash=digest(BASE/'assessment.json')
metrics=[
 ('assigned-subjects',summary['assigned_subjects'],'members',prior_hash,'/assigned_subjects'),
 ('no-exact-2021-name-count',20,'members',prior_hash,'/original_flag_counts/no_exact_2021_name'),
 ('ambiguous-2021-name-count',5,'members',prior_hash,'/original_flag_counts/multiple_same_name_2021_candidates'),
 ('below-95-overlap-count',33,'members',prior_hash,'/original_flag_counts/best_overlap_below_95'),
 ('below-50-overlap-count',3,'members',prior_hash,'/original_flag_counts/best_overlap_below_50'),
 ('same-csduid-continuity',374,'members',source_hash,'/crosswalk/same_csd_uid_across_2016_2021'),
 ('complete-annexation-successors',2,'members',source_hash,'/crosswalk/explicit_complete_annexation_successors'),
 ('2016-source-direction-extent-under-95',17,'members',source_hash,'/extent_findings/geoBoundaries_2016_to_official_2016_source_coverage_below_95'),
 ('2016-target-direction-extent-under-95',134,'members',source_hash,'/extent_findings/official_2016_csd_area_covered_by_source_below_95'),
 ('2016-either-direction-extent-under-95',141,'members',source_hash,'/extent_findings/either_direction_below_95'),
 ('low-overlap-remeasured',33,'members',source_hash,'/extent_findings/original_low_overlap_cases_remeasured'),
 ('low-overlap-match-within-tolerance',33,'members',source_hash,'/extent_findings/recomputed_2021_screen_matches_prior_within_0_002pp')]
ledger=[{'id':key,'value':value,'unit':unit,'vintage':'baseline','input_sha256':input_hash,'evaluation_commit':COMMIT} for key,value,unit,input_hash,_ in metrics]
manifest={
 'version':1,'issue':607,'lane':'geography','worker_id':WORKER,
 'subject_ids':sorted(r['source_shape_id'] for r in json.loads((HERE/'source-member-roster.json').read_text())['members']),
 'subject_ids_sha256':hashlib.sha256(json.dumps(sorted(r['source_shape_id'] for r in json.loads((HERE/'source-member-roster.json').read_text())['members']),separators=(',',':')).encode()).hexdigest(),
 'baseline':{'commit':COMMIT,'files':baseline,'pins':{'issue-485-assessment_sha256':prior_hash,'official-2021-csd_sha256':digest(BASE/'sources/statistics-canada-bc-census-subdivisions-2021.geojson.gz')},'pin_files':{'issue-485-assessment_sha256':baseline_paths[0],'official-2021-csd_sha256':baseline_paths[4]}},
 'sources':sources,'outputs':outputs,'change_receipts':files,
 'methods':[{'id':'crosswalk-packet-validation','kind':'measurement','description':'Check all 376 inherited members, complete parent chains, source and target CSDUIDs, original name/overlap flags, transition successors, measured coverage cohorts, retained source hashes and negative controls. Geometry area screens use EPSG:3347 and source-coordinate inputs remain unchanged.','software':'Python 3; pyshp 2.3.1; Shapely 2.1.2; pyproj 3.7.2','units':'CSD members; projected square-kilometre areas and percent coverage'}],
 'metrics':[{'id':key,'value':value,'unit':unit,'vintage':'baseline','input_sha256':input_hash,'evaluation_commit':COMMIT} for key,value,unit,input_hash,_ in metrics],
 'summaries':[{'metric_id':key,'value':value,'unit':unit} for key,value,unit,_,_ in metrics],
 'metric_bindings':[{'metric_id':key,'path':f'{REL}/results-summary.json','json_pointer':pointer} for key,_,_,_,pointer in metrics],
 'validation':[{'method_id':'crosswalk-packet-validation','kind':'positive-control','outcome':'passed','evidence_path':f'{REL}/control-positive-control.json'},{'method_id':'crosswalk-packet-validation','kind':'negative-control','outcome':'passed','evidence_path':f'{REL}/control-negative-control.json'},{'method_id':'crosswalk-packet-build','kind':'reproducibility','outcome':'passed','evidence_path':f'{REL}/reproduction-results.json'}],
 'conclusions':[{'text':'All 376 assigned 2016 source IDs map to unique 2016 CSDUIDs and 374 current 2021 CSDUIDs, with two table-documented complete-annexation successors; all inherited 20/5/33 exception rows are assessed.','status':'supported','source_ids':['statcan-2016-csd-digital-boundary','statcan-2016-2021-csd-changes-table-1','statcan-2021-census-subdivisions-bc','geoboundaries-canada-adm3-2016']},{'text':'The cause of 141 bidirectional 2016 administrative extent discrepancies is not established; physical shoreline/land evidence is needed before a correction proposal.','status':'unresolved','source_ids':['statcan-2016-csd-digital-boundary','geoboundaries-canada-adm3-2016']}],
 'stages':{'research':'complete','implementation':'not-proposed','geographic_approval':'unapproved'},
 'commands':['python data/regional-review/bc-admin-vintage-crosswalk-followup-2026/prepare_source_extracts.py','python data/regional-review/bc-admin-vintage-crosswalk-followup-2026/analyze_crosswalk.py','python data/regional-review/bc-admin-vintage-crosswalk-followup-2026/build_exception_findings.py','python data/regional-review/bc-admin-vintage-crosswalk-followup-2026/verify_packet.py','python data/regional-review/bc-admin-vintage-crosswalk-followup-2026/build_evidence_manifest.py']
}
(HERE/MANIFEST).write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'manifest':str(HERE/MANIFEST),'changed_files':len(files),'source_files':len(raw_sources),'outputs':len(outputs),'metrics':len(ledger),'manifest_sha256':digest(HERE/MANIFEST)},indent=2))
