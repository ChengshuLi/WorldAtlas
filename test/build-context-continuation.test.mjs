import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {foldCoverageContinuation,FIXED_MIDDLE_GRID_SHA} from '../coordination/engineering/eastern-two-gap-repair-native-20261007/chained-context.mjs';
import {validateGeometryMigrations} from '../scripts/prepare-geographic-release.mjs';
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
  const out=foldCoverageContinuation(source,args),restored=structuredClone(out);delete restored.ownership_binding;
  for(const key of ['release_id','footprints_sha256','canonical_grid_sha256'])restored[key]=source[key];
  assert.deepEqual(restored,source);assert.equal(out.ownership_binding.previous_associations.length,1);assert.equal(out.ownership_binding.previous_associations[0].geometry_migration.predecessor_release_id,releases[0].id);assert.equal(out.ownership_binding.geometry_migration.successor_release_id,releases[2].id);
  for(const bad of [steps.slice(1),[...steps].reverse(),[steps[0],steps[0]],[steps[0],{...steps[1],predecessorRelease:{...releases[1],id:'foreign'}}],[{...steps[0],selectedGridSha256:'0'.repeat(64)},steps[1]],[steps[0],{...steps[1],originalGrid:{...grids[1],size:grids[1].size+1}}]])assert.throws(()=>foldCoverageContinuation(source,{...args,steps:bad}));
  assert.throws(()=>foldCoverageContinuation(source,{...args,steps:steps.map(s=>({...s,geometryValidation:structuredClone(s.geometryValidation)}))}),/complete geometry migration validation/);
  assert.throws(()=>foldCoverageContinuation({...source,sources:[]},args));
 }finally{await fs.rm(directory,{recursive:true,force:true});}
});
