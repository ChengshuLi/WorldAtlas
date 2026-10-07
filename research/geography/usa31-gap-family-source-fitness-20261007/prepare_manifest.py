from pathlib import Path
import hashlib,json,subprocess
root=Path('research/geography/usa31-gap-family-source-fitness-20261007')
base='839883ae281af7bf012f694698624a7ec77275e1'
subject_ids=['gb:USA:ADM2:52423323B42354579566723','gb:USA:ADM2:52423323B61185146991898','gb:USA:ADM2:52423323B83071826775288']
pin_files={
 'consumed_source_payload_file':'coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-USA-ADM2-000.bin.gz',
 'source_metadata_file':'data/administrative-sources.json',
 'source_attribution_file':'coordination/engineering/original-geography-source-corpus-20261006/individual-source-attribution.json',
 'routing_report_file':'coordination/engineering/global-actionability-routing-20261007/results/report.json',
 'numeric_diagnosis_report_file':'coordination/engineering/complete-numeric-closure-diagnosis-20261007/r2/report.json',
 'numeric_scope_file':'coordination/engineering/complete-numeric-closure-diagnosis-20261007/scope.json.gz',
 'physical_comparison_report_file':'coordination/engineering/global-physical-comparison-20261006/results/report.json',
 'physical_source_run_report_file':'coordination/engineering/global-physical-sources-20261006/run-one/report.json',
 'physical_source_members_file':'coordination/engineering/global-physical-sources-20261006/run-one/members.json',
 'candidate_custody_index_file':'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json',
}
def sha(b):return hashlib.sha256(b).hexdigest()
def desc(path,b,role):return {'path':path,'bytes':len(b),'sha256':sha(b),'hash_kind':'file-bytes','role':role}
baseline_files=[]; pins={};
for k,p in pin_files.items():
 raw=subprocess.check_output(['git','show',f'{base}:{p}'])
 baseline_files.append(desc(p,raw,'original-source'))
 pins[k]=sha(raw)
contact_path='data/geography/part-26.json'
contact=subprocess.check_output(['git','show',f'{base}:{contact_path}'])
baseline_files.append(desc(contact_path,contact,'baseline-subject-features'))
assert all(pin_files[k] in [f['path'] for f in baseline_files] for k in pins)
source_full='sources/geoboundaries-usa-adm2-full-whole-source.geojson'
source_simple='sources/geoboundaries-usa-adm2-simplified-whole-source.bin.gz'
def candidate_desc(p,role):
 b=(root/p).read_bytes(); return desc(str((root/p).relative_to(Path('.'))),b,role)
