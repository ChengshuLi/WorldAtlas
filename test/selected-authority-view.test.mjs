import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {valueBytes,valueSha,normaliseRetainedRepairLedger} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

// Execute the literal completed helper and consumer tail with already-qualified
// frozen results. This isolates output lifetime without replaying source science.
const source=fs.readFileSync(new URL('../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs',import.meta.url),'utf8');
const slice=(start,end)=>{const a=source.indexOf(start),b=source.indexOf(end,a);assert(a>=0&&b>a);return source.slice(a,b);};
const demand=(v,m)=>{if(!v)throw Error(m);},hash=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const sha=b=>createHash('sha256').update(b).digest('hex');
const same=(a,b)=>valueBytes(a).equals(valueBytes(b));
const freeze=v=>{if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;};
const FILE=33554432,OUTPUT=4194304,version='a'.repeat(40);
const allowance={phaseBytes:256*1048576,rssBytes:2**40};
const pin=seed=>({commit:version,path:seed+'.json',mode:'100644',git_blob_oid:'b'.repeat(40),bytes:128,sha256:sha(seed)});
const rulePin=pin('rule'),bindingPin=pin('binding');
const fields={policy_id:'retained-source-literal-additions',policy_version:1,rule_preimage:rulePin,rule_sha256:rulePin.sha256,source_authority:bindingPin};
const entry={authority_sha256:valueSha(fields),...fields};
const registry={version:1,kind:'retained-rule-authority-registry-v1',entries:[entry]};
const projectAuthority=proof=>({authority_sha256:entry.authority_sha256,rule_sha256:entry.rule_sha256,source_scope_ids:proof.source_scope_ids,native_proof:proof.native_proof,original_ledger:proof.original_ledger,pins:proof.pins,original_pins:proof.original_pins});
const helperSource=slice('function completedSelectedAuthority(', '// Explicit committed data-only hook.');
const helper=read=>new Function('readRetainedRegistryAuthority',helperSource+'return completedSelectedAuthority;')(read);
let tail=slice(' const normalized=normaliseRetainedRepairLedger(named.ledger,registry),proofs=[];', 'export function selectedAdditiveRows');
tail=tail.slice(0,tail.lastIndexOf('}'));
assert(tail.includes('completedSelectedAuthority(child,entry,reader)'));
assert(tail.includes('proofs.push(proof);retained+=valueBytes(proof).length;'));
const oldTail=tail.replace('completedSelectedAuthority(child,entry,reader)','readRetainedRegistryAuthority(child,entry,reader)')
 .replace('proofs.push(proof);retained+=valueBytes(proof).length;','const view=projectAuthority(proof);proofs.push(view);retained+=valueBytes(view).length;');
