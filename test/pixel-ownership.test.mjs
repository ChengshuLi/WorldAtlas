import {test} from 'node:test';
import assert from 'node:assert/strict';
import {compileOwnership,sampleOwnership,packOwnership,pickOwnership,samplePackedOwnership} from '../src/pixel-ownership.js';
import {rasterize} from '../src/pixel-grid.js';
const ring=points=>Float64Array.from(points.flat());
const polygon=(index,rings)=>({index,polygons:[rings.map(ring)],bounds:[0,0,32,32]});
const geometry=[
  polygon(1,[[[0,0],[16,0],[16,24],[0,24],[0,0]],[[4,4],[12,4],[12,12],[4,12],[4,4]]]),
  polygon(2,[[[5,.5],[27,18],[19,30],[5,.5]]]),
  polygon(3,[[[16,0],[32,0],[32,32],[16,32],[16,0]]])
];
test('compiled ownership preserves holes, shared edges, overlaps and water at every detail level',()=>{
  const grid=compileOwnership(geometry,32);
  for(const stride of [1,2,4,8])for(const x of [-8,0,5,28,36])for(const y of [-4,0,7,25,35]){
    const frame={x,y,width:12,height:10,stride};
    assert.deepEqual(sampleOwnership(grid,frame),rasterize(geometry,frame),JSON.stringify(frame));
  }
});
test('ownership survives geometry disposal and alternating zoom/pan views',()=>{
  const input=structuredClone(geometry),grid=compileOwnership(input,32);
  input.length=0;
  for(let i=0;i<20;i++){
    const frame={x:i%10,y:i%5,width:16,height:16,stride:2**(i%4)};
    assert.deepEqual(sampleOwnership(grid,frame),rasterize(geometry,frame));
  }
  assert.ok(grid.rows.every(r=>r.length%3===0));
});


test('GPU row tables and picking retain every canonical cell, including tiny features',()=>{
 const grid=compileOwnership(geometry,32),packed=packOwnership(grid);
 const full=rasterize(geometry,{x:0,y:0,width:32,height:32});
 for(let y=0;y<32;y++)for(let x=0;x<32;x++)assert.equal(pickOwnership(packed,x+.5,y+.5),full[y*32+x]);
 for(const [x,y] of [[-1,0],[0,-1],[32,0],[0,32]])assert.equal(pickOwnership(packed,x,y),0);
});

test('prepacked browser fallback samples the same canonical grid',()=>{
 const packed=packOwnership(compileOwnership(geometry,32));
 for(const stride of [1,2,4,8])for(const x of [-8,0,5,28,36])for(const y of [-4,0,7,25,35]){
  const frame={x,y,width:12,height:10,stride};assert.deepEqual(samplePackedOwnership(packed,frame),rasterize(geometry,frame));
 }
});
