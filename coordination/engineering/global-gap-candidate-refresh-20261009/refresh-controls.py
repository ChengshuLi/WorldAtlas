"""Actual metadata helpers against retained original input bodies; no science."""
import copy,gzip,json,pathlib,sys
import refresh
import catalog
D=pathlib.Path(refresh.Q+'inputs');pins=json.load(open(D/'pins.json'));inputs={p['path'].rsplit('/',1)[-1]:(dict(p,commit='1'*40),gzip.decompress(pathlib.Path(p['path']).read_bytes()) if 'uncompressed_bytes' in p else pathlib.Path(p['path']).read_bytes()) for p in pins}
progress,exceptions=refresh.build_progress(inputs);assert len(progress)==16 and len(exceptions)==6
neg=[]
def reject(name,fn,expected):
 try:fn()
 except (ValueError,KeyError) as e:
  assert expected in str(e),(name,str(e));neg.append({'case':name,'reason':str(e)})
 else:raise AssertionError(name+' admitted')
def mutation(name,filename,edit,expected):
 x=copy.deepcopy(inputs);p,b=x[filename];v=json.loads(b);edit(v);x[filename]=(p,json.dumps(v).encode());reject(name,lambda:refresh.build_progress(x),expected)
mutation('foreign-integrated-identity','integrated-transitions.json',lambda v:v['rows'][0].update(component_id='physical-component:'+'0'*64),'Foreign/stale')
mutation('stale-integrated-geometry','integrated-transitions.json',lambda v:v['rows'][0].update(original_geometry_sha256='0'*64),'Foreign/stale')
mutation('coherent-foreign-selected-bank','integrated-transitions.json',lambda v:v.update(selected_release='foreign-release'),'Missing installed')
mutation('missing-complete-transition-pin','integrated-transitions.json',lambda v:v['whole_git_input_pins'].pop(),'Complete installed transition')
mutation('foreign-rule-preimage','additive-authorities.json',lambda v:v['authorities'][0]['rule_preimage'].update(version=99),'rule preimage')
mutation('duplicate-source-profile','additive-authorities.json',lambda v:v['authorities'].append(v['authorities'][0]),'Duplicate source')
mutation('foreign-source-review-head','root1561-accepted-review-comment-6073179645-20261009.json',lambda v:v.update(body=v['body'].replace('b82ee098641b0dda3fc27d281b438ec4958ffbce','0'*40)),'Foreign source')
identity=next(i for i,r in progress.items() if r.get('integrated'));source_id=next(i for i,r in progress.items() if not r.get('integrated'));p=progress[identity]
row={'component_id':identity,'current_geometry_sha256':p['geometry_sha256'],'current_feature_sha256':'a'*64,'class':'missing-land','repair_ready':True,'implemented':True,'fully_integrated':False,'delivered':False,'state_evidence':{},'source_flags':{'source_comparison':True,'numerical_diagnosis':False},'next_work':{'tasks':[],'missing_facts':['full-normal-consumer-integration']}}
result=catalog.refresh_record(row,p,p['geometry_sha256'],{identity});assert result['fully_integrated'] and result['pipeline_status']['state']=='repaired-verified-selected-release' and not result['delivered']
r=copy.deepcopy(row);r.update({'component_id':source_id,'current_geometry_sha256':progress[source_id]['geometry_sha256'],'class':'unresolved','repair_ready':False,'implemented':False})
result=catalog.refresh_record(r,progress[source_id],r['current_geometry_sha256'],{source_id});assert result['class']=='unresolved' and not result['repair_ready'] and result['pipeline_status']['state']=='eligible-source-relative-rule'
for name,edit,expected in [('unknown-production-delivery',lambda v:v['integrated'].update(production_delivered=True),'Unknown delivery'),('missing-selected-bank-binding',lambda v:v['integrated']['evidence'].pop('selection'),'Missing current bank'),('source-only-physical-promotion',lambda v:v['source_relative_repair'].update(physical_authority_approved=True),'Source-only'),('foreign-candidate-ID',lambda v:v.update(component_id=source_id),'Foreign/stale')]:
 x=copy.deepcopy(p);edit(x);reject(name,lambda:catalog.refresh_record(row,x,row['current_geometry_sha256'],{identity}),expected)
arctic=next(v for v in progress.values() if v.get('remaining_tasks',[{}])[0].get('issue')==1520)
assert arctic['remaining_tasks'][0]['issue']==1520 and arctic['source_relative_repair']['constructed'] is True
x=copy.deepcopy(arctic);x['source_relative_repair']['evidence'].pop('construction')
reject('missing-actual-construction-outcome',lambda:catalog.refresh_record(dict(r,component_id=x['component_id'],current_geometry_sha256=x['geometry_sha256']),x,x['geometry_sha256'],{x['component_id']}),'construction lacks supporting outcome')
mutation('closed-current-integration-task','current-issue-1520.json',lambda v:v.update(state='closed'),'current remaining')
print(json.dumps({'scope':'Actual retained input/helper controls only; no GIS, native or scientific execution','positive_count':4,'negative_count':len(neg),'negatives':neg},sort_keys=True))
