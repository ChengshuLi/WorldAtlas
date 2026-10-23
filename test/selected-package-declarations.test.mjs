import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {admitSelectedPackageDeclarations} from '../scripts/package-inputs.mjs';
const digest=(b,kind='sha256')=>createHash(kind).update(b).digest('hex');
const pin=(path,body)=>({path,bytes:body.length,mode:'100644',git_blob_oid:digest(Buffer.concat([Buffer.from(`blob ${body.length}\0`),body]),'sha1'),sha256:digest(body)});
function fixture(prefix='old') {
 const leaf=n=>pin(`coordination/engineering/${prefix}/${n}.json`,Buffer.from(n));
 const raw=Buffer.from(JSON.stringify({version:2,kind:'retained-native-additive-selection-v2',runtime_envelope:leaf('envelope'),logical_asset_map:{ledger:leaf('ledger'),patch:leaf('patch')}}));
 const hook=pin(`coordination/engineering/${prefix}/sidecar.json`,raw),selection={additive_release:hook};
 const roles=[hook,leaf('envelope'),leaf('ledger'),leaf('patch')];
 const definition={version:1,inputs:['.github/package-inputs.json','scripts/',...roles.map(p=>p.path)],optional_inputs:[roles[1].path],verification_paths:['scripts/check.mjs'],generated_outputs:['dist/']};
 return {selection,raw,roles,definition};
}
function transition(a,b) {
 const current={...a.definition,inputs:['.github/package-inputs.json','scripts/',...b.roles.map(p=>p.path)],optional_inputs:[]};
 const options={selection:a.selection,priorSidecarRaw:a.raw,priorEntry:n=>a.roles.find(p=>p.path===n),currentPaths:b.roles.map(p=>p.path)};
 return {current,options,run:(c=current,o=options)=>admitSelectedPackageDeclarations(a.definition,c,o)};
}
test('one authenticated rule admits repeated cumulative replacement and append-only unchanged policy',()=>{
 const a=fixture(),b=fixture('second'),c=fixture('third'),first=transition(a,b);
 assert.deepEqual(first.run().removed,a.roles.map(p=>p.path));
 assert.equal(first.run(first.current,{...first.options,priorEntry:n=>{const p=first.options.priorEntry(n);return {path:n,mode:p.mode,oid:p.git_blob_oid}}}).removed.length,4);
 const next=transition({...b,definition:first.current},c);assert.equal(next.run().removed.length,4);
 assert.deepEqual(admitSelectedPackageDeclarations(first.current,first.current).additions,[]);
});
test('unrelated removals, directory narrowing, policy/order/optional changes refuse',()=>{
 const a=fixture(),t=transition(a,fixture('next'));
 for(const change of [c=>c.inputs.splice(1,1),c=>c.inputs.splice(1,1,'scripts/check.mjs'),c=>c.inputs.reverse(),c=>c.verification_paths.push('extra.json'),c=>c.generated_outputs=[],c=>c.optional_inputs.push('scripts/')]) {
  const c=structuredClone(t.current);change(c);assert.throws(()=>t.run(c));
 }
});
test('retirement binds exact old selector/body and every removed mode/OID/size; shared current roles refuse',()=>{
 const a=fixture(),t=transition(a,fixture('next'));
 assert.throws(()=>t.run(t.current,{...t.options,priorSidecarRaw:Buffer.from('{}')}));
 assert.throws(()=>t.run(t.current,{...t.options,selection:{additive_release:{...a.selection.additive_release,sha256:'0'.repeat(64)}}}));
 for(const field of ['mode','git_blob_oid','bytes'])assert.throws(()=>t.run(t.current,{...t.options,priorEntry:n=>({...t.options.priorEntry(n),[field]:field==='bytes'?999:'0'})}));
 for(const value of [null,undefined,NaN,Infinity,-1]) for(const field of ['bytes','size'])
  assert.throws(()=>t.run(t.current,{...t.options,priorEntry:n=>({...t.options.priorEntry(n),[field]:value})}));
 assert.throws(()=>t.run(t.current,{...t.options,currentPaths:[a.roles[2].path]}),/remains a current/);
});
