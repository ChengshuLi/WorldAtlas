import test from 'node:test';
import assert from 'node:assert/strict';
import {polygonIntervals,compareRow,coverageRow} from '../scripts/audit-grid-intervals.mjs';
import {rasterize,createGridIndex,GRID_WIDTH} from '../src/pixel-grid.js';
import {compileOwnership} from '../src/pixel-ownership.js';
const ring=points=>Float64Array.from(points.flat());
const square=(x,y,w)=>ring([[x,y],[x+w,y],[x+w,y+w],[x,y+w],[x,y]]);
const item=(index,polygons)=>({index,polygons,bounds:[0,0,8,8]});
const expand=(spans,size,pick)=>{
  const row=new Uint32Array(size);
  for(const span of spans)row.fill(pick(span),span.start,span.end);
  return row;
};

test('sparse intervals match actual rasterizer and compiler, preserving deterministic first-owner priority',()=>{
  const index=[item(1,[[square(0,0,6),square(2,2,2)]]),item(2,[[square(4,1,3)]]),
    item(3,[[square(6,6,1)]])];
  const sparse=polygonIntervals(index,{size:8,rowStart:0,rowEnd:8});
  const raster=rasterize(index,{x:0,y:0,width:8,height:8}),compiled=compileOwnership(index,8);
  for(let y=0;y<8;y++){
    const spans=coverageRow(sparse.rows.get(y)??[],8);
    assert.deepEqual(expand(spans,8,s=>s.owners[0]??0),raster.slice(y*8,y*8+8));
    const native=compiled.rows[y];
    const actual=compareRow(sparse.rows.get(y)??[],native,8);
    assert.equal(actual.counts.first_owner_difference,0);
    assert.equal(actual.counts.checked_cells,8);
    if(y===1)assert.equal(actual.counts.multiple_projected_owners,2);
  }
});

test('finds a grid-only gap anywhere in an interval, without a component sample',()=>{
  const result=compareRow([{start:0,end:8,owner:1}],[0,3,1,4,8,1],8);
  assert.equal(result.counts.raster_only_gap,1);
  assert.deepEqual(result.findings[0].projected_owners,[1]);
  assert.equal(result.findings[0].start,3);
});

test('holes and separate islands retain zero-covered cells',()=>{
  const index=[item(1,[[square(0,0,6),square(2,2,2)],[square(6,6,1)]])];
  const sparse=polygonIntervals(index,{size:8,rowStart:2,rowEnd:3});
  assert.deepEqual(coverageRow(sparse.rows.get(2),8),[
    {start:0,end:2,owners:[1]},{start:2,end:4,owners:[]},
    {start:4,end:6,owners:[1]},{start:6,end:8,owners:[]}]);
});

test('half-open centre ties and clipping use the application arithmetic',()=>{
  const index=[item(1,[[square(-.5,.5,3)]])];
  const sparse=polygonIntervals(index,{size:8,rowStart:0,rowEnd:5});
  assert.equal(sparse.rows.has(3),false);
  assert.ok(sparse.ties.length>0);
  const actual=rasterize(index,{x:0,y:0,width:8,height:5});
  for(let y=0;y<5;y++)assert.deepEqual(
    expand(coverageRow(sparse.rows.get(y)??[],8),8,s=>s.owners[0]??0),actual.slice(y*8,y*8+8));
});

test('duplicate polygons belonging to one owner are not cross-owner overlap',()=>{
  assert.equal(compareRow([{start:0,end:4,owner:1},{start:0,end:4,owner:1}],[0,4,1],8)
    .counts.multiple_projected_owners,0);
});

test('outside coverage and foreign ownership remain distinct',()=>{
  const result=compareRow([{start:2,end:5,owner:2}],[0,8,1],8);
  assert.equal(result.counts.native_outside_projected,5);
  assert.equal(result.counts.foreign_owner,3);
});

test('partitioned rows produce the same sparse intervals as a complete small domain',()=>{
  const index=[item(1,[[square(0,0,7)]])];
  const all=polygonIntervals(index,{size:8,rowStart:0,rowEnd:8});
  const partial=polygonIntervals(index,{size:8,rowStart:3,rowEnd:5});
  for(let y=3;y<5;y++)assert.deepEqual(partial.rows.get(y),all.rows.get(y));
});

