// Exhaustive #1295 successor check using the existing original row/run consumers.
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {execFileSync} from 'node:child_process';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';import {gunzipSync} from 'node:zlib';
import {loadSuccessor,executedClosure,AFTER,BEFORE,TARGETS} from './native-producer.mjs';
import {nativeCandidateManifest} from '../../../scripts/native-ownership/native-candidate-manifest.mjs';
import {committedPreparationFiles,requirePlainExecution} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
import {nativePolygonIntervals} from '../../../src/native-grid.js';import {coverageRow} from '../../../scripts/audit-grid-intervals.mjs';import {loadOwnershipAssets} from '../../../src/ownership-assets.js';import {ownershipRun} from '../../../src/pixel-ownership.js';
const sha=b=>createHash('sha256').update(b).digest('hex');const json=x=>Buffer.from(JSON.stringify(x)+'\n');
function ordinary(root,p){assert(typeof p==='string'&&p.split('/').every(x=>x&&x!=='.'&&x!=='..')&&!path.isAbsolute(p));const file=path.join(root,p);assert(fs.realpathSync(file)===file&&fs.lstatSync(file).isFile());assert(fs.statSync(file).size<=32*1024*1024);return fs.readFileSync(file);}
function inventory(root,prefix=''){return fs.readdirSync(path.join(root,prefix),{withFileTypes:true}).flatMap(e=>{const p=prefix?prefix+'/'+e.name:e.name;if(e.isDirectory())return inventory(root,p);assert(e.isFile());if(p==='progress.json')return [];const raw=ordinary(root,p);return [{path:p,bytes:raw.length,sha256:sha(raw)}];}).sort((a,b)=>a.path.localeCompare(b.path));}
function codeClosure(repo,head){const names=new Set(['package.json']);function visit(p){if(names.has(p))return;names.add(p);for(const m of fs.readFileSync(path.join(repo,p),'utf8').matchAll(/(?:from\s*|import\s*)['"]([^'"]+)['"]/g))if(m[1].startsWith('.'))visit(path.posix.normalize(path.posix.join(path.posix.dirname(p),m[1])));}visit(path.relative(repo,fileURLToPath(import.meta.url)));return committedPreparationFiles(repo,head,[...names].sort());}
export async function verify(one,two,output){
 requirePlainExecution();const repo=fs.realpathSync('.'),head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),executed=codeClosure(repo,head);
 for(const root of [one,two])assert(fs.realpathSync(root)===root,'Ordinary complete run tree required');assert.notEqual(one,two);
 const first=inventory(one),second=inventory(two);assert.deepEqual(first,second,'Two complete scientific trees differ');
 for(const root of [one,two])assert.equal(JSON.parse(ordinary(root,'progress.json')).phase,'complete');
 const report=JSON.parse(gunzipSync(ordinary(one,'report.json.gz'),{maxOutputLength:32*1024*1024}));
 const capsule=JSON.parse(ordinary(one,'execution.json'));assert.equal(report.execution_commit,capsule.execution_commit);assert.deepEqual(report.executed_sources,capsule.executed_sources);
 const live=executedClosure(repo,head);for(const p of capsule.executed_sources){const current=live.find(q=>q.path===p.path);assert.deepEqual(current,p,'Executed numerical source changed since actual measurement');}
 const indexPath=capsule.ordinary_source_index.path,indexBytes=fs.readFileSync(path.join(repo,indexPath));assert.equal(indexBytes.length,capsule.ordinary_source_index.bytes);assert.equal(sha(indexBytes),capsule.ordinary_source_index.sha256);
 const sourceIndex=JSON.parse(indexBytes),storage=new Map(sourceIndex.files.map(row=>[row.original.commit+':'+row.original.path,row]));assert.deepEqual(sourceIndex.files,capsule.ordinary_sources);
 const inputs=loadSuccessor(repo,capsule.baseline_commit,{storage});assert.deepEqual(inputs.sourceFiles,capsule.source_files);assert.equal(inputs.ownerSha,capsule.owner_sha256);assert.equal(inputs.releaseId,capsule.release_id);
 const manifest=JSON.parse(ordinary(one,'manifest.json'));const expected=nativeCandidateManifest({original:inputs.manifest,originalSha256:inputs.originalCanonicalSha,baselineCommit:capsule.baseline_commit,evaluationCommit:capsule.execution_commit,releaseId:inputs.releaseId,rosterSha256:inputs.ownerSha,ownerCount:49625,latitude:{...inputs.latitude,commit:capsule.execution_commit},compiled:report.compiled});
 expected.footprints_sha256=AFTER;expected.hierarchy_sha256=inputs.predecessor.hierarchy_sha256;expected.provenance.original_source_point_sets_unchanged=false;expected.provenance.source_migration={issue:1295,proposal_commit:'b4b7db357ba92d19df513f188bbd046fe66a35e4',baseline_commit:capsule.baseline_commit,before_footprints_sha256:BEFORE,after_footprints_sha256:AFTER,changed_ids:TARGETS,history_transfer:'none',compact_context_owner_sha256:inputs.ownerSha};assert.deepEqual(manifest,expected,'Successor native convention/source/roster binding changed');
 for(const p of report.products){const raw=ordinary(one,p.path);assert.equal(raw.length,p.bytes);assert.equal(sha(raw),p.sha256);}
 const grid=await loadOwnershipAssets(manifest,async url=>{assert.match(url,/^\.\/native-v1\/ownership\/(rows|runs)-[0-9]+\.bin\.gz$/);return new Response(ordinary(one,url.slice(2)));});
 const prepared=inputs.index.map(item=>{let minLat=Infinity,maxLat=-Infinity;for(const p of item.polygons)for(const r of p)for(let k=1;k<r.length;k+=2){minLat=Math.min(minLat,r[k]);maxLat=Math.max(maxLat,r[k]);}return {...item,minLat,maxLat};});
 const counts=new Map(inputs.features.map(f=>[f.pixelIndex,0]));let checkedRows=0,checkedRuns=0,owned=0;
 for(let firstRow=0;firstRow<grid.size;firstRow+=4096){const end=Math.min(grid.size,firstRow+4096);const selected=prepared.filter(item=>item.minLat<=inputs.latitudes[firstRow]&&item.maxLat>=inputs.latitudes[end-1]);const native=nativePolygonIntervals(selected,{size:grid.size,rowStart:firstRow,rowEnd:end,latitudes:inputs.latitudes});
  for(let y=firstRow;y<end;y++){let actual=grid.rows[y*2],stop=actual+grid.rows[y*2+1],pending=null;
   const compare=segment=>{assert(actual<stop,'Missing actual ownership run');const r=ownershipRun(grid,actual);assert.equal(r.start,segment[0]);assert.equal(r.end,segment[1]);assert.equal(r.id,segment[2]);const cells=segment[1]-segment[0];counts.set(segment[2],counts.get(segment[2])+cells);owned+=cells;checkedRuns++;actual++;};
   for(const segment of coverageRow(native.rows.get(y)??[],grid.size)){const id=segment.owners[0]??0;if(!id){if(pending){compare(pending);pending=null;}continue;}if(pending&&pending[1]===segment.start&&pending[2]===id)pending[1]=segment.end;else{if(pending)compare(pending);pending=[segment.start,segment.end,id];}}
   if(pending)compare(pending);assert.equal(actual,stop,'Extra actual ownership run');checkedRows++;
  }
  console.error(JSON.stringify({completed_rows:checkedRows,checked_runs:checkedRuns}));
 }
 assert.equal(checkedRows,262166);assert.equal(checkedRuns,manifest.runWords/2);assert.equal(owned,report.compiled.owned_cells);assert.deepEqual([...counts],report.compiled.per_owner_cells);
 const result={version:1,issue:1295,status:'PASS',verification_execution_commit:head,native_measurement_execution_commit:capsule.execution_commit,baseline_commit:capsule.baseline_commit,executed_sources:executed,source_inputs:capsule,complete_two_run_products:first,
  checked_rows:checkedRows,checked_cells:grid.size**2,unchecked_cells:0,checked_runs:checkedRuns,owners:counts.size,owned_cells:owned,per_owner_cells:[...counts],footprints_sha256:AFTER,release_id:inputs.releaseId,
  limits:['Exact native rule/transport/source binding only; no independent legal, land/water or historical cause approval','Source fitness limited to the two Main-approved physical-reference additions; deployment deferred']};
 assert(!fs.existsSync(output),'Fresh verifier receipt required');fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,json(result));console.log(JSON.stringify({status:'PASS',checked_rows:checkedRows,checked_cells:grid.size**2,receipt_sha256:sha(json(result))}));return result;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){const [one,two,output]=process.argv.slice(2);await verify(path.resolve(one),path.resolve(two),path.resolve(output));}
