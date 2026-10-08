"""Metadata-only bounded candidate catalog. No geography/source truth is inferred."""
import argparse,csv,gzip,hashlib,io,json,re,subprocess,sys
from pathlib import Path
import bounded_io as bio
import catalog
P='coordination/engineering/global-gap-candidate-funnel-20261008/'
ORIGINAL='0198938719a5666b6726fb6a1e45779926eefeb2'
REPORT=P.replace('global-gap-candidate-funnel-20261008/','global-physical-comparison-20261006/results/report.json')
ORIGINAL_SHA='2a5b59198681d50f577bc4c2c321174f166aec14f57c7564100fc411ae940df0'
REPAIR='b4b7db357ba92d19df513f188bbd046fe66a35e4'
CORRECTION='coordination/engineering/eastern-two-gap-repair-20261007/run-one/corrections.json.gz'
CODE=('producer.py','catalog.py','bounded_io.py','controls.py')
HEADER=('component_id','terminal_physical_class','terminal_decision','numerical_diagnosis','source_comparison_status','source_comparison_packet','source_products','unique_source_subject_id','source_reference_year','source_geometry_sha256','historical_555_witness','historical_555_cohort','unique_source_witness_1391','land_plus_unique_route_1005','nordic_geometric_mismatch_observation','physical_status_source_relative','physical_source_vintage','next_prerequisite','current_feature_sha256','current_geometry_sha256','family')

def pin(repo,commit,path):
    # Metadata-only size lookup precedes body read. Actual Phase performs admission.
    size=int(subprocess.check_output(['git','-C',str(repo),'cat-file','-s',commit+':'+path]))
    bio.need(size<=bio.FILE,'Oversized declaration')
    raw=subprocess.check_output(['git','-C',str(repo),'show',commit+':'+path])
    p={'commit':commit,'path':path,'bytes':size,'sha256':bio.sha(raw)}
    if path.endswith('.gz'):
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as g:body=g.read(bio.FILE+1)
        bio.need(len(body)<=bio.FILE,'Oversized decoded declaration');p.update(uncompressed_bytes=len(body),uncompressed_sha256=bio.sha(body))
    return p

def ref(p,pointer):return {**p,'pointer':pointer}

def rows(raw,first):
    r=csv.DictReader(io.StringIO(raw.decode()),fieldnames=None if first else HEADER)
    bio.need(tuple(r.fieldnames)==HEADER,'CSV schema drift')
    yield from r

def live(repo,codepins):
    for p in codepins:bio.need(bio.sha((repo/p['path']).read_bytes())==p['sha256'],'Executed code drift')

def declaration(repo,head,names):
    # Whole fixed declarations are frozen separately; this function reads only the
    # small pins JSON. It never discovers or decodes scientific input bodies.
    path=P+'inputs/pins.json';raw=subprocess.check_output(['git','-C',str(repo),'show',head+':'+path])
    bio.need(len(raw)<=65536,'Input declaration bound')
    allpins=json.loads(raw);result=[]
    for name in names:
        hits=[p for p in allpins if p['path']==P+'inputs/'+name];bio.need(len(hits)==1,'Missing/duplicate frozen declaration');result.append(dict(hits[0],commit=head))
    return result+[{'commit':head,'path':path,'bytes':len(raw),'sha256':bio.sha(raw)}]

def core(repo,head,dest,pins,reserve):
    codepins=[pin(repo,head,P+n) for n in CODE];live(repo,codepins)
    phase=bio.Phase(repo,dest,pins+codepins,reserve)
    for p in codepins:phase.read(p)
    return phase,codepins

def get(phase,name):
    matches=[p for p in phase.pins.values() if p['path'].endswith('/'+name)];bio.need(len(matches)==1,'Ambiguous input');p=matches[0];return p,phase.read(p)

