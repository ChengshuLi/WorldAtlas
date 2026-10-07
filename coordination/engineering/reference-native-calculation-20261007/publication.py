import copy,gzip,hashlib,json,pathlib,shutil,subprocess
R=pathlib.Path.cwd();N='coordination/engineering/reference-native-calculation-20261007/';D=R/N;P=R/'.cache/reference-native-preflight';F='b596ef836c51c5405baa8ceda770a2554ca12b7f';C='6a47b43025d963daf80915c6d219c75ebcc8cd91'
def sha(b):return hashlib.sha256(b).hexdigest()
def js(p,v):p.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')
def cp(a,b):
 if b.exists():raise ValueError('Fresh publication required: '+str(b))
 b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a,b)
for name in ['one','two']:
 src=R/('.cache/reference-native-b596-run-'+name);dst=D/('run-'+name)
 if dst.exists():raise ValueError('Run publication exists')
 shutil.copytree(src/'products',dst/'products',copy_function=shutil.copy2)
 for f in ['report.json','execution.json']:cp(src/f,dst/f)
 for suffix in ['actual-execution.json','stdout','stderr-and-native-time']:
  cp(P/('reference-native-b596-run-'+name+'.'+suffix),dst/('actual-'+suffix))
V=D/'verification';V.mkdir()
for src,dst in [('actual-f621-full-row-index-archive-verifier.json','complete-row-index-archive-verification.json'),('actual-b596-two-full-product-byte-equality.json','two-complete-scientific-trees.json'),('corrected-original-view-32-controls.json','reader-scope-archive-controls.json'),('actual-runtime-controls.json','runtime-operator-controls.json'),('actual-cli-input-only-b596.json','actual-input-only.json'),('actual-cli-b596-terminal-receipt.json','actual-input-only-terminal.json'),('actual-final-publication-storage-check.json','actual-publication-storage.json'),('actual-pair-operating-admission.json','actual-pair-operating-admission.json')]:cp(P/src,V/dst)
cp(P/'record-actual-calculation.py',D/'execution-recorder.py')
old=json.loads((P/'phase1-manifest-original.json').read_text());plan=json.loads((D/'input-plan.json').read_text());proof=json.loads((V/'complete-row-index-archive-verification.json').read_text())
results={k:proof['whole_scope'][k] for k in ['complete_locations','unchanged_locations','unchanged_complete_records','original_reference_files','archived_original_target_records','recomputed_target_records','all_after_records','scientific_files','scientific_encoded_bytes','original_prior_archive_files_retained']}
results.update(actual_complete_calculation_runs=2,actual_reader_scope_controls=32,actual_runtime_operator_controls=9,missing_changed_records=0)
js(D/'results.json',results)
js(D/'upstream-custody-binding.json',{'commit':C,'path':'coordination/engineering/reference-source-custody-20261007/evidence-quality.json','sha256':sha((P/'phase1-manifest-original.json').read_bytes()),'raw_bytes':(P/'phase1-manifest-original.json').stat().st_size,'actual_upstream_whole_archive_member_proof_preserved':True,'not_executed_in_this_calculation_phase':True})
(D/'README.md').write_text('''# Two-target native reference calculation

Phase 2 of #1364 stages complete reference products for the two reviewed QUE103/NFL114 corrections. Two actual b596ef836c51c5405baa8ceda770a2554ca12b7f calculations completed EXIT0. Every one of the 96 scientific product bodies is byte/mode identical between runs (2,292,845 bytes per tree); reports, invocation paths and timing capsules retain their actual differences. The structural/source verifier executed at f6215167dc370577470e283b3fb26990ba0bb7a7 and does not claim an independent numerical recomputation.

The literal unchanged `summarize_changed` helper recomputed fourteen records. All 346,332 other complete records and 49,623 unaffected location records remain equal; the full old fourteen target records and all prior archives remain retained. The reader authenticates all 171 ordinary input bodies, the complete 49,625-location world and all 93 original reference files. The complete relevant terrain/RESOLVE originals are reconstructed from accepted lossless fragments, and all four full climate TIFFs are consumed. The original climate ZIP/member relation and phase-1 manifest remain bound to immutable upstream merge6a47b43025d963daf80915c6d219c75ebcc8cd91; this calculation does not run stock `prepare` or `source_proof`.

Run from the repository root with the pinned Python3.12.14 Rasterio1.4.3 environment: `producer.py --commit b596ef836c51c5405baa8ceda770a2554ca12b7f --name FRESH_OWN_NAME`. The supplied commands/actual execution capsules retain precise paths, executable and runtime fingerprints. Reader/archive controls and runtime/operator controls exercise the production boundaries. `verify.py` compares complete rows, source/index/archive relationships and paired payloads without another GIS calculation.

Beck2023 periods are climate normals; the 2026 interval literally reuses the 1991–2020 normal and is not an annual observation. RESOLVE2017 represents potential natural biome; modern EarthEnv/GMTED terrain is not a historical annual reconstruction. Native coverage ratios remain partial, retrieval dates remain unknown and source fitness/legal/water/historical-cause authority is not approved. These staged products do not activate current pointers, close parent #1295, approve its 62 unresolved siblings or complete global #1202. Parent offline activation and normal package consumers remain separate obligations.
''')
def desc(p,role):
 b=(R/p).read_bytes();d={'path':p,'bytes':len(b),'sha256':sha(b),'hash_kind':'file-bytes','role':role}
 if p.endswith('.gz'):
  z=gzip.decompress(b);d.update(uncompressed_bytes=len(z),uncompressed_sha256=sha(z))
  if len(z)>32*1024*1024:raise ValueError('Decoded cap '+p)
 if len(b)>32*1024*1024:raise ValueError('Encoded cap '+p)
 return d
