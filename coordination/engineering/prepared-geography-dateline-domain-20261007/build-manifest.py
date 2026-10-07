"""Package already executed method evidence; does not run geography measurements."""
import hashlib
import json
from pathlib import Path
import subprocess
import shlex
import sys

CASE=Path(__file__).resolve().parent
ROOT=CASE.parents[2]
BASE='9be99dfefb5871237ac464c6ef8a23e82be501f6'
PREFIX=str(CASE.relative_to(ROOT))
sha=lambda b:hashlib.sha256(b).hexdigest()
def pin(path,raw):return {'path':path,'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'}
def original(path):return subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+path])
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'
config=json.loads((CASE/'config.json').read_bytes())
preflight=json.loads((CASE/'diagnosis/necessary-input-budget-complete-static-imports.json').read_bytes())
paths={r['path'] for r in preflight['consumed_snapshot']}|{r['path'] for r in config['snapshot_files']+config['source_files']}
# This is original consumer/import/input history. New actual executed modules are outputs.
baseline=[]
modified={'docs/GEOGRAPHIC_REGRESSION.md','scripts/evidence/geometry.py','scripts/check-geographic-regression.py','test/geographic-regression.py','test/geographic-regression.test.mjs'}
for path in sorted(paths):
    f=pin(path,original(path));f['role']='preimplementation-code' if path in modified else 'original-source';baseline.append(f)
policy=json.loads(subprocess.check_output(['gh','api','repos/ChengshuLi/WorldAtlas/issues/1293']))
body=policy['body'];contract=json.loads(body.split('<!-- worldatlas-work:v1\n',1)[1].split('\n-->',1)[0])
pins=contract['evidence_quality']['pins']
files_by_path={f['path']:f for f in baseline}
pin_files={'geometry_helper_sha256':'scripts/evidence/geometry.py','detector_sha256':'scripts/check-geographic-regression.py'}
for name,path in pin_files.items():assert files_by_path[path]['sha256']==pins[name]
registry=json.loads(original('data/administrative-sources.json'))
fji=config['retained_fji'];rus=config['source_files'][1]
sources=[]
for key,descriptor,retention in [('gb:FJI:ADM2',fji,'retained'),('gb:RUS:ADM2',rus,'restoration-only')]:
    metadata=registry[key]
    source={'id':key,'url':metadata['simplifiedGeometryGeoJSON'],'role':'Complete original consumed source geometry and metadata for predecessor diagnosis, not dated water or authority',
            'vintage':'Original whole source SHA '+metadata['sha256']+'; advertised represented year '+metadata['boundaryYearRepresented'],
            'retrieved_at':'Original capture or immutable Git body reauthenticated 2026-10-07; historical first retrieval time unknown',
            'license':{'status':'redistributable','terms':metadata['boundaryLicense']+'; exact original metadata and attribution are retained in the full baseline administrative registry.'},
            'retention':retention,'verification':'unverified','temporal_status':'reference',
            'limit':'Whole original bytes authenticated; dated physical water, legal authority and historical execution cause remain unverified.'}
    if retention=='retained':source['files']=[descriptor]
    else:source['restoration']='Exact whole ordinary baseline '+BASE+':'+descriptor['path']+'; full body hash '+descriptor['sha256']+' is included in baseline.files, avoiding a redundant duplicate descriptor.'
    sources.append(source)
sources.append({'id':'prepared-world-inventory','url':'https://github.com/ChengshuLi/WorldAtlas/tree/'+BASE+'/data/geography','role':'Complete committed prepared footprint inventory and release bindings, not original source member authority',
                'vintage':BASE,'retrieved_at':'2026-10-07 immutable whole Git readback','license':{'status':'unknown','terms':'Mixed upstream terms remain in original registry; no new general licensing conclusion.'},
                'retention':'restoration-only','verification':'unverified','temporal_status':'reference',
                'restoration':'All 36 containing parts and complete release/hierarchy/index pins retained through baseline.files at exact immutable Git vintage.',
                'limit':'Prepared representation validation does not approve geography, physical water, ownership, original preparation cause or repair.'})
outputs=[]
for path in sorted(modified):outputs.append(pin(path,(ROOT/path).read_bytes()))
for target in sorted(CASE.rglob('*')):
    if not target.is_file() or '.cache' in target.parts or target.name=='evidence-quality.json' or target==ROOT/fji['path']:continue
    rel=str(target.relative_to(ROOT));raw=target.read_bytes();item=pin(rel,raw)
    if target.suffix=='.gz':
        import gzip
        decoded=gzip.decompress(raw);item.update(uncompressed_bytes=len(decoded),uncompressed_sha256=sha(decoded))
    outputs.append(item)
