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
test('every published canonical run survives compact packing, including its boundary cells and gaps',()=>{
 if(!fs.existsSync('dist/client/atlas-geography.json'))return;
 const old=readPublished(),rows=Array.from({length:old.size},(_,y)=>{
  const row=new Uint32Array(old.rows[y*2+1]*3);
  for(let k=0;k<row.length/3;k++){const r=ownershipRun(old,old.rows[y*2]+k);row.set([r.start,r.end,r.id],k*3);}
  return row;
 }),compact=packOwnership({size:old.size,rows}),legacy=packOwnership({size:old.size,rows},{version:1});
 assert.deepEqual(compact.rows,old.rows);
 let cells=0;
 for(let y=0;y<old.size;y++)for(let k=0;k<old.rows[y*2+1];k++){
  const i=old.rows[y*2]+k,r=ownershipRun(old,i);assert.deepEqual(ownershipRun(compact,i),r);
  for(const x of [r.start-1,r.start,r.end-1,r.end]){assert.equal(pickOwnership(compact,x,y),pickOwnership(old,x,y));cells++;}
 }
 assert.equal(compact.runs.byteLength,legacy.runs.byteLength/2);
 assert.deepEqual(samplePackedOwnership(compact,{x:-2,y:-2,width:129,height:131,stride:257}),samplePackedOwnership(old,{x:-2,y:-2,width:129,height:131,stride:257}));
 console.log(JSON.stringify({baselineRuns:old.runs.length/(old.version===2?2:4),boundaryAndGapCells:cells,legacyBytes:legacy.rows.byteLength+legacy.runs.byteLength,compactBytes:compact.rows.byteLength+compact.runs.byteLength}));
});