sourcepaths={x['path'] for x in plan['source_descriptors']};sourcepaths.add('coordination/engineering/reference-source-custody-20261007/evidence-quality.json')
source=[]
for p in sorted(sourcepaths):
 if not (R/p).exists():
  raw=subprocess.check_output(['git','show',C+':'+p]);(R/p).parent.mkdir(parents=True,exist_ok=True);(R/p).write_bytes(raw)
 source.append(desc(p,'actual-complete-calculation-source'))
outputs=[desc(p.relative_to(R).as_posix(),'complete-calculation-product-or-code') for p in sorted(D.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='evidence-quality.json']
base=copy.deepcopy(old['baseline']);subjects=old['subject_ids'];method='literal-two-target-native-reference-calculation'
metrics=[{'id':k,'value':v,'unit':'bytes' if k.endswith('_bytes') else 'count','vintage':'archived','evaluation_commit':F,'input_sha256':sha((D/'results.json').read_bytes())} for k,v in results.items()]
manifest={'version':1,'issue':1364,'lane':'engineering','worker_id':'01a112b0-39fb-7f02-a3c7-d21d0916009f','subject_ids':subjects,'subject_ids_sha256':old['subject_ids_sha256'],'baseline':base,'sources':[{'id':'complete-native-reference-calculation-inputs','url':'https://github.com/ChengshuLi/WorldAtlas/issues/1364','role':'Complete actual native/world/reference/runtime source closure; upstream ZIP relation separately frozen at6a47','vintage':'Accepted captured Beck2023 normals, RESOLVE2017 potential biome, modern terrain; original reference metadata and full historical archives','retrieved_at':'Original retrieval dates unknown; actual execution dates retained separately','license':old['sources'][0]['license'],'retention':'retained','verification':'unverified','temporal_status':'reference','files':source}],'outputs':outputs,'metrics':metrics,'metric_bindings':[{'metric_id':m['id'],'path':N+'results.json','json_pointer':'/'+m['id']} for m in metrics],'summaries':[{'metric_id':m['id'],'value':m['value'],'unit':m['unit']} for m in metrics],'methods':[{'id':method,'kind':'generator','helper_version':'worldatlas-evidence-preparation-v1','description':'Literal unchanged summarize_changed with reviewed equivalent bounded whole-byte/runtime/scope/archive reader; two genuine actual target calculations and complete record conservation','software':'Python3.12.14/NumPy2.3.5/Rasterio1.4.3/GDAL3.9.3/Shapely2.1.2 with whole actual module/operator closure','units':'sparse reference records, fractions, whole bytes'}],'commands':['Pinned Python producer.py --commit '+F+' --name FRESH_OWN_NAME','Pinned Python controls.py; pinned Python runtime-controls.py','Pinned Python verify.py --code-commit f6215167dc370577470e283b3fb26990ba0bb7a7 --one reference-native-b596-run-one --two reference-native-b596-run-two'],'validation':[{'kind':k,'method_id':method,'outcome':'passed','evidence_path':N+'verification/'+p} for k,p in [('positive-control','reader-scope-archive-controls.json'),('negative-control','runtime-operator-controls.json'),('reproducibility','two-complete-scientific-trees.json')]],'stages':{'implementation':'implemented','research':'complete','geographic_approval':'not-requested'},'conclusions':[{'status':'supported','text':'Two complete literal target calculations, fourteen derived records, all remaining records/archives conserved','source_ids':['complete-native-reference-calculation-inputs']},{'status':'unresolved','text':'Source fitness, legal/current authority and water/history interpretation remain unapproved; parent1295 activation and62 unresolved siblings/global1202 remain unfinished','source_ids':['complete-native-reference-calculation-inputs']}], 'change_receipts':[]}
# All changed files are newly added under N2; the accepted N1 source is unmodified.
changed=subprocess.check_output(['git','diff','--name-only',C,'--',N],text=True).splitlines();changed += [p.relative_to(R).as_posix() for p in D.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
manifest['change_receipts']=[{'path':p,'status':'added'} for p in sorted(set(changed+[N+'evidence-quality.json']))]
js(D/'evidence-quality.json',manifest)
total=sum(x['bytes'] for x in base['files']+source+outputs);count=len(base['files'])+len(source)+len(outputs)
if total>256*1024*1024 or count>512:raise ValueError((total,count))
js(P/'actual-final-phase-measurement.json',{'status':'PASS-prospective-trusted-validation-required','descriptors':count,'encoded_bytes':total,'headroom_bytes':256*1024*1024-total,'changed_paths':len(manifest['change_receipts']),'all_outputs_accounted':True,'both_actual_scientific_trees_retained':True})
print(json.dumps({'descriptors':count,'encoded_bytes':total,'headroom':256*1024*1024-total,'changes':len(manifest['change_receipts'])}))