def scope(repo,head,dest):
    names=[f'components-{i:02}.csv.gz' for i in range(1,8)]
    pins=declaration(repo,head,names);reportpin={'commit':ORIGINAL,'path':REPORT,'bytes':57840,'sha256':ORIGINAL_SHA}
    bio.need(reportpin['sha256']==ORIGINAL_SHA,'Independent original scope drift')
    phase,codepins=core(repo,head,dest,pins+[reportpin],64*1024*1024)
    get(phase,'pins.json');original=json.loads(phase.read(reportpin));seen=set();ordered=[];ledger=[]
    for i,name in enumerate(names):
        _,raw=get(phase,name)
        for r in rows(raw,i==0):
            identity=r['component_id'];bio.need(identity not in seen and re.fullmatch('physical-component:[a-f0-9]{64}',identity),'Foreign/duplicate original ID');seen.add(identity)
            ordered.append({'id':identity,'feature_sha256':r['current_feature_sha256']})
            ledger.append({'component_id':identity,'feature_sha256':r['current_feature_sha256'],'geometry_sha256':r['current_geometry_sha256']})
    bio.need(len(seen)==95173==original['component_count'],'Original count drift')
    bio.need(bio.sha(bio.canonical(ordered))==original['complete_roster_sha256'],'Complete independent ID/feature roster drift')
    phase.output('scope.jsonl.gz',b''.join(bio.canonical(r) for r in ledger),True)
    live(repo,codepins);return phase.finish({'stage':'scope','execution_commit':head,'original_scope_commit':ORIGINAL,'component_count':len(seen),'original_complete_roster_sha256':original['complete_roster_sha256'],'limits':'Metadata reconciliation only; existing source-preparation aggregate539MB was not qualified as one256MB phase.'})

