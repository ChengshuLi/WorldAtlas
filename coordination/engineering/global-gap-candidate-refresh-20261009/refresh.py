"""Bounded metadata refresh of complete original catalog leaves; no GIS replay."""
import argparse,collections,gzip,hashlib,json,pathlib,re,subprocess,sys
P='coordination/engineering/global-gap-candidate-funnel-20261008/'
Q='coordination/engineering/global-gap-candidate-refresh-20261009/'
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import bounded_io as bio
import catalog
CODE=(Q+'catalog.py',Q+'bounded_io.py',Q+'refresh.py')
def git(repo,*args):return subprocess.check_output(['git','-c','gc.auto=0','-C',str(repo),*args])
def metadata(repo,head,path):
    size=int(git(repo,'cat-file','-s',head+':'+path));bio.need(size<=1048576,'Small frozen declaration cap');return git(repo,'show',head+':'+path)
def declaration(repo,head):
    path=Q+'inputs/pins.json';raw=metadata(repo,head,path);pins=json.loads(raw)
    bio.need(len(pins)<512 and all(p['path'].startswith(Q+'inputs/') for p in pins),'Exact owned frozen inputs')
    return [dict(p,commit=head) for p in pins]+[{'commit':head,'path':path,'bytes':len(raw),'sha256':bio.sha(raw)}]
def make_phase(repo,head,dest,pins,reserve):
    code=[]
    for path in CODE:
        body=metadata(repo,head,path);bio.need((repo/path).read_bytes()==body,'Executed current code differs from immutable head');code.append({'commit':head,'path':path,'bytes':len(body),'sha256':bio.sha(body)})
    runtimepath=Q+'inputs/runtime.json';runtimepin=next(p for p in pins if p['path']==runtimepath);runtime_raw=metadata(repo,head,runtimepath);bio.need(bio.sha(runtime_raw)==runtimepin['sha256'],'Frozen runtime declaration');runtime=json.loads(runtime_raw);bio.need(str(pathlib.Path(sys.executable).resolve())==runtime['python_executable'],'Actual selected Python runtime');phase=bio.Phase(repo,dest,pins+code,reserve,runtime['files'])
    for p in code:phase.read(p)
    return phase,code

def finish(phase,code,facts):
    for p in code:bio.need(bio.sha((phase.repo/p['path']).read_bytes())==p['sha256'],'Post-execution code drift')
    return phase.finish(facts)
def read_inputs(phase):
    result={}
    for p in phase.pins.values():
        if p['path'].startswith(Q+'inputs/'):
            raw=phase.read(p);result[p['path'].rsplit('/',1)[-1]]=(p,raw)
    return result

