import test from 'node:test';import assert from 'node:assert/strict';
import {bindPublishedActivation,selectPublishedActivation} from './bind-published-activation.mjs';
import {valueBytes,valueSha} from '../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const pin=(path,body)=>({commit:'1'.repeat(40),path,mode:'100644',git_blob_oid:'2'.repeat(40),bytes:valueBytes(body).length,sha256:valueSha(body)});
function fixture(){
  const roles=['base_manifest','owner_roster','ledger','patch'];
  const assets=Object.fromEntries(roles.map(role=>[role,pin('owned/'+role+'.json',{role})]));
  const base_reference={id:'base',footprints_sha256:'3'.repeat(64),hierarchy_sha256:'4'.repeat(64)};
  const envelope={version:2,kind:'retained-native-base-plus-delta-v2',base_reference,
    effective_reference:{...base_reference,id:'effective',footprints_sha256:'5'.repeat(64)},
    ...Object.fromEntries(roles.map(role=>[role,{path:'additive-repairs/'+role+'.json',bytes:assets[role].bytes,sha256:assets[role].sha256}]))};
  Object.assign(assets.owner_roster,{decoded_bytes:123,decoded_sha256:'9'.repeat(64)});
  Object.assign(envelope.owner_roster,{path:'additive-repairs/owner_roster.json.gz',encoding:'gzip',decoded_bytes:123,decoded_sha256:'9'.repeat(64)});
  const registry={version:1,kind:'retained-rule-authority-registry-v1',entries:[]};
  return {baseSelection:{version:1,sha256:assets.base_manifest.sha256},envelope,registry,
    envelopePin:pin('owned/envelope.json',envelope),registryPin:pin('owned/registry.json',registry),assets};
}
test('synthetic publication metadata preserves existing six-key sidecar and eight-key runtime contract',()=>{
  const input=fixture(),sidecar=bindPublishedActivation(input);
  assert.equal(Object.keys(sidecar).length,6);assert.equal(Object.keys(input.envelope).length,8);
  assert.deepEqual(sidecar.logical_asset_map,input.assets);assert.deepEqual(sidecar.base_selection,input.baseSelection);
  const selected=selectPublishedActivation(input.baseSelection,pin('owned/sidecar.json',sidecar));
  assert.deepEqual(selected.additive_release,{path:'owned/sidecar.json',bytes:valueBytes(sidecar).length,sha256:valueSha(sidecar)});
});
test('actual metadata binding rejects missing/foreign outputs and invalid custody without selecting',()=>{
  const mutations=[v=>delete v.assets.patch,v=>v.assets.patch.sha256='6'.repeat(64),
    v=>v.envelopePin.bytes++,v=>v.registryPin.sha256='7'.repeat(64),v=>v.assets.patch.path='../escape',
    v=>v.assets.patch.mode='120000',v=>v.assets.patch.decoded_bytes=33554433,
    v=>v.envelope.version=1,v=>v.baseSelection.sha256='8'.repeat(64)];
  for(const mutate of mutations){const input=fixture();mutate(input);assert.throws(()=>bindPublishedActivation(input));}
  const input=fixture(),sidecar=bindPublishedActivation(input),p=pin('owned/sidecar.json',sidecar);
  assert.throws(()=>selectPublishedActivation(input.baseSelection,{...p,decoded_bytes:123,decoded_sha256:'1'.repeat(64)}));
});
