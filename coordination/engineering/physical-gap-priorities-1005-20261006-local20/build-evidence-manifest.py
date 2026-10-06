import pathlib,sys,json,subprocess,hashlib
sys.path.insert(0,'scripts')
from evidence.immutable import descriptor,canonical_json
p=pathlib.Path('coordination/engineering/physical-gap-priorities-1005-20261006-local20')
base='e205b7427c006cfea9acb5435f0aa08aace22266'
report=json.loads((p/'priorities-v2/report.json').read_bytes())
validation=json.loads((p/'complete-world-validation-v2.json').read_bytes())
assert validation['components']==95174 and validation['native_contexts']==49625 and validation['unmeasured_fragments']==5
log=pathlib.Path('.cache/priority-controls-34.tap').read_bytes()
(p/'controls-34.tap').write_bytes(log)
for kind,controls in [('positive-control',['27 analytic investigation controls and unchanged complete semantic record; actual transcript retained.','Complete-world original/native/source/contact/legacy-water/grid binding validation retained separately.']),('negative-control',['Six semantic alteration controls reject contact omission, source binding redirection, unknown omission, invented scope, promoted surface and altered original known area.','27 analytic suite includes tiny/nonmeasured originals, point versus edge contact, incomplete partitions/ranks, missing ancestry and unmatched old operation failures.'])]:
 row={'method_id':'physical-gap-priorities','kind':kind,'outcome':'passed','controls':controls,'log_sha256':hashlib.sha256(log).hexdigest(),'limits':['Synthetic controls do not independently approve factual geography; complete original semantic gate is recorded separately.']}
 (p/('physical-gap-priorities-'+kind+'.json')).write_bytes(canonical_json(row))
old={}
for pin in report['inputs']:
 if not pin['path'].startswith(str(p)+'/'):
  old[pin['path']]={**pin,'role':'original-source'}
for name in ['data/hierarchy.json','data/canonical-grid/manifest.json']:
 raw=subprocess.check_output(['git','show',base+':'+name]);old[name]={**descriptor(name,raw),'role':'original-source'}
# Preserve every complete encoded envelope with its exact original decoded bytes.
envpath='coordination/engineering/physical-gap-audit-1005-20261005-local18/input-envelope-v1/manifest.json'
envelope=json.loads(subprocess.check_output(['git','show',base+':'+envpath]))
for row in envelope['entries']:
 pin=old[row['encoded']['path']];pin.update(uncompressed_bytes=row['original']['bytes'],uncompressed_sha256=row['original']['sha256'])
# Custody filenames deliberately retain binary transport; gzip originals still
# declare the whole uncompressed bytes rather than hiding them behind extension.
custody=json.loads(subprocess.check_output(['git','show',base+':'+ 'coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json']))
for alias in custody['aliases']:
 if alias['payload'] in old and 'uncompressed_bytes' in alias['original']:
  old[alias['payload']].update({key:alias['original'][key] for key in ['uncompressed_bytes','uncompressed_sha256']})
# Existing original detector/grid gzip files also retain decoded-byte bounds.
for reportpath,field,relative in [ ('coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/report.json','outputs',False),('coordination/engineering/geographic-grid-triage-946-20261005-local08/triage-v1/report.json','sample_parts',True) ]:
 original=json.loads(subprocess.check_output(['git','show',base+':'+reportpath]))
 for pin in original[field]:
  path=str(pathlib.PurePosixPath(reportpath).parent)+'/'+pin['path'] if relative else pin['path']
  if path in old:
   old[path].update({key:pin[key] for key in ['uncompressed_bytes','uncompressed_sha256']})
new={}
paths=subprocess.check_output(['git','diff','--name-only',base],text=True).splitlines()
paths+=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],text=True).splitlines()
manifest=str(p/'evidence-quality.json')
paths=sorted(set(paths+[manifest]))
for name in paths:
 if name==manifest:continue
 target=pathlib.Path(name)
 assert target.is_file() and not target.is_symlink(),name
 new[name]=descriptor(name,target.read_bytes())
for prefix in ['priorities-v2','priorities-v3']:
 r=json.loads((p/prefix/'report.json').read_bytes())
 for pins in r['outputs'].values():
  for pin in pins:new[pin['path']]=pin
