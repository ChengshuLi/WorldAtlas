import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {gunzipSync,gzipSync} from 'node:zlib';
import {createServer} from 'vite';
import {chromium} from '@playwright/test';
import {compileOwnership,packOwnership,pickOwnership,ownershipRun,samplePackedOwnership} from '../src/pixel-ownership.js';
import {loadOwnershipAssets} from '../src/ownership-assets.js';
import {shuffleOwnershipBytes,unshuffleOwnershipBytes,encodeOwnershipVarints,decodeOwnershipVarints} from '../src/ownership-codec.js';

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
test('compact full coordinate range, split high owner bits, seam cells and owner capacity are exact',()=>{
 for(const size of [32,32768,65536,262144]){
  const bits=Math.ceil(Math.log2(size)),max=Math.min(2**32-1,2**(2*(32-bits))-1),rows=Array.from({length:size},()=>new Uint32Array());
  rows[0]=Uint32Array.of(0,1,1,size-1,size,max);rows[size-1]=Uint32Array.of(1,size-1,max-1);
  const grid=packOwnership({size,rows});
  assert.equal(pickOwnership(grid,0,0),1);assert.equal(pickOwnership(grid,size-1,0),max);
  assert.equal(pickOwnership(grid,size-1,size-1),0);assert.equal(pickOwnership(grid,size-2,size-1),max-1);
  assert.equal(pickOwnership(grid,size,0),0);assert.equal(pickOwnership(grid,-1,0),0);
  assert.deepEqual(ownershipRun(grid,1),{start:size-1,end:size,id:max});
  if(max<2**32-1){rows[0]=Uint32Array.of(0,1,max+1);assert.throws(()=>packOwnership({size,rows}),/capacity/);}
 }
});
test('v1 and v2 asset loaders preserve gzip/raw words, split row chunks and reject ambiguous manifests',async()=>{
 const rows=Array.from({length:4},()=>new Uint32Array());rows[0]=Uint32Array.of(0,1,1,3,4,3);rows[3]=Uint32Array.of(0,4,2);
 for(const version of [1,2]){
  const grid=packOwnership({size:4,rows},{version}),blobs=new Map(),parts=[];
  for(const kind of ['rows','runs'])for(let offset=0;offset<grid[kind].length;offset+=4){const words=grid[kind].slice(offset,offset+4),path=kind+offset;parts.push({kind,offset,words:words.length,path});const raw=Buffer.from(words.buffer);blobs.set('./'+path,offset?raw:gzipSync(raw));}
  const manifest={version,size:4,coordinateBits:grid.coordinateBits,runWords:grid.runs.length,parts},fetcher=async p=>new Response(blobs.get(p));
  assert.deepEqual(await loadOwnershipAssets(manifest,fetcher),grid);
  await assert.rejects(loadOwnershipAssets({...manifest,parts:parts.slice(1)},fetcher),/Incomplete/);
  await assert.rejects(loadOwnershipAssets({...manifest,parts:[...parts,parts[0]]},fetcher),/overlapping/);
  if(version===2)await assert.rejects(loadOwnershipAssets({...manifest,coordinateBits:3},fetcher),/manifest/);
  const invalidRows=grid.rows.slice();invalidRows[2]=0;blobs.set('./rows0',Buffer.from(invalidRows.slice(0,4).buffer));
  await assert.rejects(loadOwnershipAssets(manifest,fetcher),/row offset/);
 }
});
test('shuffled and row-local varint transports reconstruct every packed bit across chunk and empty-row boundaries',async()=>{
 const size=262144,rows=Array.from({length:size},()=>new Uint32Array());
 rows[3]=Uint32Array.of(0,1,268435455,6,7,1,size-1,size,16415);rows[4]=Uint32Array.of(6,19,16415,19,20,16415);rows[size-1]=Uint32Array.of(0,size,1);
 const grid=packOwnership({size,rows});
 for(const encoding of ['byte-shuffle','row-varint']){
  const parts=[],blobs=new Map();
  for(const kind of ['rows','runs'])for(let offset=0;offset<grid[kind].length;offset+=kind==='rows'?131072:4){
   const words=grid[kind].slice(offset,offset+(kind==='rows'?131072:4)),path=kind+offset,codec=kind==='rows'?'byte-shuffle':encoding;
   const raw=codec==='byte-shuffle'?shuffleOwnershipBytes(words):encodeOwnershipVarints(words,{rows:grid.rows,offset,coordinateBits:grid.coordinateBits});
   const decoded=codec==='byte-shuffle'?unshuffleOwnershipBytes(raw,words.length):decodeOwnershipVarints(raw,{rows:grid.rows,offset,words:words.length,coordinateBits:grid.coordinateBits,size});assert.deepEqual(decoded,words);
   parts.push({kind,offset,words:words.length,path,encoding:codec});blobs.set('./'+path,gzipSync(raw));
  }
  assert.deepEqual(await loadOwnershipAssets({version:2,size,coordinateBits:grid.coordinateBits,runWords:grid.runs.length,parts},async p=>new Response(blobs.get(p))),grid);
 }
 assert.throws(()=>decodeOwnershipVarints(Uint8Array.of(128),{rows:grid.rows,offset:0,words:2,coordinateBits:grid.coordinateBits,size}),/Incomplete/);
});
test('real WebGL framebuffer agrees for legacy/compact holes, odd runs, maximum coordinates and high IDs',async()=>{
 const server=await createServer({server:{port:3294,strictPort:true},logLevel:'error'});let browser;
 try{
  await server.listen();
  browser=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const page=await browser.newPage();await page.goto('http://localhost:3294/src/pixel-ownership.js');
  const result=await page.evaluate(async()=>{
   const {PixelGPU}=await import('/src/pixel-gpu.js'),{compileOwnership,packOwnership,pickOwnership}=await import('/src/pixel-ownership.js');
   const ring=(a,b,c,d)=>new Float64Array([a,b,c,b,c,d,a,d,a,b]);
   const index=[{index:1,polygons:[[ring(0,0,16,32),ring(4,4,8,8)]]},{index:2,polygons:[[ring(16,0,32,32)]]},{index:3,polygons:[[ring(5,5,6,6)]]}],results=[];
   for(const version of [1,2]){
    const grid=packOwnership(compileOwnership(index,32),{version}),canvas=document.createElement('canvas');canvas.width=128;canvas.height=128;
    const gpu=new PixelGPU(canvas),gl=gpu.gl;gpu.ownership('location',grid);
    const colors=Uint8Array.of(0,0,0,0,255,0,0,255,0,255,0,255,0,0,255,255);gpu.upload('colors',colors);gpu.upload('metadata',Uint32Array.of(0,0,1,1,2,1,1,1),2);
    gpu.draw({origin:{x:0,y:0},scale:4,zoom:9,localBorders:true,selected:0,hasPolitical:false,dpr:1});
    const pixels=new Uint8Array(128*128*4);gl.readPixels(0,0,128,128,gl.RGBA,gl.UNSIGNED_BYTE,pixels);let mismatches=0;
    for(let y=0;y<32;y++)for(let x=0;x<32;x++){const id=pickOwnership(grid,x,y),at=((127-(y*4+2))*128+x*4+2)*4;for(let c=0;c<4;c++)if(pixels[at+c]!==colors[id*4+c])mismatches++;}
    results.push({version,mismatches,error:gl.getError()});gpu.destroy();
   }
   const size=262144,rows=Array.from({length:size},()=>new Uint32Array());rows[size-1]=Uint32Array.of(size-1,size,16415);
   const canvas=document.createElement('canvas');canvas.width=16;canvas.height=16;const gpu=new PixelGPU(canvas),gl=gpu.gl;
   gpu.ownership('location',packOwnership({size,rows}));const colors=new Uint8Array(16416*4);colors.set([193,71,29,255],16415*4);gpu.upload('colors',colors);gpu.upload('metadata',new Uint32Array(16416*2),2);
   gpu.draw({origin:{x:size-1,y:size-1},scale:16,zoom:10,localBorders:false,selected:0,hasPolitical:false,dpr:1});const pixel=new Uint8Array(4);gl.readPixels(8,8,1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixel);
   const high={pixel:[...pixel],error:gl.getError(),size:gl.getUniform(gpu.program,gl.getUniformLocation(gpu.program,'locationWorldSize')),maxTextureSize:gl.getParameter(gl.MAX_TEXTURE_SIZE)};
   const uploads=gpu.uploads;for(let k=0;k<30;k++)gpu.draw({origin:{x:size-1+k/100,y:size-1},scale:16+k/10,zoom:10,localBorders:false,selected:0,hasPolitical:false,dpr:1});high.navigationOwnershipUploads=gpu.uploads-uploads;gpu.destroy();return {results,high};
  });
  assert.deepEqual(result.results,[{version:1,mismatches:0,error:0},{version:2,mismatches:0,error:0}]);assert.deepEqual(result.high.pixel,[193,71,29,255]);assert.equal(result.high.error,0);assert.equal(result.high.size,262144);assert.equal(result.high.navigationOwnershipUploads,0);console.log(JSON.stringify(result));
 }finally{try{await browser?.close();}finally{await server.close();}}
});