def build_progress(inputs):
    """All declared complete bodies have already passed whole encoded/decoded IO."""
    def named(name):return json.loads(inputs[name][1])
    def original(pin):
        matches=[(p,b) for p,b in inputs.values() if any(v.get('sha256')==pin['sha256'] and v['path']==pin['path'] and v['commit']==pin['commit'] for v in p.get('original_bindings',[p.get('original_binding',{})]))]
        bio.need(len(matches)==1,'Missing/duplicate complete original authority body');p,b=matches[0]
        bio.need(p['bytes']==pin['bytes'] and p['sha256']==pin['sha256'],'Original custody hash/size join drift')
        return p,b
    def value(pin):return json.loads(original(pin)[1])
    def reference(pin,pointer='/'):p,_=original(pin);return dict(p,pointer=pointer)
    progress={};exceptions={};trans=named('integrated-transitions.json');tp=trans['whole_git_input_pins']
    bio.need(len(tp)==6 and len({p['path'] for p in tp})==6,'Complete installed transition input roster');lookup={p['path']:value(p) for p in tp};migration=next(v for p,v in lookup.items() if p.endswith('/index.json'));selection=lookup['data/ownership-selection.json'];manifest=lookup['data/canonical-grid/eastern-v8/manifest.json'];normal=next(v for p,v in lookup.items() if p.endswith('hosted-normal-build-qualification.json'))
    merge=named('accepted-merge.json');match=re.search(r'<!-- worldatlas-merge-result:v1\s*(.*?)\s*-->',merge['body'],re.S)
    bio.need(match and merge['user']['login']=='github-actions[bot]','Actual accepted merge receipt required');receipt=json.loads(match.group(1));bio.need(receipt['accepted'] is True and receipt['merge_commit']==trans['merge_commit'],'Foreign/unaccepted merge transition')
    bio.need(migration['activated'] is True and migration['activation']['kind']=='installed-offline-repository' and migration['activation']['production_deployment_verified'] is False,'Offline activation identity')
    bio.need(selection['sha256']==trans['selected_native_manifest_ref']['sha256'] and selection['release_id']==trans['selected_release'],'Missing installed selected-bank binding')
    bio.need(manifest['geographic_release']==selection['release_id'] and normal['status']=='full-normal-hosted-build-PASS' and normal['violations']==[] and migration['after_footprints_sha256']==manifest['footprints_sha256'] and migration['activation']['native_manifest_sha256']==selection['sha256'],'Selected manifest/normal consumer identity')
    mp=next(p for p in tp if p['path'].endswith('/index.json'));sp=next(p for p in tp if p['path']=='data/ownership-selection.json');np=next(p for p in tp if p['path'].endswith('hosted-normal-build-qualification.json'))
    for row in trans['rows']:
        identity=row['component_id'];proposal=value(row['proposal_ref']);candidate=proposal[int(row['proposal_ref']['pointer'][1:])]
        bio.need(candidate['component_id']==identity and candidate['component_geometry_sha256']==row['original_geometry_sha256'],'Foreign/stale complete proposal transition')
        bio.need(identity in value(row['approval_ref'])['body'] and row['original_geometry_sha256'] in value(row['approval_ref'])['body'],'Exact original approved geometry');bio.need(candidate['subject_id'] in migration['proposed_subjects'] and set(migration['proposed_subjects'])==set(manifest['provenance']['source_migration']['changed_ids']),'Actual selected migration target identities')
        refs={'source':reference(row['approval_ref']), 'rule':reference(row['approval_ref']), 'review':reference(row['approval_ref']), 'proposal':reference(row['proposal_ref'],row['proposal_ref']['pointer'])}
        source={'authority_domain':'retained-source-relative-reference','eligible':True,'constructed':True,'current_bank_rebound':True,'activated':True,'physical_authority_approved':False,'current_physical_truth_approved':False,'evidence':refs,'profile':'Main-approved-narrow-reference-correction','limits':['Original narrow reference approval is preserved; no contemporary physical-truth or production delivery claim.']}
        evidence={'migration':reference(mp),'selection':reference(sp),'manifest':reference(trans['selected_native_manifest_ref']),'normal_build':reference(np),'accepted_merge':dict(inputs['accepted-merge.json'][0],pointer='/body')}
        progress[identity]={'component_id':identity,'geometry_sha256':row['original_geometry_sha256'],'source_relative_repair':source,'integrated':{'component_id':identity,'geometry_sha256':row['original_geometry_sha256'],'production_delivered':False,'evidence':evidence}}
    extraction=named('additive-authorities.json');arctic_proof=next((json.loads(b) for p,b in inputs.values() if p.get('original_binding',{}).get('path','').endswith('/delivery/run-1/geometry-proof.json')),None)
    bio.need(arctic_proof and arctic_proof['current_pointers_activated'] is False,'Actual unactivated Arctic construction proof');arctic_pin=next(p for p,b in inputs.values() if p.get('original_binding',{}).get('path','').endswith('/delivery/run-1/geometry-proof.json'))
    for a in extraction['authorities']:
        request=value(a['pins']['native_request']);source_request=value(a['pins']['source_request']);facts=value(a['pins']['source_facts']);ledger=value(a['pins']['ledger']);native=value(a['pins']['native_facts'])
        preimage=a['rule_preimage'];bio.need(bio.sha(bio.canonical(preimage))==a['rule_sha256']==ledger['rule_sha256'],'Exact original rule preimage drift')
        bio.need(preimage['executed_code']==request['executed_code'] and preimage['native_method']=='native-linear-evenodd-first-owner-v1','Original proposal method/code rule binding')
        if preimage['version']==3:bio.need(preimage['source_rule']==source_request['source_rule'] and preimage['source_profile']==facts['source_profile'],'Original source policy preimage drift')
        else:bio.need(preimage['source_rule_body_sha256']==source_request['source_rule']['review_body_sha256'],'Original pilot source review rule binding')
        review_name='root1547-accepted-review-comment-6071720745-20261009.json' if a['name']=='pilot-add031' else 'root1561-accepted-review-comment-6073179645-20261009.json'
        review=named(review_name);typed=json.loads(re.search(r'<!-- worldatlas-review:v1\s*(.*?)\s*-->',review['body'],re.S).group(1));bio.need(typed['outcome']=='accepted' and typed['author_worker_id']!=typed['reviewer_worker_id'] and typed['head_sha']==('52bed5c24c27e4a9256ae6aea26c640b9082a2a2' if a['name']=='pilot-add031' else 'b82ee098641b0dda3fc27d281b438ec4958ffbce'),'Foreign source acceptance review')
        inventory_pin=next(p for p in request['additive']['inputs'] if p['path'].endswith('/inventory.jsonl.gz'));ip,ib=original(inventory_pin);rows=[json.loads(b) for b in ib.splitlines()];catalog.exact_ids(rows)
        bio.need(len(rows)==(7 if a['name']=='pilot-add031' else 13) and facts['source_compatible']==(3 if len(rows)==7 else 11),'Complete original source scope')
        assignments={r['component_id']:r for r in ledger['rows'] if r['disposition']=='assigned'}
        bio.need(native['removed_cells']==native['reassigned_cells']==0 and sum(r['native_cells'] for r in assignments.values())==ledger['assigned_cells']==native['assigned_cells'],'Actual proposal conservation binding')
        for ordinal,r in enumerate(rows):
            identity=r['component_id'];bio.need(type(r['source_compatible']) is bool and r['source_compatible']==(not r['failed_premises']),'Source premises/exception mismatch')
            case=value(r['source_case']['source']);case_rows=case.get('results',case.get('cases'));bio.need(isinstance(case_rows,list),'Whole original source case roster required');case_row=case_rows[r['source_case']['ordinal']];bio.need(case_row['component_id']==identity,'Coherently foreign complete source case')
            case_pin,case_bytes=inputs['case-'+r['source_case']['row_sha256']+'.json'];bio.need(bio.sha(case_bytes)==r['source_case']['row_sha256'] and json.loads(case_bytes)==case_row and case_pin['ordinal']==r['source_case']['ordinal'] and case_pin['case_source_sha256']==r['source_case']['source']['sha256'],'Full source case ordinal/hash mismatch')
            if a['name']=='pilot-add031':
                derived=all(v is True for v in case_row['repair_ready_criteria'].values()) and case_row['native_source_covers_candidate'] is True and case_row['v22_source_covers_candidate'] is True
            else:
                derived=case_row['source_predicate_support_pass'] is True and case_row['candidate_support_requirements']['candidate_vs_alaska_parent'] is True and case_row['source_parent_coverage']['candidate_covered_exactly'] is True and case_row['native_linked_support_covers_candidate'] is True and case_row['geometry_validity']['candidate']['valid'] is True and case_row['original_25_relation_predicates_match'] is True and case_row['original_contacts_match_all_17_actual_atlas_features'] is True
            bio.need(derived==r['source_compatible'],'Original complete case source premises disagree with inventory')
            if not r['source_compatible']:
                exceptions[identity]={'source':dict(ip,pointer='/records/'+str(ordinal)),'failed_premises':r['failed_premises']};continue
            bio.need(identity not in progress,'Duplicate source eligible original component')
            geometry=bio.sha(bio.canonical(r['candidate']));bio.need((case_row.get('candidate_geometry')==r['candidate']) if a['name']=='pilot-add031' else case_row['candidate_geometry_sha256']==geometry,'Whole source case candidate geometry binding');bio.need(not r.get('original_candidate_geometry_sha256') or geometry==r['original_candidate_geometry_sha256'],'Complete original candidate geometry drift')
            assignment=assignments.get(identity);constructed=assignment is not None or identity in arctic_proof['constructed_components']
            if assignment:bio.need(assignment['geometry']==r['candidate'] and assignment['source_receipt_sha256']==a['pins']['source_facts']['sha256'],'Foreign/stale constructed candidate source binding')
            source={'authority_domain':'retained-source-relative-reference','eligible':True,'constructed':constructed,'current_bank_rebound':False,'activated':False,'physical_authority_approved':False,'current_physical_truth_approved':False,'profile':facts.get('source_profile','retained-AAFC-GSHHG-pilot'),'rule_sha256':ledger['rule_sha256'],'evidence':{'source':dict(ip,pointer='/records/'+str(ordinal)),'rule':dict(inputs['additive-authorities.json'][0],pointer='/authorities/'+str(extraction['authorities'].index(a))+'/rule_preimage'),'review':dict(inputs[review_name][0],pointer='/body'),'proposal':reference(a['pins']['ledger'],'/rows/'+str(next(i for i,v in enumerate(ledger['rows']) if v['component_id']==identity)))},'limits':r['limits']}
            if identity in arctic_proof['constructed_components']:
                source['evidence']['construction']=dict(arctic_pin,pointer='/exact_constructions/'+str(next(i for i,c in enumerate(arctic_proof['exact_constructions']) if identity in c['component_ids'])))
            elif assignment:source['evidence']['construction']=source['evidence']['proposal']
            issue=1520 if identity in arctic_proof['constructed_components'] else 1523
            taskpin,taskbody=inputs[f'current-issue-{issue}.json'];task=json.loads(taskbody);bio.need(task['number']==issue and task['state']=='open','Actual current remaining engineering task')
            progress[identity]={'component_id':identity,'geometry_sha256':geometry,'source_relative_repair':source,'remaining_tasks':[{'issue':issue,'role':'source-relative-integration','scope_ref':dict(taskpin,pointer='/body'),'missing_facts':['fresh-current-bank-rebind','normal-consumer-integration']}]} 
    bio.need(len(progress)==16 and len(set(progress))==16,'Frozen source eligibility roster/count drift')
    return progress,exceptions

