from pathlib import Path
import os,json,hashlib,subprocess,time,resource,datetime
w=Path.cwd();b=w/'.takeover/private-recovery.git';d=w/'.takeover/full-foreign-variants834';draft=d/'qualification-drafts'
code='168ac2ab36663e31ca16f767340c0ab46bea4185';proposal='6a40d178fa32d66653334727541527b4768a501c';prefix='coordination/engineering/myanmar-adm3-current-cells-20261014/full-foreign13-variant-study-001/'
env=os.environ|{'GIT_DIR':str(b),'GIT_INDEX_FILE':str(b/'full13-qualification.index'),'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_ALTERNATE_OBJECT_DIRECTORIES':str(b/'objects')}
for k in ['NODE_OPTIONS','NODE_PATH']:env.pop(k,None)
for k,c in [('GIT_AUTHOR_NAME','user.name'),('GIT_AUTHOR_EMAIL','user.email')]:env[k]=subprocess.check_output(['git','config',c]).decode().strip()
env['GIT_COMMITTER_NAME']=env['GIT_AUTHOR_NAME'];env['GIT_COMMITTER_EMAIL']=env['GIT_AUTHOR_EMAIL']
def git(*a,raw=None):return subprocess.check_output(['git','-c','protocol.allow=never',*a],env=env,input=raw)
def blob(path,raw):
 oid=git('hash-object','-w','--stdin',raw=raw).decode().strip();git('update-index','--add','--cacheinfo','100644',oid,path)
 return {'path':path,'mode':'100644','git_blob_oid':oid,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def data(path,x):return blob(path,(json.dumps(x,indent=2)+'\n').encode())
def commit(message,parent,other=None):
 args=['commit-tree',git('write-tree').decode().strip(),'-p',parent]
 if other:args+=['-p',other]
 return git(*args,raw=(message+'\n').encode()).decode().strip()
git('read-tree',code)
adoption={'kind':'parent-adoption-of-exact13-same-build-full-foreign-source-choices','parent_worker':'01a12753-bff2-74b6-b6c9-db64be422011','proposal':proposal,'proposal_sha256':'415a7f4a543bc97e9a1372324545e5e88d69bc3f4aff5a566d2971c87ac0baff','exact_scope':13,'source_members':8,'accepted_credit':0,'received_utc':'2026-10-16T09:20:00Z','exact_parent_message':'Root reviewed exact13 proposal80655B SHA415a7f4a and authenticated whole physical result. One concrete narrative correction: the actual sole contradictory_land_water_support MultiLineString issue belongs to Lawngtlai ID76128533B70210707786180, not Chandel ID76128533B59855617266389. Both source_records and whole result agree; limits sentence/earlier report misnames it. Preserve original proposal, correct the adoption/addendum wording. Root adopts bounded exact13 same-build full-source choices: literal member/stable-owner joins, exclusive matching country reference, zero current-world contacts, original MMR negatives and full siblings retained. All13 mapped-land centres/no boundary; Lawngtlai issue remains genuine and must pass actual stock guards at its point, not waived. Proceed missing qualification with actual measured full-family capacity (Thai full product is265MB decoded; don’t impose arbitrary old768MiB/256MiB ceilings). No new geometry/parent/sovereignty claim or repair credit.'}
data(prefix+'adopted13/parent-adoption-and-narrative-correction.json',adoption)
for country in ['IND','THA']:
 for name in ['adopted-provider-families.json','exact-adopted-source-choice.json']:
  blob(prefix+'adopted13/'+country+'/'+name,(draft/country/name).read_bytes())
 blob(prefix+'adopted13/'+country+'/retained-original-negative-contexts.json',(draft/country/'territorial-context-records.json').read_bytes())
A=commit('Adopt exact thirteen original full-foreign source choices with unchanged stock code',code,proposal)
typed={}
for country in ['IND','THA']:
 n=json.load(open(draft/country/'territorial-context-records.json'));scopepath=prefix+'adopted13/'+country+'/exact-adopted-source-choice.json'
 scopeblob=git('ls-tree',A,'--',scopepath).decode().split()[2];raw=git('cat-file','blob',scopeblob)
 scopepin={'commit':A,'path':scopepath,'mode':'100644','git_blob_oid':scopeblob,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
 records=[]
 for r in n['records']:
  i=r.pop('adoption_scope_index');records.append(r|{'adoption':{'id':'exact-adopted-source-choice','pointer':f'/scope/{i}/adopted_decision'},'scope':{'id':'exact-adopted-scope','pointer':f'/scope/{i}','owner_pointer':'/owner'}})
 doc={'version':1,'kind':'adopted-native-territorial-applicability-v1','provenance':[{'id':'complete-original-MMR-family','role':'original-source','parts':n['parts']},{'id':'exact-adopted-source-choice','role':'adoption','pin':scopepin},{'id':'exact-adopted-scope','role':'scope','pin':scopepin}],'records':records}
 typed[country]=data(prefix+'adopted13/'+country+'/territorial-applicability.json',doc)
execution=commit('Bind exact adopted13 original Myanmar contextual geometry provenance',A)
configs={}
for country in ['IND','THA']:
 evidence=json.load(open(draft/country/'source-evidence.template.json'));basepath=prefix+'adopted13/'+country+'/'
 for field,name in [('adopted_provider_families','adopted-provider-families.json'),('territorial_applicability','territorial-applicability.json')]:
  p=basepath+name;oid=git('ls-tree',execution,'--',p).decode().split()[2];raw=git('cat-file','blob',oid)
  evidence[field]={'commit':execution,'path':p,'mode':'100644','git_blob_oid':oid,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
 data(basepath+'source-evidence.json',evidence);blob(basepath+'candidate-native-patch.json',(draft/country/'candidate-native-patch.json').read_bytes())
inputs=commit('Bind exact adopted13 source evidence to retained whole physical and full family operands',execution)
git('update-ref','refs/heads/engineering/myanmar-full-foreign13-qualification-inputs-20261016',inputs)
for country in ['IND','THA']:
 basepath=prefix+'adopted13/'+country+'/'
 config={'version':1,'source_evidence':{'commit':inputs,'path':basepath+'source-evidence.json'},'native_patch':{'commit':inputs,'path':basepath+'candidate-native-patch.json'}}
 (d/f'{country}-native13-authority-config.json').write_text(json.dumps(config,indent=2)+'\n');configs[country]=config
changed=git('diff','--name-only',code,execution).decode().splitlines();assert all(p.startswith(prefix)for p in changed)
checkout_env={k:v for k,v in env.items()if k not in ['GIT_DIR','GIT_INDEX_FILE']}
actual=subprocess.check_output(['git','rev-parse','HEAD'],env=checkout_env).decode().strip();assert actual==code
subprocess.check_call(['git','diff','--quiet'],env=checkout_env);subprocess.check_call(['git','diff','--cached','--quiet'],env=checkout_env)
subprocess.check_call(['git','read-tree','-m','-u',code,execution],env=checkout_env)
subprocess.check_call(['git','update-ref','refs/heads/engineering/myanmar-takeover-20261016',execution,code],env=checkout_env)
git('update-ref','refs/heads/cloud-stock-code-context',execution)
binding={'actual_execution_tree':execution,'unchanged_stock_code':code,'accepted_equivalent_code':'ffe590afe39e14caafdf25f45c5b6bbb8a49fc1b','input_commit':inputs,'source_choice_adoption_commit':A,'changed_data_paths':changed,'original_proposal_unchanged':proposal,'all_original_negatives_and_whole_physical_issues_retained':True,'scope':13,'accepted_credit':0}
(d/'adopted13-actual-execution-tree.json').write_text(json.dumps(binding,indent=2)+'\n');print(json.dumps(binding),flush=True)
for country in ['IND','THA']:
 dest='.cache/delivery-handoff/full-foreign13-'+country+'-native-authority-'+execution[:12]
 command=['node','scripts/prepare-delivery-handoff.mjs','native-authority',str((d/f'{country}-native13-authority-config.json').relative_to(w)),dest]
 start=time.monotonic();p=subprocess.run(command,env=env,cwd=w,capture_output=True,timeout=600)
 receipt={'command':command,'actual_execution_tree':execution,'code':code,'input_commit':inputs,'elapsed_seconds':time.monotonic()-start,'max_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'exit_code':p.returncode,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_or_physical_producers_replayed':False}
 (d/f'{country}-native13-authority-execution.json').write_text(json.dumps(receipt,indent=2)+'\n');(d/f'{country}-native13-authority.stdout.json').write_bytes(p.stdout);(d/f'{country}-native13-authority.stderr.log').write_bytes(p.stderr)
 print(json.dumps(receipt),flush=True);print(p.stdout.decode()[:4000],flush=True);print(p.stderr.decode()[:5000],flush=True)
