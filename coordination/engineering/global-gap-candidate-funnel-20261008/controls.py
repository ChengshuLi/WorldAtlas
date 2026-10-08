"""Bounded contract controls; no geometry or original source acquisition."""
import copy,json,types,pathlib
p=pathlib.Path(__file__).with_name('catalog.py');m=types.ModuleType('catalog');exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__)
id='physical-component:'+'a'*64;other='physical-component:'+'b'*64
r={'component_id':id,'current_geometry_sha256':'c'*64,'current_feature_sha256':'d'*64,'family':'gap-source-batch:'+'e'*24,'physical_status_source_relative':'mapped-land-support','physical_source_vintage':'archived source-relative','numerical_diagnosis':'not-in-#1300-numeric-first-cohort','source_comparison_status':'one-compatible-recorded-subject-uniquely-covers-component','source_comparison_packet':'original-packet','source_products':'original-products','unique_source_subject_id':'original-subject','source_reference_year':'2021','source_geometry_sha256':'f'*64,'next_prerequisite':'physical/source fitness','historical_555_witness':'true','unique_source_witness_1391':'true','land_plus_unique_route_1005':'true','nordic_geometric_mismatch_observation':'false'}
def ref(pointer):return {'commit':'1'*40,'path':'retained/decisions.json','sha256':'2'*64,'bytes':100,'pointer':pointer}
def key(ref):return(ref['commit'],ref['path'],ref['sha256'],ref['pointer'])
source=ref('/source/0');approval=ref('/approval/0');ready=ref('/readiness/0');impl=ref('/implementation/0');taskref=ref('/task/0')
verified={key(approval):{'component_id':id,'class':'missing-land'},key(ready):{'component_id':id,'state':'repair_ready'},key(impl):{'component_id':id,'state':'implemented'},key(taskref):{'component_ids':[id],'issue':1295}}
d={'component_id':id,'geometry_sha256':'c'*64,'class':'missing-land','decision':approval,'repair_ready':True,'implemented':True,'fully_integrated':False,'delivered':False,'state_evidence':{'repair_ready':ready,'implemented':impl}}
task={'component_ids':[id],'issue':1295,'scope_ref':taskref,'missing_facts':['full-normal-consumer-integration'],'role':'engineering-repair'}
unknown=m.catalog_record(r,source,{},verified,[task]);assert unknown['class']=='unresolved' and unknown['provisional_support']=='land' and not unknown['implemented']
accepted=m.catalog_record(r,source,{id:d},verified,[task]);assert accepted['implemented'] and not accepted['fully_integrated'];s=m.summarize([accepted],{id});assert s['classes']['missing-land']==1 and s['percentages']['implemented']==100 and s['counts']['fully_integrated']==0
neg=[]
def reject(name,call,expected):
 try:call()
 except ValueError as e:assert expected in str(e),(name,str(e));neg.append({'name':name,'rejection':str(e)})
 else:raise AssertionError(name+' accepted')
reject('raw-duplicate-ID',lambda:m.exact_ids([r,r]),'Duplicate')
reject('missing-full-ID',lambda:m.summarize([accepted],{id,other}),'Missing complete')
reject('foreign-full-ID',lambda:m.summarize([accepted],{other}),'foreign')
b=copy.deepcopy(d);b['geometry_sha256']='0'*64
reject('stale-whole-geometry-decision',lambda:m.catalog_record(r,source,{id:b},verified,[task]),'stale decision')
b=copy.deepcopy(d);b['decision']['commit']='3'*40
reject('coherently-stale-decision-ref',lambda:m.catalog_record(r,source,{id:b},verified,[task]),'Unverified')
b=copy.deepcopy(d);b['fully_integrated']=True
reject('implemented-is-not-integrated',lambda:m.catalog_record(r,source,{id:b},verified,[task]),'lacks actual evidence')
b=copy.deepcopy(d);b['implemented']=False;b['fully_integrated']=True;b['state_evidence']['fully_integrated']=impl
reject('invalid-integration-transition',lambda:m.catalog_record(r,source,{id:b},verified,[task]),'transition evidence')
b=copy.deepcopy(d);b['delivered']=True
reject('integration-is-not-delivery',lambda:m.catalog_record(r,source,{id:b},verified,[task]),'lacks actual evidence')
b=copy.deepcopy(r);b['unique_source_witness_1391']='false'
reject('555-nested-membership-drift',lambda:m.catalog_record(b,source,{},verified,[]),'Historical555')
b=copy.deepcopy(task);b['issue']=999
reject('coherent-task-foreign-issue',lambda:m.catalog_record(r,source,{},verified,[b]),'Foreign/stale task')
b=copy.deepcopy(task);b['scope_ref']['sha256']='0'*64
reject('stale-task-scope-hash',lambda:m.catalog_record(r,source,{},verified,[b]),'Foreign/stale task')
b=copy.deepcopy(verified);b[key(approval)]['component_id']=other
reject('coherently-wrong-approved-component',lambda:m.catalog_record(r,source,{id:d},b,[task]),'foreign accepted')
b=copy.deepcopy(unknown);b['implemented']=True
reject('adjacent-summary-invalid-transition',lambda:m.summarize([b],{id}),'precedes readiness')
b=copy.deepcopy(accepted);b['class']='fabricated'
reject('adjacent-summary-foreign-final-class',lambda:m.summarize([b],{id}),'Unknown final')
print(json.dumps({'scope':'Synthetic schema/join/transition controls only, not full catalog production or physical approval','positives':3,'negatives':neg,'negative_count':len(neg)}))
