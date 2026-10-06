import test from 'node:test';import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';import {gzipSync} from 'node:zlib';
import {compileNativeOwnership} from '../scripts/native-ownership/compile-native-ownership.mjs';
import {shuffleOwnershipBytes} from '../src/ownership-codec.js';
import {loadOwnershipAssets} from '../src/ownership-assets.js';
import {pickOwnership,samplePackedOwnership,ownershipRun} from '../src/pixel-ownership.js';
const sha=b=>createHash('sha256').update(b).digest('hex');
const ring=p=>Float64Array.from(p.flat());
const rect=(w,s,e,n)=>ring([[w,s],[e,s],[e,n],[w,n],[w,s]]);
const item=(index,...polygons)=>({index,polygons,minLat:80,maxLat:81});
const table=size=>Float64Array.from({length:size},(_,y)=>size/2-y-.5);
// Independent exact rational orientation, not scanline intersections or ceil.
function oracle(index,x,latitude,size){
  const den=2n*BigInt(size),lon=(2n*BigInt(x)+1n)*360n-180n*den;
  const lat=BigInt(latitude*2)*BigInt(size);
  for(const f of index)for(const polygon of f.polygons){
    let crossings=0;
    for(const r of polygon)for(let k=0;k<r.length-2;k+=2){
      const [x1,y1,x2,y2]=r.slice(k,k+4);
      if(!(Math.min(y1,y2)<latitude&&latitude<=Math.max(y1,y2)))continue;
      const turn=(lon-BigInt(x1)*den)*BigInt(y2-y1)-(lat-BigInt(y1)*den)*BigInt(x2-x1);
      if(y2>y1?turn>=0n:turn<=0n)crossings++;
    }
    if(crossings%2)return f.index;
  }
  return 0;
}
async function build(index,size,opts={}){
  const assets=new Map(),seen=[];
  const metadata=await compileNativeOwnership(index,{size,latitudes:table(size),...opts,
    writePart:async(part,words)=>{
      assert.equal(words.length,part.words);seen.push(words);
      const path=`ownership/${part.kind}-${part.offset}.bin.gz`,bytes=gzipSync(shuffleOwnershipBytes(words),{level:9});
      const raw=Buffer.alloc(words.length*4);words.forEach((value,i)=>raw.writeUInt32LE(value,i*4));
      const descriptor={...part,path,encoding:'byte-shuffle',sha256:sha(bytes),decoded_sha256:sha(raw)};
      assets.set('./'+path,bytes);return descriptor;
    }});
  // Tiny synthetic domains exercise packing/native mathematics, not the
  // authenticated canonical reference rule. Keep the full compiler metadata;
  // pass only the generic packing contract to the actual decoder here.
  const {method,...packing}=metadata;
  const grid=await loadOwnershipAssets(packing,async url=>new Response(assets.get(url)));
  return {metadata,grid,assets,seen};
}
const fixture=()=>[
  item(1,[rect(-100,-14,40,15),rect(-40,-5,10,5)],[rect(100,-2,130,3)]),
  item(2,[ring([[0,-12],[75,13],[120,-12],[0,-12]])]),
  item(3,[rect(-175,-15,-150,15)])
];
test('streamed candidate round-trips actual codecs and every cell matches independent native oracle',async()=>{
  const index=fixture(),before=JSON.stringify(index),size=32,latitudes=table(size);
  const result=await build(index,size,{rowBlock:7,partWords:8});
  assert.equal(JSON.stringify(index),before,'original rings/indices/bounds remain unchanged');
  let cells=0;
  for(let y=0;y<size;y++){
    let previousEnd=0,previousId=0;
    for(let n=result.grid.rows[y*2];n<result.grid.rows[y*2]+result.grid.rows[y*2+1];n++){
      const r=ownershipRun(result.grid,n);
      assert.ok(r.start>=previousEnd&&r.end>r.start);
      assert.ok(r.start!==previousEnd||r.id!==previousId,'equal-owner touching runs are merged');
      previousEnd=r.end;previousId=r.id;cells+=r.end-r.start;
    }
    const sampled=samplePackedOwnership(result.grid,{x:0,y,width:size,height:1});
    for(let x=0;x<size;x++){
      const expected=oracle(index,x,latitudes[y],size);
      assert.equal(pickOwnership(result.grid,x,y),expected,`pick${x},${y}`);
      assert.equal(sampled[x],expected,`sample${x},${y}`);
    }
  }
  assert.equal(result.metadata.owned_cells,cells);
  assert.equal(result.metadata.checked_cells,size**2);
  assert.equal(result.metadata.unchecked_cells,0);
  assert.ok(result.metadata.multiple_owner_cells>0);
  assert.equal(result.metadata.per_owner_cells.reduce((n,r)=>n+r[1],0),cells);
  assert.equal(result.metadata.runWords,result.grid.runs.length);
  assert.equal(pickOwnership(result.grid,15,15),0,'native hole remains unowned');
});
test('row block and transport part boundaries preserve identical full decoded words',async()=>{
  const runs=[];
  for(const opts of [{rowBlock:1,partWords:2},{rowBlock:7,partWords:8},{rowBlock:32,partWords:1048576}])
    runs.push(await build(fixture(),32,opts));
  for(const r of runs.slice(1)){
    assert.deepEqual(r.grid.rows,runs[0].grid.rows);assert.deepEqual(r.grid.runs,runs[0].grid.runs);
    assert.deepEqual(r.metadata.per_owner_cells,runs[0].metadata.per_owner_cells);
  }
  const repeat=await build(fixture(),32,{rowBlock:7,partWords:8});
  assert.deepEqual([...repeat.assets],[...runs[1].assets],'identical transport bytes on two runs');
});
test('same-owner duplicate polygons, overlaps, split dateline islands and empty rows retain semantics',async()=>{
  const p=[rect(-30,-2,30,2)];
  const index=[item(1,p,p),item(2,p),item(3,[rect(-180,-10,-160,10)],[rect(160,-10,180,10)])];
  const result=await build(index,32,{rowBlock:3,partWords:4});
  for(let y=0;y<32;y++)for(let x=0;x<32;x++)
    assert.equal(pickOwnership(result.grid,x,y),oracle(index,x,table(32)[y],32));
  assert.equal(pickOwnership(result.grid,16,15),1);
  assert.equal(result.grid.rows[1],0,'empty first row preserved');
});
test('invalid inactive rings, ordering, part bounds and writer failures never produce a valid result',async()=>{
  const malformed=[item(1,[ring([[0,-10],[1,-10],[1,-9],[0,-8]])])];
  let writes=0;
  await assert.rejects(compileNativeOwnership(malformed,{size:32,latitudes:table(32),rowBlock:1,
    writePart:async()=>{writes++;}}),/Unclosed/);
  assert.equal(writes,0,'inactive malformed ring rejected before emitting');
  await assert.rejects(build([fixture()[0],fixture()[0]],32),/owner order/);
  await assert.rejects(build(fixture(),32,{partWords:3}),/bounded canonical/);
  await assert.rejects(build(fixture(),32,{rowBlock:4097}),/bounded canonical/);
  await assert.rejects(compileNativeOwnership(fixture(),{size:32,latitudes:table(32),partWords:2,
    writePart:async()=>{throw Error('writer unavailable');}}),/writer unavailable/);
});

