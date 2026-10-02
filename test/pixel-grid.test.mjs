import {test} from 'node:test';
import assert from 'node:assert/strict';
import {rasterize,borderKind,borderStyle,viewStride,GRID_ZOOM,GRID_WIDTH} from '../src/pixel-grid.js';
const ring=(x1,y1,x2,y2)=>new Float64Array([x1,y1,x2,y1,x2,y2,x1,y2,x1,y1]);
const item=(index,polygons,bounds)=>({index,polygons,bounds});
test('pixel ownership is exclusive and adjacent locations tile without a seam',()=>{
  const index=[item(1,[[ring(0,0,2,4)]],[0,0,2,4]),item(2,[[ring(2,0,4,4)]],[2,0,4,4])];
  const ids=rasterize(index,{x:0,y:0,width:4,height:4});
  assert.deepEqual([...ids],[1,1,2,2,1,1,2,2,1,1,2,2,1,1,2,2]);
});
test('holes, water and defensive overlap handling have one integer ID per cell',()=>{
  const index=[item(1,[[ring(0,0,4,4),ring(1,1,3,3)]],[0,0,4,4]),item(2,[[ring(0,0,4,4)]],[0,0,4,4])];
  const ids=rasterize(index,{x:0,y:0,width:5,height:5});
  assert.equal(ids[0],1);assert.equal(ids[6],2);assert.equal(ids[24],0);
  assert.ok([...ids].every(id=>[0,1,2].includes(id)));
});
test('panning and lower-detail views sample the same canonical geographic cells',()=>{
  const index=[item(1,[[ring(0,0,3,4)]],[0,0,3,4]),item(2,[[ring(3,0,8,4)]],[3,0,8,4])];
  const full=rasterize(index,{x:0,y:0,width:8,height:4});
  const moved=rasterize(index,{x:2,y:0,width:4,height:4});
  const coarse=rasterize(index,{x:0,y:0,width:4,height:2,stride:2});
  for(let y=0;y<4;y++)for(let x=0;x<4;x++)assert.equal(moved[y*4+x],full[y*8+x+2]);
  for(let y=0;y<2;y++)for(let x=0;x<4;x++)assert.equal(coarse[y*4+x],full[y*16+x*2]);
});
test('province borders are stronger and local borders disappear at distant zoom',()=>{
  const provinces=[null,'province-a','province-a','province-b'];
  assert.equal(borderKind(1,2,provinces),'location');assert.equal(borderKind(2,3,provinces),'province');assert.equal(borderKind(0,1,provinces),'coast');
  assert.equal(borderStyle('location',6),null);assert.ok(borderStyle('province',6));
  assert.ok(borderStyle('province',10).width>borderStyle('location',10).width);
});

test('Canvas fallback samples near screen resolution without four-pixel blocks',()=>{
 assert.equal(GRID_WIDTH,32768);
 for(let zoom=1;zoom<=13;zoom+=.25){const size=2**(zoom-GRID_ZOOM)*viewStride(zoom);assert.ok(size>=1);if(zoom<=7)assert.ok(size<2);}
});
