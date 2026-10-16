import pathlib,json,hashlib,gzip,subprocess
B=pathlib.Path(__file__).resolve().parent;D=B/'actual-selected-joint-001';P=D/'complete-output'
a=json.loads((D/'stdout.json').read_text());n=a['native'];ex=json.loads((D/'execution.json').read_text());f=json.loads((P/'derived-facts.json').read_text());pub=json.loads((P/'derived-publication.json').read_text());routes=json.loads((P/'checkpoint-routes.json').read_text());cert=json.loads(gzip.decompress((P/'derived-certificate.json.gz').read_bytes()))
sha=lambda r:hashlib.sha256(r).hexdigest()
value=lambda x:(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()
keys=json.loads((B/'exact1929-key-join.json').read_text());expected_rows=sorted({r['y'] for r in keys});bykey={(r['y'],r['x']):r for r in keys}
assert len(keys)==len(bykey)==1929 and all(r['actual_base_owner']==r['actual_effective_owner']==0 for r in keys)
assert ex['exit_code']==0 and ex['root_head_after']==ex['actual_executing_head']=='6d7f2550867f9dafaa8d497457de44c24081f7f0'
assert a['mode']=='authenticated-checkpoint-append-v1' and n['status']=='no-new-native-loss' and n['lost_or_reassigned_cells']==0 and n['intervals']==[]
assert n['affected_rows']==len(expected_rows)==1180 and n['native_row_scope']['changed_rows']==expected_rows
assert sorted(n['native_row_scope']['shared_base_reused_rows']+n['native_row_scope']['shared_base_acquired_rows'])==expected_rows
assert len(n['native_row_scope']['shared_base_acquired_rows'])==1180 and n['native_row_scope']['shared_base_reused_rows']==[]
w=n['repair_visibility']['witnesses']; assert n['repair_visibility']['new_components']==len(w)==27
assert len({r['component_id'] for r in w})==27
for r in w:assert r['previous_owner']==0 and r['candidate_owner']==bykey[(r['y'],r['x'])]['owner']
assert f['executing_commit']==ex['actual_executing_head'] and f['baseline_commit']==ex['accepted_baseline'] and f['candidate_commit']==ex['candidate']
actual_digest=subprocess.check_output(['/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node','--input-type=module','-e',"import fs from 'node:fs';import {createHash} from 'node:crypto';const a=JSON.parse(fs.readFileSync(process.argv[1]));for(const k of ['runtime','caller_runtime','execution_runtimes','execution_code_inventory'])delete a.native[k];const c=v=>Array.isArray(v)?v.map(c):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,c(v[k])])):v;process.stdout.write(createHash('sha256').update(JSON.stringify(c(a.native))+'\\n').digest('hex'));",str(D/'stdout.json')]).decode()
assert f['native_result_sha256']==actual_digest
assert f['accepted_checkpoint'] is False and f['validation_stage']=='native-passed' and f['candidate_code_executed'] is False
assert pub['accepted_checkpoint'] is False and pub['validation_stage']=='native-passed' and pub['complete'] is True
for k in ['certificate','facts','routes']:
 pin=pub[k];raw=(P/pin['path']).read_bytes();assert len(raw)==pin['bytes'] and sha(raw)==pin['sha256']
raw=gzip.decompress((P/pub['certificate']['path']).read_bytes());assert len(raw)==pub['certificate']['decoded_bytes'] and sha(raw)==pub['certificate']['decoded_sha256']
assert routes['candidate_commit']==ex['candidate'] and cert['kind']=='selected-coordinate-neighbor-certificate-v2'
assert len(cert['entries'])==49625 and len(cert['inputs'])==36
out={'executing_head':ex['actual_executing_head'],'reviewed_tree':'7bcc218864254084cf33d0eeac09264351274fec','baseline':ex['accepted_baseline'],'candidate':ex['candidate'],'exit_code':0,'elapsed_seconds':ex['elapsed_seconds'],'mode':a['mode'],'native_status':n['status'],'original_requested_keys':1929,'all_original_keys_prior_base_and_effective_owner_zero_retained':True,'current_consumer_complete_base_overlap_guard_passed':True,'exact_affected_rows':1180,'all1180_complete_shared_base_rows_actually_acquired':True,'lost_or_reassigned_cells':0,'new_component_visibility_witnesses':27,'witness_prior_owner_zero_and_candidate_owner_exact':True,'all_four_emitted_products_hash_readback_passed':True,'native_result_digest_matches_facts':True,'certificate_entries':49625,'certificate_input_roles':36,'actual_reader_inventory_counts':{k:len(v) for k,v in f['actual_reader_inventories'].items()},'route_count':len(routes['routes']),'accepted_checkpoint':False,'accepted_repair_credit':0,'source_or_qualification_replay':False,'limits':['Prior-owner-zero whole-key observations are retained from actual accepted-data lookups; current consumer independently applied cumulative patches to the same complete original base rows, refusing any additive overlap.','27 visibility witnesses are component-level visibility, not a substitute for the 1929 exact-request/result join already independently reviewed.','Executing capability remains reviewed and unmerged; emitted native-passed candidate custody is not accepted adoption.']}
(D/'result-checks.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