const reader=phaseBytes=>new ImmutableReader('.',version,{runtimeBytes:1,executionBytes:0,metadataBytes:0,outputBytes:OUTPUT,allowance:phaseBytes?{...allowance,phaseBytes}:allowance});
function fixture(points=4){
 const ring=Array.from({length:points},(_,i)=>[i/points,i/points]);ring.push(ring[0]);
 const geometry={type:'Polygon',coordinates:[ring]};
 const original={representation:'native-cells',component_id:'source-target:fixture',target_id:'fixture',pixelIndex:1,disposition:'assigned',base_geometry:geometry,base_geometry_sha256:valueSha(geometry),native_rows:[{y:1,runs:[[0,1,1]]}],native_bounds:[-1,-1,1,1],native_cells:1,source_receipt_sha256:'c'.repeat(64)};
 const ledger={version:2,kind:'native-additive-repair-ledger-v2',authority_registry_sha256:valueSha(registry),scope_ids:[original.component_id],rows:[{...original,authority_sha256:entry.authority_sha256,rule_sha256:entry.rule_sha256}]};
 const baseReference={id:'geography:fixture',footprints_sha256:'d'.repeat(64),hierarchy_sha256:'e'.repeat(64)};
 const effectiveReference={...baseReference};
 const manifest={size:262166,coordinateBits:18,method:'native-linear-evenodd-first-owner-v1',native_latitudes:{sha256:'f'.repeat(64)},hierarchy_sha256:baseReference.hierarchy_sha256,original_assets:{bounds:{sha256:'0'.repeat(64)}}};
 const patch={version:2,kind:'unassigned-native-cells-v1',base_reference:baseReference,effective_reference:effectiveReference,authority_registry_sha256:valueSha(registry),ledger_sha256:valueSha(ledger),rows:original.native_rows};
 const envelope={version:2,base_reference:baseReference,effective_reference:effectiveReference};
 const proof=freeze({version:1,kind:'authenticated-registry-source-custody-v1',authority_sha256:entry.authority_sha256,rule_sha256:entry.rule_sha256,policy_id:entry.policy_id,policy_version:1,source_scope_ids:[original.component_id],source_rows:[original],original_ledger:{version:2,kind:'native-additive-repair-ledger-v2',scope_ids:[original.component_id],rows:null},native_proof:{native_contract:manifest,native_patches:[{base_reference:baseReference,rows:patch.rows}]},pins:[rulePin,bindingPin],original_pins:{source_evidence:pin('evidence'),native_patch:pin('patch')},limitations:['Full authenticated scientific result presentation.']});
 const aliased=freeze({...proof,original_ledger:{...proof.original_ledger,rows:proof.source_rows}});
 const f={proof:aliased,original,ledger,patch,envelope,manifest,baseReference};refresh(f);return f;
}
function refresh(f){
 f.patch.ledger_sha256=valueSha(f.ledger);
 f.envelope.effective_reference.footprints_sha256=valueSha({domain:'worldatlas-effective-native-footprints:v2',base_reference:f.baseReference,authority_registry_sha256:valueSha(registry),ledger_sha256:valueSha(f.ledger),components:[...normaliseRetainedRepairLedger(f.ledger,registry).rows.values()]});
}
function run(f,{legacy=false,phaseBytes,rebind=false}={}){
 const r=reader(phaseBytes),selection={release_id:f.baseReference.id},snapshot={reader:r};let calls=0;
 const readRetainedRegistryAuthority=(child,actualEntry,observer)=>{calls++;assert(child instanceof ImmutableReader);assert.equal(actualEntry,entry);assert.equal(observer,r);return f.proof;};
 const dependencies={demand,hash,valueBytes,valueSha,same,freeze,normaliseRetainedRepairLedger,ImmutableReader,projectAuthority,readRetainedRegistryAuthority,
  completedSelectedAuthority:helper(readRetainedRegistryAuthority),selectedAdditions:new WeakMap(),
  reclaimCompletedRebindFrame:()=>{assert(rebind);},
  readCurrentRebindCustody:(_reader,_pin,args)=>{assert(rebind);assert.deepEqual(args.registry.entries,[]);assert.deepEqual(args.originalRows,[]);assert.deepEqual(args.originalPatches,[]);return {current_targets:[]};}};
 const locals={snapshot,reader:r,selection,manifest:f.manifest,owners:[{id:'fixture'}],registry,baseSelection:selection,sidecar:{logical_asset_map:{ledger:{sha256:valueSha(f.ledger)}}},admitted:[],named:{ledger:f.ledger,patch:f.patch},envelope:f.envelope,resolver:{release:f.baseReference}};
 const result=new Function(...Object.keys(dependencies),...Object.keys(locals),legacy?oldTail:tail)(...Object.values(dependencies),...Object.values(locals));
 assert.equal(calls,1);return result;
}

test('completed selected authority forwards custody and preserves a mutable exact projection of frozen graphs',()=>{
 const f=fixture(),child=reader(),observer={};let calls=0;
 const view=helper((actualReader,actualEntry,actualObserver)=>{calls++;assert.equal(actualReader,child);assert.equal(actualEntry,entry);assert.equal(actualObserver,observer);return f.proof;})(child,entry,observer);
 assert.equal(calls,1);assert.deepEqual(view,projectAuthority(f.proof));assert.equal(Object.isFrozen(view),false);
 for(const name of ['source_scope_ids','native_proof','original_ledger','pins','original_pins']){assert.equal(view[name],f.proof[name]);assert(Object.isFrozen(view[name]));}
 delete view.original_ledger;view.native_proof={...view.native_proof};
 assert.equal(f.proof.source_rows,f.proof.original_ledger.rows);assert(Object.hasOwn(f.proof,'original_ledger'));
});

