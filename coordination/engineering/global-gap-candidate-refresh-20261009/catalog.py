"""Candidate funnel contracts. Provisional support never grants final approval.
All data adapters must supply authenticated immutable refs; no GIS is performed.
"""
import hashlib,json,re
from collections import Counter
CLASSES=('missing-land','water','mixed','calculation-or-rendering-defect','reference-disagreement','unresolved')
STATES=('repair_ready','implemented','fully_integrated','delivered')
SUPPORT={'mapped-land-support':'land','mapped-inland-water-support':'water','mixed-source-support':'mixed'}

def require(ok,message):
    if not ok:raise ValueError(message)

def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()

def sha(raw):return hashlib.sha256(raw).hexdigest()

def exact_ids(rows,field='component_id'):
    result={}
    for row in rows:
        identity=row.get(field)
        require(isinstance(identity,str) and re.fullmatch(r'physical-component:[a-f0-9]{64}',identity),'Invalid original component ID')
        require(identity not in result,'Duplicate original component ID')
        result[identity]=row
    return result

def immutable_ref(ref):
    require(isinstance(ref,dict) and re.fullmatch('[a-f0-9]{40}',ref.get('commit','')) and re.fullmatch('[a-f0-9]{64}',ref.get('sha256','')),'Immutable decision/source vintage required')
    path=ref.get('path')
    require(isinstance(path,str) and not path.startswith('/') and '\\' not in path and all(s not in ('','.','..') for s in path.split('/')),'Safe original evidence path required')
    require(type(ref.get('bytes')) is int and 0<=ref['bytes']<=33554432,'Ordinary original evidence size required')
    require(isinstance(ref.get('pointer'),str) and ref['pointer'].startswith('/'),'Exact decision/source record pointer required')
    return ref

def decision_for(identity,row,decision,verified_refs):
    if decision is None:
        return {'class':'unresolved','decision':None,**{state:False for state in STATES},'state_evidence':{}}
    require(decision.get('component_id')==identity and decision.get('geometry_sha256')==row['current_geometry_sha256'],'Foreign/stale decision identity/geometry')
    result={k:decision[k] for k in ('class','decision',*STATES,'state_evidence')}
    require(result['class'] in CLASSES and result['class']!='unresolved','Accepted decision needs a disjoint resolved class')
    ref=immutable_ref(result['decision']);key=(ref['commit'],ref['path'],ref['sha256'],ref['pointer'])
    require(key in verified_refs and (verified_refs[key].get('component_id')==identity or identity in verified_refs[key].get('component_ids',[])) and verified_refs[key].get('class')==result['class'],'Unverified/coherently foreign accepted decision')
    for state in STATES:
        require(type(result[state]) is bool,'Explicit candidate progress flags required')
        if result[state]:
            require(state in result['state_evidence'],'Candidate transition lacks actual evidence')
            r=immutable_ref(result['state_evidence'][state]);k=(r['commit'],r['path'],r['sha256'],r['pointer'])
            require(k in verified_refs and (verified_refs[k].get('component_id')==identity or identity in verified_refs[k].get('component_ids',[])) and verified_refs[k].get('state')==state,'Unverified/coherently foreign transition evidence')
    require(not result['implemented'] or result['repair_ready'],'Implementation cannot precede repair readiness')
    require(not result['fully_integrated'] or result['implemented'],'Full integration cannot precede implementation')
    require(not result['delivered'] or result['fully_integrated'],'Delivery cannot precede full integration')
    require(not any(result[state] for state in STATES) or result['class'] in ('missing-land','calculation-or-rendering-defect'),'Non-repair classification cannot claim repair progress')
    return result

def source_flags(row):
    require(row['physical_status_source_relative'] in ('mapped-land-support','mapped-inland-water-support','mixed-source-support','outside-mapped-L1-context','unknown'),'Unknown provisional physical support')
    require(row['source_comparison_status'] in ('not-in-57,785-source-comparison-cohort','no-source-intersection-in-literal-domain','one-compatible-recorded-subject-uniquely-covers-component','positive-source-coverage-mixed-partial-or-subject-unresolved','zero-area-contact-only'),'Unknown source comparison observation')
    fields=('historical_555_witness','unique_source_witness_1391','land_plus_unique_route_1005','nordic_geometric_mismatch_observation')
    require(all(row.get(k) in ('true','false') for k in fields),'Explicit provisional source flags required')
    flags={k:row[k]=='true' for k in fields}
    flags['source_comparison']=row['source_comparison_status']!='not-in-57,785-source-comparison-cohort'
    flags['numerical_diagnosis']=row['numerical_diagnosis']!='not-in-#1300-numeric-first-cohort'
    require(not flags['historical_555_witness'] or flags['unique_source_witness_1391'],'Historical555 must remain within1391')
    require(not flags['land_plus_unique_route_1005'] or flags['unique_source_witness_1391'],'Land1005 must remain within1391')
    require(not flags['unique_source_witness_1391'] or flags['source_comparison'],'Unique1391 must remain within57785')
    return flags