def leaf(repo,head,scopehead,scopepath,index,dest):
    names=[f'components-{index:02}.csv.gz']+[f'component-provenance-{i:02}.jsonl.gz' for i in range(1,10)]+['issue1295-capture.json','issue1394-capture.json','issue1431-capture.json','issue1481-capture.json']
    pins=declaration(repo,head,names);declpath=P+'inputs/scope-pin.json';declraw=subprocess.check_output(['git','-C',str(repo),'show',head+':'+declpath]);bio.need(len(declraw)<=4096,'Scope declaration bound');sp=json.loads(declraw);bio.need(sp['commit']==scopehead and sp['path']==scopepath,'Frozen original scope locator drift');pins.append({'commit':head,'path':declpath,'bytes':len(declraw),'sha256':bio.sha(declraw)});cp={'commit':REPAIR,'path':CORRECTION,'bytes':94693,'sha256':'ba3cda4a21245e00706a5fe065565d579f71298c2b839d56c1bcbd340459602e','uncompressed_bytes':320200,'uncompressed_sha256':'897ca97928956c190fb4b1a25f0364333528b8d789f5e9f60f345f9299803e3e'}
    bio.need(cp['sha256']=='ba3cda4a21245e00706a5fe065565d579f71298c2b839d56c1bcbd340459602e','Original merged repair body drift')
    phase,codepins=core(repo,head,dest,pins+[sp,cp],96*1024*1024)
    get(phase,'pins.json');get(phase,'scope-pin.json');expected={r['component_id']:r for r in map(json.loads,phase.read(sp).splitlines())};bio.need(len(expected)==95173,'Incomplete independent scope')
    rp,raw=get(phase,f'components-{index:02}.csv.gz');inputs=list(rows(raw,index==1));catalog.exact_ids(inputs);ids={r['component_id'] for r in inputs}
    provenance={}
    for n in range(1,10):
        pp,raw=get(phase,f'component-provenance-{n:02}.jsonl.gz')
        for ordinal,line in enumerate(raw.splitlines()):
            r=json.loads(line)
            if r['component_id'] in ids:
                bio.need(r['component_id'] not in provenance,'Duplicate source provenance');provenance[r['component_id']]={'reference':ref(pp,'/records/'+str(ordinal)),'record':r}
    bio.need(set(provenance)==ids,'Missing candidate source provenance')
    captures={}
    for n in (1295,1394,1431,1481):
        p,b=get(phase,f'issue{n}-capture.json');x=json.loads(b);bio.need(x['number']==n,'Foreign captured task');captures[n]=(p,x)
    corrections=json.loads(phase.read(cp));bio.need(len(corrections)==2,'Incomplete original repair proposal')
    decisions={};verified={};taskrefs={}
    approvalp,approval=captures[1295];body=approval['body']
    bio.need(bio.sha(body.encode())=='7568352df4141a74153ce56dcbd31aca31b856da0df09c85b8388cfc3e630530','Accepted Main approval body drift')
    for ordinal,r in enumerate(corrections):
        identity=r['component_id'];geometry=r['component_geometry_sha256'];bio.need(identity in body and geometry in body,'Approval lacks exact candidate geometry')
        bio.need(r['source_scope']=='Main-approved physical-reference portion correction only' and r['historical_transfer'] is False,'Foreign/historical implementation claim')
        ar=ref(approvalp,'/body');ir=ref(cp,'/'+str(ordinal));key=lambda p:(p['commit'],p['path'],p['sha256'],p['pointer'])
        # Whole captured body is the actual pointer; each named component's
        # geometry and narrow approval interpretation were checked above.
        verified.setdefault(key(ar),{'component_ids':[],'class':'missing-land','state':'repair_ready'})['component_ids'].append(identity)
        verified[key(ir)]={'component_id':identity,'state':'implemented'}
        decisions[identity]={'component_id':identity,'geometry_sha256':geometry,'class':'missing-land','decision':ar,'repair_ready':True,'implemented':True,'fully_integrated':False,'delivered':False,'state_evidence':{'repair_ready':ar,'implemented':ir}}
    tasks=[]
    p,x=captures[1431];contract=json.loads(re.search(r'<!-- worldatlas-work:v1\s*(.*?)\s*-->',x['body'],re.S).group(1));scopeids=[s for s in contract['evidence_quality']['subject_ids'] if s.startswith('physical-component:')];bio.need(len(scopeids)==15,'1431 original candidate scope drift')
    p,x=captures[1481];arctic=json.loads(re.search(r'<!-- worldatlas-work:v1\s*(.*?)\s*-->',x['body'],re.S).group(1));arcticids=[v for v in arctic['evidence_quality']['subject_ids'] if v.startswith('physical-component:')];bio.need(len(arcticids)==7,'1481 exact Arctic source-fitness scope drift')
    for n,scopeids,role,facts in [(1295,list(decisions),'repair-integration',['full-normal-consumer-integration']),(1431,scopeids,'source-fitness',['source-fitness-and-date']),(1481,arcticids,'source-fitness',['source-fitness-and-date']),(1394,[r['component_id'] for r in inputs if r['numerical_diagnosis']=='retained-unresolved-original-replay-mismatch'],'numerical-reproduction',['original-numerical-reproduction'])]:
        p,x=captures[n];r=ref(p,'/body');verified[(r['commit'],r['path'],r['sha256'],r['pointer'])]={'issue':n,'component_ids':scopeids};tasks.append({'issue':n,'component_ids':scopeids,'scope_ref':r,'role':role,'missing_facts':facts})
    output=[]
    for ordinal,r in enumerate(inputs):
        e=expected.get(r['component_id']);bio.need(e and e['feature_sha256']==r['current_feature_sha256'] and e['geometry_sha256']==r['current_geometry_sha256'],'Stale candidate ID/feature/geometry')
        record=catalog.catalog_record(r,ref(rp,'/records/'+str(ordinal)),decisions,verified,tasks);record['original_source_provenance']=provenance[r['component_id']];record['progress_scope']='Two implemented geometric proposals remain unactivated; no full integration/delivery proof.';output.append(record)
    # Every whole output remains below8MiB decoded. No geometry is copied.
    shard=[];size=0;number=0
    for r in output:
        b=bio.canonical(r)
        if size+len(b)>bio.SHARD:
            phase.output(f'catalog-{number:02}.jsonl.gz',b''.join(shard),True);number+=1;shard=[];size=0
        shard.append(b);size+=len(b)
    if shard:phase.output(f'catalog-{number:02}.jsonl.gz',b''.join(shard),True)
    # Small membership/metrics leaf retains exact ID and source flags for parent
    # conservation; actual catalog references remain in whole-file inventory.
    metric=[{'component_id':r['component_id'],'class':r['class'],**{s:r[s] for s in catalog.STATES},'flags':r['source_flags'],'provisional_support':r['provisional_support'],'tasks':[t['issue'] for t in r['next_work']['tasks']],'missing_facts':r['next_work']['missing_facts'],'unassigned_requirements':r['next_work']['unassigned_requirements']} for r in output]
    phase.output('membership-metrics.jsonl.gz',b''.join(bio.canonical(r) for r in metric),True)
    phase.output('summary.json',bio.canonical(catalog.summarize(output,ids)))
    live(repo,codepins);return phase.finish({'stage':'catalog-leaf','execution_commit':head,'scope_commit':scopehead,'source_shard':index,'component_count':len(output),'accepted_classifications':sum(r['class']!='unresolved' for r in output),'fully_integrated':0,'delivered':0,'limits':'Source flags/provenance are retained observations, not independently approved physical truth; source-preparation aggregate is unqualified.'})

