import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {authenticateOriginalValidator,validateBuildContextVintage,requireCurrentMigrationSource} from '../coordination/engineering/subject-descriptor-decode-20261007/context-vintage-dispatch.mjs';
import {validateContextMigration} from '../scripts/native-ownership/validate-context-migration.mjs';
import {requireValidatedGeometryMigrations} from '../scripts/prepare-geographic-release.mjs';
import {footprintHash} from '../scripts/check-prepared.mjs';
import {loadPackageInputs,containsPackagePath} from '../scripts/package-inputs.mjs';
const ns='coordination/engineering/subject-descriptor-decode-20261007';
const capture=path.resolve(ns+'/legacy-context-v1');
const digest=b=>createHash('sha256').update(b).digest('hex');
async function fixture(action){
 await fs.mkdir('.cache',{recursive:true});const root=await fs.mkdtemp('.cache/context-vintage-control-');
 try{await fs.cp(capture,path.join(root,'code'),{recursive:true});await action(path.resolve(root),path.resolve(root,'code'));}
 finally{await fs.rm(root,{recursive:true,force:true});}
}
test('complete literal original validator imports authenticate and execute their own realm',async()=>{
 const result=await authenticateOriginalValidator();assert.equal(result.index.files.length,17);
 assert.equal(typeof result.validate,'function');assert.equal(result.index.source_commit,'83bed8c4c49e8f54077bb4abf0f32d41d0992f81');
 const inputs=loadPackageInputs();assert(containsPackagePath(inputs.inputs,ns+'/context-vintage-dispatch.mjs'));
 for(const pin of result.index.files)assert(containsPackagePath(inputs.inputs,ns+'/legacy-context-v1/'+pin.path));
});
test('changed captured implementation and coherently rebound inventory reject before import',async()=>fixture(async(_,code)=>{
 const name=path.join(code,'scripts/evidence-quality.mjs');await fs.appendFile(name,'\n// changed original code\n');
 await assert.rejects(authenticateOriginalValidator({snapshotRoot:code}),/code bytes or mode differ/);
 const index=JSON.parse(await fs.readFile(path.join(code,'index.json'))),raw=await fs.readFile(name);
 Object.assign(index.files.find(p=>p.path==='scripts/evidence-quality.mjs'),{sha256:digest(raw),bytes:raw.length});
 await fs.writeFile(path.join(code,'index.json'),JSON.stringify(index));
 await assert.rejects(authenticateOriginalValidator({snapshotRoot:code}),/inventory bytes differ/);
}));
test('missing original package/module and changed ordinary mode reject',async()=>fixture(async(_,code)=>{
 await fs.rm(path.join(code,'package.json'));
 await assert.rejects(authenticateOriginalValidator({snapshotRoot:code}),/ENOENT/);
 await fs.copyFile(path.join(capture,'package.json'),path.join(code,'package.json'));
 await fs.chmod(path.join(code,'scripts/evidence-quality.mjs'),0o755);
 await assert.rejects(authenticateOriginalValidator({snapshotRoot:code}),/mode differ/);
 await fs.chmod(path.join(code,'scripts/evidence-quality.mjs'),0o644);
 await fs.rm(path.join(code,'src/native-grid.js'));
 await assert.rejects(authenticateOriginalValidator({snapshotRoot:code}),/ENOENT/);
}));
test('leaf and ancestor symlinks never become captured original code',async()=>fixture(async(root,code)=>{
 await fs.symlink(code,path.join(root,'alias'));
 await assert.rejects(authenticateOriginalValidator({snapshotRoot:path.join(root,'alias')}),/symlink ancestors/);
 await fs.rm(path.join(code,'scripts/evidence-quality.mjs'));
 await fs.symlink(path.join(capture,'scripts/evidence-quality.mjs'),path.join(code,'scripts/evidence-quality.mjs'));
 await assert.rejects(authenticateOriginalValidator({snapshotRoot:code}),/symlinks/);
}));
test('actual original-stage entry rejects changed stage and reaches authenticated data guard',async()=>{
 const raw=await fs.readFile(ns+'/fixtures/original-context-stage.json');
 const {index}=await authenticateOriginalValidator();
 assert.equal(raw.length,index.stage_bytes);assert.equal(digest(raw),index.stage_sha256);
 const stage=JSON.parse(raw);stage.execution_commit='0'.repeat(40);
 await assert.rejects(validateBuildContextVintage({readFile:()=>Buffer.from(JSON.stringify(stage))}),/Original context stage bytes differ/);
 let actualOriginalDataRead=false;
 await assert.rejects(validateBuildContextVintage({readFile:name=>{
  if(name==='data/native-context-migration/manifest.json')return raw;
  if(name===stage.original_stage.path){actualOriginalDataRead=true;return Buffer.from('{}');}
  throw Error('Unexpected real-stage fixture read: '+name);
 }}),/Context migration input bytes differ/);
 assert(actualOriginalDataRead,'actual captured stage must reach original data authentication');
});
test('genuine old realm proof rejects in current consumer; same validated operands mint current proof',async()=>{
 await authenticateOriginalValidator();
 const old=await import(pathToFileURL(path.join(capture,'scripts/native-ownership/validate-context-migration.mjs')).href);
 const feature=(id,left,right,index)=>({id,pixelIndex:index,properties:{parent_id:'province'},geometry:{type:'Polygon',coordinates:[[[left,0],[right,0],[right,1],[left,1],[left,0]]]}});
 const before=[feature('a',0,1,1),feature('b',2,3,2)],after=[feature('a',0,1.25,1),before[1]];
 const oldHash=footprintHash(before),newHash=footprintHash(after),hierarchy='1'.repeat(64);
 const predecessor={id:'synthetic:before',footprints_sha256:oldHash,hierarchy_sha256:hierarchy};
 const successor={id:'synthetic:after',footprints_sha256:newHash,hierarchy_sha256:hierarchy};
 const archived={id:'a',geometry:before[0].geometry,properties:{id:'a',parent_id:'province'}};
 const receipt={version:1,geometry_stage_validated:true,historical_claims_transferred:false,before_footprints_sha256:oldHash,after_footprints_sha256:newHash,
  changed_ids:['a'],removed_ids:[],added_ids:[],reused_ids:['b'],archives:[{id:'a',feature:archived}],
  relationships:[{kind:'source-backed-shared-seam-reference',before_ids:['a'],after_ids:['a'],history_transfer:false}],
  source_evidence:[{url:'https://example.com/synthetic-control-only',source_sha256:'2'.repeat(64)}]};
 await fixture(async root=>{
  const raw=Buffer.from(JSON.stringify(receipt));await fs.writeFile(path.join(root,'receipt.json'),raw);
  await fs.writeFile(path.join(root,'index.json'),JSON.stringify({before_footprints_sha256:oldHash,after_footprints_sha256:newHash,history_transfer:false,files:{'migration-receipt.json':{archive_path:'receipt.json',sha256:digest(raw)}}}));
  successor.metadata={predecessor_release_id:predecessor.id,geometry_migration:{sha256:digest(raw),history_transfer:'none'}};
  const operands={original:before,migrated:after,candidates:{a:after[0].geometry},predecessorRelease:predecessor,release:successor,migrationManifestFile:path.join(root,'index.json')};
  const historical=old.validateContextMigration(operands);
  assert.throws(()=>requireValidatedGeometryMigrations(historical.geometryValidation),/complete geometry migration validation/);
  const current=validateContextMigration(operands);assert.equal(requireValidatedGeometryMigrations(current.geometryValidation),current.geometryValidation);
  const stageBinding={geometry_manifest:{sha256:digest(await fs.readFile(path.join(root,'index.json')))}};
  assert.equal(requireCurrentMigrationSource(current,stageBinding),current);
  assert.throws(()=>requireCurrentMigrationSource(historical,stageBinding),/complete geometry migration validation/);
  // A formatting-only index mutation keeps the migration receipt equal, but
  // must not evade the original stage's exact index-body source binding.
  const originalIndex=await fs.readFile(path.join(root,'index.json'));
  await fs.writeFile(path.join(root,'index.json'),Buffer.concat([originalIndex,Buffer.from('\n')]));
  const indexChanged=validateContextMigration(operands);
  const {geometryValidation:ignored,...sameReceipt}=indexChanged;
  const {geometryValidation:unused,...originalReceipt}=current;
  assert.deepEqual(sameReceipt,originalReceipt);
  assert.throws(()=>requireCurrentMigrationSource(indexChanged,stageBinding),/index differs/);
  await fs.writeFile(path.join(root,'index.json'),originalIndex);
  const {geometryValidation:a,...ar}=historical,{geometryValidation:b,...br}=current;assert.deepEqual(ar,br);
  assert.throws(()=>validateContextMigration({...operands,migrated:[after[0],feature('b',2,3.1,2)]}),/footprints|unchanged field/);
  assert.throws(()=>validateContextMigration({...operands,predecessorRelease:{...predecessor,id:'foreign'}}),/predecessor/);
 });
});