def task_for(identity,record,tasks,verified_refs):
    assigned=[]
    for task in tasks:
        if identity not in task['component_ids']:continue
        require(type(task['issue']) is int and task['issue']>0,'Actual task issue required')
        r=immutable_ref(task['scope_ref']);k=(r['commit'],r['path'],r['sha256'],r['pointer'])
        require(k in verified_refs and identity in verified_refs[k].get('component_ids',[]) and verified_refs[k].get('issue')==task['issue'],'Foreign/stale task scope reference')
        require(task.get('missing_facts') and all(isinstance(s,str) and s for s in task['missing_facts']),'Task must specify exact missing facts')
        assigned.append({'issue':task['issue'],'missing_facts':task['missing_facts'],'scope_ref':task['scope_ref'],'role':task['role']})
    if record['delivered']:need=[]
    elif record['fully_integrated']:need=['verified-delivery']
    elif record['implemented']:need=['full-normal-consumer-integration']
    elif record['repair_ready']:need=['engineering-implementation']
    elif record['class']!='unresolved':need=['repair-authority-or-no-repair-disposition']
    else:need=['accepted-physical-class','source-fitness-and-date','cause-and-repair-authority']
    return {'missing_facts':need,'tasks':assigned,'unassigned_requirements':[fact for fact in need if not any(fact in task['missing_facts'] for task in assigned)],'original_next_prerequisite':record['source_evidence']['next_prerequisite']}

def catalog_record(row,source_ref,decisions,verified_refs,tasks):
    identity=row['component_id'];immutable_ref(source_ref)
    flags=source_flags(row);result=decision_for(identity,row,decisions.get(identity),verified_refs)
    evidence={k:row[k] for k in ('physical_status_source_relative','physical_source_vintage','numerical_diagnosis','source_comparison_status','source_comparison_packet','source_products','unique_source_subject_id','source_reference_year','source_geometry_sha256','next_prerequisite')}
    record={'component_id':identity,'current_feature_sha256':row['current_feature_sha256'],'current_geometry_sha256':row['current_geometry_sha256'],'family':row['family'],'source_evidence':evidence,'source_record':source_ref,'source_flags':flags,'provisional_support':SUPPORT.get(row['physical_status_source_relative'],'unknown-or-unmapped'),**result}
    record['next_work']=task_for(identity,record,tasks,verified_refs)
    return record

def summarize(records,expected_ids):
    counts=Counter();classes=Counter({c:0 for c in CLASSES});seen=set();task_counts=Counter();missing=Counter()
    for r in records:
        identity=r['component_id'];require(identity in expected_ids and identity not in seen,'Missing/duplicate/foreign catalog identity');seen.add(identity)
        require(r['class'] in CLASSES,'Unknown final class')
        require(all(type(r[state]) is bool for state in STATES),'Invalid report progress flags')
        require(not r['implemented'] or r['repair_ready'],'Report implementation precedes readiness')
        require(not r['fully_integrated'] or r['implemented'],'Report integration precedes implementation')
        require(not r['delivered'] or r['fully_integrated'],'Report delivery precedes integration')
        require(r['class']!='unresolved' or (r['decision'] is None and not any(r[state] for state in STATES)),'Report provisional evidence promoted to repair')
        if r['class']!='unresolved':immutable_ref(r['decision'])
        for state in STATES:
            if r[state]:immutable_ref(r['state_evidence'][state])
        classes[r['class']]+=1
        counts['accepted_classifications']+=r['class']!='unresolved'
        for state in STATES:counts[state]+=r[state]
        for flag,value in r['source_flags'].items():counts[flag]+=value
        counts['provisional_land_or_water']+=r['provisional_support'] in ('land','water')
        for t in r['next_work']['tasks']:task_counts[str(t['issue'])]+=1
        missing.update(r['next_work']['missing_facts'])
    require(seen==set(expected_ids),'Missing complete original catalog identity')
    n=len(seen);require(sum(classes.values())==n,'Final class count conservation failure')
    return {'component_count':n,'classes':dict(classes),'counts':dict(counts),'percentages':{k:100*v/n for k,v in counts.items()},'task_candidate_counts':dict(task_counts),'missing_fact_counts':dict(missing),'limits':['Provisional source comparison/numerical diagnoses are not accepted physical truth.','Implementation, full integration and verified delivery are separate measured states.','Component percentages use original component count, not affected geographic area.']}

