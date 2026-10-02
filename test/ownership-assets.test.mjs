import {test} from 'node:test';
import assert from 'node:assert/strict';
import {gzipSync} from 'node:zlib';
import {loadOwnershipAssets} from '../src/ownership-assets.js';
test('ownership assets reconstruct out-of-order compressed chunks and reject truncation',async()=>{
 const rows=new Uint32Array([0,1,1,1]),a=new Uint32Array([0,2,7]),b=new Uint32Array([0,2,8]);
 const manifest={version:1,size:2,runWords:6,parts:[{kind:'runs',offset:3,words:3,path:'b'},{kind:'rows',offset:0,words:4,path:'rows'},{kind:'runs',offset:0,words:3,path:'a'}]};
 const files={a,b,rows};const result=await loadOwnershipAssets(manifest,async url=>new Response(gzipSync(files[url.slice(2)])));
 assert.deepEqual(result.rows,rows);assert.deepEqual(result.runs,new Uint32Array([...a,...b]));
 await assert.rejects(loadOwnershipAssets(manifest,async()=>new Response(new Uint8Array(4))),/Incomplete/);
});
