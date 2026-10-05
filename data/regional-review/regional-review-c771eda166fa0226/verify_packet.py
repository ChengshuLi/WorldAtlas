#!/usr/bin/env python3
"""Offline scope, source-byte, handoff, and two-run reproduction checks for #471."""
import gzip,hashlib,json,os,subprocess,sys
from pathlib import Path
OWN=Path(__file__).resolve().parent
REPO=OWN.parents[2]
read=lambda p: json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda b: hashlib.sha256(b).hexdigest()
asserts=[]
def ok(condition,message):
 if not condition: raise SystemExit('FAIL: '+message)
 asserts.append(message)
scope=read(OWN/'issue-scope-pinned.json'); receipt=read(OWN/'baseline-receipt.json')
assert len(scope['member_location_ids'])==216 and len(set(scope['member_location_ids']))==216
asserts.append('exact issue roster contains 216 unique IDs')
assert receipt['baseline_commit']=='7ffd4e35364ec8246b9add7459378b3f971fcd72'
asserts.append('baseline commit matches pinned latest main')
bgz=(OWN/'baseline-members.geojson.gz').read_bytes(); raw=gzip.decompress(bgz)
assert len(bgz)==receipt['extracted_members']['compressed_bytes'] and sha(bgz)==receipt['extracted_members']['compressed_sha256']
assert len(raw)==receipt['extracted_members']['uncompressed_bytes'] and sha(raw)==receipt['extracted_members']['uncompressed_sha256']
base=json.loads(raw); ids=[f.get('id') or (f.get('properties') or {}).get('id') for f in base['features']]
assert ids==scope['member_location_ids'] and len(ids)==216
asserts.append('baseline gzip restores exact issue roster')
register=read(OWN/'sources/register.json'); fetch=read(OWN/'sources/retrieval-verified.json')
assert register['version']==2 and len(register['sources'])==6 and len(fetch)==6
fetch_by={s['id']:s for s in fetch}
for source in register['sources']:
 rec=fetch_by[source['id']]
 assert source['original_sha256']==rec['original_sha256'] and source['retained_gzip_sha256']==rec['retained_gzip_sha256']
 gzpath=REPO/source['retained_path']; zipped=gzpath.read_bytes(); original=gzip.decompress(zipped)
 assert len(original)==source['original_bytes'] and sha(original)==source['original_sha256']
 assert len(zipped)==source['retained_gzip_bytes'] and sha(zipped)==source['retained_gzip_sha256']
 assert sha((OWN/source['metadata_snapshot']['path']).read_bytes())==source['metadata_snapshot']['sha256']
 assert sha((OWN/source['citation_and_use_snapshot']['path']).read_bytes())==source['citation_and_use_snapshot']['sha256']
asserts.append('all six geoBoundaries child/parent original, compressed, metadata, and citation bytes verify')
ne_register=read(OWN/'sources/natural-earth-10m-admin1/register.json')
assert ne_register['commit']=='ca96624a56bd078437bca8184e78163e5039ad19' and len(ne_register['retained_original_components_gzip_losslessly'])==7
for source in ne_register['retained_original_components_gzip_losslessly']:
 retained=REPO/source['retained_path']; zipped=retained.read_bytes(); original=gzip.decompress(zipped)
 assert len(original)==source['original_bytes'] and sha(original)==source['original_sha256']
 assert len(zipped)==source['retained_gzip_bytes'] and sha(zipped)==source['retained_gzip_sha256']
asserts.append('Natural Earth source components restore byte-for-byte from pinned commit hashes and the public-domain register')
cr=read(OWN/'source-crosswalk.json'); cross=cr['members']; assert len(cross)==216 and {r['id'] for r in cross}==set(scope['member_location_ids'])
asserts.append('crosswalk has exactly one row per issue subject')
assert not any(k.startswith('gss2021_union_') for r in cross for k in r)
gss=cr['summary']['gss2021']; assert gss['official_unit_count']==261 and len(gss['inner_sha256'])==64
assert all(r.get('gss2021_spatial_record') is None or isinstance(r['gss2021_spatial_record'],int) for r in cross)
assert any(r.get('gss2021_named_match_record') is not None for r in cross)
asserts.append('GSS official named candidate is distinct from nearest spatial candidate; no misleading union metric remains')
control=cr['summary']['geometry_method']['controls']; assert control=={'identical_triangle_overlap':1.0,'disjoint_triangle_overlap':0.0,'passed':True}
asserts.append('positive and negative equal-area overlap controls pass')
assessment=read(OWN/'assessment.json'); assert assessment['subject_count']==216 and len(assessment['subjects'])==216
assert {r['id'] for r in assessment['subjects']}==set(scope['member_location_ids'])
valid={'justified','correction-needed','insufficient-evidence'}
assert all(r['status'] in valid and r['evidence'] and 'source_payload_sha256' in r for r in assessment['subjects'])
assert len(assessment['provinces'])==18 and len(assessment['areas'])==3
for p in assessment['provinces']:
 members=[x['id'] for x in assessment['subjects'] if x['province_id']==p['id']]
 assert sorted(members)==sorted(p['subject_ids']) and len(members)==p['scoped_location_count']