PIPELINE=('awaiting-evidence','evidence-ready','eligible-source-relative-rule','repaired-verified-selected-release','confirmed-water-or-no-defect','rejected-or-ambiguous')

def refresh_record(original,progress,expected_geometry,authority_ids):
    """Project authenticated transitions onto the existing original catalog row.
    Source-relative eligibility is a separate domain; it never changes class.
    """
    record=json.loads(json.dumps(original));identity=record['component_id']
    require(record['current_geometry_sha256']==expected_geometry,'Stale original catalog geometry')
    require(identity in authority_ids,'Foreign catalog identity')
    record['source_relative_repair']=None
    if progress is not None:
        require(progress['component_id']==identity and progress['geometry_sha256']==expected_geometry,'Foreign/stale progress candidate')
        source=progress['source_relative_repair']
        require(source['authority_domain']=='retained-source-relative-reference','Wrong source authority domain')
        require(type(source['eligible']) is bool and source['eligible'],'Source decision must be eligible')
        require(type(source['constructed']) is bool and type(source['current_bank_rebound']) is bool and type(source['activated']) is bool,'Explicit source transition types')
        require(source['current_bank_rebound']==source['activated'],'Unbound selected bank transition')
        require(not source['activated'] or source['constructed'],'Activation without complete construction')
        require(source['physical_authority_approved'] is False and source['current_physical_truth_approved'] is False,'Source-only physical promotion')
        for ref in source['evidence'].values():immutable_ref(ref)
        require({'source','rule','review','proposal'}<=set(source['evidence']),'Missing source/rule/review/proposal custody')
        require(not source['constructed'] or 'construction' in source['evidence'] or progress.get('integrated'),'True construction lacks supporting outcome')
        record['source_relative_repair']=source
        if progress.get('integrated'):
            require(record['implemented'] and record['class']=='missing-land','Proposal-only integration')
            integration=progress['integrated']
            require(integration['component_id']==identity and integration['geometry_sha256']==expected_geometry,'Coherently foreign integrated transition')
            require(integration['production_delivered'] is False,'Unknown delivery cannot become delivered')
            require({'migration','selection','manifest','normal_build','accepted_merge'}<=set(integration['evidence']),'Missing current bank/normal consumer binding')
            for ref in integration['evidence'].values():immutable_ref(ref)
            record['fully_integrated']=True;record['state_evidence']['fully_integrated']=integration['evidence']['normal_build']
    if record['fully_integrated']:
        state='repaired-verified-selected-release';domain='verified-offline-selected-release';missing=['verified-production-delivery']
    elif record['source_relative_repair']:
        state='eligible-source-relative-rule';domain='retained-source-relative-reference';missing=['fresh-current-bank-rebind','normal-consumer-integration','physical-authority-and-observation-date']
    elif record['class'] in ('water','reference-disagreement'):
        state='confirmed-water-or-no-defect';domain='accepted-physical-classification';missing=[]
    elif record.get('source_rule_exception'):
        state='rejected-or-ambiguous';domain='retained-source-relative-reference';missing=['source-parent-exception-resolution','physical-authority-and-observation-date']
    elif record['source_flags']['source_comparison'] or record['source_flags']['numerical_diagnosis']:
        state='evidence-ready';domain='provisional-observations';missing=list(record['next_work']['missing_facts'])
    else:
        state='awaiting-evidence';domain='unresolved';missing=list(record['next_work']['missing_facts'])
    require(state in PIPELINE,'Unknown disjoint pipeline status')
    record['pipeline_status']={'state':state,'authority_domain':domain}
    record['next_work']['historical_scope_tasks']=record['next_work']['tasks']
    record['next_work']['tasks']=progress.get('remaining_tasks',[]) if progress else record.pop('_current_tasks',[])
    record.pop('_current_tasks',None)
    for task in record['next_work']['tasks']:immutable_ref(task['scope_ref'])
    record['next_work']['missing_facts']=missing
    record['next_work']['unassigned_requirements']=[f for f in missing if not any(f in task['missing_facts'] for task in record['next_work']['tasks'])]
    record['progress_scope']='Verified offline integration and retained-source eligibility are separate domains; production delivery and contemporary physical authority remain unapproved.'
    return record
