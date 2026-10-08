#!/usr/bin/env python3
"""Build the issue-1481 evidence manifest from its reviewed contract and packet bytes."""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; P=Path(__file__).resolve().parent
BASE='960ba2f4fef0fc9881b8a106a944e6e3874e98c9'
def sha(b): return hashlib.sha256(b).hexdigest()
def desc(path,raw=None,decoded=None):
 if raw is None: raw=(P/path).read_bytes()
 d={'path':(Path('research/geography/arctic-seven-source-fit-20261008')/path).as_posix(),'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'}
 if decoded is not None:d.update(uncompressed_bytes=len(decoded),uncompressed_sha256=sha(decoded))
 return d
body=(P/'issue-contract.md').read_text()
match=re.search(r'<!-- worldatlas-work:v1\s*(\{.*?\})\s*-->',body,re.S); assert match
contract=json.loads(match.group(1)); spec=contract['evidence_quality']; pins=spec['pins']
keypath={
 'world_index':'data/world-index.json','hierarchy':'data/hierarchy.json','semantic_registry':'data/semantic-sources.json',
 'source_manifest':'data/regional-review/regional-review-a9f03b364bdefa4a/sources-manifest.json',
 'source_v22':'data/regional-review/regional-review-a9f03b364bdefa4a/sources/aafc-terrestrial-ecoregions-v2.2.geojson',
 'source_ecoprovinces':'data/regional-review/regional-review-a9f03b364bdefa4a/sources/aafc-ecoprovinces-baseline-arcgis-layer0.geojson',
 'two_gap_input_index':'coordination/engineering/eastern-two-gap-repair-20261007/input-index.json',
 'four_family_context':'coordination/engineering/eastern-two-gap-repair-20261007/run-two/full-four-family-context.json.gz',
}
for n in range(34):keypath[f'geography_part_{n:02}']=f'data/geography/part-{n}.json'
keypath['geography_source_restoration_additions']='data/geography/source-restoration-additions.json'
keypath['geography_macro_loose_ends_additions']='data/geography/macro-loose-ends-v5-additions.json'
for n in range(47,54):keypath[f'retired_archive_{n:03}']=f'coordination/engineering/eastern-two-gap-repair-20261007/inputs/i{n:03}.bin.gz'
assert set(pins)==set(keypath),(set(pins)-set(keypath),set(keypath)-set(pins))
files=[]; pin_files={}
for key,p in keypath.items():
 raw=subprocess.check_output(['git','show',f'{BASE}:{p}'])
 assert sha(raw)==pins[key],(key,sha(raw),pins[key])
 files.append({'path':p,'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'})
 pin_files[key]=p
for p in ['scripts/evidence/geometry.py','scripts/ellipsoidal_area.py']:
 raw=subprocess.check_output(['git','show',f'{BASE}:{p}'])
 files.append({'path':p,'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'})
source_manifest=json.loads((ROOT/'data/regional-review/regional-review-a9f03b364bdefa4a/sources-manifest.json').read_bytes())
citations={x['path'].removeprefix('sources/'):x for x in source_manifest['sources'] if isinstance(x.get('path'),str)}
source_files=[desc('sources/aafc-ecoregions.native.geojson')]
output_paths=['source-custody.json','retired-member-context.json','source-custody-phase2.json','retired-member-context-phase2.json','native-archive-verification.json','neighbor-scan-a.json','neighbor-scan-b.json','execution-budget.json','candidate-decisions.json','proposed-additions.geojson','positive-control.json','negative-control.json','README.md','issue-contract.md','prepare_sources.py','scan_neighbors.py','verify_native_member.sh','reproduce_fit.py','build_manifest.py']
output_paths += [
 'phase-plan.json','runtime-lock.json','native-tools-lock.json','native-tools-lock.sh',
 'build_phase_plan.py','build_run_record.py','build_runtime_lock.py','build_native_tools_lock.py','r7-execution-budget.json',
 'run_source_phase.py','source_phase_runtime.py','native_archive_extract.sh',
 'vintages/r7-native-extract/native-archive-extraction.json',
 'vintages/r7-native-extract/execution-receipt.json','vintages/r7-native-extract/publication.json',
 'vintages/r7-retired/source-custody-phase2.json','vintages/r7-retired/retired-member-context-phase2.json',
 'vintages/r7-retired/execution-receipt.json','vintages/r7-retired/publication.json',
]
for partition in 'abcd':
 output_paths += [f'vintages/r7-scan-{partition}/neighbor-scan-{partition}.json',
  f'vintages/r7-scan-{partition}/execution-receipt.json',f'vintages/r7-scan-{partition}/publication.json']