test('packaged coverage supports all modes, gap explanations and unavailable-reference fallback', {timeout:180000},async()=>{
 const {createServer:serve}=await import('node:http'),{projectCell,GRID_ZOOM}=await import('../src/pixel-grid.js');
 const path=await import('node:path'),root=path.resolve('dist/client');
 // Use the retained Portugal–Spain gap. The former Saravan–Panjgur probe
 // now has a reviewed location owner and must not open a coverage-gap popup.
 const point=projectCell(-6.936928247,39.864122024);
 assert.equal(pickOwnership(readPublished(),...point),0,'Gap popup probe must remain unassigned in the actual packaged grid');
 const server=serve((request,response)=>{
  const pathname=decodeURIComponent(new URL(request.url,'http://localhost').pathname),file=path.resolve(root,'.'+(pathname==='/'?'/index.html':pathname));
  if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){response.writeHead(404);response.end();return;}
  response.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':file.endsWith('.html')?'text/html':'application/octet-stream');fs.createReadStream(file).pipe(response);
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const base=`http://127.0.0.1:${server.address().port}`,browser=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 try{
  for(const unavailable of [false,true]){
   const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];
   page.on('pageerror',error=>errors.push(error.message));
   await page.route('**/*',route=>{
    const url=new URL(route.request().url());
    if(url.origin!==base)return route.abort();
    if(url.pathname.startsWith('/api/')||(unavailable&&url.pathname.startsWith('/coverage-classification/')))return route.fulfill({status:503,json:{error:'Isolated unavailable-service control'}});
    return route.continue();
   });
   await page.goto(base);
   await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.rendered==='true',null,{timeout:60000}).catch(error=>{error.message+='; page errors: '+JSON.stringify(errors);throw error;});
   await page.locator('#loading').waitFor({state:'hidden',timeout:60000});
   assert.equal(await page.locator('.atlas-pixel-canvas').getAttribute('data-renderer'),'webgl2');
   const before=await page.locator('.atlas-pixel-canvas').evaluate(canvas=>({...canvas.dataset}));
   assert.equal(before.coverageUploads,unavailable?'0':'2');
   for(const year of ['1444','2021','2026']){
    await page.locator('#year-input').fill(year);await page.locator('#year-form button').click();
    await page.locator('#loading').waitFor({state:'hidden',timeout:60000});
    assert.match(await page.locator('#map-year').textContent(),new RegExp(year==='1444'?'1,444':year==='2021'?'2,021':'2,026'));
   }
   for(const mode of ['owner','population','culture','religion','rank','topography','vegetation','climate','location','province','area','region','subcontinent','continent']){
    await page.locator(`[data-mode="${mode}"]`).click();assert.equal(await page.locator(`[data-mode="${mode}"]`).getAttribute('aria-pressed'),'true');
   }
   await page.locator('#search').fill('Idanha');
   await page.locator('[data-result]').filter({hasText:'Idanha'}).first().click();
   await page.waitForTimeout(600);
   const cursor=await page.locator('.atlas-pixel-canvas').evaluate((canvas,{point,gridZoom})=>{
    const [x,y,zoom]=canvas.dataset.frame.split('/').map(Number),box=canvas.getBoundingClientRect(),scale=2**(zoom-gridZoom);
    return {x:box.x+(point[0]-x)*scale,y:box.y+(point[1]-y)*scale};
   },{point,gridZoom:GRID_ZOOM});
   assert.ok(cursor.x>0&&cursor.x<1440&&cursor.y>0&&cursor.y<1080,JSON.stringify(cursor));
   await page.mouse.move(cursor.x,cursor.y);await page.mouse.wheel(0,-800);await page.waitForTimeout(900);await page.mouse.click(cursor.x,cursor.y);
   const popup=page.locator('.leaflet-popup-content').last();await popup.waitFor();
   assert.match(await popup.textContent(),unavailable?/Unverified geographic coverage/:/Possible geographic coverage gap/);
   if(!unavailable)assert.equal(await popup.locator('a').count(),2);
   const after=await page.locator('.atlas-pixel-canvas').evaluate(canvas=>({...canvas.dataset}));
   assert.equal(after.compilations,before.compilations);assert.equal(after.ownershipUploads,before.ownershipUploads);assert.equal(after.coverageUploads,before.coverageUploads);
   assert.deepEqual(errors,[]);await page.close();
  }
 }finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
});