def leaf(repo,head,index,dest):
    pins=declaration(repo,head);raw=metadata(repo,head,Q+'inputs/original-leaves.json');original=json.loads(raw);part=original['leaves'][index-1];bio.need(part['ordinal']==index,'Exact original leaf ordinal')
    phase,code=make_phase(repo,head,dest,pins+[part['inventory']]+part['outputs'],96*1024*1024)
    inputs=read_inputs(phase);progress,exceptions=build_progress(inputs);inventory=json.loads(phase.read(part['inventory']));expected={}
    for p in part['outputs']:
        bio.need(any(all(p.get(k)==v.get(k) for k in ('path','bytes','sha256','uncompressed_bytes','uncompressed_sha256')) for v in inventory['outputs']),'Original whole leaf output inventory binding')
        body=phase.read(p)
        if p['path'].endswith('membership-metrics.jsonl.gz'):expected=catalog.exact_ids(map(json.loads,body.splitlines()))
    current_task_pin,current_task_raw=inputs['current-issue-1394.json'];current_task=json.loads(current_task_raw);bio.need(current_task['number']==1394 and current_task['state']=='open','Actual ongoing original replay task');output=[]
    for p in part['outputs']:
        if not p['path'].rsplit('/',1)[-1].startswith('catalog-'):continue
        for row in map(json.loads,phase.read(p).splitlines()):
            identity=row['component_id'];bio.need(identity in expected,'Foreign original catalog row');row['source_rule_exception']=exceptions.get(identity);row['_current_tasks']=[dict(t,current_issue_ref=dict(current_task_pin,pointer='/body')) for t in row['next_work']['tasks'] if t['issue']==1394]
            output.append(catalog.refresh_record(row,progress.get(identity),row['current_geometry_sha256'],expected))
    bio.need(len(output)==len(expected) and len(catalog.exact_ids(output))==len(expected),'Complete original leaf conservation')
    shard=[];size=0;n=0
    for row in output:
        body=bio.canonical(row)
        if size+len(body)>bio.SHARD:phase.output(f'catalog-{n:02}.jsonl.gz',b''.join(shard),True);n+=1;shard=[];size=0
        shard.append(body);size+=len(body)
    if shard:phase.output(f'catalog-{n:02}.jsonl.gz',b''.join(shard),True)
    metrics=[{'component_id':r['component_id'],'class':r['class'],**{s:r[s] for s in catalog.STATES},'flags':r['source_flags'],'pipeline_status':r['pipeline_status'],'current_feature_sha256':r['current_feature_sha256'],'current_geometry_sha256':r['current_geometry_sha256'],'source_relative_eligible':r['source_relative_repair'] is not None,'source_relative_constructed':bool(r['source_relative_repair'] and r['source_relative_repair']['constructed']),'source_rule_exception':r['source_rule_exception'],'missing_facts':r['next_work']['missing_facts'],'task_ids':[t['issue'] for t in r['next_work']['tasks']],'unassigned_requirements':r['next_work']['unassigned_requirements']} for r in output]
    phase.output('membership-metrics.jsonl.gz',b''.join(bio.canonical(r) for r in metrics),True)
    return finish(phase,code,{'stage':'refreshed-catalog-leaf','execution_commit':head,'ordinal':index,'component_count':len(output),'original_inventory':part['inventory'],'limits':'Metadata reconciliation only; no new scientific, physical or production approval.'})

