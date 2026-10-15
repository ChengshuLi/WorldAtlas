import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {foldCoverageContinuation,FIXED_MIDDLE_GRID_SHA,shareUnchangedContextGeometry,selectBuildContextValidator,replayOriginalV1} from '../scripts/native-ownership/chained-build-context.mjs';
test('build context dispatch preserves original realm and exact two-target continuation',async()=>{
 const legacyToken={},currentToken={};let legacyCalls=0,currentCalls=0;
 const legacy=async()=>{legacyCalls++;return legacyToken;},current=async()=>{currentCalls++;return currentToken;};
 const select=stage=>selectBuildContextValidator(stage,{legacy,current});
 assert.equal(select(null),legacy);assert.equal(select({version:1}),legacy);
 assert.equal(await select({version:1})(),legacyToken);
 assert.equal(await select({version:2,kind:'retained-identity-context-continuation-v2',issue:1295})(),currentToken);
 for(const stage of [{version:2,kind:'retained-identity-context-continuation-v2',issue:1296},{version:2,kind:'other',issue:1295},{version:2,kind:'retained-identity-context-continuation-v2'}])assert.throws(()=>select(stage));
 assert.equal(legacyCalls,1);assert.equal(currentCalls,1);
 assert.throws(()=>selectBuildContextValidator({version:2,kind:'retained-identity-context-continuation-v2',issue:1295},{legacy,current:{}}));
});
import {validateGeometryMigrations,requireValidatedGeometryMigrations} from '../scripts/prepare-geographic-release.mjs';
import vm from 'node:vm';
const builder=await fs.readFile('scripts/build-static-inner.mjs','utf8');
const releaseSource=builder.match(/function releaseBuildContextBaselines\(context\) \{[\s\S]*?\n}/)[0];
const realm=vm.createContext({requireValidatedGeometryMigrations,Number,Set,Array,Error});
vm.runInContext(releaseSource+';globalThis.release=releaseBuildContextBaselines;',realm);
import {footprintHash} from '../scripts/check-prepared.mjs';
const digest=b=>createHash('sha256').update(b).digest('hex');
const physical=JSON.parse(await fs.readFile('data/coverage-classification/manifest.json'));
const legacy=JSON.parse(await fs.readFile('data/canonical-grid/manifest.json'));
const native=JSON.parse(await fs.readFile('data/native-ownership/repaired-v7/manifest.json'));
const feature=(right)=>({id:'a',properties:{id:'a',parent_id:'province'},geometry:{type:'Polygon',coordinates:[[[0,0],[right,0],[right,1],[0,1],[0,0]]]}});

