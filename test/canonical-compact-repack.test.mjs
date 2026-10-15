import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {packOwnership,pickOwnership,ownershipRun,samplePackedOwnership} from '../src/pixel-ownership.js';
import {unshuffleOwnershipBytes,decodeOwnershipVarints} from '../src/ownership-codec.js';

function readPublished(){
 const manifest=JSON.parse(fs.readFileSync('dist/client/atlas-geography.json')).pixelMap;
 const grid={...manifest,rows:new Uint32Array(manifest.size*2),runs:new Uint32Array(manifest.runWords)};
 for(const part of [...manifest.parts.filter(p=>p.kind==='rows'),...manifest.parts.filter(p=>p.kind==='runs')]){const raw=gunzipSync(fs.readFileSync('dist/client/'+part.path)),words=part.encoding==='byte-shuffle'?unshuffleOwnershipBytes(raw,part.words):part.encoding==='row-varint'?decodeOwnershipVarints(raw,{rows:grid.rows,offset:part.offset,words:part.words,coordinateBits:manifest.coordinateBits,size:manifest.size}):new Uint32Array(raw.buffer,raw.byteOffset,raw.byteLength/4);grid[part.kind].set(words,part.offset);}
 return grid;
}
test('legacy run storage uses four Uint32 words and compact storage uses two',()=>{
 const rows=[Uint32Array.of(0,1,1,3,4,7),new Uint32Array(),Uint32Array.of(1,4,65537),new Uint32Array()];
 const legacy=packOwnership({size:4,rows},{version:1}),compact=packOwnership({size:4,rows});
 assert.deepEqual(legacy.rows,Uint32Array.of(0,2,2,0,2,1,3,0));
 assert.deepEqual(legacy.runs,Uint32Array.of(0,1,1,0,3,4,7,0,1,4,65537,0));
 assert.deepEqual(compact.rows,legacy.rows);
 assert.equal(legacy.runs.byteLength,3*4*Uint32Array.BYTES_PER_ELEMENT);
 assert.equal(compact.runs.byteLength,legacy.runs.byteLength/2);
 for(let i=0;i<3;i++)assert.deepEqual(ownershipRun(compact,i),ownershipRun(legacy,i));
});
test('every published canonical run survives compact packing, including its boundary cells and gaps',()=>{
 if(!fs.existsSync('dist/client/atlas-geography.json'))return;
 const old=readPublished(),rows=Array.from({length:old.size},(_,y)=>{
  const row=new Uint32Array(old.rows[y*2+1]*3);
  for(let k=0;k<row.length/3;k++){const r=ownershipRun(old,old.rows[y*2]+k);row.set([r.start,r.end,r.id],k*3);}
  return row;
 }),compact=packOwnership({size:old.size,rows}),baselineRuns=old.runs.length/(old.version===2?2:4);
 assert.deepEqual(compact.rows,old.rows);
 let cells=0;
 for(let y=0;y<old.size;y++)for(let k=0;k<old.rows[y*2+1];k++){
  const i=old.rows[y*2]+k,r=ownershipRun(old,i);assert.deepEqual(ownershipRun(compact,i),r);
  for(const x of [r.start-1,r.start,r.end-1,r.end]){assert.equal(pickOwnership(compact,x,y),pickOwnership(old,x,y));cells++;}
 }
 assert.equal(compact.runs.byteLength,baselineRuns*2*Uint32Array.BYTES_PER_ELEMENT);
 assert.deepEqual(samplePackedOwnership(compact,{x:-2,y:-2,width:129,height:131,stride:257}),samplePackedOwnership(old,{x:-2,y:-2,width:129,height:131,stride:257}));
 // The v1 layout is checked above; do not allocate a second complete grid just to count its bytes.
 console.log(JSON.stringify({baselineRuns,boundaryAndGapCells:cells,legacyLayoutBytes:old.rows.byteLength+baselineRuns*4*Uint32Array.BYTES_PER_ELEMENT,compactBytes:compact.rows.byteLength+compact.runs.byteLength}));
});