def parent(repo,head,dest):
    path=Q+'inputs/parent-pins.json';raw=metadata(repo,head,path);pins=json.loads(raw);own={'commit':head,'path':path,'bytes':len(raw),'sha256':bio.sha(raw)}
    basepins=declaration(repo,head);ep=next(p for p in basepins if p['path'].endswith('/expectation.json'));rp=next(p for p in basepins if p['path'].endswith('/runtime.json'))
    phase,code=make_phase(repo,head,dest,pins+[own,ep,rp],8*1024*1024);phase.read(own);phase.read(rp);expect=json.loads(phase.read(ep));seen=set();counts=collections.Counter();pipeline=collections.Counter();flags=collections.Counter();classes=collections.Counter();nested=collections.Counter();catalog_outputs=[]
    bio.need(len(pins)==15,'All seven complete leaf inventories and memberships plus original scope');scope_pin=next(p for p in pins if p['path'].endswith('/scope.jsonl.gz'));scope=catalog.exact_ids(map(json.loads,phase.read(scope_pin).splitlines()))
    for invpin in [p for p in pins if p['path'].endswith('/inventory.json.gz')]:
        inv=json.loads(phase.read(invpin));bio.need(inv['facts']['stage']=='refreshed-catalog-leaf','Foreign parent leaf');catalog_outputs.extend(inv['outputs'])
        mp=next(p for p in pins if p['path']==invpin['path'].rsplit('/',1)[0]+'/membership-metrics.jsonl.gz');bio.need(any(all(mp.get(k)==q.get(k) for k in ('path','bytes','sha256','uncompressed_bytes','uncompressed_sha256')) for q in inv['outputs']),'Whole membership inventory custody')
        for r in map(json.loads,phase.read(mp).splitlines()):
            identity=r['component_id'];bio.need(identity in scope and identity not in seen and r['current_feature_sha256']==scope[identity]['feature_sha256'] and r['current_geometry_sha256']==scope[identity]['geometry_sha256'],'Duplicate/foreign/stale parent candidate');seen.add(identity);classes[r['class']]+=1;pipeline[r['pipeline_status']['state']]+=1
            for s in catalog.STATES:bio.need(type(r[s]) is bool,'Exact transition flags');counts[s]+=r[s]
            counts['accepted_classifications']+=r['class']!='unresolved';counts['accepted_source_relative_repair_decisions']+=r['source_relative_eligible'];counts['source_relative_constructed']+=r['source_relative_constructed'];flags.update({k:int(v) for k,v in r['flags'].items()})
            for name,a,b in [('numeric_1391','numerical_diagnosis','unique_source_witness_1391'),('numeric_555','numerical_diagnosis','historical_555_witness'),('555_1005','historical_555_witness','land_plus_unique_route_1005')]:nested[name]+=r['flags'][a] and r['flags'][b]
    bio.need(seen==set(scope) and len(seen)==expect['original_component_count'] and sum(pipeline.values())==len(seen),'Complete disjoint pipeline conservation')
    for k in ('accepted_classifications','implemented','fully_integrated','delivered','accepted_source_relative_repair_decisions'):bio.need(counts[k]==expect[k],'Frozen refresh expectation drift: '+k)
    for k,v in {'source_comparison':57785,'historical_555_witness':555,'unique_source_witness_1391':1391,'land_plus_unique_route_1005':1005}.items():bio.need(flags[k]==v,'Original observation cohort drift')
    bio.need(nested=={'numeric_1391':142,'numeric_555':60,'555_1005':430},'Original exact intersections drift')
    report={'component_count':len(seen),'counts':dict(counts),'classes':dict(classes),'exclusive_pipeline_counts':dict(pipeline),'supporting_observation_counts':dict(flags),'exact_intersections':dict(nested),'catalog_output_inventory':catalog_outputs,'authority_domains_separate':True,'limits':expect['limits']+['Offline integration2 is not production delivery. Accepted source-relative16 is not accepted contemporary physical authority.','Original source/numerical full scientific work remains separate; this refresh does no source preparation, geometry calculation, native computation or activation.']}
    phase.output('report.json',bio.canonical(report));phase.output('report.md',('Original candidates: '+str(len(seen))+'\n\n'+json.dumps(dict(counts),sort_keys=True)+'\n\n'+'\n'.join(report['limits'])+'\n').encode())
    return finish(phase,code,{'stage':'refreshed-parent-report','execution_commit':head,**{k:v for k,v in counts.items()},'component_count':len(seen)})

def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=('leaf','parent'));ap.add_argument('--head',required=True);ap.add_argument('--index',type=int);ap.add_argument('--destination',required=True);args=ap.parse_args();repo=pathlib.Path(git(pathlib.Path.cwd(),'rev-parse','--show-toplevel').decode().strip());bio.need(git(repo,'rev-parse','HEAD').decode().strip()==args.head,'Actual immutable execution head')
    bio.need(re.fullmatch('[a-zA-Z0-9-]+',args.destination),'Plain unique destination');dest=repo/Q/'vintages'/args.destination
    if args.stage=='leaf':bio.need(type(args.index) is int and args.index in range(1,8),'Exact seven-leaf index');result=leaf(repo,args.head,args.index,dest)
    else:result=parent(repo,args.head,dest)
    print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
