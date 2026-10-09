#!/usr/bin/env python3
"""Capture the exact complete #1626 component assignment into a fresh vintage."""
import datetime,gzip,hashlib,json,platform,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OWNED='research/geography/melanesia-gap-batch-37ed51b2-20261009/'
RUN='candidate-capture-001'
PINS=ROOT/OWNED/'candidate-capture-pins.json'
SCOPE=ROOT/OWNED/'inputs/assignment-scope.json'
if (ROOT/OWNED/'vintages'/RUN).exists():raise SystemExit('refusing existing vintage')
pins=json.loads(PINS.read_text());scope_bytes=SCOPE.read_bytes();scope=json.loads(scope_bytes)
assert scope['campaign']==1202 and scope['worker']=='geo4' and scope['assignment_scope']=='complete-existing-operational-batch'
batch=scope['batch'];ids=batch['complete_component_ids'];assert len(ids)==363 and len(ids)==len(set(ids)) and batch['component_count']==363
helper_path='scripts/evidence/immutable.py';helper_row=next(x for x in pins['files'] if x['path']==helper_path)
helper_bytes=subprocess.check_output(['git','-C',str(ROOT),'show',pins['baseline_commit']+':'+helper_path]);assert len(helper_bytes)==helper_row['bytes'] and hashlib.sha256(helper_bytes).hexdigest()==helper_row['sha256']
ns={'__name__':'pinned_evidence','__file__':str(ROOT/helper_path)};exec(compile(helper_bytes,str(ROOT/helper_path),'exec'),ns)
Baseline=ns['Baseline'];NewVintage=ns['NewVintage'];canonical_json=ns['canonical_json']
baseline=Baseline(ROOT,pins['baseline_commit'],pins['files']);assert baseline.pinned_bytes(helper_path)==helper_bytes
index=json.loads(baseline.pinned_bytes(pins['custody_index']))
index_payload_paths={x['path']:x for x in index['payloads']}
component_aliases={}
for payload in pins['component_payloads']:
 entries=[x for x in index['aliases'] if x.get('payload')==payload and '/components-v3/components-' in x['original']['path']]
 assert len(entries)==1
 original=entries[0]['original'];listed=index_payload_paths[payload]
 assert listed['bytes']==original['bytes'] and listed['sha256']==original['sha256']
 assert len(baseline.pinned_bytes(payload))==original['bytes']
 baseline.admit(payload+':decoded',original['uncompressed_bytes'])
 component_aliases[payload]=original
records={};started=time.monotonic()
for payload in pins['component_payloads']:
 raw=gzip.decompress(baseline.pinned_bytes(payload));original=component_aliases[payload]
 assert len(raw)==original['uncompressed_bytes'] and hashlib.sha256(raw).hexdigest()==original['uncompressed_sha256']
 value=json.loads(raw);features=value if isinstance(value,list) else value.get('features',[])
 for f in features:
  fid=f.get('id')
  if fid in ids:
   assert fid not in records
   records[fid]={'feature':f,'component_feature_sha256':hashlib.sha256(canonical_json(f)).hexdigest(),'component_geometry_sha256':hashlib.sha256(canonical_json(f['geometry'])).hexdigest(),'custody_payload':payload,'original_source_path':original['path'],'original_source_bytes':original['bytes'],'original_source_sha256':original['sha256'],'original_decoded_bytes':original['uncompressed_bytes'],'original_decoded_sha256':original['uncompressed_sha256']}
assert set(records)==set(ids),f"candidate record closure failed: {len(records)} of {len(ids)}"
rows=[{'component_id':fid,**records[fid]} for fid in ids]
result={'schema':'melanesia-complete-candidate-capture/v1','batch_id':batch['batch_id'],'component_count':len(rows),'component_ids_sha256':hashlib.sha256(canonical_json(sorted(ids))).hexdigest(),'scope_file_sha256':hashlib.sha256(scope_bytes).hexdigest(),'source_generation':'physical-gap-components-1005 custody-v1 aliases for original components-v3; exact original Feature records preserved','candidate_records':rows,'limits':['candidate capture only; no source fit, native cell assignment, contemporary authority, or cause is concluded']}
execution={'status':'completed','completed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline_commit':pins['baseline_commit'],'scope_file':{'path':str(SCOPE.relative_to(ROOT)),'bytes':len(scope_bytes),'sha256':hashlib.sha256(scope_bytes).hexdigest(),'origin':'task-assigned external full-batch work index copied byte-for-byte into this owned packet'},'script':{'path':str(Path(__file__).relative_to(ROOT)),'bytes':Path(__file__).stat().st_size,'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},'runtime':{'python':platform.python_version()},'elapsed_seconds':time.monotonic()-started,'admitted_input_bytes':sum(baseline.consumed.values()),'helper':'pinned scripts/evidence/immutable.py Baseline + NewVintage'}
values={'candidate-capture.json':canonical_json(result),'execution.json':canonical_json(execution),'capture-candidates.py':Path(__file__).read_bytes(),'candidate-capture-pins.json':PINS.read_bytes(),'assignment-scope.json':scope_bytes}
NewVintage(baseline,OWNED,RUN,list(values)).publish_bytes(values)
print(json.dumps({'status':'published','batch_id':batch['batch_id'],'candidates':len(rows),'admitted_input_bytes':sum(baseline.consumed.values())}))
