"""Post-execution evidence metadata; no scientific or subject execution."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
NS=Path('coordination/engineering/subject-descriptor-decode-20261007')
BASE='83bed8c4c49e8f54077bb4abf0f32d41d0992f81'
FREEZE='4de4a4c2ed0c908eb08f3927b45ad73e75539b65'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def git(c,p):return subprocess.check_output(['git','-C',str(ROOT),'show',c+':'+p],stderr=subprocess.DEVNULL)
def desc(p,raw=None):
 raw=(ROOT/p).read_bytes() if raw is None else raw
 return {'path':str(p),'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'}
plan=json.loads((ROOT/NS/'source-plan.json').read_text());inputs=[]
for f in plan['files']:
 assert git(BASE,f['path'])==git(plan['source_commit'],f['path']);inputs.append(dict(f))
inputs.extend(desc(p,git(BASE,p)) for p in ['scripts/evidence-quality.mjs','test/evidence-quality.test.mjs'])
paths=sorted(set(subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only',BASE],text=True).splitlines()+subprocess.check_output(['git','-C',str(ROOT),'ls-files','--others','--exclude-standard'],text=True).splitlines()))
manifest=str(NS/'evidence-quality.json');paths=[p for p in paths if p!=manifest];outputs=[desc(p) for p in paths];receipts=[]
for p in paths+[manifest]:
 try:old=git(BASE,p)
 except subprocess.CalledProcessError:old=None
 receipts.append({'path':p,'status':'added' if old is None else 'modified',**({'original_sha256':sha(old)} if old is not None else {})})
metrics=[];bindings=[]
for k,v in [('subject_count',53),('physical_components',45),('current_contacts',8),('numeric_siblings_preserved',21),('source_files',12),('passed_tests',32)]:
 p=str(NS/'verification'/('positive-controls.json' if k=='passed_tests' else 'reproducibility.json' if k=='source_files' else 'run-one-subjects.json'));raw=(ROOT/p).read_bytes();assert json.loads(raw)[k]==v
 metrics.append({'id':k,'value':v,'unit':'count','vintage':'archived','input_sha256':sha(raw),'evaluation_commit':FREEZE});bindings.append({'metric_id':k,'path':p,'json_pointer':'/'+k})
m={'version':1,'issue':1393,'lane':'engineering','worker_id':'01a10fea-fe9b-7722-a974-0269a733a330','subject_ids':[],'subject_ids_sha256':sha(b'[]'),
'baseline':{'commit':BASE,'files':inputs,'pins':{'original_subject_validator':sha(git(BASE,'scripts/evidence-quality.mjs'))},'pin_files':{'original_subject_validator':'scripts/evidence-quality.mjs'}},
'sources':[{'id':'original-subject-custody','url':'https://github.com/ChengshuLi/WorldAtlas/tree/'+plan['source_commit'],'role':'Retained component/contact identity custody only','vintage':plan['source_commit'],'retrieved_at':'2026-10-07','license':{'status':'unknown','terms':'Underlying terms/date/physical authority remain as retained by original research; this fix grants no approval'},'retention':'restoration-only','verification':'unverified','temporal_status':'unknown','restoration':'Read all twelve immutable whole Git files in source-plan.json; encoded and decoded descriptors are in the baseline','limit':'Subject membership/byte verification only; no numerical geography or source-fitness approval'}],
'outputs':outputs,'methods':[{'id':'subject-decode','kind':'code','description':'Declared gzip subject JSON through the existing bounded reader, exact baseline membership and real-entry controls','software':'Node24.19.0; Python metadata only; no GIS','units':'bytes and subject identities'}],
'validation':[{'method_id':'subject-decode','kind':k,'outcome':'passed','evidence_path':str(NS/'verification'/(k+'-controls.json'))} for k in ['positive','negative']]+[{'method_id':'subject-decode','kind':'reproducibility','outcome':'passed','evidence_path':str(NS/'verification/reproducibility.json')}],
'metrics':metrics,'metric_bindings':bindings,'summaries':[{'metric_id':v['id'],'value':v['value'],'unit':v['unit']} for v in metrics],'conclusions':[{'text':'Corrected readers preserve complete membership and bounded decoding; source physical/date/license approvals remain unresolved','status':'unresolved','source_ids':['original-subject-custody']}],
'stages':{'research':'complete','implementation':'implemented','geographic_approval':'not-requested'},'commands':['node --test test/evidence-quality.test.mjs test/premerge-evidence.test.mjs','node '+str(NS/'check-subjects.mjs')+' '+FREEZE+' run-one|run-two'],'change_receipts':receipts}
(ROOT/manifest).write_text(json.dumps(m,indent=2)+'\n');print(json.dumps({'outputs':len(outputs),'baseline_files':len(inputs),'bytes':sum(x['bytes'] for x in outputs+inputs),'metrics':len(metrics)}))