assert len({f['path'] for f in outputs})==len(outputs)
report=json.loads((CASE/'run-one/report.json').read_bytes())
proof=json.loads((CASE/'verification/whole-readback.json').read_bytes())
metrics=[];bindings=[];summaries=[]
for key,value,pointer,unit in [('complete_features',report['feature_count'],'/feature_count','complete features'),('strict_default_failures',report['strict_default_failures'],'/strict_default_failures','retained strict failures'),('prepared_failures',report['prepared_failures'],'/prepared_failures','prepared failures')]:
    metrics.append({'id':key,'value':value,'unit':unit,'input_sha256':sha((CASE/'config.json').read_bytes()),'evaluation_commit':report['code_commit'],'vintage':'archived'})
    bindings.append({'metric_id':key,'path':PREFIX+'/run-one/report.json','json_pointer':pointer});summaries.append({'metric_id':key,'value':value,'unit':unit})
metrics.append({'id':'complete_directed_seam_contacts','value':proof['complete_directed_seam_contacts'],'unit':'directed complete seam contacts','input_sha256':sha((CASE/'config.json').read_bytes()),'evaluation_commit':report['code_commit'],'vintage':'archived'})
bindings.append({'metric_id':'complete_directed_seam_contacts','path':PREFIX+'/verification/whole-readback.json','json_pointer':'/complete_directed_seam_contacts'})
summaries.append({'metric_id':'complete_directed_seam_contacts','value':proof['complete_directed_seam_contacts'],'unit':'directed complete seam contacts'})
receipts=[{'path':f['path'],'status':'modified','original_sha256':sha(original(f['path']))} for f in outputs if f['path'] in modified]
receipts.extend({'path':f['path'],'status':'added'} for f in outputs if f['path'] not in modified)
receipts.extend({'path':fji['path'],'status':'added'} for _ in [0])
receipts.append({'path':PREFIX+'/evidence-quality.json','status':'added'})
manifest={'version':1,'issue':1293,'lane':'engineering','worker_id':'01a10fea-fe9b-7722-a974-0269a733a330','subject_ids':[],
          'subject_ids_sha256':sha(b'[]'),'baseline':{'commit':BASE,'files':baseline,'pins':pins,'pin_files':pin_files},'sources':sources,'outputs':outputs,
          'methods':[{'id':'prepared-domain-validation','kind':'measurement','description':'Fixed committed prepared antimeridian-cut representation; strict original-source defaults unchanged. Exact member/whole/periodic validity before clipping/union, only opposing exact world-seam contacts admitted; whole immutable roster/source/code/runtime bindings and two actual full ordered validations.',
                      'software':'Python3.12.14 / NumPy2.3.5 / Shapely2.1.2 / GEOS3.13.1 / PyProj3.7.2; actual science commit '+report['code_commit'],
                      'units':'validity dispositions, full geometry hashes and exact original coordinate pointsets; no new geographic area or distance metric claimed','prepared_domain':report['domain']}],
          'metrics':metrics,'metric_bindings':bindings,'summaries':summaries,
          'conclusions':[{'status':'supported','source_ids':[s['id'] for s in sources],'text':'Both actual complete 49,625-feature executions agree: prepared failures zero, three strict-source failures and all twelve directed seam contacts retained. No source pointset or installed geography changed.'},
                         {'status':'unresolved','source_ids':['gb:FJI:ADM2','gb:RUS:ADM2'],'text':'Original Fiji out-of-range source coordinates remain unsupported; original/current source member differences and historical execution cause are not resolved. This method does not approve land, water, ownership, legal authority or repair.'}],
          'stages':{'research':'complete','implementation':'implemented','geographic_approval':'unapproved'},
          'commands':[shlex.join(r['complete_command']) for r in [report,json.loads((CASE/'run-two/report.json').read_bytes())]],
          'validation':[{'method_id':'prepared-domain-validation','kind':kind,'outcome':'passed','evidence_path':PREFIX+'/verification/'+kind+'.json'} for kind in ['positive-control','negative-control','reproducibility']],
          'change_receipts':sorted(receipts,key=lambda r:r['path'])}
(CASE/'evidence-quality.json').write_bytes(canonical(manifest))
all_files=baseline+[fji]+outputs
print(json.dumps({'descriptors':len(all_files),'encoded_bytes':sum(f['bytes'] for f in all_files),'headroom':256*1024*1024-sum(f['bytes'] for f in all_files),'max_encoded':max(f['bytes'] for f in all_files),'max_decoded':max(f.get('uncompressed_bytes',f['bytes']) for f in all_files),'changed_files':len(receipts)}))