// Source-equivalent collinear sampling must not change production codec output.
import {nativeRowLatitudes} from '../src/native-grid.js';
test('noded and unnoded shared borders yield identical complete native ownership assets',async()=>{
 const original=[item(1,[ring([[0,0],[10,30],[-10,0],[0,0]])]),
  item(2,[ring([[0,0],[10,0],[10,30],[5,15],[0,0]])])];
 const noded=[item(1,[ring([[0,0],[5,15],[10,30],[-10,0],[0,0]])]),original[1]];
 // Exact collinearity: 5*30 - 15*10 = 0; source point sets are identical.
 for(const size of [32,127,256]){
  const options={latitudes:nativeRowLatitudes(size),rowBlock:17,partWords:128};
  const a=await build(original,size,options),b=await build(noded,size,options);
  assert.deepEqual(a.grid.rows,b.grid.rows);
  assert.deepEqual(a.grid.runs,b.grid.runs);
  assert.deepEqual([...a.assets],[...b.assets]);
  assert.deepEqual(a.metadata.per_owner_cells,b.metadata.per_owner_cells);
  assert.ok(a.metadata.owned_cells>0);
 }
});

test('owners without sampled cells remain explicit and malformed latitude tables emit no assets',async()=>{
 const index=[item(1,[rect(-30,-2,30,2)]),item(2,[rect(1,80,2,81)])];
 const result=await build(index,32);
 assert.deepEqual(result.metadata.per_owner_cells.map(r=>r[0]),[1,2]);
 assert.equal(result.metadata.per_owner_cells[1][1],0);
 for(const latitudes of [Float64Array.from([0]),Float64Array.from({length:32},()=>0),
  Float64Array.from({length:32},(_,i)=>i===31?NaN:16-i-.5)]){
  let writes=0;
  await assert.rejects(compileNativeOwnership(index,{size:32,latitudes,writePart:async()=>{writes++;}}));
  assert.equal(writes,0);
 }
});
