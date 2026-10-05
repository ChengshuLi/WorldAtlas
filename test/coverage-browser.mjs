// Isolated local fixture. No user browser, account profile or production requests.
import assert from 'node:assert/strict';
import {createServer} from 'vite';
import {chromium} from '@playwright/test';
const html=`<!doctype html><link rel="stylesheet" href="/node_modules/leaflet/dist/leaflet.css"><style>#map{width:800px;height:600px;background:#637f99}</style><div id="map"></div><script type="module">
import * as L from '/node_modules/leaflet/dist/leaflet-src.esm.js';
import {PixelLayer} from '/src/pixel-layer.js';
import {PixelCanvasLayer} from '/src/pixel-canvas-layer.js';
import {createGridIndex} from '/src/pixel-grid.js';
import {compileOwnership,packOwnership} from '/src/pixel-ownership.js';
function rectangle(id,west,east){return {type:'Feature',id,properties:{name:id,parent_id:'province'},geometry:{type:'Polygon',coordinates:[[[west,51.3],[east,51.3],[east,51.7],[west,51.7],[west,51.3]]]}};}
const features=[rectangle('location',-.2,.02)];
const physical=[rectangle('land',-.2,.25),rectangle('water',.25,.4)];physical[0].pixelIndex=1;physical[1].pixelIndex=2;
const coverage={grid:packOwnership(compileOwnership(createGridIndex(physical))),manifest:{sources:[{name:'Fixture physical reference',url:'https://example.test/physical'}]}};
const map=L.map('map',{zoomSnap:0,minZoom:1,maxZoom:13}).setView([51.5,.12],10);
let color='#447744';
const options={ownership:packOwnership(compileOwnership(createGridIndex(features))),coverage:location.search.includes('unknown')?null:coverage,color:()=>color,selected:()=>null,locationBorders:()=>true,select:id=>window.selected=id};
const layer=new (location.search.includes('canvas')?PixelCanvasLayer:PixelLayer)(features,options).addTo(map);
window.fixture={map,layer,L,options,setColor:value=>color=value};
</script>`;
const server=await createServer({cacheDir:'.cache/coverage-vite',server:{host:'127.0.0.1',port:0},plugins:[{name:'coverage-fixture',configureServer(server){server.middlewares.use('/fixture',(_req,res)=>{res.setHeader('Content-Type','text/html');res.end(html);});}}]});
await server.listen();const port=server.httpServer.address().port,browser=await chromium.launch(process.env.ATLAS_TEST_CHROMIUM?{executablePath:process.env.ATLAS_TEST_CHROMIUM}:{});
try{
 for(const renderer of ['gpu','canvas'])for(const unknown of [false,true]){
  const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`http://127.0.0.1:${port}/fixture?${renderer}${unknown?'&unknown':''}`);
  await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.rendered==='true');
  assert.equal(await page.evaluate(()=>!!window.fixture.layer.gpu),renderer==='gpu');
  const before=await page.locator('.atlas-pixel-canvas').evaluate(c=>({...c.dataset}));
  const pixels=await page.evaluate(()=>{
   const {layer}=window.fixture,canvas=layer.canvas,w=canvas.width,h=canvas.height;
   if(layer.gpu){layer.draw();const bytes=new Uint8Array(20*20*4);layer.gpu.gl.readPixels(Math.floor(w/2)-10,Math.floor(h/2)-10,20,20,layer.gpu.gl.RGBA,layer.gpu.gl.UNSIGNED_BYTE,bytes);return [...bytes];}
   return [...canvas.getContext('2d').getImageData(Math.floor(w/2)-10,Math.floor(h/2)-10,20,20).data];
  });
  const colors=new Set();for(let i=0;i<pixels.length;i+=4)if(pixels[i+3])colors.add(pixels.slice(i,i+3).join(','));
  if(!unknown){assert.ok(colors.has('247,223,179'),renderer+' gap background');assert.ok(colors.has('170,79,36'),renderer+' visible hatch');}else assert.equal(colors.size,0);
  await page.evaluate(()=>window.fixture.layer.click({latlng:window.fixture.L.latLng(51.5,.12)}));
  assert.match(await page.locator('.leaflet-popup-content').last().textContent(),unknown?/Unverified geographic coverage/:/Possible geographic coverage gap/);
  assert.equal(await page.evaluate(()=>window.selected),undefined);
  await page.evaluate(()=>{const {layer,L}=window.fixture;layer.click({latlng:L.latLng(51.5,.3)});});
  assert.match(await page.locator('.leaflet-popup-content').last().textContent(),unknown?/Unverified geographic coverage/:/Reference water/);
  await page.evaluate(()=>{const {layer,L}=window.fixture;layer.click({latlng:L.latLng(51.5,-.1)});});
  assert.equal(await page.evaluate(()=>window.selected),'location');
  for(let i=0;i<14;i++)await page.evaluate(i=>{const {layer,map,setColor}=window.fixture;setColor(i%2?'#447744':'#774444');layer.setStyle();map.setZoom(10+(i%2)*.25,{animate:false});},i);
  await page.waitForTimeout(250);
  const after=await page.locator('.atlas-pixel-canvas').evaluate(c=>({...c.dataset}));
  assert.equal(after.compilations,before.compilations);assert.equal(after.ownershipUploads,before.ownershipUploads);assert.equal(after.coverageUploads,before.coverageUploads);
  if(renderer==='gpu'){
    await page.evaluate(()=>{const {layer}=window.fixture;window.contextExtension=layer.gpu.gl.getExtension('WEBGL_lose_context');if(!window.contextExtension)throw Error('Context loss control unavailable');window.contextExtension.loseContext();});
    await page.waitForFunction(()=>window.fixture.layer.lost===true);
    await page.waitForTimeout(100);
    await page.evaluate(()=>window.contextExtension.restoreContext());
    await page.waitForFunction(()=>window.fixture.layer.lost===false);
    assert.equal(await page.evaluate(()=>window.fixture.layer.gpu.coverageUploads),unknown?0:2);
    await page.evaluate(()=>window.fixture.layer.click({latlng:window.fixture.L.latLng(51.5,.12)}));
    assert.match(await page.locator('.leaflet-popup-content').last().textContent(),unknown?/Unverified geographic coverage/:/Possible geographic coverage gap/);
  }
  assert.deepEqual(errors,[]);await page.close();console.log(renderer+(unknown?' unknown':' classified')+': hatch, gap/water explanation, ordinary selection and cached ownership passed');
 }
}finally{await browser.close();await server.close();}
