#!/usr/bin/env python3
"""Capture only the assigned batch rows from one complete corrected catalog leaf."""
import datetime,gzip,hashlib,json,platform,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OWNED='research/geography/melanesia-gap-batch-37ed51b2-20261009/'
if len(sys.argv)!=2 or sys.argv[1] not in [str(x) for x in range(1,8)]:raise SystemExit('usage: python3.12 capture-catalog.py LEAF_1_TO_7')
leaf=sys.argv[1];RUN='catalog-route-l'+leaf.zfill(2);pinpath=ROOT/OWNED/'catalog-capture-pins.json';pins=json.loads(pinpath.read_text())['leaves'][leaf]
if (ROOT/OWNED/'vintages'/RUN).exists():raise SystemExit('refusing existing vintage')
helper_path='scripts/evidence/immutable.py';hrow=next(x for x in pins['files']if x['path']==helper_path);hb=subprocess.check_output(['git','-C',str(ROOT),'show',json.loads(pinpath.read_text())['baseline_commit']+':'+helper_path]);assert len(hb)==hrow['bytes'] and hashlib.sha256(hb).hexdigest()==hrow['sha256']
ns={'__name__':'pinned_evidence','__file__':str(ROOT/helper_path)};exec(compile(hb,str(ROOT/helper_path),'exec'),ns)
Baseline=ns['Baseline'];NewVintage=ns['NewVintage'];canonical_json=ns['canonical_json'];commit=json.loads(pinpath.read_text())['baseline_commit']
baseline=Baseline(ROOT,commit,pins['files']);assert baseline.pinned_bytes(helper_path)==hb
candidate_path=next(x['path']for x in pins['files']if x['path'].endswith('/candidate-capture.json'));scope=json.loads(baseline.pinned_bytes(candidate_path));ids=[x['component_id']for x in scope['candidate_records']];idset=set(ids);assert len(ids)==363 and len(idset)==363
pubpath=next(x['path']for x in pins['files']if x['path'].endswith('/publication.json'));pub=json.loads(baseline.pinned_bytes(pubpath));cap_pin=next(x for x in pub['outputs']if x['path']==candidate_path);assert cap_pin['sha256']==hashlib.sha256(baseline.pinned_bytes(candidate_path)).hexdigest()
rows={};scanned=0;started=time.monotonic();catalog_decoded=[]
for path in pins['catalog_shards']:
 encoded=baseline.pinned_bytes(path);expected=next(x['decoded_bytes']for x in pins['files']if x['path']==path);baseline.admit(path+':decoded',expected);decoded=gzip.decompress(encoded);assert len(decoded)==expected
 catalog_decoded.append({'path':path,'encoded_bytes':len(encoded),'encoded_sha256':hashlib.sha256(encoded).hexdigest(),'decoded_bytes':len(decoded),'decoded_sha256':hashlib.sha256(decoded).hexdigest()})
 for line in decoded.splitlines():
  row=json.loads(line);scanned+=1;component_id=row.get('component_id')
  if component_id in idset:assert component_id not in rows;rows[component_id]=row
execution_commit=commit
result={'schema':'melanesia-batch-catalog-snapshot/v1','batch_id':scope['batch_id'],'assigned_component_count':len(ids),'assigned_component_ids_sha256':scope['component_ids_sha256'],'leaf_index':int(leaf),'catalog_rows_scanned':scanned,'assigned_rows_in_leaf':len(rows),'catalog_leaf_source_commit':execution_commit,'catalog_shard_inputs':catalog_decoded,'catalog_snapshot_rows':[{'component_id':i,'catalog_row':rows[i]}for i in sorted(rows)],'limits':['retained routing snapshot only; the catalog is not new scientific analysis or an accepted physical/source-fit decision']}
script_bytes=Path(__file__).read_bytes();execrow={'status':'completed','completed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline_commit':commit,'leaf_index':int(leaf),'command':sys.executable+' '+str(Path(__file__).relative_to(ROOT))+' '+leaf,'script_sha256':hashlib.sha256(script_bytes).hexdigest(),'script_bytes':len(script_bytes),'runtime':{'python':platform.python_version()},'elapsed_seconds':time.monotonic()-started,'admitted_input_bytes':sum(baseline.consumed.values()),'helper':'pinned Baseline + exclusive NewVintage'}
values={'catalog-subset.json':canonical_json(result),'execution.json':canonical_json(execrow),'capture-catalog.py':script_bytes,'catalog-capture-pins.json':pinpath.read_bytes()}
NewVintage(baseline,OWNED,RUN,list(values)).publish_bytes(values)
print(json.dumps({'status':'published','leaf':leaf,'assigned_rows':len(rows),'scanned_rows':scanned,'admitted_bytes':sum(baseline.consumed.values())}))
