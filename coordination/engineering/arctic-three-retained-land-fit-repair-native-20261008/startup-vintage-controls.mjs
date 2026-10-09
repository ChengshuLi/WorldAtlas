// Real stock packer -> emitted descriptor -> stock browser loader boundary.
// Tiny run stream, complete normative native row-table shape; no grid compiler.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {packageVersionedStartupOwnership} from './startup-vintage.mjs';
import {packageStartupOwnership} from '../../../scripts/package-startup-ownership.mjs';
import {shuffleOwnershipBytes} from '../../../src/ownership-codec.js';
import {loadOwnershipAssets} from '../../../src/ownership-assets.js';
const sha=b=>createHash('sha256').update(b).digest('hex');
const root=await fs.mkdtemp(path.join(await fs.realpath(os.tmpdir()),'atlas-1520-startup-'));
try{
 const source=path.join(root,'source'),dest=path.join(root,'dist');await fs.mkdir(path.join(source,'native-v1/ownership'),{recursive:true});
 const rows=new Uint32Array(262166*2);rows.set([0,1,1,1]);for(let y=2;y<262166;y++)rows[y*2]=2;
 const runs=Uint32Array.of(0,(1<<19)|7,0,(1<<19)|8);
 const manifest={version:2,size:262166,coordinateBits:19,runWords:4,method:'native-linear-evenodd-first-owner-v1',footprints_sha256:'1'.repeat(64),hierarchy_sha256:'2'.repeat(64),geographic_release:'geography:review:fixture',native_latitudes:{root:'repository',role:'immutable-normative-rule-input',path:'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz',commit:'3'.repeat(40),sha256:'4'.repeat(64),decoded_sha256:'66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23',decoded_bytes:262166*8,bytes:100},parts:[]};
 const originals=new Map();for(const [kind,words] of [['rows',rows],['runs',runs]]){const relative=`native-v1/ownership/${kind}-0.bin.gz`,bytes=gzipSync(shuffleOwnershipBytes(words));await fs.writeFile(path.join(source,relative),bytes);originals.set(relative,bytes);manifest.parts.push({kind,path:relative,offset:0,words:words.length,encoding:'byte-shuffle',sha256:sha(bytes),decoded_sha256:sha(Buffer.from(words.buffer))});}
 const manifestPath=path.join(source,'manifest.json'),manifestBytes=Buffer.from(JSON.stringify(manifest));await fs.writeFile(manifestPath,manifestBytes);const manifestSha=sha(manifestBytes),args={manifest,manifestPath,manifestSha,source,destination:dest};
 const old=await packageStartupOwnership({manifest,source,destination:dest});const oldBytes=await fs.readFile(path.join(dest,old.outputs[0].path));
 const oldRuns=runs.slice();runs[3]=(1<<19)|9;
 const newSource=path.join(root,'successor');await fs.cp(source,newSource,{recursive:true});
 const newRun=gzipSync(shuffleOwnershipBytes(runs));manifest.parts[1]={...manifest.parts[1],sha256:sha(newRun),decoded_sha256:sha(Buffer.from(runs.buffer))};
 await fs.writeFile(path.join(newSource,manifest.parts[1].path),newRun);const newManifestRaw=Buffer.from(JSON.stringify(manifest));await fs.writeFile(path.join(newSource,'manifest.json'),newManifestRaw);
 const nextArgs={...args,source:newSource,manifestPath:path.join(newSource,'manifest.json'),manifestSha:sha(newManifestRaw)};
 const versioned=await packageVersionedStartupOwnership(nextArgs);assert.equal(versioned.pixelMap.parts[0].path,manifest.parts[0].path);assert.deepEqual(versioned.pixelMap.parts[0],manifest.parts[0]);
 await fs.mkdir(path.dirname(path.join(dest,manifest.parts[0].path)),{recursive:true});await fs.writeFile(path.join(dest,manifest.parts[0].path),originals.get(manifest.parts[0].path));
 const urls=[];const fetcher=async url=>{urls.push(url);try{return new Response(await fs.readFile(path.join(dest,url.slice(2))));}catch{return new Response('',{status:404});}};
 const loaded=await loadOwnershipAssets(versioned.pixelMap,fetcher);assert.deepEqual(loaded.rows,rows);assert.deepEqual(loaded.runs,runs);assert(urls.some(url=>url===`./ownership-vintages/${nextArgs.manifestSha}/native-v1/ownership/startup-runs-0.bin.gz`));
 assert.deepEqual(await fs.readFile(path.join(dest,old.outputs[0].path)),oldBytes);for(const [relative,bytes] of originals)assert.deepEqual(await fs.readFile(path.join(source,relative)),bytes);
 const oldLoaded=await loadOwnershipAssets(old.pixelMap,fetcher);assert.deepEqual(oldLoaded.runs,oldRuns);
 assert.notDeepEqual(await fs.readFile(path.join(dest,versioned.outputs[0].path)),oldBytes);
 const expectRejected=async fn=>{await assert.rejects(fn);};
 await expectRejected(()=>packageVersionedStartupOwnership({...args,destination:path.join(root,'fresh'),manifestSha:'5'.repeat(64)}));
 await expectRejected(()=>packageVersionedStartupOwnership({...args,destination:dest+'/../escape'}));
 await expectRejected(()=>packageVersionedStartupOwnership({...args,manifestSha:'../escape'}));
 await expectRejected(()=>packageVersionedStartupOwnership({...args,destination:path.join(root,'missing'),manifestPath:path.join(root,'absent')}));
 await expectRejected(()=>packageVersionedStartupOwnership(nextArgs));
 const missing={...versioned.pixelMap,parts:versioned.pixelMap.parts.map(p=>p.kind==='runs'?{...p,path:p.path+'-missing'}:p)};await expectRejected(()=>loadOwnershipAssets(missing,fetcher));
 const changed={...versioned.pixelMap,parts:versioned.pixelMap.parts.map(p=>p.kind==='runs'?{...p,sha256:'6'.repeat(64)}:p)};await expectRejected(()=>loadOwnershipAssets(changed,fetcher));
 await fs.symlink(dest,path.join(root,'linked'));await expectRejected(()=>packageVersionedStartupOwnership({...args,destination:path.join(root,'linked')}));
 console.log(JSON.stringify({positive:2,negative:8,stock_packer_browser_inverse:true,full_native_row_shape:262166,old_urls_and_bytes_preserved:true,limits:'Tiny two-run fixture, not full current bank or normal release qualification'}));
}finally{await fs.rm(root,{recursive:true,force:true});}