output_paths += [f'vintages/r7-fit/{name}' for name in [
 'candidate-decisions.json','proposed-additions.geojson','positive-control.json','negative-control.json',
 'execution-receipt.json','publication.json']]
output_paths += [str(path.relative_to(P)) for path in sorted((P/'exploratory').rglob('*')) if path.is_file()]
outputs=[desc(x) for x in output_paths]
output_by_name={Path(x['path']).name:x for x in outputs}
subjects=spec['subject_ids']; subject_hash=sha(json.dumps(sorted(subjects),separators=(',',':')).encode())
results=json.loads((P/'vintages/r7-fit/candidate-decisions.json').read_bytes())['results']
metrics=[
 {'id':'active-feature-count','value':49625,'unit':'features','vintage':'baseline','input_sha256':pins['world_index'],'evaluation_commit':BASE},
 {'id':'candidate-count','value':7,'unit':'components','vintage':'baseline','input_sha256':sha((P/'vintages/r7-fit/candidate-decisions.json').read_bytes()),'evaluation_commit':BASE},
 {'id':'repair-ready-count','value':sum(r['decision']=='repair-ready-geometric-proposal' for r in results),'unit':'components','vintage':'baseline','input_sha256':sha((P/'vintages/r7-fit/candidate-decisions.json').read_bytes()),'evaluation_commit':BASE},
 {'id':'unresolved-count','value':sum(r['decision']!='repair-ready-geometric-proposal' for r in results),'unit':'components','vintage':'baseline','input_sha256':sha((P/'vintages/r7-fit/candidate-decisions.json').read_bytes()),'evaluation_commit':BASE},
 {'id':'exact-one-envelope-count','value':sum(r['exactly_one_covering_named_envelope_both_editions'] for r in results),'unit':'components','vintage':'baseline','input_sha256':sha((P/'vintages/r7-fit/candidate-decisions.json').read_bytes()),'evaluation_commit':BASE},
 {'id':'native-ecoregion-feature-count','value':218,'unit':'features','vintage':'baseline','input_sha256':sha((P/'vintages/r7-fit/candidate-decisions.json').read_bytes()),'evaluation_commit':BASE},
 {'id':'native-unique-ecoregion-id-count','value':194,'unit':'ids','vintage':'baseline','input_sha256':sha((P/'vintages/r7-fit/candidate-decisions.json').read_bytes()),'evaluation_commit':BASE},
 {'id':'retired-reference-location-count','value':19050,'unit':'locations','vintage':'baseline','input_sha256':sha((P/'vintages/r7-fit/candidate-decisions.json').read_bytes()),'evaluation_commit':BASE},
]
sources=[
 {'id':'aafc-native-ecoregions','url':'https://www.arcgis.com/home/item.html?id=ee462b0692cc4005aefee69dc44f010d','role':'Exact original AAFC native ecoregion source member; ECO15/ECO25 coverage','vintage':'Registered source archive member retrieved 2026-10-01; underlying effective date not established','retrieved_at':'2026-10-01','license':{'status':'redistributable','terms':'Open Government Licence – Canada as stated by linked AAFC source item'},'retention':'retained','verification':'verified','temporal_status':'unknown','files':[source_files[0]]},
 {'id':'aafc-terrestrial-ecoregions-v22','url':citations['aafc-terrestrial-ecoregions-v2.2.geojson']['url'],'role':'Complete official AAFC v2.2 comparison edition','vintage':citations['aafc-terrestrial-ecoregions-v2.2.geojson']['source_vintage'],'retrieved_at':citations['aafc-terrestrial-ecoregions-v2.2.geojson']['retrieved_utc'],'license':{'status':'redistributable','terms':'Open Government Licence – Canada'},'retention':'restoration-only','verification':'verified','temporal_status':'reference','restoration':'Read the complete original GeoJSON directly from its issue-pinned baseline path.','limit':'The pinned whole-file source is used in the fit reproduction and is not duplicated as a candidate copy.'},
 {'id':'aafc-ecoprovinces-parent','url':citations['aafc-ecoprovinces-baseline-arcgis-layer0.geojson']['url'],'role':'Parent ecoprovince identity and name comparison','vintage':citations['aafc-ecoprovinces-baseline-arcgis-layer0.geojson']['source_vintage'],'retrieved_at':citations['aafc-ecoprovinces-baseline-arcgis-layer0.geojson']['retrieved_utc'],'license':{'status':'redistributable','terms':'Open Government Licence – Canada as stated by linked AAFC item'},'retention':'restoration-only','verification':'verified','temporal_status':'reference','restoration':'Read the complete original GeoJSON directly from its issue-pinned baseline path.','limit':'The pinned whole-file source is used in the fit reproduction and is not duplicated as a candidate copy.'},
 {'id':'atlas-baseline-target-neighbor-context','url':'https://github.com/ChengshuLi/WorldAtlas','role':'Pinned current target, hierarchy, and full active neighbor context','vintage':f'Immutable repository baseline {BASE}','retrieved_at':'2026-10-08','license':{'status':'unknown','terms':'Repository data use is governed by repository terms; this reference does not redistribute it as an external source.'},'retention':'restoration-only','verification':'verified','temporal_status':'reference','restoration':'Read paths pinned in baseline.files at the listed immutable commit.','limit':'Atlas geometry and hierarchy are current reference context, not independent boundary authority.'},
 {'id':'retired-administrative-cartographic-context','url':'https://github.com/ChengshuLi/WorldAtlas','role':'Exact retired-member context for five candidate-adjacent administrative records','vintage':'Undated cartographic-reference archive; historical effective year is null','retrieved_at':'2026-10-08','license':{'status':'unknown','terms':'Repository archive custody is pinned; effective historical date and legal status are not supplied.'},'retention':'restoration-only','verification':'verified','temporal_status':'unknown','restoration':'Reconstruct the pinned archive from i047–i053 using the evidence reproduction script.','limit':'Undated administrative footprints provide context only; they do not establish historic cause or physical boundary authority.'},
]
conclusions=[]
for r in results:
 status='supported' if r['decision']=='repair-ready-geometric-proposal' else 'unresolved'
 if status=='supported':text=f"{r['component_id']}: fully covered by exactly one named ECO{r['source_ecoregion_id']} envelope in native and v2.2 editions; hierarchy and retired-member context are compatible; union is valid, lossless, additive, and has no new positive-area active-neighbor overlap."
 elif r['union_loss_area_deg2']>0:text=f"{r['component_id']}: source fit and context pass, but exact additive no-loss criterion is unresolved because target union leaves a nonempty loss residual of {r['union_loss_area_deg2']:.17g} square degrees. Residual geometry is retained; no tolerance is applied."
 else:text=f"{r['component_id']}: source fit and context pass, but existing target overlap means the union gain ({r['union_gain_area_deg2']:.17g} square degrees) is not the full candidate; candidate-minus-gain geometry is retained."
 conclusions.append({'text':text,'status':status,'source_ids':['aafc-native-ecoregions','aafc-terrestrial-ecoregions-v22','aafc-ecoprovinces-parent','atlas-baseline-target-neighbor-context','retired-administrative-cartographic-context']})