test('actual selected consumer accepts only the bounded projected output and preserves final bytes and identities',()=>{
 const small=fixture();assert(valueBytes(run(small)).equals(valueBytes(run(small,{legacy:true}))));
 const large=fixture(70000);assert(valueBytes(large.proof).length>OUTPUT);assert(valueBytes(projectAuthority(large.proof)).length<OUTPUT);
 assert.throws(()=>run(large,{legacy:true}),/Complete detached authority view exceeds prospective output reserve/);
 const selected=run(large);assert.equal(selected.assigned_cells,1);
 assert.equal(selected.ledger.rows[0].base_geometry,large.original.base_geometry);
 assert.equal(selected.normalized_rows[0].base_geometry,large.original.base_geometry);
 assert.equal(selected.normalized_rows[0].native_rows[0].runs[0],large.original.native_rows[0].runs[0]);
 assert.equal(selected.authority_proofs[0].pins,large.proof.pins);assert.equal(selected.authority_proofs[0].source_scope_ids,large.proof.source_scope_ids);
 assert.throws(()=>{selected.normalized_rows[0].base_geometry.coordinates[0][0][0]=9;},TypeError);
 const oversized=fixture(115000);assert(valueBytes(projectAuthority(oversized.proof)).length>OUTPUT);
 assert.throws(()=>run(oversized),/Complete detached authority view exceeds prospective output reserve/);
 assert.throws(()=>run(large,{phaseBytes:OUTPUT+100}),/Installed runtime\/metadata exceeds complete phase/);
});

test('current rebind still mutates its wrapper and selected source, patch and scope controls still refuse',()=>{
 const f=fixture();f.ledger.current_rebind=pin('rebind');f.ledger.current_targets=[];refresh(f);
 assert(valueBytes(run(f,{rebind:true})).equals(valueBytes(run(f,{legacy:true,rebind:true}))));
 const row=fixture();row.ledger.rows[0].source_receipt_sha256='9'.repeat(64);assert.throws(()=>run(row),/rebinds/);
 const patch=fixture();patch.patch.rows=[{y:1,runs:[[1,2,1]]}];assert.throws(()=>run(patch),/omits\/invents/);
 const missing=fixture();missing.ledger.rows=[];missing.ledger.scope_ids=[];assert.throws(()=>run(missing),/omits\/invents|scope/);
});

test('unchanged whole-input reader charges parsed plus encoded bodies and refuses before opening over-phase data',()=>{
 const pinCheck=new Function('demand','hash','FILE',slice('function pinCheck(p){','// Bounds derive')+'return pinCheck;')(demand,hash,FILE);
 const makeRead=new Function('reader','pinCheck','demand','gunzipSync','sha',slice(' const read=p=>{\n  pinCheck(p);',' const evidence=JSON.parse(read(binding.source_evidence))')+'return read;');
 const encoded=Buffer.from(JSON.stringify({targets:[{base_geometry:fixture(70000).original.base_geometry}]}));
 const inputPin={...pin('evidence'),bytes:encoded.length,sha256:sha(encoded)};
 function acquisition(phaseBytes){
  const r=reader(phaseBytes);let bodyReads=0;r.descriptor=()=>({...inputPin});
  r.git=(...args)=>{if(args[0]==='cat-file'&&args[1]==='blob'){bodyReads++;return encoded;}return Buffer.alloc(0);};
  return {r,get bodyReads(){return bodyReads;},read:makeRead(r,pinCheck,demand,gunzipSync,sha)};
 }
 const acquired=acquisition(),before=acquired.r.used;assert.equal(acquired.read(inputPin),encoded);assert.equal(acquired.r.used-before,7*encoded.length);assert.equal(acquired.bodyReads,1);
 const refused=acquisition(OUTPUT+6*encoded.length);assert.throws(()=>refused.read(inputPin),/Source-target complete parsed acquisition exceeds phase|Complete phase exceeds prospective cap/);assert.equal(refused.bodyReads,0);
});