test('strict ordered two-step fold retains all physical fields and both actual migration bindings',async()=>{
 await fs.mkdir('.cache',{recursive:true});const directory=await fs.mkdtemp('.cache/two-stage-coverage-');
 try{
  const features=[feature(1),feature(1.25),feature(1.5)];
  const releases=features.map((f,i)=>({version:6+i,id:i===0?physical.release_id:'geography:fixture-'+(7+i-1),footprints_sha256:footprintHash([f]),hierarchy_sha256:legacy.hierarchy_sha256}));
  const grids=[{...legacy,footprints_sha256:releases[0].footprints_sha256},...releases.slice(1).map(r=>({...native,footprints_sha256:r.footprints_sha256,geographic_release:r.id}))];
  const gridHashes=[physical.canonical_grid_sha256,FIXED_MIDDLE_GRID_SHA,'9'.repeat(64)],steps=[];
  for(let i=0;i<2;i++){
   const receipt={version:1,geometry_stage_validated:true,historical_claims_transferred:false,before_footprints_sha256:releases[i].footprints_sha256,after_footprints_sha256:releases[i+1].footprints_sha256,changed_ids:['a'],removed_ids:[],added_ids:[],reused_ids:[],archives:[{id:'a',feature:features[i]}],relationships:[{kind:'source-backed-shared-seam-reference',before_ids:['a'],after_ids:['a'],history_transfer:false}],source_evidence:[{url:'https://example.com/synthetic-only',source_sha256:'1'.repeat(64)}]};
   const raw=Buffer.from(JSON.stringify(receipt)),base=directory+'/'+i;await fs.mkdir(base);await fs.writeFile(base+'/migration-receipt.json',raw);await fs.writeFile(base+'/index.json',JSON.stringify({before_footprints_sha256:releases[i].footprints_sha256,after_footprints_sha256:releases[i+1].footprints_sha256,history_transfer:false,files:{'migration-receipt.json':{sha256:digest(raw)}}}));
   releases[i+1].metadata={predecessor_release_id:releases[i].id,geometry_migration:{sha256:digest(raw),before_footprints_sha256:releases[i].footprints_sha256,after_footprints_sha256:releases[i+1].footprints_sha256,history_transfer:'none'}};
   const geometryValidation=validateGeometryMigrations({features:[features[i+1]],baselineIds:['a'],baselineFootprints:releases[i].footprints_sha256,manifestFiles:[base+'/index.json']});
   steps.push({originalGrid:grids[i],originalGridSha256:gridHashes[i],selectedGrid:grids[i+1],selectedGridSha256:gridHashes[i+1],predecessorRelease:releases[i],release:releases[i+1],geometryValidation});
  }
  const source={...physical,footprints_sha256:releases[0].footprints_sha256},args={originalGrid:grids[0],originalGridSha256:gridHashes[0],selectedGrid:grids[2],selectedGridSha256:gridHashes[2],release:releases[2],steps};
  const beforeRelease=JSON.stringify(foldCoverageContinuation(source,args));
  const proofsBefore=steps.map(step=>JSON.stringify({...step.geometryValidation,baselineFeatures:null}));
  assert.throws(()=>realm.release({receipt:{migration:{locations:1}},geometryValidation:structuredClone(steps[1].geometryValidation),coverageContinuation:{originalGeometryValidation:steps[0].geometryValidation}}),/complete geometry migration validation/);
  assert.throws(()=>realm.release({receipt:{migration:{locations:2}},geometryValidation:steps[1].geometryValidation,coverageContinuation:{originalGeometryValidation:steps[0].geometryValidation}}),/baseline work arrays/);
  assert(steps.every(step=>step.geometryValidation.baselineFeatures.length===1));
  const released=realm.release({receipt:{migration:{locations:1}},geometryValidation:steps[1].geometryValidation,coverageContinuation:{originalGeometryValidation:steps[0].geometryValidation}});
  assert.equal(released.released_baseline_feature_references,2);
  for(let i=0;i<2;i++){requireValidatedGeometryMigrations(steps[i].geometryValidation);assert.equal(steps[i].geometryValidation.baselineFeatures,null);assert.equal(JSON.stringify(steps[i].geometryValidation),proofsBefore[i]);}
  assert.equal(JSON.stringify(foldCoverageContinuation(source,args)),beforeRelease,'Both real branded coverage folds are byte-identical after releasing unused work arrays');
  const pair=steps[1].geometryValidation.pairs[0],previous=pair.history_transfer;pair.history_transfer='forged';assert.throws(()=>foldCoverageContinuation(source,args),/complete geometry migration validation/);pair.history_transfer=previous;
  const out=foldCoverageContinuation(source,args),restored=structuredClone(out);delete restored.ownership_binding;
  for(const key of ['release_id','footprints_sha256','canonical_grid_sha256'])restored[key]=source[key];
  assert.deepEqual(restored,source);assert.equal(out.ownership_binding.previous_associations.length,1);assert.equal(out.ownership_binding.previous_associations[0].geometry_migration.predecessor_release_id,releases[0].id);assert.equal(out.ownership_binding.geometry_migration.successor_release_id,releases[2].id);
  for(const bad of [steps.slice(1),[...steps].reverse(),[steps[0],steps[0]],[steps[0],{...steps[1],predecessorRelease:{...releases[1],id:'foreign'}}],[{...steps[0],selectedGridSha256:'0'.repeat(64)},steps[1]],[steps[0],{...steps[1],originalGrid:{...grids[1],size:grids[1].size+1}}]])assert.throws(()=>foldCoverageContinuation(source,{...args,steps:bad}));
  assert.throws(()=>foldCoverageContinuation(source,{...args,steps:steps.map(s=>({...s,geometryValidation:structuredClone(s.geometryValidation)}))}),/complete geometry migration validation/);
  assert.throws(()=>foldCoverageContinuation({...source,sources:[]},args));
 }finally{await fs.rm(directory,{recursive:true,force:true});}
});