metricrows=[('component_count','/component_count',report['component_count'],'components'),('fragment_count','/fragment_count',report['fragment_count'],'fragments'),('native_context_count','/native_context_count',report['native_context_count'],'locations')]
metricrows += [('issue_roster_count','/declared_issue_subject_roster_count',report['declared_issue_subject_roster_count'],'issues'),('original_overlay_unknowns','/original_unknown_overlay_count',report['original_unknown_overlay_count'],'operations'),('original_difference_unknowns','/original_unknown_difference_count',report['original_unknown_difference_count'],'operations')]
metricrows += [('order-'+name,'/complete_order_counts/'+name,value,'components') for name,value in report['complete_order_counts'].items()]
metricrows += [('difference-'+name,'/difference_unknown_accounting/'+name,value,'operations') for name,value in report['difference_unknown_accounting'].items()]
metricrows += [('partition-'+name,'/partition_counts/'+name,value,'components') for name,value in report['partition_counts'].items()]
rpath=str(p/'priorities-v2/report.json')
metrics=[{'id':name,'value':value,'unit':unit,'vintage':'archived','evaluation_commit':report['executed_code_commit'],'input_sha256':new[rpath]['sha256']} for name,pointer,value,unit in metricrows]
bindings=[{'metric_id':name,'path':rpath,'json_pointer':pointer} for name,pointer,value,unit in metricrows]
result={'version':1,'issue':1005,'lane':'engineering','worker_id':'01a10893-2a57-72e0-aa08-5c36088d5206','subject_ids':[],'subject_ids_sha256':hashlib.sha256(b'[]').hexdigest(),
 'baseline':{'commit':base,'files':list(old.values()),'pins':{'canonical_grid':old['data/canonical-grid/manifest.json']['sha256'],'hierarchy':old['data/hierarchy.json']['sha256']},'pin_files':{'canonical_grid':'data/canonical-grid/manifest.json','hierarchy':'data/hierarchy.json'}},
 'sources':[{'id':'retained-original-audits','url':'https://github.com/ChengshuLi/WorldAtlas/tree/'+base,'retrieved_at':'2026-10-06','vintage':base,'temporal_status':'reference','verification':'unverified','retention':'restoration-only','role':'Complete retained audit, original native/source bindings, old grid samples, archived dated-water reports and original issue rosters; investigation context only.','license':{'status':'unknown','terms':'Original source terms remain heterogeneous; no new geographic authority or reuse approval is asserted.'},'restoration':'All consumed original input files pinned in baseline descriptors; native original bytes restored from45 complete immutable encoded envelopes and crosschecked at original commits. Both actual derived runs are retained in full. The open-issue API pages are complete original newly retained bytes.','limit':'Investigation priorities do not certify legal boundaries, dry land, water, new-grid coverage, approved regional branches or delivery.'}],
 'outputs':list(new.values()),'methods':[{'id':'physical-gap-priorities','kind':'generator','helper_version':'worldatlas-evidence-preparation-v1','description':'Exact original component/source/contact/hierarchy/legacy-grid/water-context joins; complete partitions and three total investigation orders. No geometry modification or new spatial/raster measurement.','software':'Python3.12.14; zlib '+report['software']['zlib']+'; imported Shapely2.1.2/GEOS3.13.1; shared immutable preparation v1','units':'components, source references, original known area_m2 and zero-based total-order positions'}],
 'metrics':metrics,'metric_bindings':bindings,'summaries':[],
 'change_receipts':[{'path':name,'status':'added'} for name in paths],
 'validation':[{'method_id':'physical-gap-priorities','kind':kind,'outcome':'passed','evidence_path':str(p/('physical-gap-priorities-'+kind+'.json'))} for kind in ['positive-control','negative-control','reproducibility']],
 'stages':{'implementation':'implemented','research':'partial','geographic_approval':'unapproved'},
 'conclusions':[{'text':'Every retained candidate has exact original identity/measurement uncertainty, diagnostic contact/context references and complete investigation ranks; no candidate is automatically assigned geography.','status':'supported','source_ids':['retained-original-audits']},{'text':'Source-backed repairs, grid discrepancies, renderer parity, complete release/content revalidation and verified delivery remain required for the worldwide goal.','status':'unresolved','source_ids':[]}],
 'commands':['python -B scripts/build-physical-gap-priorities.py --commit '+report['input_commit']+' --issues '+str(p/'open-issues-api-pages-20261006.json')+' --output '+str(p/'reviewer-new-vintage'),'python -B scripts/validate-physical-gap-priorities.py --prefix '+str(p/'priorities-v2'),'node --test test/physical-gap-priority-controls.test.mjs test/physical-gap-priority-evidence-controls.test.mjs test/physical-gap-priority-evidence.test.mjs']}
pathlib.Path(manifest).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'baseline_files':len(old),'outputs':len(new),'all_declared_bytes':sum(row['bytes'] for row in list(old.values())+list(new.values())),'changed_files':len(paths)}))
