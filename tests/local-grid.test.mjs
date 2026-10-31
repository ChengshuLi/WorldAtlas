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
import {gridLinePixels} from '../web/local-grid.js';
test('fractional zoom and offsets retain screen-aligned lines in both axes',()=>{
 for(const scale of [9,9.1,10.5,17.37,36]) for(const offset of [-42.72,.11,-.5]) {
  const lines=gridLinePixels(offset,scale,800,65536);
  assert.ok(lines.length>=Math.floor(800/scale)-1);
  assert.ok(lines.every(Number.isInteger));
  for(let i=1;i<lines.length;i++) assert.ok(Math.abs(lines[i]-lines[i-1]-scale)<1.01);
 }
});
import {wrapColumn} from '../web/local-grid.js';
test('wraps columns across both directions and multiple worlds',()=>{
 assert.equal(wrapColumn(-1,65536),65535);assert.equal(wrapColumn(65536,65536),0);assert.equal(wrapColumn(65536*7+19,65536),19);
});
test('canvas renders wrapped native cells without blank horizontal margins',()=>{
 const palette=Array.from({length:32},(_,i)=>[i,0,0]);const meta={width:6,height:2,palette},data={rows:new Uint32Array([0,3,4]),runs:new Uint32Array([2,2,3,18,6,9,6,1])};
 for(const scale of [.7,2,3.1])for(const ox of [-101,-12,-11.9,-2.6,0,9,101]){
  const w=31,h=2,pixels=renderPixels(meta,data,w,h,scale,ox,0);
  for(let py=0;py<h;py++)for(let px=0;px<w;px++){
   const x=wrapColumn(Math.floor((px+.5-ox)/scale),meta.width),y=Math.floor((py+.5)/scale);
   if(y<meta.height)assert.equal(pixels[py*w+px]&255,cellValue(data.rows,data.runs,x,y));
  }
 }
});
test('wrapped rendering and picking agree at floating-point run boundaries',()=>{
 const meta={width:6,height:2,palette:Array.from({length:32},(_,i)=>[i,0,0])},data={rows:new Uint32Array([0,3,4]),runs:new Uint32Array([2,2,3,18,6,9,6,1])};
 for(let i=1;i<4000;i++){
  const scale=.01+(i*37%3600)/100,ox=(i*13.37%1000)-500,sy=Math.floor(.5/scale);
  if(sy>=2)continue;
  const pixels=renderPixels(meta,data,101,1,scale,ox,0);
  for(let x=0;x<101;x++)assert.equal(pixels[x]&255,cellValue(data.rows,data.runs,wrapColumn(Math.floor((x+.5-ox)/scale),6),sy));
 }
});