test('malformed native rows and coordinates fail instead of silently leaving unchecked cells',()=>{
  assert.throws(()=>compareRow([],[0,5,1,4,8,2],8),/Invalid native/);
  assert.throws(()=>polygonIntervals([item(1,[[ring([[0,0],[1,0],[1,1],[0,NaN],[0,0]])]])],
    {size:8,rowStart:0,rowEnd:8}),/Nonfinite/);
  assert.throws(()=>polygonIntervals([],{size:10000,rowStart:0,rowEnd:5000}),/bounded/);
});

test('split dateline geometry stays at both edges of the actual world grid',()=>{
  const feature={id:'dateline-fixture',geometry:{type:'MultiPolygon',coordinates:[
    [[[179.9,-.1],[180,-.1],[180,.1],[179.9,.1],[179.9,-.1]]],
    [[[-180,-.1],[-179.9,-.1],[-179.9,.1],[-180,.1],[-180,-.1]]]
  ]}};
  const index=createGridIndex([feature]),start=GRID_WIDTH/2-1;
  const sparse=polygonIntervals(index,{size:GRID_WIDTH,rowStart:start,rowEnd:start+2});
  const actual=rasterize(index,{x:0,y:start,width:GRID_WIDTH,height:2});
  for(let y=start;y<start+2;y++){
    const row=expand(coverageRow(sparse.rows.get(y)??[],GRID_WIDTH),GRID_WIDTH,s=>s.owners[0]??0);
    assert.deepEqual(row,actual.slice((y-start)*GRID_WIDTH,(y-start+1)*GRID_WIDTH));
    assert.equal(row[0],1);assert.equal(row.at(-1),1);assert.equal(row[GRID_WIDTH/2],0);
  }
});

test('using unprojected longitude/latitude is detected as a representation mismatch',()=>{
  const feature={id:'projection-fixture',geometry:{type:'Polygon',coordinates:[
    [[0,-.1],[.1,-.1],[.1,.1],[0,.1],[0,-.1]]]
  }};
  const start=GRID_WIDTH/2,index=createGridIndex([feature]);
  const actual=rasterize(index,{x:0,y:start,width:GRID_WIDTH,height:1});
  const native=[];
  for(let a=0;a<actual.length;){
    let b=a+1;while(b<actual.length&&actual[b]===actual[a])b++;
    if(actual[a])native.push(a,b,actual[a]);a=b;
  }
  const wrong=[item(1,[[ring(feature.geometry.coordinates[0])]])];
  const sparse=polygonIntervals(wrong,{size:GRID_WIDTH,rowStart:start,rowEnd:start+1});
  assert.ok(compareRow(sparse.rows.get(start)??[],native,GRID_WIDTH).counts.native_outside_projected>0);
});


test('horizontal boundary centres include both endpoints and clip to the declared domain',()=>{
  const index=[item(1,[[ring([[0,.5],[4,.5],[4,2.5],[0,2.5],[0,.5]])]])];
  const all=polygonIntervals(index,{size:8,rowStart:0,rowEnd:8});
  assert.deepEqual(all.ties.filter(t=>t.kind==='horizontal-boundary-cell-centres'),[
    {y:0,start:0,end:4,owner:1,kind:'horizontal-boundary-cell-centres'},
    {y:2,start:0,end:4,owner:1,kind:'horizontal-boundary-cell-centres'}]);
  assert.equal(all.rows.has(2),false);
  const clipped=polygonIntervals([item(1,[[ring([[-.5,.5],[8.5,.5],[8.5,2.5],[-.5,2.5],[-.5,.5]])]])],
    {size:8,rowStart:2,rowEnd:3});
  assert.deepEqual(clipped.ties,[{y:2,start:0,end:8,owner:1,kind:'horizontal-boundary-cell-centres'}]);
});

test('excluded upper vertices remain boundary diagnostics without changing fill',()=>{
  const index=[item(1,[[ring([[0,0],[4,0],[2.5,2.5],[0,0]])]])];
  const all=polygonIntervals(index,{size:8,rowStart:0,rowEnd:8});
  assert.equal(all.rows.has(2),false);
  assert.equal(all.ties.filter(t=>t.y===2&&t.x===2.5&&
    t.kind==='excluded-upper-vertex-on-cell-centre').length,2);
  const partial=polygonIntervals(index,{size:8,rowStart:2,rowEnd:3});
  assert.deepEqual(partial.ties,all.ties.filter(t=>t.y===2));
  const actual=rasterize(index,{x:0,y:0,width:8,height:8});
  for(let y=0;y<8;y++)assert.deepEqual(
    expand(coverageRow(all.rows.get(y)??[],8),8,s=>s.owners[0]??0),actual.slice(y*8,y*8+8));
});
