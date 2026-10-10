import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {gunzipSync,gzipSync} from 'node:zlib';
import {createServer} from 'vite';
import {chromium} from '@playwright/test';
import {compileOwnership,packOwnership,pickOwnership,ownershipRun,samplePackedOwnership} from '../src/pixel-ownership.js';
import {loadOwnershipAssets} from '../src/ownership-assets.js';
import {NATIVE_METHOD} from '../src/ownership-method.js';
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

test('packaged coverage supports all modes, gap explanations and unavailable-reference policy', {timeout:180000},async()=>{
 const {createServer:serve}=await import('node:http'),{projectCell,GRID_ZOOM}=await import('../src/pixel-grid.js');
 const path=await import('node:path'),root=path.resolve('dist/client');
 // Use the retained Portugal–Spain gap. The former Saravan–Panjgur probe
 // now has a reviewed location owner and must not open a coverage-gap popup.
 const point=projectCell(-6.936928247,39.864122024);
 assert.equal(pickOwnership(readPublished(),...point),0,'Gap popup probe must remain unassigned in the actual packaged grid');
 const native=JSON.parse(fs.readFileSync(path.join(root,'atlas-geography.json'))).pixelMap.method===NATIVE_METHOD;
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
   if(unavailable&&native){
    // The native generation requires its complete pinned classification input.
    // A failed stream must not publish a partial map or a false gap fallback.
    await page.waitForFunction(()=>document.querySelector('#loading')?.textContent.includes('Atlas could not load. Check the server and reload the page.'));
    assert.equal(await page.locator('.atlas-pixel-canvas').count(),0);
    assert.deepEqual(errors,[]);await page.close();continue;
   }
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

// Actual selected output probe in the existing shard0 route.
test('actual selected additive cells draw and pick identically in production GPU and Canvas', {timeout:240000},async t=>{
 const {createHash}=await import('node:crypto'),path=await import('node:path');
 const digest=raw=>createHash('sha256').update(raw).digest('hex');
 const repo=path.resolve('.'),output=path.resolve('dist/client');
 const whole=(root,pin)=>{
  assert.ok(pin&&typeof pin.path==='string'&&!path.isAbsolute(pin.path)&&!pin.path.split('/').some(p=>!p||p==='.'||p==='..'));
  let file=root;for(const part of pin.path.split('/')){file=path.join(file,part);assert.equal(fs.lstatSync(file).isSymbolicLink(),false);}
  const first=fs.lstatSync(file);assert.ok(first.isFile());
  if(pin.mode)assert.equal(first.mode&0o777,parseInt(pin.mode,8)&0o777);
  const fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);let raw;
  try{raw=fs.readFileSync(fd);const held=fs.fstatSync(fd),last=fs.lstatSync(file);for(const k of ['dev','ino','size','mode','mtimeMs','ctimeMs'])assert.equal(first[k],held[k]),assert.equal(held[k],last[k]);}finally{fs.closeSync(fd);}
  assert.equal(raw.length,pin.bytes);assert.equal(digest(raw),pin.sha256);
  if(pin.encoding==='gzip'||pin.decoded_bytes!==undefined){const decoded=gunzipSync(raw,{maxOutputLength:pin.decoded_bytes});assert.equal(decoded.length,pin.decoded_bytes);assert.equal(digest(decoded),pin.decoded_sha256);return decoded;}
  return raw;
 };
 const json=(root,pin)=>JSON.parse(whole(root,pin));
 const selection=JSON.parse(fs.readFileSync('data/ownership-selection.json'));
 assert.equal(selection.version,1);assert.equal(typeof selection.manifest_path,'string');
 if(selection.additive_release===undefined){t.skip('Actual selected bank has no additive release');return;}
 const sidecar=json(repo,selection.additive_release),envelope=json(repo,sidecar.runtime_envelope);
 assert.deepEqual(Object.keys(envelope).sort(),['base_manifest','base_reference','effective_reference','kind','ledger','owner_roster','patch','version'].sort());
 assert.equal(envelope.version,2);assert.equal(envelope.kind,'retained-native-base-plus-delta-v2');
 const atlas=JSON.parse(fs.readFileSync(path.join(output,'atlas-geography.json')));
 assert.deepEqual(atlas.additiveRelease,envelope);assert.deepEqual(atlas.reference_release,envelope.effective_reference);
 const bodies={};for(const role of ['base_manifest','ledger','owner_roster','patch']){
  const published=whole(output,envelope[role]),original=whole(repo,sidecar.logical_asset_map[role]);
  assert.deepEqual(published,original);bodies[role]=JSON.parse(published);
 }
 const {ledger,patch,owner_roster:owners,base_manifest:manifest}=bodies;
 assert.equal(envelope.base_manifest.sha256,selection.sha256);assert.equal(atlas.pixelMap.canonical_grid_sha256,selection.sha256);
 const certificate=json(repo,ledger.current_rebind),request=json(repo,certificate.request),result=json(repo,certificate.result);
 assert.deepEqual(result.original_rows,request.original_rows);assert.deepEqual(result.current_targets,request.current_targets);
 assert.deepEqual(result.base_selection,certificate.base_selection);assert.deepEqual(result.native.rows,patch.rows);
 assert.deepEqual(request.base_selection,sidecar.base_selection);
 assert.ok(owners.length>0&&owners.length<2**24);
 assert.equal(manifest.original_assets.bounds.sha256,envelope.owner_roster.sha256);
 assert.deepEqual(owners.map(o=>o.index),owners.map((_,i)=>i+1));assert.equal(new Set(owners.map(o=>o.id)).size,owners.length);
 const latitudePin=atlas.pixelMap.native_latitudes;
 assert.equal(latitudePin.transport_path,'native-v1/native-row-latitudes.f64le.gz');
 const latitudes=whole(output,{...latitudePin,path:latitudePin.transport_path});
 assert.equal(latitudes.length,manifest.size*8);assert.equal(digest(latitudes),manifest.native_latitudes.decoded_sha256);
 // Reuse complete qualified row inputs; do not repeat the old fourteen-million-cell CPU proof.
 const observed=new Map();for(const row of [...request.current_rows,...request.acquisition.predecessor_rows]){
  if(observed.has(row.y))assert.deepEqual(observed.get(row.y),row);else observed.set(row.y,row);
 }
 const probes=[],addedKeys=new Set(),gainByOwner=new Map();
 for(const row of patch.rows)for(const [start,end,owner]of row.runs){
  assert.ok(owners[owner-1]);for(let x=start;x<end;x++){
   const key=x+'/'+row.y;assert.equal(addedKeys.has(key),false);addedKeys.add(key);
   assert.ok(observed.has(row.y));assert.ok(!observed.get(row.y).runs.some(([a,b])=>a<=x&&x<b));
   probes.push({x,y:row.y,before:0,after:owner,added:true});gainByOwner.set(owner,(gainByOwner.get(owner)??0)+1);
  }
 }
 assert.ok(probes.length>0);assert.equal(probes.length,result.native.assigned_cells);
 for(const row of observed.values()){
  const run=row.runs.find(([a,b])=>a<b);assert.ok(run,'Complete observed row needs a stable before control');
  probes.push({x:run[0],y:row.y,before:run[2],after:run[2],added:false});
 }
 for(const probe of probes){probe.lon=(probe.x+.5)/manifest.size*360-180;probe.lat=latitudes.readDoubleLE(probe.y*8);assert.ok(Number.isFinite(probe.lat));}
 const expectedGains=new Map();for(const row of result.native.rows)for(const [start,end,owner]of row.runs)expectedGains.set(owner,(expectedGains.get(owner)??0)+end-start);
 assert.deepEqual([...gainByOwner].sort((a,b)=>a[0]-b[0]),[...expectedGains].filter(([,cells])=>cells>0).sort((a,b)=>a[0]-b[0]));
 const payload={atlas,owners,probes};
 const html=`<!doctype html><link rel="stylesheet" href="/node_modules/leaflet/dist/leaflet.css"><style>#map{width:256px;height:256px}</style><div id="map"></div><script type="module">
 import * as L from '/node_modules/leaflet/dist/leaflet-src.esm.js';
 import {PixelLayer} from '/src/pixel-layer.js';import {PixelCanvasLayer} from '/src/pixel-canvas-layer.js';
 import {loadOwnershipAssets} from '/src/ownership-assets.js';import {loadAdditiveNativePatch} from '/src/effective-footprint.js';
 import {readJSON} from '/src/data-client.js';
 import {pickOwnership} from '/src/pixel-ownership.js';import {projectCell} from '/src/pixel-grid.js';
 const payload=await fetch('/selected-render-input').then(r=>r.json()),fetcher=p=>fetch('/selected-assets/'+(p.startsWith('./')?p.slice(2):p));
 const base=await loadOwnershipAssets(payload.atlas.pixelMap,fetcher);
 const originalFeatures=(await Promise.all(payload.atlas.parts.map(p=>readJSON('/selected-assets/'+p)))).flat();
 if(originalFeatures.length!==payload.owners.length||originalFeatures.some((f,i)=>f.id!==payload.owners[i].id||f.pixelIndex!==payload.owners[i].index||f.properties.parent_id!==payload.owners[i].province_id))throw Error('Complete emitted catalog/owner roster mismatch');
 const features=originalFeatures.map(f=>({...f,properties:{...f.properties}}));
 const effective=await loadAdditiveNativePatch(payload.atlas,features,base,{fetcher});
 const map=L.map('map',{zoomSnap:0,minZoom:1,maxZoom:13}).setView([0,0],13),rgba=id=>id?[id&255,id>>>8&255,id>>>16&255,255]:[0,0,0,0];
 const color=f=>'#'+rgba(f.pixelIndex).slice(0,3).map(x=>x.toString(16).padStart(2,'0')).join('');
 window.selectedRender={L,map,payload,base,effective,originalFeatures,features,rgba,pickOwnership,projectCell,color,PixelLayer,PixelCanvasLayer};
 </script>`;
 const server=await createServer({server:{host:'127.0.0.1',port:0},logLevel:'error',plugins:[{name:'selected-added-cell-test',configureServer(s){s.middlewares.use((req,res,next)=>{
  const name=new URL(req.url,'http://localhost').pathname;
  if(name==='/selected-render'){res.setHeader('Content-Type','text/html');res.end(html);return;}
  if(name==='/selected-render-input'){res.setHeader('Content-Type','application/json');res.end(JSON.stringify(payload));return;}
  if(!name.startsWith('/selected-assets/')){next();return;}
  const relative=decodeURIComponent(name.slice('/selected-assets/'.length)),file=path.resolve(output,relative);
  if(!file.startsWith(output+path.sep)||relative.split('/').some(x=>x==='..')||!fs.existsSync(file)){res.statusCode=404;res.end();return;}
  res.setHeader('Content-Type','application/octet-stream');fs.createReadStream(file).pipe(res);
 });}}]});let browser;
 try{
  await server.listen();const port=server.httpServer.address().port;
  browser=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const page=await browser.newPage({deviceScaleFactor:1}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',route=>{const u=new URL(route.request().url());return u.protocol==='http:'&&u.hostname==='127.0.0.1'&&u.port===String(port)?route.continue():route.abort();});
  await page.goto(`http://127.0.0.1:${port}/selected-render`);await page.waitForFunction(()=>!!window.selectedRender);
  const observations=await page.evaluate(async()=>{
   const s=window.selectedRender,checks=[];
   for(const renderer of ['gpu','canvas'])for(const vintage of ['before','after']){
    const grid=vintage==='before'?s.base:s.effective,features=vintage==='before'?s.originalFeatures:s.features;
    const options={ownership:grid,orderedOwners:true,color:s.color,selected:()=>null,locationBorders:()=>false,select:id=>s.selected=id};
    const layer=new(renderer==='gpu'?s.PixelLayer:s.PixelCanvasLayer)(features,options).addTo(s.map);
    if((!!layer.gpu)!==(renderer==='gpu'))throw Error('Unexpected renderer fallback');
    let checked=0;
    for(const probe of s.payload.probes){
     const latlng=s.L.latLng(probe.lat,probe.lon),expected=probe[vintage];s.map.setView(latlng,13,{animate:false});
     cancelAnimationFrame(layer.pending);await layer.draw();const projected=s.projectCell(probe.lon,probe.lat);
     if(Math.floor(projected[0])!==probe.x||Math.floor(projected[1])!==probe.y)throw Error('Normative cell center projection drift');
     if(s.pickOwnership(grid,probe.x,probe.y)!==expected||(layer.pick(latlng)?.id??null)!==(expected?s.payload.owners[expected-1].id:null))throw Error('Selected owner/pick mismatch');
     s.selected=null;if(expected){layer.click({latlng});if(s.selected!==s.payload.owners[expected-1].id)throw Error('Production click selected another owner');}
     const c=layer.canvas,at=s.map.latLngToContainerPoint(latlng),mapRect=s.map.getContainer().getBoundingClientRect(),rect=c.getBoundingClientRect();
     const x=Math.floor(mapRect.left+at.x-rect.left),y=Math.floor(mapRect.top+at.y-rect.top);let pixel;
     if(layer.gpu){pixel=new Uint8Array(4);const gl=layer.gpu.gl;gl.readPixels(x,c.height-1-y,1,1,gl.RGBA,gl.UNSIGNED_BYTE,pixel);if(gl.getError()!==0)throw Error('GPU read error');}
     else pixel=c.getContext('2d').getImageData(x,y,1,1).data;
     if(!s.rgba(expected).every((v,i)=>v===pixel[i]))throw Error('Selected fill mismatch '+renderer+'/'+vintage+'/'+probe.x+'/'+probe.y);
     checked++;
    }
    if(Number(layer.canvas.dataset.compilations)!==0)throw Error('Precompiled selected bank was recompiled');
    checks.push({renderer,vintage,checked});layer.remove();
   }
   return checks;
  });
  assert.deepEqual(errors,[]);assert.equal(observations.length,4);assert.ok(observations.every(o=>o.checked===probes.length));
  console.log(JSON.stringify({kind:'actual-selected-additive-gpu-canvas-picking',backend:'headless SwiftShader/Canvas2D; not physical-device performance',selected_envelope_sha256:sidecar.runtime_envelope.sha256,owners:owners.length,added_cells:result.native.assigned_cells,complete_observed_rows:observed.size,stable_before_controls:observed.size,observations}));
 }finally{await browser?.close();await server.close();}
});