sources=[
 {'id':'geoboundaries-usa-adm2-full-2018','url':'https://www.geoboundaries.org/api/current/gbOpen/USA/ADM2/','role':'Full-resolution USA ADM2 comparison product; contact features and source comparison','vintage':'represented 2018; release 9469f09592ced973a3448cf66b6100b741b64c0d','retrieved_at':'2026-10-07','license':{'status':'redistributable','terms':'Retained product metadata identifies Public Domain; geoBoundaries distribution documentation separately requires CC-BY 4.0 attribution. Both statements are preserved without resolving beyond the explicit terms.'},'retention':'retained','verification':'verified','temporal_status':'historical','supported_interval':{'from':2018,'to':2019},'files':[candidate_desc(source_full,'original-source')]},
 {'id':'geoboundaries-usa-adm2-simplified-2018','url':'https://www.geoboundaries.org/api/current/gbOpen/USA/ADM2/','role':'Consumed simplified USA ADM2 source and complete source-feature roster','vintage':'represented 2018; source update 2023-01-19; build 2023-12-12','retrieved_at':'2026-10-07','license':{'status':'redistributable','terms':'Retained product metadata identifies Public Domain; geoBoundaries distribution documentation separately requires CC-BY 4.0 attribution. Both statements are preserved without resolving beyond the explicit terms.'},'retention':'retained','verification':'verified','temporal_status':'historical','supported_interval':{'from':2018,'to':2019},'files':[candidate_desc(source_simple,'original-source')]},
 {'id':'census-tigerweb-2026-target-counties','url':'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/query','role':'Exact target-contact current county comparison; Nassau, Suffolk and Westchester','vintage':'2026 service capture; retrieved 2026-10-07T10:58:04Z','retrieved_at':'2026-10-07T10:58:04Z','license':{'status':'unknown','terms':'Captured endpoint metadata does not state source reuse or positional-accuracy terms; retain as bounded evidence only.'},'retention':'restoration-only','verification':'verified','temporal_status':'reference','restoration':'The exact request URL, parameters, layer metadata and returned target-only GeoJSON are preserved under sources/; repeat the bounded HTTPS query recorded in the retrieval receipt.','limit':'Only three exact counties were requested; this service capture does not establish historical boundary fitness, legal authority, or national coverage.'},
 {'id':'gshhg-2.3.7-physical-reference','url':'https://www.ngdc.noaa.gov/mgg/shorelines/shorelines.html','role':'Physical shoreline reference records used by the retained 31 component query','vintage':'GSHHG 2.3.7 release dated 2017-06-15; observation dates heterogeneous or unknown','retrieved_at':'2026-10-07','license':{'status':'unknown','terms':'Retained GSHHG LICENSE.TXT and README.TXT conflict about LGPL version direction; original full archive/native binary exceed the packet retention cap.'},'retention':'restoration-only','verification':'verified','temporal_status':'unknown','restoration':'Use the immutable physical source run report, member roster and query record hashes to locate the pinned GSHHG 2.3.7 release; selected native query records and source license files are retained in the packet.','limit':'Whole source ZIP is 118,617,033 bytes and native gshhs_f.b is 95,809,336 bytes, both above the 32 MiB per-file cap. Shoreline/channel registration, river width, seasonal wetness and source observation dates remain unresolved.'},
 {'id':'census-tigerline-2018-national','url':'https://www2.census.gov/geo/tiger/TIGER2018/COUNTY/tl_2018_us_county.zip','role':'Official same-purpose 2018 TIGER/Line target county geometry and complete attributes','vintage':'TIGER/Line 2018; modified 2018-09-18','retrieved_at':'2026-10-07','license':{'status':'unknown','terms':'Archive body not retained; license terms were not independently assessed from the target archive.'},'retention':'restoration-only','verification':'verified','temporal_status':'historical','supported_interval':{'from':2018,'to':2019},'restoration':'The full official archive was downloaded to temporary storage, complete archive SHA-256 recorded, and the three target rows extracted with exact shapefile/DBF member and record hashes in sources/census-tigerline-2018-extraction.json. Target rows are retained in sources/census-tigerline-2018-target-counties.geojson.','limit':'The 79,219,478-byte full archive exceeds the 32 MiB packet cap and is not included; only the exact three target county rows and extraction receipt are committed.'},
 {'id':'census-tigerline-2025-national','url':'https://www2.census.gov/geo/tiger/TIGER2025/COUNTY/tl_2025_us_county.zip','role':'Official later same-purpose 2025 TIGER/Line target county geometry and complete attributes','vintage':'TIGER/Line 2025; modified 2025-09-23','retrieved_at':'2026-10-07','license':{'status':'unknown','terms':'Archive body not retained; license terms were not independently assessed from the target archive.'},'retention':'restoration-only','verification':'verified','temporal_status':'historical','supported_interval':{'from':2025,'to':2026},'restoration':'The full official archive was downloaded to temporary storage, complete archive SHA-256 recorded, and the three target rows extracted with exact shapefile/DBF member and record hashes in sources/census-tigerline-2025-extraction.json. Target rows are retained in sources/census-tigerline-2025-target-counties.geojson.','limit':'The 83,989,800-byte full archive exceeds the 32 MiB packet cap and is not included; only the exact three target county rows and extraction receipt are committed.'},
 {'id':'worldatlas-accepted-routing-and-candidate-ancestry','url':'https://github.com/ChengshuLi/WorldAtlas','role':'Immutable accepted family routing, complete component ancestry, numeric diagnosis, physical query and source run evidence','vintage':'Pinned commits 0198938719a5666b6726fb6a1e45779926eefeb2, ea880cdc37b0bdfc63fdb52b79d74545a3e59c88, bec82842ad5d9cf07e38a78395df8d5e7a6f4591 and f8f99612e4d83d561b370189a1969c3e4301a1e3','retrieved_at':'2026-10-07','license':{'status':'unknown','terms':'Repository evidence is retained as audit material; upstream component/source rights remain governed by the individually recorded sources.'},'retention':'restoration-only','verification':'verified','temporal_status':'reference','restoration':'Use the immutable commits, the complete candidate custody index aliases, and the exact report paths pinned by the manifest; rebuild the target roster from the retained packet evidence.','limit':'Ancestor packages are preserved as Git objects and custody aliases; they are not reproduced in full in this bounded issue packet.'}
]
outputs=[]
source_paths={source_full,source_simple}
for p in sorted(root.rglob('*')):
 if not p.is_file(): continue
 rel=str(p.relative_to(Path('.')))
 if rel==str(root/'evidence-quality.json'): continue
 if rel in {str(root/x) for x in source_paths}: continue
 role='report'
 outputs.append(desc(rel,p.read_bytes(),role))
