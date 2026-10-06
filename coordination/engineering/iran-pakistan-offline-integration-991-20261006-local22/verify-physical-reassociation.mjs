// Exercise the real retained physical classifier against the repaired release.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import assert from 'node:assert/strict';
import {validateGeometryMigrations} from '../../../scripts/prepare-geographic-release.mjs';
import {rebindCoverageManifest} from '../../../scripts/rebind-coverage-manifest.mjs';
import {loadCoverageClassification} from '../../../src/coverage-classification.js';
import {committedPreparationFiles,requirePlainExecution,candidateBudget} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
requirePlainExecution();
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const output=path.resolve(root,process.argv[2]??'');
if(!output.startsWith(path.join(root,prefix)+path.sep)||fs.existsSync(output))throw Error('Fresh owned output required');
const head=execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
const baseline='d0cc67eac85038159f88a673acbc39b77ab7461d';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const code=committedPreparationFiles(root,head,['package.json',prefix+'/verify-physical-reassociation.mjs',
 'scripts/prepare-geographic-release.mjs','scripts/check-prepared.mjs','scripts/read-geographic-release-manifest.mjs',
 'hosted/geographic-releases.js','scripts/rebind-coverage-manifest.mjs','src/coverage-classification.js',
 'src/ownership-method.js','src/ownership-codec.js','src/pixel-ownership.js','src/pixel-grid.js',
 'scripts/native-ownership/native-preparation-guards.mjs']);
const inputs=[],budget=candidateBudget(code);
const read=(commit,name)=>{
 const raw=execFileSync('git',['-C',root,'show',commit+':'+name],{maxBuffer:32*1024*1024});
 const pin={commit,path:name,bytes:raw.length,sha256:sha(raw)};inputs.push(pin);budget.add(pin);return raw;
};
const json=(commit,name)=>JSON.parse(name.endsWith('.gz')?gunzipSync(read(commit,name)):read(commit,name));
const before=json(baseline,'data/world-index.json').parts.flatMap(name=>json(baseline,'data/'+name).features);
const pending=json(head,prefix+'/results-v2/summary.json');
const candidates=json(pending.candidate_geometry_commit,pending.candidate_geometry_file.path);
const after=before.map(feature=>candidates[feature.id]?{...feature,geometry:candidates[feature.id]}:feature);
const releaseIndex=json(head,prefix+'/successor-release-v1/releases-v7-gzip.json.gz');
const predecessor=releaseIndex.releases.at(-2),release=releaseIndex.releases.at(-1);
for(const name of ['index.json','migration-receipt.json']){
 const file=prefix+'/release-proof-v3/'+name,raw=read(head,file);
 if(!raw.equals(fs.readFileSync(path.join(root,file))))throw Error('Mutable migration proof');
}
const geometryValidation=validateGeometryMigrations({features:after,baselineIds:before.map(f=>f.id),
 baselineFootprints:predecessor.footprints_sha256,manifestFiles:[path.join(root,prefix,'release-proof-v3/index.json')]});
const originalBytes=read(baseline,'data/canonical-grid/manifest.json'),selectedBytes=read(head,prefix+'/native-selected-v1/manifest.json');
const manifest=json(baseline,'data/coverage-classification/manifest.json');
const rebound=rebindCoverageManifest(manifest,{originalGrid:JSON.parse(originalBytes),originalGridSha256:sha(originalBytes),
 selectedGrid:JSON.parse(selectedBytes),selectedGridSha256:sha(selectedBytes),release,predecessorRelease:predecessor,geometryValidation});
const {ownership_binding,...original}=structuredClone(rebound);
original.release_id=manifest.release_id;original.footprints_sha256=manifest.footprints_sha256;original.canonical_grid_sha256=manifest.canonical_grid_sha256;
assert.deepEqual(original,manifest);
const assets=new Map(manifest.parts.map(part=>[part.path,read(baseline,'data/'+part.path)]));
const fetcher=async url=>new Response(assets.get(url.replace(/^\.\//,'')));
const expected={...rebound};
const decoded=await loadCoverageClassification(rebound,expected,fetcher);
const controls=[];
await assert.rejects(()=>loadCoverageClassification({...rebound,footprints_sha256:'0'.repeat(64)},expected,fetcher));controls.push('stale-footprint');
await assert.rejects(()=>loadCoverageClassification({...rebound,release_id:predecessor.id},expected,fetcher));controls.push('stale-release');
const damaged=manifest.parts[0].path;
await assert.rejects(()=>loadCoverageClassification(rebound,expected,async url=>{
 const name=url.replace(/^\.\//,''),raw=Buffer.from(assets.get(name));if(name===damaged)raw[raw.length-1]^=1;return new Response(raw);
}));controls.push('damaged-original-physical-bytes');
const report={version:1,execution_commit:head,executed_sources:code,inputs,predecessor_release_id:predecessor.id,
 successor_release_id:release.id,complete_geometry_reconstruction:before.length,changed_ids:[...geometryValidation.changedIds].sort(),
 physical_parts:assets.size,checked_rows:decoded.grid.size,checked_runs:decoded.grid.runs.length/2,
 physical_rows_sha256:sha(Buffer.from(decoded.grid.rows.buffer)),physical_runs_sha256:sha(Buffer.from(decoded.grid.runs.buffer)),
 original_physical_fields_preserved:true,classification_recomputed:false,physical_water_reinterpreted:false,
 controls,ownership_binding,historical_claims_transferred:false,installed:false,published:false,budget:budget.snapshot()};
fs.mkdirSync(output);
for(const [name,value] of [['manifest.json',rebound],['verification.json',report]]){
 const raw=Buffer.from(JSON.stringify(value)+'\n');budget.add({bytes:raw.length});fs.writeFileSync(path.join(output,name),raw,{flag:'wx'});
}
console.log(JSON.stringify({physical_parts:assets.size,rows:decoded.grid.size,controls:controls.length,installed:false}));
