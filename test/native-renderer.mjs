// Isolated headless graphics fixture: fresh managed profile, localhost-only
// requests. Never connects to a user browser, account or production service.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {createServer} from 'vite';
import {chromium} from '@playwright/test';
import {compileNativeRuntime} from '../src/native-runtime.js';
import {createGridIndex} from '../src/pixel-grid.js';
import {compileOwnership,packOwnership,pickOwnership} from '../src/pixel-ownership.js';
const table=gunzipSync(await fs.readFile('coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz'));
const size=262166,latitudes=Float64Array.from({length:size},(_,y)=>table.readDoubleLE(y*8));
const rectangle=(a,b,c,d)=>[[a,b],[c,b],[c,d],[a,d],[a,b]];
const feature=(id,pixelIndex,coordinates,type='Polygon')=>({type:'Feature',id,pixelIndex,
 properties:{name:id,parent_id:'fixture-province'},geometry:{type,coordinates}});
const features=[feature('left',1,[[[0,0],[10,30],[-10,0],[0,0]]]),
 feature('right',8192,[[[0,0],[10,0],[10,30],[5,15],[0,0]]]),
 feature('hole-location',8193,[rectangle(55,45,65,55),rectangle(59,49,61,51)]),
 feature('dateline-location',67108863,[[rectangle(179,0,180,1)],[rectangle(-180,0,-179,1)]],'MultiPolygon')];
const ownership=await compileNativeRuntime(features.map((f,i)=>({...f,pixelIndex:i+1})),{size,latitudes});
const legacy=packOwnership(compileOwnership(createGridIndex(features)));
assert.equal(pickOwnership(legacy,134651,120032),0);
assert.equal(pickOwnership(ownership,134651,120032),1);
const physical=[feature('land',1,[rectangle(55,45,65,55),rectangle(59.5,49.5,60.5,50.5)]),
 feature('water',2,[rectangle(59.5,49.5,60.5,50.5)])];
const physicalGrid=packOwnership(compileOwnership(createGridIndex(physical)));
const grids={ownership,physicalGrid};
const scratch='.cache/native-renderer-controls';await fs.mkdir(scratch,{recursive:true});
const profile=await fs.mkdtemp(path.resolve(scratch,'profile-'));
const html=`<!doctype html><link rel="stylesheet" href="/node_modules/leaflet/dist/leaflet.css"><style>#map{width:800px;height:600px;background:#637f99}</style><div id="map"></div><script type="module">
import * as L from '/node_modules/leaflet/dist/leaflet-src.esm.js';
import {PixelLayer} from '/src/pixel-layer.js';import {PixelCanvasLayer} from '/src/pixel-canvas-layer.js';
const features=${JSON.stringify(features)};
async function grid(name){const metadata=await fetch('/fixture-grid/'+name+'/metadata').then(r=>r.json());for(const kind of ['rows','runs'])metadata[kind]=new Uint32Array(await fetch('/fixture-grid/'+name+'/'+kind).then(r=>r.arrayBuffer()));return metadata;}
const ownership=await grid('ownership'),physical=await grid('physicalGrid');
const map=L.map('map',{zoomSnap:0,minZoom:1,maxZoom:13}).setView([14.999938044092211,4.900177749975228],13);
let color='#447744';
const classified=!location.search.includes('unknown');
const options={ownership,orderedOwners:true,coverage:classified?{grid:physical,manifest:{sources:[{name:'Synthetic physical control',url:'https://example.test/physical'}]}}:null,
 color:()=>color,selected:()=>null,locationBorders:()=>false,select:id=>window.selected=id};
const layer=new (location.search.includes('canvas')?PixelCanvasLayer:PixelLayer)(features,options).addTo(map);
window.fixture={layer,map,L,ownership,options,setColor:value=>color=value};
</script>`;
const server=await createServer({cacheDir:path.resolve(scratch,'vite'),server:{host:'127.0.0.1',port:0},
 plugins:[{name:'native-renderer-fixture',configureServer(s){s.middlewares.use((req,res,next)=>{
  if(req.url.startsWith('/fixture?')){res.setHeader('Content-Type','text/html');res.end(html);return;}
  const match=/^\/fixture-grid\/(ownership|physicalGrid)\/(metadata|rows|runs)$/.exec(req.url);
  if(!match){next();return;}
  const [,name,kind]=match,grid=grids[name];
  if(kind==='metadata'){const {rows,runs,...metadata}=grid;res.setHeader('Content-Type','application/json');res.end(JSON.stringify(metadata));}
  else{res.setHeader('Content-Type','application/octet-stream');res.end(Buffer.from(grid[kind].buffer));}
 });}}]});
