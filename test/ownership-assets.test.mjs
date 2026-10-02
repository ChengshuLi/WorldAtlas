import {test} from 'node:test';
import assert from 'node:assert/strict';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {loadOwnershipAssets} from '../src/ownership-assets.js';
test('ownership assets reconstruct out-of-order compressed chunks and reject truncation',async()=>{
 const rows=new Uint32Array([0,1,1,1]),a=new Uint32Array([0,2,7,0]),b=new Uint32Array([0,2,8,0]);
 const manifest={version:1,size:2,runWords:8,parts:[{kind:'runs',offset:4,words:4,path:'b'},{kind:'rows',offset:0,words:4,path:'rows'},{kind:'runs',offset:0,words:4,path:'a'}]};
 const files={a,b,rows};const result=await loadOwnershipAssets(manifest,async url=>new Response(gzipSync(Buffer.from(files[url.slice(2)].buffer))));
 assert.deepEqual(result.rows,rows);assert.deepEqual(result.runs,new Uint32Array([...a,...b]));
 await assert.rejects(loadOwnershipAssets(manifest,async()=>new Response(new Uint8Array(4))),/Incomplete/);
});
test('version-pinned ownership digests reject mixed deployments and support host-decoded gzip',async()=>{
 const digest=bytes=>createHash('sha256').update(bytes).digest('hex'),rows=Uint32Array.of(0,1,1,0),runs=Uint32Array.of(0,2,7,0),files={rows:Buffer.from(rows.buffer),runs:Buffer.from(runs.buffer)};
 const manifest={version:1,size:2,runWords:4,parts:Object.entries(files).map(([path,raw])=>({kind:path,path,offset:0,words:4,sha256:digest(gzipSync(raw)),decoded_sha256:digest(raw)}))};
 for(const alreadyDecoded of [false,true]){const result=await loadOwnershipAssets(manifest,async url=>new Response(alreadyDecoded?files[url.slice(2)]:gzipSync(files[url.slice(2)])));assert.deepEqual(result.rows,rows);assert.deepEqual(result.runs,runs);}
 const mixed=Buffer.from(files.runs);mixed.writeUInt32LE(8,8);
 await assert.rejects(loadOwnershipAssets(manifest,async url=>new Response(gzipSync(url.endsWith('runs')?mixed:files.rows))),/checksum/);
 await assert.rejects(loadOwnershipAssets(manifest,async url=>new Response(url.endsWith('runs')?mixed:files.rows)),/checksum/);
});