def parent(repo,head,dest):
    from collections import Counter
    path=P+'inputs/parent-pins.json';raw=subprocess.check_output(['git','-C',str(repo),'show',head+':'+path]);bio.need(len(raw)<=65536,'Parent declaration bound');pins=json.loads(raw)
    phase,codepins=core(repo,head,dest,pins+[{'commit':head,'path':path,'bytes':len(raw),'sha256':bio.sha(raw)}],16*1024*1024)
    get(phase,'parent-pins.json');sp=[p for p in pins if p['path'].endswith('/scope.jsonl.gz')];bio.need(len(sp)==1,'Exact original scope required')
    expected={r['component_id'] for r in map(json.loads,phase.read(sp[0]).splitlines())};bio.need(len(expected)==95173,'Complete original scope required')
    counts=Counter();classes=Counter({c:0 for c in catalog.CLASSES});seen=set();tasks=Counter();missing=Counter();unassigned=Counter();nested=Counter()
    members=[p for p in pins if p['path'].endswith('/membership-metrics.jsonl.gz')];bio.need(len(members)==7,'Complete seven bounded catalog leaves required')
    inventory=[p for p in pins if p['path'].endswith('/inventory.json.gz')];bio.need(len(inventory)==7,'Whole catalog output inventories required')
    complete_outputs=[]
    for p in inventory:
        inv=json.loads(phase.read(p));bio.need(inv['facts']['stage']=='catalog-leaf','Foreign catalog inventory');complete_outputs.extend(inv['outputs'])
        own=[q for q in members if q['commit']==p['commit'] and q['path'].rsplit('/',1)[0]==p['path'].rsplit('/',1)[0]];bio.need(len(own)==1 and any(all(q.get(k)==own[0].get(k) for k in ('path','bytes','sha256','uncompressed_bytes','uncompressed_sha256')) for q in inv['outputs']),'Leaf membership not bound to whole catalog inventory')
    for p in members:
        for line in phase.read(p).splitlines():
            r=json.loads(line);identity=r['component_id'];bio.need(identity in expected and identity not in seen,'Missing/duplicate/foreign parent identity');seen.add(identity)
            bio.need(r['class'] in catalog.CLASSES and all(type(r[x]) is bool for x in catalog.STATES),'Foreign class/progress type')
            bio.need(not r['implemented'] or r['repair_ready'],'Implementation before readiness');bio.need(not r['fully_integrated'] or r['implemented'],'Integration before implementation');bio.need(not r['delivered'] or r['fully_integrated'],'Delivery before integration');bio.need(r['class']!='unresolved' or not any(r[x] for x in catalog.STATES),'Provisional promoted to accepted progress')
            f=r['flags'];bio.need(not f['historical_555_witness'] or f['unique_source_witness_1391'],'555 nesting drift');bio.need(not f['land_plus_unique_route_1005'] or f['unique_source_witness_1391'],'1005 nesting drift');bio.need(not f['unique_source_witness_1391'] or f['source_comparison'],'1391 nesting drift')
            classes[r['class']]+=1;counts['accepted_classifications']+=r['class']!='unresolved'
            for state in catalog.STATES:counts[state]+=r[state]
            for flag,value in f.items():bio.need(type(value) is bool,'Flag type drift');counts[flag]+=value
            counts['provisional_land_or_water']+=r['provisional_support'] in ('land','water');tasks.update(map(str,r['tasks']));missing.update(r['missing_facts']);unassigned.update(r['unassigned_requirements'])
            for name,a,b in [('numeric_1391','numerical_diagnosis','unique_source_witness_1391'),('numeric_555','numerical_diagnosis','historical_555_witness'),('555_1005','historical_555_witness','land_plus_unique_route_1005')]:nested[name]+=f[a] and f[b]
    bio.need(seen==expected and sum(classes.values())==95173,'Global count conservation failure')
    for key,n in {'source_comparison':57785,'historical_555_witness':555,'unique_source_witness_1391':1391,'land_plus_unique_route_1005':1005,'numerical_diagnosis':26276,'accepted_classifications':2,'implemented':2,'fully_integrated':0,'delivered':0}.items():bio.need(counts[key]==n,'Original reconciled count drift: '+key)
    bio.need(nested=={'numeric_1391':142,'numeric_555':60,'555_1005':430},'Original corrected exact intersections drift');bio.need(tasks['1394']==1294 and tasks['1431']==15 and tasks['1295']==2 and tasks['1481']==7,'Exact bounded candidate task scope drift')
    report={'component_count':len(seen),'classes':dict(classes),'counts':dict(counts),'percentages':{k:100*v/len(seen) for k,v in counts.items()},'exact_intersections':dict(nested),'task_candidate_counts':dict(tasks),'missing_fact_counts':dict(missing),'unassigned_requirement_counts':dict(unassigned),'catalog_output_inventory':complete_outputs,'original_milestones':['global audit','source fitness and accepted classification','systematic repairs','full integration and prevention gate'],'limits':['Existing source comparison and numerical observations remain provisional.','Two Main-approved narrow physical-region corrections are implemented geometric proposals, unactivated.','Full integration and delivery are zero; they require separate complete normal consumer proof.','Seven Arctic candidates are bound to source-fitness task1481, not approved repairs.','Direct-source preparation consumed539MB encoded+decoded across its inputs and is not qualified as one256MB phase. This tracker does not promote that preparation or source-relative diagnoses to physical authority.']}
    phase.output('report.json',bio.canonical(report));phase.output('report.md',(('Original candidates: '+str(len(seen))+'\n\nAccepted narrow classifications: 2; implemented proposals: 2; fully integrated: 0; delivered: 0.\n\n'+ '\n'.join(report['limits'])+'\n')).encode())
    live(repo,codepins);return phase.finish({'stage':'parent-report','execution_commit':head,'component_count':len(seen),'accepted_classifications':2,'implemented':2,'fully_integrated':0,'delivered':0})

def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['scope','leaf','parent']);ap.add_argument('--head',required=True);ap.add_argument('--destination',required=True);ap.add_argument('--scope-head');ap.add_argument('--scope-path');ap.add_argument('--index',type=int);a=ap.parse_args()
    repo=Path(subprocess.check_output(['git','rev-parse','--show-toplevel']).decode().strip())
    bio.need(subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()==a.head,'Actual immutable execution vintage required')
    dest=repo/P/'vintages'/a.destination
    if a.stage=='scope':result=scope(repo,a.head,dest)
    elif a.stage=='parent':result=parent(repo,a.head,dest)
    else:
        bio.need(a.scope_head and a.scope_path and a.index in range(1,8),'Exact original scope and bounded leaf required');result=leaf(repo,a.head,a.scope_head,a.scope_path,a.index,dest)
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
