import assert from 'node:assert/strict';
import {ImmutableReader,loadBaseSelection,loadSelection,selectedGeometrySourceAlias} from './control-import/scripts/check-effective-geographic-regression.mjs';
import {currentRebindSourceView} from './control-import/coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const root='/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/8c86b01772c1c827/cf40d9d594efb1cc1cb6158e6803afea25baf2d6058a2324fe45a0b23a03fb41/work';
const candidate='c76a77a850f0d88f99529096c2a29ae65fd22720';
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
const full=loadSelection(fullReader);assert.ok(full.additive&&Object.isFrozen(full));
assert.equal(currentRebindSourceView(full),full.geometrySources);
assert.ok(full.additive.ledger);assert.equal(full.additive.ledger.rows.length,12);
console.log(JSON.stringify({status:'PASS',private_intermediate:true,final_selected_additive:true,negative_controls:negatives,reopened_bodies:reads,intermediate_metadata_unchanged:true,components:12,max_phase_bytes:fullReader.used,limits:['Control import changes only private base-frame export; complete actual c76 operands are read by unchanged authority predicates. Runtime/output reserves are zero for semantic controls; not whole-gate or RSS qualification.']}));
