"""Metadata only: no source extraction, native parser, geometry or producer invocation.
Run only after actual two-run exit receipts and root's canonical retention.
"""
import argparse
import gzip
import hashlib
import json
import pathlib
import re
import subprocess

NS='coordination/engineering/gshhg-native-member-custody-20261007/'
LIMIT=33554432
BUDGET=268435456
BLOCK=8388608
BASE='f8f99612e4d83d561b370189a1969c3e4301a1e3'
EXEC='bc1dcbecebedf35203cf14b92a91ef0d957cf2f0'

def require(ok,message):
    if not ok:raise ValueError(message)

def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()

def hash_file(path):
    h=hashlib.sha256();n=0
    with path.open('rb') as f:
        for b in iter(lambda:f.read(BLOCK),b''):h.update(b);n+=len(b)
    return n,h.hexdigest()

def descriptor(path,relative):
    require(not path.is_symlink() and path.is_file(),'Ordinary retained file required: '+str(path))
    n,h=hash_file(path);require(n<=LIMIT,'Encoded ordinary bound: '+relative)
    value={'path':relative,'bytes':n,'sha256':h,'hash_kind':'file-bytes'}
    if path.name.endswith('.gz'):
        decoded=hashlib.sha256();size=0
        with gzip.open(path,'rb') as f:
            while True:
                b=f.read(min(BLOCK,LIMIT-size+1))
                if not b:break
                size+=len(b);require(size<=LIMIT,'Decoded ordinary bound: '+relative);decoded.update(b)
        value.update(uncompressed_bytes=size,uncompressed_sha256=decoded.hexdigest())
    return value

