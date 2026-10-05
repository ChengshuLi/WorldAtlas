import test from 'node:test';
import assert from 'node:assert/strict';
import {nativePolygonIntervals,nativeRowLatitudes,NATIVE_GRID_METHOD} from '../src/native-grid.js';
import {createGridIndex,rasterize,GRID_WIDTH} from '../src/pixel-grid.js';
import {coverageRow} from '../scripts/audit-grid-intervals.mjs';

const ring=points=>Float64Array.from(points.flat());
const rectangle=(west,south,east,north)=>ring([[west,south],[east,south],[east,north],[west,north],[west,south]]);
const item=(index,...polygons)=>({index,polygons});
const table=size=>Float64Array.from({length:size},(_,y)=>size/2-y-.5);
const owner=(result,x,y)=>coverageRow(result.rows.get(y)??[],result.size).find(s=>s.start<=x&&x<s.end).owners[0]??0;
const run=(index,size=32,extra={})=>nativePolygonIntervals(index,{size,rowStart:0,rowEnd:size,latitudes:table(size),...extra});

// Independent integer-coordinate ray oracle. It evaluates orientation at the
// exact rational longitude of a cell centre, without computing intersections
// or rounding them to columns as the production scanline implementation does.
function integerOracle(index,x,latitude,size){
  const denominator=2n*BigInt(size);
  const longitude=(2n*BigInt(x)+1n)*360n-180n*denominator;
  const lat=BigInt(latitude*2)*BigInt(size);
  for(const feature of index)for(const polygon of feature.polygons){
    let crossings=0;
    for(const r of polygon)for(let k=0;k<r.length-2;k+=2){
      const x1=r[k],y1=r[k+1],x2=r[k+2],y2=r[k+3];
      if(!(Math.min(y1,y2)<latitude&&latitude<=Math.max(y1,y2)))continue;
      const orientation=(longitude-BigInt(x1)*denominator)*BigInt(y2-y1)-
        (lat-BigInt(y1)*denominator)*BigInt(x2-x1);
      if(y2>y1?orientation>=0n:orientation<=0n)crossings++;
    }
    if(crossings%2)return feature.index;
  }
  return 0;
}

test('actual projected collinear-border gap disappears under unchanged native membership',()=>{
  const left=[[0,0],[10,30],[-10,0],[0,0]],right=[[0,0],[10,0],[10,30],[5,15],[0,0]];
  const features=[left,right].map((r,i)=>({id:i?'right':'left',geometry:{type:'Polygon',coordinates:[r]}}));
  const x=134651,y=120032;
  assert.equal(rasterize(createGridIndex(features),{x,y,width:1,height:1})[0],0);
  const latitudes=nativeRowLatitudes(GRID_WIDTH);
  const original=nativePolygonIntervals([item(1,[ring(left)]),item(2,[ring(right)])],
    {size:GRID_WIDTH,rowStart:y-1,rowEnd:y+2,latitudes});
  const noded=nativePolygonIntervals([item(1,[ring([[0,0],[5,15],[10,30],[-10,0],[0,0]])]),item(2,[ring(right)])],
    {size:GRID_WIDTH,rowStart:y-1,rowEnd:y+2,latitudes});
  assert.equal(owner(original,x,y),1);
  assert.deepEqual([...original.rows],[...noded.rows]);
  assert.equal(original.method,NATIVE_GRID_METHOD);
  assert.ok(latitudes[y]>14&&latitudes[y]<16);
});

test('all cells agree with independent orientation oracle for holes, islands, overlap and true omissions',()=>{
  const index=[
    item(1,[rectangle(-100,-14,40,15),rectangle(-40,-5,10,5)],[rectangle(100,-2,130,3)]),
    item(2,[ring([[0,-12],[75,13],[120,-12],[0,-12]])]),
    item(3,[rectangle(-175,-15,-150,15)])
  ];
  const size=32,latitudes=table(size),result=run(index);
  let blank=0,owned=0;
  for(let y=0;y<size;y++)for(let x=0;x<size;x++){
    const expected=integerOracle(index,x,latitudes[y],size);
    assert.equal(owner(result,x,y),expected,`cell${x},${y}`);
    if(expected)owned++;else blank++;
  }
  assert.ok(blank>0&&owned>0);
  assert.equal(owner(result,15,15),0,'real native hole stays empty');
});