for a in assessment['areas']:
 members=[x['id'] for x in assessment['subjects'] if x['area_id']==a['id']]
 assert sorted(members)==sorted(a['subject_ids']) and len(members)==a['scoped_location_count']
asserts.append('all 216 members individually assessed; all 18 province and 3 area rosters reconcile')
city=assessment['gambia_banjul_aggregation']; part=city['source_layer_partition']
assert part['complete_partition'] and part['source_feature_count']==48 and part['standalone_scoped_source_count']==39 and part['aggregate_member_source_count']==9
assert city['atlas_vs_nine_source_member_union']['iou']>=.94 and {x['name'] for x in city['lga_intersections']}=={'Brikama','Kanifing','Banjul'}
ne=city['natural_earth_record']
assert ne['target_attributes']['adm1_code']=='GMB-2153' and ne['target_attributes']['type_en']=='Independent City'
assert ne['natural_earth_vs_atlas_city']['iou']<.6 and ne['natural_earth_vs_nine_geoBoundaries_member_union']['iou']<.6
asserts.append('Gambia district layer partitions into 39 standalone plus nine city-member IDs; city overlay and three-LGA parent screen reproduce')
coverage=read(OWN/'coverage-screen.json'); assert set(coverage['source_remainders'])=={'GMB','GHA','CIV'}
assert len(coverage['source_remainders']['GHA']['source_layer_remainder_ids'])==147 and len(coverage['source_remainders']['CIV']['source_layer_remainder_ids'])==447
assert len(coverage['source_parent_screens']['GHA']['source_child_coverage_below_0_95'])==20
asserts.append('partial-country source remainders and 20 weak Ghana source-parent overlaps are explicit')
handoffs=read(OWN/'findings-and-handoffs.json'); assert [h['issue'] for h in handoffs['handoffs']]==[830,835,831,832]
assert [len(h['subject_ids']) for h in handoffs['handoffs']]==[1,10,84,63]
assert handoffs['subject_count']==158 and all(h['status']=='blocked' for h in handoffs['handoffs'])
asserts.append('four bounded blocked follow-ups cover exact disjoint findings')
ref=read(OWN/'reference-source-checksums.json'); assert len(ref['unredistributable_or_restore_only']['ghana_gss_geofiles']['sha256'])==64
asserts.append('unknown-term official comparators use checksummed restoration-only records')
issue_meta=read(OWN/'issue-metadata.json'); assert issue_meta['machine_contract']['owned_paths']==['data/regional-review/regional-review-c771eda166fa0226/']
asserts.append('issue declares this exact owned path')
# Reproduce deterministic generated results twice and require byte-identical outputs.
outputs=['source-crosswalk.json','source-crosswalk.csv','assessment.json','coverage-screen.json','findings-and-handoffs.json']
before={p:sha((OWN/p).read_bytes()) for p in outputs}
env=os.environ.copy()
for command in [['compare_source_crosswalk.py'],['analyze_packet.py'],['build_handoffs.py'],['compare_source_crosswalk.py'],['analyze_packet.py'],['build_handoffs.py']]:
 result=subprocess.run([sys.executable,str(OWN/command[0])],cwd=REPO,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 if result.returncode: raise SystemExit(f'FAIL: {command[0]}: {result.stderr or result.stdout}')
after={p:sha((OWN/p).read_bytes()) for p in outputs}
assert before==after,'generator outputs changed between independent runs'
asserts.append('source crosswalk, subject/province/area assessment, coverage, and handoffs reproduce identically twice')
index=read(OWN/'evidence-review-index.json'); listed={x['path']:x for x in index['files']}
actual={p.relative_to(REPO).as_posix():p for p in OWN.rglob('*') if p.is_file() and p.name!='evidence-review-index.json'}
assert set(listed)==set(actual),'review index file roster differs from packet tree'
for name,p in actual.items():
 b=p.read_bytes(); d=listed[name]; assert len(b)==d['bytes'] and sha(b)==d['sha256'],f'review index hash mismatch: {name}'
asserts.append('whole-file evidence-review index covers every packet file exactly')
# No tracked or untracked worktree change may leave the declared owned directory.
status=subprocess.run(['git','status','--porcelain','--untracked-files=all'],cwd=REPO,stdout=subprocess.PIPE,text=True,check=True).stdout
outside=[line[3:] for line in status.splitlines() if line[3:] and not line[3:].startswith('data/regional-review/regional-review-c771eda166fa0226/')]
assert not outside,'worktree contains paths outside the issue owned path: '+repr(outside)
asserts.append('worktree changes stay within the declared owned path')
print(json.dumps({'result':'passed','checks':asserts,'subjects':216,'provinces':18,'areas':3,'status_counts':assessment['status_counts'],'followups':len(handoffs['handoffs'])},ensure_ascii=False,indent=2))
