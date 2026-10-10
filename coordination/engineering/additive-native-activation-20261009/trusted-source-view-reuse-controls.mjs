import assert from 'node:assert/strict';
import fs from 'node:fs';import os from 'node:os';import path from 'node:path';
import {execFileSync} from 'node:child_process';import {pathToFileURL} from 'node:url';
const root=path.resolve(process.argv[2]??process.cwd()),candidate=process.argv[3]??execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
assert.match(candidate,/^[a-f0-9]{40}$/);
const fixture=fs.mkdtempSync(path.join(os.tmpdir(),'selected-source-alias-control-'));
try{
 const helper='coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
 for(const name of ['scripts/check-effective-geographic-regression.mjs',helper,'src/ownership-codec.js']){
  let raw=fs.readFileSync(path.join(root,name));
  const original=execFileSync('git',['-C',root,'show','HEAD:'+name],{maxBuffer:33554432});assert.ok(raw.equals(original),'Control code must equal immutable HEAD');
  if(name.startsWith('scripts/'))raw=Buffer.from(raw.toString().replace('function loadBaseSelection(reader) {','export function loadBaseSelection(reader) {'));
  const target=path.join(fixture,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,raw,{flag:'wx'});
 }
 fs.writeFileSync(path.join(fixture,'package.json'),'{"type":"module"}\n',{flag:'wx'});
 const {ImmutableReader,loadBaseSelection,loadSelection,selectedGeometrySourceAlias}=await import(pathToFileURL(path.join(fixture,'scripts/check-effective-geographic-regression.mjs')));
 const {currentRebindSourceView}=await import(pathToFileURL(path.join(fixture,helper)));
const reader=new ImmutableReader(root,candidate,{runtimeBytes:0,outputBytes:0});
// Only control instrumentation exports the literal production private base frame.
const snapshot=loadBaseSelection(reader),view=snapshot.geometrySources;
assert.equal(Object.isFrozen(snapshot),false);assert.ok(Object.isFrozen(view));
const used=reader.used,metadata=reader.metadataBytes,read=reader.read;let reads=0;
reader.read=()=>{reads++;throw Error('Unexpected reopened source body');};
let negatives=0;const refuses=f=>{assert.throws(f);negatives++;};
const replace=(key,value)=>{const old=snapshot[key];snapshot[key]=value;try{refuses(()=>selectedGeometrySourceAlias(snapshot));}finally{snapshot[key]=old;}};
try{
 assert.equal(selectedGeometrySourceAlias(snapshot),view);assert.equal(currentRebindSourceView(snapshot),view);
 refuses(()=>selectedGeometrySourceAlias({...snapshot}));
 replace('geometrySources',Object.create(Object.getPrototypeOf(view)));replace('reader',{});replace('manifest',{...snapshot.manifest});replace('owners',[...snapshot.owners]);
 const oldVersion=reader.version;reader.version='0'.repeat(40);try{refuses(()=>selectedGeometrySourceAlias(snapshot));}finally{reader.version=oldVersion;}
 const id=snapshot.selection.release_id;snapshot.selection.release_id='foreign';try{refuses(()=>selectedGeometrySourceAlias(snapshot));}finally{snapshot.selection.release_id=id;}
 const override=view.bank.overrides[0];assert.ok(override);view.replacements.delete(override.logical_path);try{refuses(()=>selectedGeometrySourceAlias(snapshot));}finally{view.replacements.set(override.logical_path,override);}
 view.replacements.set(override.logical_path,{...override});try{refuses(()=>selectedGeometrySourceAlias(snapshot));}finally{view.replacements.set(override.logical_path,override);}
 assert.equal(currentRebindSourceView(snapshot),view);assert.equal(reads,0);assert.equal(reader.used,used);assert.equal(reader.metadataBytes,metadata);
}finally{reader.read=read;}
// Actual full selected-additive caller traverses the private intermediate path,
// validates current-rebind/output authority and then returns a frozen snapshot.
const fullReader=new ImmutableReader(root,candidate,{runtimeBytes:0,outputBytes:0});
const full=loadSelection(fullReader);assert.ok(Object.isFrozen(full));
assert.equal(currentRebindSourceView(full),full.geometrySources);
if(full.selection.additive_release){assert.ok(full.additive.ledger);assert.equal(full.additive.ledger.rows.length,20);assert.equal(full.additive.ledger.rows.filter(r=>r.disposition==='assigned').length,12);}
console.log(JSON.stringify({status:'PASS',private_intermediate:true,final_selected_additive:Boolean(full.additive),negative_controls:negatives,reopened_bodies:reads,intermediate_metadata_unchanged:true,components:full.additive?.ledger.rows.filter(r=>r.disposition==='assigned').length??0,max_phase_bytes:fullReader.used,limits:['Control import changes only private base-frame export; complete actual c76 operands are read by unchanged authority predicates. Runtime/output reserves are zero for semantic controls; not whole-gate or RSS qualification.']}));

}finally{fs.rmSync(fixture,{recursive:true,force:true});}
