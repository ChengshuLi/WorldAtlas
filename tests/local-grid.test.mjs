import test from 'node:test';
import assert from 'node:assert/strict';
import {cellValue,validateGrid} from '../web/local-grid.js';
test('local native lookup preserves every cell and run boundary',()=>{
 const meta={width:6,height:2,local_grid:{run_count:4}},rows=new Uint32Array([0,3,4]),runs=new Uint32Array([2,2,3,18,6,9,6,1]);
 validateGrid(meta,rows,runs);
 assert.deepEqual(Array.from({length:6},(_,x)=>cellValue(rows,runs,x,0)),[2,2,18,9,9,9]);
 assert.equal(cellValue(rows,runs,5,1),1);
});
test('65536-column exclusive endpoint is not truncated to 16 bits',()=>{
 const meta={width:65536,height:1,local_grid:{run_count:1}},rows=new Uint32Array([0,1]),runs=new Uint32Array([65536,22]);
 validateGrid(meta,rows,runs);assert.equal(cellValue(rows,runs,65535,0),22);
});
test('rejects incomplete native grid',()=>assert.throws(()=>validateGrid({width:6,height:1,local_grid:{run_count:1}},new Uint32Array([0,1]),new Uint32Array([5,2]))));
import {renderPixels} from '../web/local-grid.js';
test('canvas renders exactly the loaded native cell at each screen pixel',()=>{
 const palette=Array.from({length:32},(_,i)=>[i,0,0]);
 const meta={width:6,height:2,palette},data={rows:new Uint32Array([0,3,4]),runs:new Uint32Array([2,2,3,18,6,9,6,1])};
 for(const [scale,ox,oy,w,h] of [[2,0,0,12,4],[3.1,-2.6,-.2,12,5],[.7,0,0,4,1]]){
  const pixels=renderPixels(meta,data,w,h,scale,ox,oy);
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){
   const sx=Math.floor((x+.5-ox)/scale),sy=Math.floor((y+.5-oy)/scale);
   assert.equal(pixels[y*w+x]&255,cellValue(data.rows,data.runs,sx,sy));
  }
 }
});