ids=[]
for line in (root/'accepted-routing-component-rows.json').read_text().splitlines():
 try: ids.append(json.loads(line).get('subject_id'))
 except: pass
# Issue scope is exactly 3 contact subjects, not 31 component IDs.
subject_ids_sha=sha(json.dumps(sorted(subject_ids),separators=(',',':')).encode())
manifest={
 'version':1,'issue':1377,'lane':'geography','worker_id':'01a11550-a19b-7330-955c-e56e90985bf3',
 'subject_ids':subject_ids,'subject_ids_sha256':subject_ids_sha,
 'baseline':{'commit':base,'files':baseline_files,'pins':pins,'pin_files':pin_files,'subject_files':{x:contact_path for x in subject_ids}},
 'sources':sources,'outputs':outputs,
 'methods':[{'id':'bounded-source-fitness-review','kind':'source','description':'Join exact immutable family/component/numeric/physical/source record identities; restore and hash all target geometry; retain raw source records; compare exact contact products and recorded equal-area overlap summaries without geometry repair, snapping, semantic inference or ownership transfer.','software':'Python 3; Shapely 2.1.2; pyproj 3.7.2; WorldAtlas evidence-quality v1','units':'Exact IDs and SHA-256; square metres inherited only where explicitly marked; dimensionless intersection-over-union.'}],
 'metrics':[],'metric_bindings':[],'summaries':[],
 'conclusions':[
  {'text':'The exact accepted family has 31 members; all 31 current features and physical query rows were restored and identity/hash matched, and all 15 numeric-first target IDs matched complete #1300 retained scope rows.','status':'supported','source_ids':['worldatlas-accepted-routing-and-candidate-ancestry']},
  {'text':'Source suitability is unresolved for all 31 components. The physical records cite GSHHG 2.3.7 with heterogeneous or unknown observation dates, and legal/water/ownership status is not established. Preserve all candidates and defer geometry processing.','status':'unresolved','source_ids':['gshhg-2.3.7-physical-reference','worldatlas-accepted-routing-and-candidate-ancestry']},
  {'text':'The three contacts were compared against exact rows extracted from complete, SHA-pinned official 2018 and 2025 TIGER/Line national archives, the retained 2018 geoBoundaries full and simplified products, and the bounded 2026 Census TIGERweb capture. The TIGER/Line county geometries are similar between 2018 and 2025 and 2025 TIGER/Line matches the 2026 TIGERweb capture; geoBoundaries differs materially for Suffolk and Nassau. The reason for these differences remains unresolved; source fit, legal authority and land/water status are not established.','status':'unresolved','source_ids':['geoboundaries-usa-adm2-full-2018','geoboundaries-usa-adm2-simplified-2018','census-tigerweb-2026-target-counties','census-tigerline-2018-national','census-tigerline-2025-national']}
 ],
 'stages':{'research':'partial','implementation':'not-proposed','geographic_approval':'unapproved'},
 'commands':['From repository root, run python3 research/geography/usa31-gap-family-source-fitness-20261007/build_evidence.py (offline reconstruction from pinned commits and captured inputs).','Run extract_tigerline_targets.py YEAR /path/to/tl_YEAR_us_county.zip for a newly downloaded full official TIGER/Line archive; the committed target rows and receipt do not require the full archive.','Run the bounded sources/capture_tigerweb_source.py only when a new Census TIGERweb capture is explicitly required; it performs a limited HTTPS source query.','Run the bundled Node evidence-quality validator against research/geography/usa31-gap-family-source-fitness-20261007/evidence-quality.json and the repository root.'],
 'change_receipts':[{'path':line.split('\t',1)[1],'status':{'A':'added','M':'modified','D':'removed','R':'renamed'}.get(line.split('\t',1)[0][0],line.split('\t',1)[0]),'previous_path':None} for line in subprocess.check_output(['git','diff','--name-status',base,'HEAD','--',str(root)],text=True).splitlines()],
 'external_snapshots':{'collision_issue_359_snapshot_body':'8f1539c649a0dd937eeddbbc21dcd50ba899043b47454d1a04b510a17ea8a1a6'},
 'claim_id':'ebb0dbbd-c2a5-4baf-8625-3a82030ce801','branch':'geography/usa31-gap-family-source-fitness-20261007','review_kind':'source'
}
(root/'evidence-quality.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
print('outputs',len(outputs),'baseline',len(baseline_files),'sources',len(sources),'pins',len(pins))
