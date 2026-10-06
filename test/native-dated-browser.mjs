// Actual main year/rebuild functions + actual browser native worker + renderers.
// Only data/DOM endpoints are isolated synthetic fixtures; localhost profile only.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {createServer} from 'vite';
import {chromium} from '@playwright/test';
import {compileNativeRuntime} from '../src/native-runtime.js';
const source=await fs.readFile('src/main.js','utf8');
const extract=(first,last)=>{const a=source.indexOf(first),b=source.indexOf(last,a);assert.ok(a>=0&&b>a);return source.slice(a,b);};
const yearBody=extract('async function loadYear(next) {',"\n$('#year-form')");
const rebuildBody=extract('function rebuildGeometry(preparedNative) {','\nfunction render() {');
const table=gunzipSync(await fs.readFile('coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz'));
const size=262166,latitudes=Float64Array.from({length:size},(_,y)=>table.readDoubleLE(y*8));
const ring=(a,b,c,d)=>[[a,b],[c,b],[c,d],[a,d],[a,b]];
const f=(id,pixelIndex,coordinates)=>({type:'Feature',id,pixelIndex,properties:{name:id,parent_id:'p'},geometry:{type:'Polygon',coordinates}});
const features=[f('A',1,[ring(0,0,2,2)]),f('B',2,[ring(4,0,6,2)]),f('C',3,[ring(8,0,10,2)])];
const base=await compileNativeRuntime(features,{size,latitudes});
const sha=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
base.footprints_sha256=sha(features.map(x=>[x.id,x.geometry]).sort((a,b)=>a[0].localeCompare(b[0])));
base.reference_owner_sha256=sha(features.map(x=>[x.pixelIndex,x.id]));
const scratch='.cache/native-dated-browser';await fs.mkdir(scratch,{recursive:true});
const profile=await fs.mkdtemp(path.resolve(scratch,'profile-'));
const html=`<!doctype html><link rel="stylesheet" href="/node_modules/leaflet/dist/leaflet.css"><style>#map{width:800px;height:600px;background:#637f99}</style><div id="map"></div><script type="module">
import * as L from '/node_modules/leaflet/dist/leaflet-src.esm.js';
import {PixelLayer as GPU} from '/src/pixel-layer.js';import {PixelCanvasLayer} from '/src/pixel-canvas-layer.js';
import {prepareNativeLocationContext as prepareRealContext} from '/src/native-context-client.js';
import {nativeDisplayContext} from '/src/native-location-context.js';
import {locationInventoryChanged,boundaryFootprintsChanged} from '/src/pixel-metadata.js';
import {NATIVE_METHOD} from '/src/ownership-method.js';import {GRID_ZOOM} from '/src/pixel-grid.js';
const original=${JSON.stringify(features)},events=[],nodes=new Map(),colors={A:'#447744',B:'#774444',C:'#444477',D:'#884488'};
const $=id=>{if(!nodes.has(id))nodes.set(id,{checked:false,setAttribute(){}});return nodes.get(id);};
const metadata=await fetch('/grid/metadata').then(r=>r.json());
for(const kind of ['rows','runs'])metadata[kind]=new Uint32Array(await fetch('/grid/'+kind).then(r=>r.arrayBuffer()));
const nativeLatitudes=new Float64Array(await fetch('/latitudes').then(r=>r.arrayBuffer()));
const referenceData={features:original,ownership:metadata,nativeLatitudes,coverage:null,units:[],temporal:{history:[]}};
const PixelLayer=location.search.includes('canvas')?PixelCanvasLayer:GPU;
const map=L.map('map',{zoomSnap:0,minZoom:1,maxZoom:13}).setView([1,1],13);
let data=referenceData,year=2026,temporal,desiredYear,timer,controller,parents=new Map(),features=new Map(),polities,states=new Map(),boundaries=new Map(),geoLayer,layers,selected=null,mode='owner';
const color=f=>colors[f.id],categoryColor=()=>'',state=()=>({}),value=()=>null,displayName=f=>f.id,select=id=>window.picked=id;
const formatYear=String,yearToTick=y=>y,resolveAttributes=()=>new Map();
const resolveTemporal=(reference,y)=>({features:y===2020?original.slice(1):y===2019?[{...original[0],id:'D',pixelIndex:undefined},...original.slice(1)]:original,units:[],entities:new Map()});
const ensureGeometry=async()=>{events.push({geometryRead:true});};
const loadSnapshot=async y=>({boundaries:y===2020?[{location_id:'B',geometry:{type:'Polygon',coordinates:[${JSON.stringify(ring(4,0,7,2))},${JSON.stringify(ring(4.75,.75,5.25,1.25))}]}}]:[],states:[],attributes:[]});
const prepareNativeLocationContext=(input,options)=>prepareRealContext(input,{...options,workerFactory:()=>{
 const worker=new Worker(new URL('/src/native-context-worker.js',import.meta.url),{type:'module'});
 const event={started:true,terminated:false,messages:0};events.push(event);
 worker.addEventListener('message',()=>event.messages++);
 const terminate=worker.terminate.bind(worker);worker.terminate=()=>{event.terminated=true;terminate();};
 return worker;
}});
${rebuildBody}
const render=()=>{geoLayer.setPolitical([]);geoLayer.setStyle();events.push({renderYear:year});};
${yearBody}
rebuildGeometry({grid:baseForReference(),features:original});render();
function baseForReference(){return referenceData.ownership;}
window.fixture={map,L,events,loadYear,get layer(){return geoLayer;},get year(){return year;},get ids(){return data.features.map(f=>f.id);},get error(){return $('#year-error').textContent??'';}};
</script>`;
const server=await createServer({cacheDir:path.resolve(scratch,'vite'),server:{host:'127.0.0.1',port:0},plugins:[{
 name:'native-dated-fixture',configureServer(s){s.middlewares.use((req,res,next)=>{
  if(req.url.startsWith('/fixture?')){res.setHeader('Content-Type','text/html');res.end(html);return;}
  if(req.url==='/latitudes'){res.end(Buffer.from(latitudes.buffer));return;}
  if(req.url==='/grid/metadata'){const {rows,runs,...metadata}=base;res.setHeader('Content-Type','application/json');res.end(JSON.stringify(metadata));return;}
  if(req.url==='/grid/rows'||req.url==='/grid/runs'){res.end(Buffer.from(base[req.url.slice(6)].buffer));return;}
  next();
 });}
}]});
let context;const observations=[];
try{
 await server.listen();const port=server.httpServer.address().port;
 context=await chromium.launchPersistentContext(profile,{headless:true,
  ...(process.env.ATLAS_TEST_CHROMIUM?{executablePath:process.env.ATLAS_TEST_CHROMIUM}:{}),
  args:['--use-angle=swiftshader','--enable-unsafe-swiftshader'],viewport:{width:1000,height:750}});
 await context.route('**/*',route=>{const url=new URL(route.request().url());return url.protocol==='http:'&&url.hostname==='127.0.0.1'&&url.port===String(port)?route.continue():route.abort();});
 for(const renderer of ['gpu','canvas']){
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:'+port+'/fixture?'+renderer);
  await page.waitForFunction(()=>window.fixture?.layer.canvas.dataset.rendered==='true');
  const point=async(lon,lat,id,rgba)=>{
   await page.evaluate(([lon,lat])=>window.fixture.map.setView([lat,lon],13,{animate:false}),[lon,lat]);
   await page.waitForTimeout(100);
   assert.equal(await page.evaluate(([lon,lat])=>window.fixture.layer.pick(window.fixture.L.latLng(lat,lon))?.id??null,[lon,lat]),id);
   await page.evaluate(([lon,lat])=>window.fixture.layer.click({latlng:window.fixture.L.latLng(lat,lon)}),[lon,lat]);
   if(id)assert.equal(await page.evaluate(()=>window.picked),id);
   const pixel=await page.evaluate(()=>{const layer=window.fixture.layer,c=layer.canvas;
    if(layer.gpu){layer.draw();const bytes=new Uint8Array(4);layer.gpu.gl.readPixels(Math.floor(c.width/2),Math.floor(c.height/2),1,1,layer.gpu.gl.RGBA,layer.gpu.gl.UNSIGNED_BYTE,bytes);return [...bytes];}
    return [...c.getContext('2d').getImageData(Math.floor(c.width/2),Math.floor(c.height/2),1,1).data];});
   if(rgba)assert.deepEqual(pixel,rgba,renderer+' fill matches displayed ID '+id);else assert.equal(pixel[3],0);
  };
  await point(1,1,'A',[68,119,68,255]);
  await page.evaluate(()=>{window.pending=window.fixture.loadYear(2020);window.retainedYear=window.fixture.year;});
  assert.equal(await page.evaluate(()=>window.retainedYear),2026);
  await page.evaluate(()=>window.pending);assert.equal(await page.evaluate(()=>window.fixture.year),2020);
  await point(1,1,null);await point(5,1,null);await point(4.5,1,'B',[119,68,68,255]);await point(9,1,'C',[68,68,119,255]);
  await page.evaluate(()=>window.fixture.loadYear(2019));
  await point(1,1,'D',[136,68,136,255]);await point(5,1,'B',[119,68,68,255]);
  const started=await page.evaluate(()=>window.fixture.events.filter(e=>e.started).length);
  await page.evaluate(()=>{window.stale=window.fixture.loadYear(2020);});
  await page.waitForFunction(n=>window.fixture.events.filter(e=>e.started).length>n,started,{polling:5});
  await page.evaluate(()=>window.fixture.loadYear(2026));await page.evaluate(()=>window.stale);
  assert.equal(await page.evaluate(()=>window.fixture.year),2026);
  assert.deepEqual(await page.evaluate(()=>window.fixture.ids),['A','B','C']);
  await point(1,1,'A',[68,119,68,255]);await point(5,1,'B',[119,68,68,255]);await point(9,1,'C',[68,68,119,255]);
  assert.equal(await page.evaluate(()=>window.fixture.events.some(e=>e.renderYear===2020&&e!==window.fixture.events.find(e=>e.renderYear===2020))),false,'stale year never rendered again');
  assert.ok(await page.evaluate(()=>window.fixture.events.filter(e=>e.started).every(e=>e.terminated)));
  assert.equal(await page.evaluate(()=>window.fixture.error),'');assert.deepEqual(errors,[]);
  observations.push({renderer,actual_main_year_and_rebuild:true,actual_browser_native_worker:true,
   removed_ID_and_changed_geometry:true,real_hole_preserved:true,same_count_ID_replacement:true,
   dense_ID_pick_and_palette:true,stale_year_canceled:true,reference_restored:true,worker_cleanup:true});
  await page.close();
 }
 const result={kind:'joined-native-dated-worker-renderer-control',main_source_sha256:createHash('sha256').update(source).digest('hex'),observations,
  limits:['Synthetic bounded localhost fixture; actual main year/rebuild functions, worker/client and renderers; other UI and data endpoints isolated.',
   'Software WebGL2 and Canvas correctness only, not broad dated-boundary or device performance, factual geography or delivery.']};
 await fs.writeFile(path.join(scratch,'result.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
}finally{await context?.close();await server.close();await fs.rm(profile,{recursive:true});}