test('memory sharing preserves exact geometry values/order and refuses signed-zero or changed inputs',()=>{
 const reference=[feature(1)],rows=structuredClone(reference),before=JSON.stringify(rows);
 assert.equal(shareUnchangedContextGeometry(rows,reference),1);assert.equal(rows[0].geometry,reference[0].geometry);assert.equal(JSON.stringify(rows),before);
 const changed=[feature(2)];assert.equal(shareUnchangedContextGeometry(changed,reference),0);
 const zero=structuredClone(reference);zero[0].geometry.coordinates[0][0][0]=-0;assert.equal(shareUnchangedContextGeometry(zero,reference),0);assert(Object.is(zero[0].geometry.coordinates[0][0][0],-0));
 const reordered=structuredClone(reference);reordered[0].geometry={coordinates:reordered[0].geometry.coordinates,type:'Polygon'};assert.equal(shareUnchangedContextGeometry(reordered,reference),0);
});


import os from 'node:os';
import path from 'node:path';
test('original replay awaits real child, retains binary output and rejects actual failures',async()=>{
 const directory=await fs.realpath(await fs.mkdtemp(path.join(os.tmpdir(),'1295-replay-control-')));
 const runner=path.join(directory,'runner.mjs'),outerArgs=[...process.execArgv];
 try{
  await fs.writeFile(runner,`import fs from 'node:fs';fs.writeFileSync('actual-child-argv.json',JSON.stringify({execArgv:process.execArgv,argv:process.argv,cwd:process.cwd(),stage:process.env.WORLDATLAS_PACKAGE_STAGE}));if(process.argv.length!==2||JSON.stringify(process.execArgv)!==JSON.stringify([])||process.cwd()!==process.env.WORLDATLAS_PACKAGE_STAGE)process.exit(19);setTimeout(()=>process.stdout.write(Buffer.from([0,255,195,169])),80);`);
  let ticks=0;const timer=setInterval(()=>ticks++,5);timer.unref();let complete=false;
  const pending=replayOriginalV1(runner,directory).then(raw=>{complete=true;return raw;});
  await new Promise(resolve=>setTimeout(resolve,20));assert.equal(complete,false);
  const raw=await pending;clearInterval(timer);assert(ticks>0);assert(Buffer.isBuffer(raw));assert.deepEqual(raw,Buffer.from([0,255,195,169]));
  const actualLaunch=JSON.parse(await fs.readFile(path.join(directory,'actual-child-argv.json')));assert.deepEqual(actualLaunch.execArgv,[]);assert.deepEqual(actualLaunch.argv,[process.execPath,runner]);assert.equal(actualLaunch.cwd,directory);assert.equal(actualLaunch.stage,directory);assert.deepEqual(process.execArgv,outerArgs,'Replay does not change outer runtime arguments');
  await fs.writeFile(runner,`process.stderr.write('literal failure');process.exit(23);`);
  await assert.rejects(replayOriginalV1(runner,directory),error=>error.code===23&&Buffer.isBuffer(error.stderr)&&error.stderr.toString()==='literal failure');
  await fs.writeFile(runner,`process.kill(process.pid,'SIGTERM');`);
  await assert.rejects(replayOriginalV1(runner,directory),error=>error.signal==='SIGTERM');
  await assert.rejects(replayOriginalV1(path.join(directory,'missing.mjs'),directory));
  await fs.writeFile(runner,`process.stdout.write(Buffer.alloc(32*1024*1024+1,65));`);
  const completeOutput=await replayOriginalV1(runner,directory);assert.equal(completeOutput.length,32*1024*1024+1);assert(completeOutput.every(byte=>byte===65));
 }finally{await fs.rm(directory,{recursive:true,force:true});}
});