change_receipts=[{'path':x['path'],'status':'added'} for x in source_files+outputs
 if x['path']!='research/geography/arctic-seven-source-fit-20261008/evidence-quality.json']
change_receipts.append({'path':'research/geography/arctic-seven-source-fit-20261008/evidence-quality.json','status':'added'})
manifest={'version':1,'issue':1481,'lane':'geography','worker_id':'01a112c1-ac99-74b1-9047-a1da2dd0e245','subject_ids':subjects,'subject_ids_sha256':subject_hash,
 'baseline':{'version':1,'commit':BASE,'files':files,'pins':pins,'pin_files':pin_files,'subject_files':{sid:'data/geography/part-29.json' for sid in subjects}},
 'sources':sources,'outputs':outputs,
 'methods':[{'id':'exact-aafc-envelope-and-topology','kind':'geography','helper_version':'worldatlas-evidence-geometry-v1','description':'GEOS/Shapely exact coverage, intersection, union, difference, validity, and equality predicates on stored GeoJSON coordinate values; geodesic candidate-area diagnostics use the pinned shared WGS84 helper. No snapping, buffering, repair, or tolerance is used for acceptance.','software':'Python 3.12; Shapely 2.1.2 / GEOS 3.13.1; pyproj WGS84 helper','units':'m2 for candidate area; square degrees for exact planar residuals; degrees for coordinate contact length','axis_order':'longitude-latitude','crs':'EPSG:4326','area_method':'WGS84 straight-source-edge ellipsoidal integral','distance_method':'WGS84 inverse geodesic'}],
 'metrics':metrics,'summaries':[{'metric_id':'candidate-count','value':7,'unit':'components'},{'metric_id':'repair-ready-count','value':3,'unit':'components'},{'metric_id':'unresolved-count','value':4,'unit':'components'},{'metric_id':'exact-one-envelope-count','value':7,'unit':'components'},{'metric_id':'active-feature-count','value':49625,'unit':'features'}],
 'metric_bindings':[
  {'metric_id':'active-feature-count','path':output_by_name['candidate-decisions.json']['path'],'json_pointer':'/active_feature_count'},
  {'metric_id':'candidate-count','path':output_by_name['candidate-decisions.json']['path'],'json_pointer':'/component_count'},
  {'metric_id':'repair-ready-count','path':output_by_name['candidate-decisions.json']['path'],'json_pointer':'/repair_ready_count'},
  {'metric_id':'unresolved-count','path':output_by_name['candidate-decisions.json']['path'],'json_pointer':'/unresolved_count'},
  {'metric_id':'exact-one-envelope-count','path':output_by_name['candidate-decisions.json']['path'],'json_pointer':'/exactly_one_covering_named_envelope_count'},
  {'metric_id':'native-ecoregion-feature-count','path':output_by_name['candidate-decisions.json']['path'],'json_pointer':'/native_feature_count'},
  {'metric_id':'native-unique-ecoregion-id-count','path':output_by_name['candidate-decisions.json']['path'],'json_pointer':'/native_unique_ecoregion_id_count'},
  {'metric_id':'retired-reference-location-count','path':output_by_name['retired-member-context-phase2.json']['path'],'json_pointer':'/location_count'}],
 'change_receipts':change_receipts,
 'validation':[
  {'method_id':'exact-aafc-envelope-and-topology','kind':'positive-control','outcome':'passed','evidence_path':'research/geography/arctic-seven-source-fit-20261008/vintages/r7-fit/positive-control.json'},
  {'method_id':'exact-aafc-envelope-and-topology','kind':'negative-control','outcome':'passed','evidence_path':'research/geography/arctic-seven-source-fit-20261008/vintages/r7-fit/negative-control.json'}],
 'conclusions':conclusions,'stages':{'research':'partial','implementation':'proposed','geographic_approval':'unapproved'},
 'commands':['bash research/geography/arctic-seven-source-fit-20261008/native_archive_extract.sh EXECUTION_COMMIT PLAN_SHA256 NATIVE_TOOLS_LOCK_SHA256','python research/geography/arctic-seven-source-fit-20261008/run_source_phase.py retired-context --baseline EXECUTION_COMMIT --plan-sha256 PLAN_SHA256','python research/geography/arctic-seven-source-fit-20261008/run_source_phase.py neighbor-scan-{a,b,c,d} --baseline EXECUTION_COMMIT --plan-sha256 PLAN_SHA256','python research/geography/arctic-seven-source-fit-20261008/run_source_phase.py source-fit --baseline EXECUTION_COMMIT --plan-sha256 PLAN_SHA256','python research/geography/arctic-seven-source-fit-20261008/build_run_record.py','python research/geography/arctic-seven-source-fit-20261008/build_manifest.py','node scripts/evidence-quality.mjs research/geography/arctic-seven-source-fit-20261008/evidence-quality.json']}
(P/'evidence-quality.json').write_text(json.dumps(manifest,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')
print(json.dumps({'pins':len(pins),'baseline_files':len(files),'sources':len(sources),'outputs':len(outputs),'bytes':sum(x['bytes'] for x in files+outputs+source_files),'subject_hash':subject_hash}))
