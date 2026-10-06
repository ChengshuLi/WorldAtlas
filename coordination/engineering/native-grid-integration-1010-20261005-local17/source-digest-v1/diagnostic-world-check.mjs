import fs from 'node:fs/promises';
import {gunzipSync} from 'node:zlib';
import {Worker} from 'node:worker_threads';
import {pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
import {loadOwnershipAssets} from '../../../../src/ownership-assets.js';
import {loadNativeLatitudes} from '../../../../src/native-latitudes.js';
const atlas=JSON.parse(await fs.readFile('dist/atlas-geography.json'));
const fetcher=async url=>new Response(await fs.readFile('dist/'+url.slice(2)));
const base=await loadOwnershipAssets(atlas.pixelMap,fetcher,{requireNative:true,expectedReference:atlas.reference_release});
const latitudes=await loadNativeLatitudes(atlas.pixelMap,atlas.reference_release,fetcher);
const catalogs=[];
for(const p of atlas.parts)catalogs.push(...JSON.parse(gunzipSync(await fs.readFile('dist/'+p))));
const geometries=new Map();
for(const p of atlas.geometryParts)for(const f of JSON.parse(gunzipSync(await fs.readFile('dist/'+p))))geometries.set(f.id,f.geometry);
const referenceFeatures=catalogs.map(f=>({...f,geometry:geometries.get(f.id)}));
const firstLatitude=(value,strict=false)=>{let lo=0,hi=latitudes.length;while(lo<hi){const mid=(lo+hi)>>1;if(strict?latitudes[mid]>=value:latitudes[mid]>value)lo=mid+1;else hi=mid;}return lo;};
let chosen,min=Infinity;
for(const f of referenceFeatures){
 const polygons=f.geometry.type==='Polygon'?[f.geometry.coordinates]:f.geometry.coordinates;
 let low=Infinity,high=-Infinity;
 for(const p of polygons)for(const ring of p)for(const point of ring){low=Math.min(low,point[1]);high=Math.max(high,point[1]);}
 const affected=firstLatitude(low,true)-firstLatitude(high);
 if(affected>0&&affected<min){chosen=f;min=affected;if(min===1)break;}
}
assert(chosen);
const replacement=structuredClone(chosen);
const ring=replacement.geometry.type==='Polygon'?replacement.geometry.coordinates[0]:replacement.geometry.coordinates[0][0];
ring.splice(1,0,[...ring[0]]);
const features=referenceFeatures.map(f=>f.id===chosen.id?replacement:f);
const bundled=(await fs.readdir('dist/assets')).filter(name=>/^native-context-worker-.*[.]js$/.test(name));assert.equal(bundled.length,1);
const workerPath='dist/assets/'+bundled[0];
const target=pathToFileURL(process.cwd()+'/'+workerPath).href;
const script=`const {parentPort}=require('node:worker_threads');globalThis.self={postMessage:(message,transfer)=>parentPort.postMessage({...message,diagnostic:process.memoryUsage()},transfer)};import(${JSON.stringify(target)}).then(()=>{parentPort.on('message',data=>self.onmessage({data}));parentPort.postMessage({ready:true});});`;
const started=performance.now(),worker=new Worker(script,{eval:true}),progress=[];
const output=await new Promise((resolve,reject)=>{
 worker.on('error',reject);
 worker.on('message',message=>{
  if(message.ready){worker.postMessage({type:'compile-native-context',revision:1,input:{referenceFeatures,features,base,latitudes}});return;}
  if(message.progress){progress.push({...message.progress,memory:message.diagnostic});return;}
  if(message.error){reject(Error(message.error));return;}
  resolve(message);
 });
});
const readyMs=performance.now()-started;
const diagnostics={main:process.memoryUsage(),workerAtCompletion:output.diagnostic,workerProgress:progress};
await fs.mkdir('.cache/native-context-proof',{recursive:true});
await fs.writeFile('.cache/native-context-proof/digest-memory-profile.json',JSON.stringify(diagnostics,null,2)+'\n');
await worker.terminate();
assert.deepEqual(output.grid.rows,base.rows);assert.deepEqual(output.grid.runs,base.runs);
assert.equal(output.owners.length,49625);
const byOwner=new Map(catalogs.map(f=>[f.pixelIndex,f.id]));
for(let i=0;i<output.owners.length;i++)assert.deepEqual(output.owners[i],{index:i+1,id:byOwner.get(i+1),referenceIndex:i+1});
const receipt={worker_path:workerPath,worker_bytes_sha256:(await import('node:crypto')).createHash('sha256').update(await fs.readFile(workerPath)).digest('hex'),
 scope:'Actual bundled source-native context worker on complete world inputs; source-equivalent duplicated existing vertex, no factual boundary edit or deployment',
 method:output.grid.method,locations:referenceFeatures.length,selected_location:chosen.id,affected_native_rows:min,
 accounting:output.accounting,every_output_row_and_run_word_equal_to_verified_native_base:true,
 worker_compile_ms:output.compileMs,ready_ms:readyMs,total_including_exhaustive_comparison_ms:performance.now()-started,process_maxRSS_raw:process.resourceUsage().maxRSS,progress_updates:progress.length};
receipt.compiler_source_sha256=(await import('node:crypto')).createHash('sha256').update(await fs.readFile('src/native-location-context.js')).digest('hex');
const receiptPath=process.env.ATLAS_NATIVE_CONTEXT_RECEIPT??'.cache/native-context-proof/world-check-result.json';
await fs.mkdir((await import('node:path')).dirname(receiptPath),{recursive:true});
await fs.writeFile(receiptPath,JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify(receipt));