import {gzipSync} from 'node:zlib';
import {acquireOriginalContextPair,constructAliasedContextChunk} from '../coordination/engineering/eastern-two-gap-repair-native-20261007/context-record-alias.mjs';
test('whole original context aliases authenticate both complete directions and reject incomplete or changed identities',async()=>{
 const root=await fs.realpath(await fs.mkdtemp(path.join(os.tmpdir(),'context-alias-custody-')));
 try{
  const rows=[{id:'a',pixelIndex:1,geometry:{type:'Point',coordinates:[0,0]}},{id:'b',pixelIndex:2,geometry:{type:'Point',coordinates:[1,1]}}];
  const beforeRaw=Buffer.from(JSON.stringify(rows)+'\n'),next=structuredClone(rows);next[0].geometry.coordinates[0]=0.25;
  const afterRaw=Buffer.from(JSON.stringify(next)+'\n');
  const write=async(name,raw)=>{const wire=gzipSync(raw),file=path.join(root,name);await fs.writeFile(file,wire);return {file,pin:{bytes:wire.length,sha256:digest(wire),decoded_bytes:raw.length,decoded_sha256:digest(raw),mode:'100644'}};};
  const before=await write('before.gz',beforeRaw),after=await write('after.gz',afterRaw);
  const args={beforeFile:before.file,beforePin:before.pin,afterFile:after.file,afterPin:after.pin};
  const pair=acquireOriginalContextPair(args);
  assert.deepEqual(constructAliasedContextChunk(beforeRaw,pair).rows,next);
  assert.deepEqual(constructAliasedContextChunk(afterRaw,pair,{baseSide:1}).rows,rows);
  assert.throws(()=>constructAliasedContextChunk(beforeRaw,structuredClone(pair)),/live authenticated/);
  for(const values of [next.slice(1),[...next].reverse(),[{...next[0],id:'foreign'},next[1]],[next[0],{...next[1],id:'a'}]]){
   const bad=await write('bad.gz',Buffer.from(JSON.stringify(values)));assert.throws(()=>acquireOriginalContextPair({...args,afterFile:bad.file,afterPin:bad.pin}));
  }
  const truncated=await write('truncated.gz',afterRaw.subarray(0,afterRaw.length-2));
  assert.throws(()=>acquireOriginalContextPair({...args,afterFile:truncated.file,afterPin:truncated.pin}));
  await fs.symlink(after.file,path.join(root,'link.gz'));assert.throws(()=>acquireOriginalContextPair({...args,afterFile:path.join(root,'link.gz')}));
  pair.changes[0].after[0]^=1;assert.throws(()=>constructAliasedContextChunk(beforeRaw,pair),/live authenticated/);
 }finally{await fs.rm(root,{recursive:true,force:true});}
});
test('build-context v2 dispatch reaches the actual lineage validator with plain current-execution arguments',async()=>{
 const root=await fs.realpath(await fs.mkdtemp(path.join(os.tmpdir(),'context-v2-dispatch-')));
 try{
  const moduleUrl=new URL('../scripts/native-ownership/validate-build-context-stage.mjs',import.meta.url).href,runner=path.join(root,'dispatch.mjs');
  await fs.writeFile(runner,`import assert from 'node:assert/strict';import {validateBuildContextStage} from ${JSON.stringify(moduleUrl)};await assert.rejects(validateBuildContextStage({readFile:()=>Buffer.from(JSON.stringify({version:2,issue:1296}))}),error=>error.code==='ERR_ASSERTION'&&error.actual===1296&&error.expected===1295);process.stdout.write('verified');`);
  assert.equal((await replayOriginalV1(runner,root)).toString(),'verified');
 }finally{await fs.rm(root,{recursive:true,force:true});}
});

