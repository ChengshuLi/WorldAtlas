from pathlib import Path
import json, subprocess
r=Path(__file__).parent;root=r.parent.parent;w=root/'.worldatlas-workspaces/8c86b01772c1c827/13630faa807843641a6abb3484134a94a87e5c38c2665c17f5c9742c84749ddf/work';base=w/'coordination/engineering/melanesia363-additive-delivery-20261010/selected-integration/selected353-compact-NCL-qualified'
node='/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
def b(v):
 script="let s='';for await(const c of process.stdin)s+=c;const cv=v=>Array.isArray(v)?v.map(cv):v&&typeof v==='object'?Object.keys(v).sort().reduce((o,k)=>(o[k]=cv(v[k]),o),Object.create(null)):v;process.stdout.write(String(Buffer.byteLength(JSON.stringify(cv(JSON.parse(s)))+'\\n')));"
 return int(subprocess.check_output([node,'--input-type=module','-e',script],input=json.dumps(v,ensure_ascii=False).encode()))
request=json.loads((base/'request.json').read_bytes());result=json.loads((base/'result.json').read_bytes());facts=json.loads((base/'facts.json').read_bytes());fixture=json.loads((root/'.cache/runtime-integration-combined18-proof-projection-20261010/actual-needed-metadata-fixtures.json').read_bytes())
keys=['authority_sha256','rule_sha256','source_scope_ids','native_proof','original_ledger','pins','original_pins'];old=[{k:p[k] for k in keys} for p in fixture['proofs']];small=[dict([(k,p[k]) for k in keys if k not in ['native_proof','original_ledger']]+[('native_proof',{k:p['native_proof'][k] for k in ['native_contract','native_patches']})]) for p in fixture['proofs']];reduction=2*(b(old)-b(small))
spec={'targetSources':request['acquisition']['target_sources'],'predecessorProof':request['acquisition']['predecessor_proof']};code_delta=2*((r/'P2-proposed.mjs').stat().st_size-(r/'P2-base.mjs').stat().st_size)
body_release=2*(b(request)+b(result))-64 # conservative framing allowance
native_peak=241778918-body_release-reduction+2*b(spec)+code_delta
saved=json.loads((root/'.cache/runtime-integration-source-grouping-20261010/actual-group041-sourcefacts.json').read_bytes())['baseline_acquisition']
# The input descriptor/phase roster shape is selected353's actual retained shape;
# all mutable byte/phase numerical values are conservatively widened to9 digits.
def wide(v):
 if isinstance(v,list):return [wide(x) for x in v]
 if isinstance(v,dict):return {k:(268435456 if k in ['bytes','decoded_bytes','complete_phase_bytes','descriptors'] and isinstance(x,int) else wide(x))for k,x in v.items()}
 return v
acquired={'base_selection':request['base_selection'],'current_targets':request['current_targets'],'current_rows':request['current_rows'],'source_inputs':request['acquisition']['source_inputs'],'acquisition':request['acquisition'],'acquisition_phases':wide(facts['acquisition_phases']),'input_inventory':wide(saved['input_inventory']),'result':result,'limits':['Actual selected before-state acquisition and exact applicability only. Original registry/source/native authority must also be authenticated by the committed reader; no activation or physical approval.','External cold operating qualification and repeated whole outputs remain mandatory before publishing a current_rebind certificate.']}
# Entire old completion phase already carries FULL selected snapshot (larger
# than the base snapshot during additive loading), runtime/code/output/8MiB.
# Charge the entire acquired graph, original selected metadata/proofs, both raw
# product reopens4x, and maximum allowed external raw/canonical buffers afresh.
selected_metadata=b(fixture['ledger'])+b(fixture['registry'])+b(small)+131072
external_caps=1048576+131072+40960+8192+1048576
post_bound=176435592+code_delta+2*b(acquired)+2*selected_metadata+4*(b(request)+b(result))+4*external_caps+262144
out={'scope':'Prospective staged-frame bound using actual retained353 products and precise5ba additive/completion scalars; no acquisition/numerical operator. Fixture phase scalar synthetic1 is discarded in early proof projection, so removal is conservative. Descriptor/phase values widened to stock9-digit ceilings.', 'actual_failed_additive_phase':241778918,'actual_completion_phase':176435592,'child_cap':234734255,'actual_overrun':7044663,'request_canonical_bytes':b(request),'result_canonical_bytes':b(result),'released_doubled_product_metadata_lower_bound':body_release,'acquisition_spec_bytes':b(spec),'retained_original_proofs_before_bytes':b(old),'retained_original_proofs_after_bytes':b(small),'released_doubled_original_proof_metadata_lower_bound':reduction,'changed_execution_bytes':code_delta,'staged_native_window_upper_bound':native_peak,'staged_native_window_margin':234734255-native_peak,'conservative_acquired_graph_bytes':b(acquired),'conservative_selected_metadata_bytes':selected_metadata,'external_raw_caps_bytes':external_caps,'reopened_phase_upper_bound':post_bound,'reopened_phase_margin':234734255-post_bound,'scope_notes':['All current/historical method identities, whole input hashes, source/native primitive checks, native contract and unchanged verifyCurrentRebindProducts remain mandatory.','Early body phase cannot increase: result body/decode admission is deferred. Before/acquisition/after maxima are retained explicitly; new phase never hides a completed peak.','4x product pre-read reservations cover encoded+parsed/canonical/expected-result scratch, in addition to entire live acquired graph and complete base snapshot.','Actual RSS/heap/operating fit remains pending genuine changed qualification.']}
(r/'acquisition-spec-retained.json').write_text(json.dumps(spec,indent=2)+'\n')
(r/'projected-actual-25-proof-metadata.json').write_text(json.dumps(small,indent=2)+'\n')
(r/'reopened-acquired-shape-upper-bound.json').write_text(json.dumps(acquired,indent=2)+'\n')
(r/'conservative-accounting.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