let context;
const observations=[];
try{
 await server.listen();const port=server.httpServer.address().port;
 context=await chromium.launchPersistentContext(profile,{headless:true,
  ...(process.env.ATLAS_TEST_CHROMIUM?{executablePath:process.env.ATLAS_TEST_CHROMIUM}:{}),
  args:['--use-angle=swiftshader','--enable-unsafe-swiftshader'],viewport:{width:1000,height:750}});
 await context.route('**/*',route=>{const url=new URL(route.request().url());return url.protocol==='http:'&&url.hostname==='127.0.0.1'&&url.port===String(port)?route.continue():route.abort();});
 for(const renderer of ['gpu','canvas'])for(const unknown of [false,true]){
  const page=await context.newPage(),errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto(`http://127.0.0.1:${port}/fixture?${renderer}${unknown?'&unknown':''}`);
  await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.rendered==='true');
  assert.equal(await page.evaluate(()=>!!window.fixture.layer.gpu),renderer==='gpu');
  const readCenter=()=>page.evaluate(()=>{const {layer}=window.fixture,c=layer.canvas;
   if(layer.gpu){layer.draw();const b=new Uint8Array(4);layer.gpu.gl.readPixels(Math.floor(c.width/2),Math.floor(c.height/2),1,1,layer.gpu.gl.RGBA,layer.gpu.gl.UNSIGNED_BYTE,b);return [...b];}
   return [...c.getContext('2d').getImageData(Math.floor(c.width/2),Math.floor(c.height/2),1,1).data];});
  const recovered=await readCenter();assert.deepEqual(recovered,[68,119,68,255],renderer+' recovered native cell fill');
  const before=await page.locator('.atlas-pixel-canvas').evaluate(c=>({...c.dataset}));
  for(let i=0;i<14;i++){
   const expected=i%2?[68,119,68,255]:[119,68,68,255];
   await page.evaluate(i=>{const {layer,setColor}=window.fixture;setColor(i%2?'#447744':'#774444');layer.setStyle();},i);
   await page.waitForFunction(expected=>{const {layer}=window.fixture,c=layer.canvas;let bytes;
    if(layer.gpu){layer.draw();bytes=new Uint8Array(4);layer.gpu.gl.readPixels(Math.floor(c.width/2),Math.floor(c.height/2),1,1,layer.gpu.gl.RGBA,layer.gpu.gl.UNSIGNED_BYTE,bytes);}
    else bytes=c.getContext('2d').getImageData(Math.floor(c.width/2),Math.floor(c.height/2),1,1).data;
    return expected.every((v,n)=>v===bytes[n]);},expected);
   await page.evaluate(()=>window.fixture.layer.click({latlng:window.fixture.L.latLng(14.999938044092211,4.900177749975228)}));
   assert.equal(await page.evaluate(()=>window.selected),'left');
  }
  // Picking remains exact even when Canvas displays a coarser viewport sample.
  await page.evaluate(()=>window.fixture.map.setZoom(7,{animate:false}));
  await page.waitForTimeout(100);
  assert.equal(await page.evaluate(()=>window.fixture.layer.pick(window.fixture.L.latLng(14.999938044092211,4.900177749975228))?.id),'left');
  for(const [latitude,longitude,id]of [[50,60,null],[50,59.25,null],[.5,179.5,'dateline-location'],[.5,-179.5,'dateline-location']]){
   await page.evaluate(([lat,lon])=>window.fixture.map.setView([lat,lon],13,{animate:false}),[latitude,longitude]);
   await page.waitForTimeout(100);
   assert.equal(await page.evaluate(([lat,lon])=>window.fixture.layer.pick(window.fixture.L.latLng(lat,lon))?.id??null,[latitude,longitude]),id);
   await page.evaluate(([lat,lon])=>window.fixture.layer.click({latlng:window.fixture.L.latLng(lat,lon)}),[latitude,longitude]);
   if(id)assert.equal(await page.evaluate(()=>window.selected),id);
   else{
    const pixel=await readCenter();
    if(unknown||longitude===60)assert.equal(pixel[3],0,renderer+' true water/unknown stays transparent');
    else assert.ok([[170,79,36,255],[247,223,179,255]].some(color=>color.every((v,i)=>v===pixel[i])),renderer+' uncovered reference land has gap hatch: '+pixel);
    const expected=unknown?/Unverified geographic coverage/:longitude===60?/Reference water/:/Possible geographic coverage gap/;
    assert.match(await page.locator('.leaflet-popup-content').last().textContent(),expected);
    assert.match(await page.locator('.leaflet-popup-content').last().textContent(),/50[.]00000°/);
   }
  }
  const after=await page.locator('.atlas-pixel-canvas').evaluate(c=>({...c.dataset}));
  assert.equal(after.compilations,before.compilations);
  if(renderer==='gpu'){
   assert.equal(after.ownershipUploads,before.ownershipUploads);assert.equal(after.coverageUploads,before.coverageUploads);
   await page.evaluate(()=>{window.extension=window.fixture.layer.gpu.gl.getExtension('WEBGL_lose_context');if(!window.extension)throw Error('Context loss unavailable');window.extension.loseContext();});
   await page.waitForFunction(()=>window.fixture.layer.lost===true);await page.waitForTimeout(100);
   await page.evaluate(()=>window.extension.restoreContext());await page.waitForFunction(()=>window.fixture.layer.lost===false);
   assert.equal(await page.evaluate(()=>window.fixture.layer.pick(window.fixture.L.latLng(14.999938044092211,4.900177749975228))?.id),'left');
   await page.evaluate(()=>window.fixture.map.setView([14.999938044092211,4.900177749975228],13,{animate:false}));
   await page.waitForTimeout(100);
   assert.deepEqual(await readCenter(),[68,119,68,255],renderer+' restored native fill');
  }
  assert.deepEqual(errors,[]);
  observations.push({renderer,unknown,recovered_rgba:recovered,exact_low_zoom_pick:true,dateline_both_sides:true,
   hole_not_assigned:true,palette_updates:14,compilations:after.compilations,context_restore:renderer==='gpu'});
  await page.close();
 }
 const result={kind:'isolated-native-renderer-controls',backend:'headless Chromium WebGL2 SwiftShader and Canvas2D; not physical-device performance',observations};
 await fs.writeFile(path.join(scratch,'result.json'),JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify(result));
}finally{await context?.close();await server.close();await fs.rm(profile,{recursive:true});}