test('exact shared-boundary samples and horizontal endpoints follow explicit half-open rule',()=>{
  const size=36,latitudes=Float64Array.from({length:size},(_,y)=>18-y);
  const index=[item(1,[rectangle(-175,0,-5,10)]),item(2,[rectangle(-5,0,175,10)])];
  const result=run(index,size,{latitudes});
  assert.equal(owner(result,17,9),2,'right polygon includes shared left edge');
  assert.equal(owner(result,0,8),1,'maximum latitude is included');
  assert.equal(owner(result,0,18),0,'minimum latitude is excluded');
  assert.ok(result.ties.some(t=>t.kind==='horizontal-native-boundary-centres'&&t.y===18&&t.start===0&&t.end===18));
  assert.ok(result.ties.some(t=>t.kind==='excluded-native-lower-vertex-centre'&&t.y===18&&t.x===17));
  for(let y=0;y<size;y++)for(let x=0;x<size;x++)
    assert.equal(owner(result,x,y),integerOracle(index,x,latitudes[y],size));
});

test('native interval partitioning is identical to a complete bounded run',()=>{
  const index=[item(1,[ring([[-150,-16],[80,16],[150,-16],[-150,-16]])])],size=32;
  const complete=run(index),rows=[],ties=[];
  for(let rowStart=0;rowStart<size;rowStart+=8){
    const part=run(index,size,{rowStart,rowEnd:rowStart+8});rows.push(...part.rows);ties.push(...part.ties);
  }
  assert.deepEqual(rows,[...complete.rows]);
  assert.deepEqual(ties,complete.ties);
});

test('separately split dateline islands and polar clipping retain every original span',()=>{
  const size=32,index=[item(1,[rectangle(-180,-90,-160,90)]),item(2,[rectangle(160,-90,180,90)])];
  const result=run(index,size,{latitudes:nativeRowLatitudes(size)});
  for(let y=0;y<size;y++){
    assert.equal(owner(result,0,y),1);assert.equal(owner(result,size-1,y),2);
    assert.equal(owner(result,size/2,y),0);
  }
});

test('duplicate same-owner polygons do not create foreign ownership and first owner stays stable',()=>{
  const p=[rectangle(-170,-15,170,15)],result=run([item(1,p,p),item(2,p)]);
  assert.equal(owner(result,15,15),1);
  assert.deepEqual(coverageRow(result.rows.get(15),32).find(s=>s.owners.length).owners,[1,2]);
});

test('very small native features are retained without an area cutoff',()=>{
  const size=36,latitudes=Float64Array.from({length:size},(_,y)=>18-y);
  const tiny=[rectangle(-5-2**-40,9-2**-40,-5+2**-40,9+2**-40)];
  assert.equal(owner(run([item(1,tiny)],size,{latitudes}),17,9),1);
});

test('missing, malformed, noncanonical and oversized domains fail explicitly',()=>{
  const good=[item(1,[rectangle(-20,-10,20,10)])];
  assert.throws(()=>run(good,32,{rowEnd:33}),/explicit latitude/);
  assert.throws(()=>run(good,32,{latitudes:Float64Array.from({length:32},(_,y)=>y)}),/latitude table/);
  assert.throws(()=>run([good[0],good[0]]),/owner order/);
  assert.throws(()=>run([item(1,[ring([[0,0],[1,0],[0,1],[1,1]])])]),/Unclosed/);
  assert.throws(()=>run([item(1,[rectangle(0,0,181,1)])]),/lon\/lat/);
  assert.throws(()=>run([item(1,[rectangle(0,0,1,NaN)])]),/Unclosed|lon\/lat/);
  assert.throws(()=>nativePolygonIntervals(good,{size:8192,rowStart:0,rowEnd:4097,latitudes:nativeRowLatitudes(8192)}),/at most4096/);
});