def run(a):
    repo=a.repo.resolve();packet=repo/NS
    index=json.loads((packet/'input-index.json').read_bytes())
    issue=json.loads(a.issue_json.read_bytes())
    body=issue['body'];spec=json.loads(re.search(r'<!-- worldatlas-work:v1\s*(.*?)\s*-->',body,re.S).group(1))
    require(spec['evidence_quality']['manifest_path']==NS+'evidence-quality.json','Actual issue namespace differs')
    require(a.worker=='01a10893-2a57-72e0-aa08-5c36088d5206','Actual root author identity required')
    pairs=[]
    reports=[]
    for label,root in [('one',a.run_one),('two',a.run_two)]:
        report=json.loads((root/'report.json').read_bytes())
        require(report['status']=='PASS' and report['execution_commit']==EXEC,'Actual frozen report differs')
        require(report['unique_source_input_count']==12 and report['unique_source_bytes']==118671090,
                'Complete source read roster differs')
        require(report['member_payloads_decompressed']==['gshhs_f.b'],'Wrong fresh decompressed source scope')
        require(report['actual_downstream_reader']['full_validation_before_consumer'] is True and
                report['actual_downstream_reader']['source_zip_reads_by_downstream']==0,'Actual downstream guard missing')
        require(len(report['outputs'])==23,'Complete scientific output roster differs')
        actual=[]
        for row in report['outputs']:
            require(pathlib.PurePosixPath(row['path']).name==row['path'],'Unsafe output name')
            got=descriptor(root/row['path'],row['path'])
            for k,v in got.items():require(row[k]==v,'Actual complete scientific body differs: '+row['path'])
            actual.append(got)
        require(len({r['path'] for r in actual})==23,'Duplicate complete output')
        pairs.append(actual)
        reports.append({'label':label,'report':descriptor(root/'report.json',NS+'proof/run-'+label+'-report.json'),
                        'actual_execution':{'start_utc':report['actual_start_utc'],'end_utc':report['actual_end_utc'],
                         'elapsed_seconds':report['elapsed_seconds'],'command':report['command'],'pid':report['pid']},
                        'complete_ordered_outputs':actual})
    require(pairs[0]==pairs[1],'Actual full scientific trees differ; no dedup permitted')
    # Caller must retain truthful process terminal receipts, not infer exit from reports.
    terminal=json.loads(a.terminal_receipt.read_bytes())
    require(terminal['execution_commit']==EXEC and len(terminal['runs'])==2 and
            all(x['exit_code']==0 for x in terminal['runs']),'Actual two terminal receipts required')
    for row in pairs[0]:
        require(descriptor(packet/'results'/row['path'],row['path'])==row,'Canonical retained body differs')
    for item in reports:
        path=repo/item['report']['path']
        require(descriptor(path,item['report']['path'])==item['report'],'Retained original actual report differs')
    tree_sha=hashlib.sha256(canonical(pairs[0])).hexdigest()
    proof={'status':'PASS','method_id':'native-member-byte-custody','kind':'reproducibility','outcome':'passed',
           'run_one_sha256':tree_sha,'run_two_sha256':tree_sha,'execution_commit':EXEC,'method':'Complete ordered whole encoded and decoded body comparison; no numerical rerun',
           'runs':reports,'actual_terminal_receipt':terminal,'canonical_path':NS+'results/',
           'scientific_payload_count':23,'scientific_payload_encoded_bytes':sum(x['bytes'] for x in pairs[0]),
           'limits':['Two actual frozen executions remain distinct; only byte-identical full payloads are retained once.',
                     'Only target member decompressed; seventeen other body hashes remain inherited upstream.']}
    proofpath=packet/'proof/reproducibility.json';require(not proofpath.exists(),'Fresh reproducibility metadata required')
    proofpath.write_bytes(canonical(proof))
    ledger={'native_records':188612,'native_bytes':95809336,'ordinary_native_fragments':3,
            'original_archive_directory_members':18,'fresh_member_bodies_decompressed':1,'actual_complete_executions':2}
    ledgerpath=packet/'proof/counts.json';require(not ledgerpath.exists(),'Fresh ledger metadata required');ledgerpath.write_bytes(canonical(ledger))
    baseline=[]
    for pin in index['source_files']:
        raw=subprocess.check_output(['git','-C',str(repo),'show',pin['commit']+':'+pin['path']])
        tree=subprocess.check_output(['git','-C',str(repo),'ls-tree',pin['commit'],'--',pin['path']]).decode().strip().split()
        require(tree[0]==pin['mode']=='100644' and tree[2]==pin['blob'],'Actual source mode/OID differs')
        require(len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'Actual source whole bytes differ')
        # The machine manifest has one baseline commit; prove exact byte/OID
        # identity there separately, preserving actual per-read vintage above.
        baseline_raw=subprocess.check_output(['git','-C',str(repo),'show',BASE+':'+pin['path']])
        require(baseline_raw==raw,'Single-baseline descriptor differs from actual per-source vintage')
        baseline.append(dict({k:pin[k] for k in ('path','bytes','sha256','hash_kind')},role='original-source',
                             actual_consumed_commit=pin['commit'],original_mode=pin['mode'],original_blob=pin['blob']))
    pin_paths={}
    for name,sha in spec['evidence_quality']['pins'].items():
        choices=[x['path'] for x in baseline if x['sha256']==sha];require(len(choices)==1,'Missing/ambiguous actual issue pin: '+name)
        pin_paths[name]=choices[0]
    controls_path=packet/'proof/controls.json'
    controls=json.loads(controls_path.read_bytes())
    require(controls['status']=='PASS' and controls['execution_commit']==EXEC and controls['count']==63 and
            all(x['status']=='PASS' for x in controls['controls']),'Actual63 controls not complete')
    controls_desc=descriptor(controls_path,NS+'proof/controls.json')
    for kind in ('positive-control','negative-control'):
        typed={'method_id':'native-member-byte-custody','kind':kind,'outcome':'passed',
               'actual_controls':controls_desc,'actual_control_count':63,'execution_commit':EXEC,
               'limits':['Typed link to retained actual63 production controls, not a new control execution.']}
        dst=packet/'proof'/(kind+'.json');require(not dst.exists(),'Fresh typed receipt required');dst.write_bytes(canonical(typed))
    files=sorted(p for p in packet.rglob('*') if p.is_file() and p.name!='evidence-quality.json')
    outputs=[dict(descriptor(p,p.relative_to(repo).as_posix()),role='evidence') for p in files]
    require(all(not p.is_symlink() for p in packet.rglob('*')),'Nonordinary retained tree')
    require(len(baseline)+len(outputs)<=512 and sum(x['bytes'] for x in baseline+outputs)<=BUDGET,'Complete flat admission exceeded')
    upstream=json.loads(subprocess.check_output(['git','-C',str(repo),'show',BASE+':coordination/engineering/global-physical-sources-20261006/evidence-quality.json']))
    source=dict(upstream['sources'][0]);source.pop('files',None);source['retention']='restoration-only'
    source['role']='Complete original ZIP source custody and exact full gshhs_f.b byte extraction; no polygon/physical authority approval.'
    source['restoration']='Twelve complete original files at '+BASE+' are ordinary baseline inputs; exact paths/modes/OIDs are bound by input-index.json and actual read receipts.'
    source['limit']='Physical/political authority, water/registration/observation-date accuracy and conflicting historical license wording remain unverified; other17 whole body hashes inherited only.'
    methods=[{'id':'native-member-byte-custody','kind':'generator','helper_version':'worldatlas-evidence-preparation-v1',
              'description':'Authenticate all12 original bodies, all18 ZIP directory rows, decompress only full gshhs_f.b, retain all188612 headers/coordinate byte hashes and three exact contiguous aliases; both complete frozen runs execute validate-then-consume no-ZIP reader.',
              'software':'Python3.12.14/zlib exact executable, extension and standard-library hashes in runtime-pins.json; existing immutable.py byte codec unchanged.',
              'units':'exact bytes/native integer microdegrees/records; no geometry operations or area/distance measures'}]
    metrics=[];bindings=[];ledgerdesc=descriptor(ledgerpath,NS+'proof/counts.json')
    for key,value in ledger.items():
        metrics.append({'id':key,'value':value,'unit':'bytes' if key=='native_bytes' else 'count','vintage':'archived',
                        'evaluation_commit':EXEC,'input_sha256':ledgerdesc['sha256']})
        bindings.append({'metric_id':key,'path':ledgerdesc['path'],'json_pointer':'/'+key})
    manifest={'version':1,'issue':1376,'lane':'engineering','worker_id':a.worker,'subject_ids':[],
              'subject_ids_sha256':hashlib.sha256(b'[]').hexdigest(),
              'baseline':{'commit':BASE,'files':baseline,'pins':spec['evidence_quality']['pins'],'pin_files':pin_paths},
              'sources':[source],'outputs':outputs,'methods':methods,'metrics':metrics,'metric_bindings':bindings,'summaries':[],
              'validation':[{'method_id':'native-member-byte-custody','kind':kind,'outcome':'passed','evidence_path':NS+path}
                            for kind,path in [('positive-control','proof/positive-control.json'),('negative-control','proof/negative-control.json'),('reproducibility','proof/reproducibility.json')]],
              'conclusions':[{'source_ids':[source['id']],'status':'unresolved','text':'Complete original native byte custody is retained; no geometry validity, physical classification, repair, political or source-authority approval. Old1353 ZIP-dependent observations remain unadmitted.'}],
              'stages':{'research':'partial','implementation':'implemented','geographic_approval':'not-requested'},
              'commands':[str(x['actual_execution']['command']) for x in reports],
              'change_receipts':[{'path':p.relative_to(repo).as_posix(),'status':'added'} for p in files]+[{'path':NS+'evidence-quality.json','status':'added'}]}
    dest=packet/'evidence-quality.json';require(not dest.exists(),'Fresh manifest required');dest.write_bytes(canonical(manifest))
    print(json.dumps({'status':'prepared-not-admitted','descriptors':len(baseline)+len(outputs),'bytes':sum(x['bytes'] for x in baseline+outputs),'changes':len(files)+1}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=pathlib.Path,required=True);p.add_argument('--run-one',type=pathlib.Path,required=True)
    p.add_argument('--run-two',type=pathlib.Path,required=True);p.add_argument('--terminal-receipt',type=pathlib.Path,required=True)
    p.add_argument('--issue-json',type=pathlib.Path,required=True);p.add_argument('--worker',required=True);run(p.parse_args())