import syncFs from 'node:fs';
import {gunzipSync} from 'node:zlib';
test('production changed-context getter authenticates its actual complete immutable transport',async()=>{
 const source=await fs.readFile('scripts/canonical-restoration.mjs','utf8');
 const prefix=source.slice(0,source.indexOf('function copy(')).replace(/^import .*;\n/gm,'').replace(/^export .*;\n/gm,'');
 const first=source.indexOf('export function restoredContextPatch('),last=source.indexOf('function checkoutMetadata',first),getter=source.slice(first,last).replace('export function','function');
 const root=syncFs.realpathSync(process.cwd());
 // Supply only the existing prior-restoration brand; run the literal production
 // getter, ordinary readers, hashes and pinned original transport on disk.
 const get=new Function('fs','path','assert','createHash','gunzipSync','restored',prefix+'\n'+getter+'\nreturn restoredContextPatch;')(syncFs,path,assert,createHash,gunzipSync,new Map([[root,{}]]));
 const patch=get(root);assert.equal(patch.raw.length,patch.pin.bytes);assert.equal(digest(patch.raw),patch.pin.sha256);
 assert(patch.source_parts.length>0);assert.equal(JSON.parse(gunzipSync(patch.raw)).kind,'whole-original-encoded-context-byte-delta-v1');
});

import {authenticateArcticContinuationInputs} from '../coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/arctic-context.mjs';
import {authenticateReleaseCatalogueMetadata} from '../coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/arctic-package-preflight.mjs';
test('arctic continuation inventory preserves exact stage and complete ordinary pin identities',async()=>{
 const root=await fs.realpath(await fs.mkdtemp(path.join(os.tmpdir(),'arctic-input-custody-')));
 try{
  const raw=Buffer.from('complete ordinary input'),file=path.join(root,'input.json');await fs.writeFile(file,raw);
  const pin={path:'input.json',bytes:raw.length,sha256:digest(raw)};
  const stage={version:3,issue:1520,kind:'arctic-retained-land-context-continuation-v3',subjects:['atlas:physical:CAN-15:NWT','atlas:physical:CAN-25:NUN'],before_footprints_sha256:'b9a3c8bf375217dba3a50d1a022ec7e4ac6c6f1cdedff22845da953c805b7433',after_footprints_sha256:'2deeff1457ff9238cb3dbe599e9a858dcce29d8ba88e2a66abe2785ddec0aed9'};
  for(const name of ['priorStage','registry','priorRegistry','changedRows','contextIndex','nativeManifest','priorNativeManifest','nativeComparison','geometryManifest','migrationReceipt'])stage[name]={...pin};
  const check=value=>authenticateArcticContinuationInputs({root,stage:value});
  assert.deepEqual([...check(stage).pins.values()],[pin]);
  for(const change of [v=>v.issue=1521,v=>v.subjects.reverse(),v=>delete v.nativeManifest,v=>v.changedRows.bytes++,v=>v.changedRows.sha256='bad']){
   const wrong=structuredClone(stage);change(wrong);assert.throws(()=>check(wrong));
  }
  await fs.rename(file,path.join(root,'original.json'));await fs.symlink(path.join(root,'original.json'),file);assert.throws(()=>check(stage));
 }finally{await fs.rm(root,{recursive:true,force:true});}
});
test('arctic release catalogue authenticates complete gzip bytes and decoded identity',async()=>{
 const root=await fs.realpath(await fs.mkdtemp(path.join(os.tmpdir(),'arctic-catalogue-custody-')));
 try{
  const body=Buffer.from(JSON.stringify({version:1,products:[{path:'actual-original-product'}]})),raw=gzipSync(body),file=path.join(root,'catalogue.json.gz');await fs.writeFile(file,raw);
  const pin={path:'catalogue.json.gz',bytes:raw.length,sha256:digest(raw),decoded_bytes:body.length,decoded_sha256:digest(body)};
  assert.deepEqual(authenticateReleaseCatalogueMetadata(root,pin),JSON.parse(body));
  for(const change of [v=>v.bytes++,v=>v.sha256='0'.repeat(64),v=>v.decoded_bytes--,v=>v.decoded_sha256='0'.repeat(64)]){
   const wrong={...pin};change(wrong);assert.throws(()=>authenticateReleaseCatalogueMetadata(root,wrong));
  }
  await fs.writeFile(file,raw.subarray(0,raw.length-1));assert.throws(()=>authenticateReleaseCatalogueMetadata(root,pin));
 }finally{await fs.rm(root,{recursive:true,force:true});}
});
