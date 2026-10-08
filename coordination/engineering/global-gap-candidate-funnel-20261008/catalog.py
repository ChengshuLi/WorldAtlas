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
