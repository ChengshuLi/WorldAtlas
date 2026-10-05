// Isolated fixture: never attach to a user's browser or fetch production content.
import assert from 'node:assert/strict';
import {createServer} from 'vite';
import {chromium} from '@playwright/test';

const html=`<!doctype html><link rel="stylesheet" href="/node_modules/leaflet/dist/leaflet.css"><style>#map{width:800px;height:600px}.atlas-wheel-zoom canvas{transition:none}</style><div id="map"></div>
<script type="module">
import * as L from '/node_modules/leaflet/dist/leaflet-src.esm.js';
import {installWheelZoom} from '/src/wheel-zoom.js';
import {PixelLayer} from '/src/pixel-layer.js';
import {PixelCanvasLayer} from '/src/pixel-canvas-layer.js';
import {createGridIndex} from '/src/pixel-grid.js';
import {compileOwnership,packOwnership} from '/src/pixel-ownership.js';
const map=L.map('map',{zoomSnap:0,scrollWheelZoom:false,minZoom:1,maxZoom:13,zoomControl:false,maxBounds:[[-89,-210],[89,210]]}).setView([51.5,0],10);
installWheelZoom(map);
const features=[{type:'Feature',id:'fixture',properties:{name:'Fixture',parent_id:'province'},geometry:{type:'Polygon',coordinates:[[[-.1,51.4],[.1,51.4],[.1,51.6],[-.1,51.6],[-.1,51.4]]]}}];
const options={ownership:packOwnership(compileOwnership(createGridIndex(features))),color:()=> '#447744',selected:()=>null,locationBorders:()=>true,select:id=>window.selected=id};
const layer=new (location.search.includes('canvas')?PixelCanvasLayer:PixelLayer)(features,options).addTo(map);
window.fixture={map,layer,L};
</script>`;
const server=await createServer({server:{host:'127.0.0.1',port:3887,strictPort:true},plugins:[{name:'wheel-fixture',configureServer(server){server.middlewares.use('/fixture',(_req,res)=>{res.setHeader('Content-Type','text/html');res.end(html);});}}]});
await server.listen();
const browser=await chromium.launch();
try{
 for(const renderer of ['gpu','canvas']){
  const page=await browser.newPage(),errors=[];
  page.on('pageerror',e=>{errors.push(e.message);console.error(e.message);});
  page.on('console',message=>{if(message.type()==='error')console.error(message.text());});
  await page.goto('http://127.0.0.1:3887/fixture?'+renderer);
  await page.waitForFunction(()=>document.querySelector('canvas')?.dataset.rendered==='true',null,{timeout:30000}).catch(async error=>{console.error(await page.evaluate(()=>({fixture:!!window.fixture,canvas:[...document.querySelectorAll('canvas')].map(c=>({...c.dataset})),html:document.body.innerHTML.slice(0,1000)})));throw error;});
  const point={x:450,y:280};
  const anchor=await page.evaluate(p=>{const {map}=window.fixture;const bounds=map.getContainer().getBoundingClientRect();const ll=map.containerPointToLatLng([p.x-bounds.x,p.y-bounds.y]);return {lat:ll.lat,lng:ll.lng};},point);
  const counters=await page.locator('canvas').evaluate(c=>({...c.dataset}));
  await page.mouse.move(point.x,point.y);
  for(let i=0;i<4;i++){await page.mouse.wheel(0,-40);await page.waitForTimeout(15);}
  await page.waitForFunction(()=>!document.querySelector('#map').classList.contains('atlas-wheel-zoom'));
  const result=await page.evaluate(({point,anchor})=>{const {map,L,layer}=window.fixture;const bounds=map.getContainer().getBoundingClientRect();return {zoom:map.getZoom(),anchor:map.latLngToContainerPoint(anchor).distanceTo(L.point(point.x-bounds.x,point.y-bounds.y)),picked:layer.pick(map.getCenter())?.id};},{point,anchor});
  assert.ok(Math.abs(result.zoom-12)<.001,JSON.stringify(result));
  assert.ok(result.anchor<=1,JSON.stringify(result));
  assert.equal(result.picked,'fixture');
  await page.waitForTimeout(200);
  const after=await page.locator('canvas').evaluate(c=>({...c.dataset}));
  assert.equal(after.compilations,counters.compilations);
  assert.equal(after.ownershipUploads,counters.ownershipUploads);
  // Reversing an unfinished gesture must immediately move in the new direction.
  await page.mouse.wheel(0,-120);await page.waitForTimeout(20);
  const reversalStart=await page.evaluate(()=>window.fixture.map.getZoom());
  await page.mouse.wheel(0,120);await page.waitForTimeout(50);
  assert.ok(await page.evaluate(z=>window.fixture.map.getZoom()<z,reversalStart));
  // External camera actions supersede outstanding wheel animation.
  await page.evaluate(()=>window.fixture.map.setView([51.5,0],8,{animate:false}));
  await page.waitForTimeout(300);
  assert.equal(await page.evaluate(()=>window.fixture.map.getZoom()),8);
  await page.evaluate(()=>window.fixture.map.zoomIn());await page.waitForTimeout(400);
  assert.equal(await page.evaluate(()=>window.fixture.map.getZoom()),9);
  await page.locator('#map').dispatchEvent('wheel',{deltaY:-3,deltaMode:1});
  await page.waitForTimeout(400);
  assert.ok(Math.abs(await page.evaluate(()=>window.fixture.map.getZoom())-10.5)<.001);
  await page.locator('#map').dispatchEvent('wheel',{deltaY:-120,ctrlKey:true});
  await page.waitForTimeout(100);
  assert.ok(Math.abs(await page.evaluate(()=>window.fixture.map.getZoom())-10.5)<.001);
  await page.locator('#map').dispatchEvent('wheel',{deltaY:-1,deltaMode:2});
  await page.waitForTimeout(400);
  assert.equal(await page.evaluate(()=>window.fixture.map.getZoom()),13);
  await page.locator('#map').dispatchEvent('wheel',{deltaY:10000,deltaMode:0});
  await page.waitForTimeout(600);
  assert.equal(await page.evaluate(()=>window.fixture.map.getZoom()),1);
  await page.evaluate(()=>window.fixture.map.setView([51.5,0],10,{animate:false}));
  await page.waitForTimeout(200);
  await page.mouse.click(408,308);
  assert.equal(await page.evaluate(()=>window.selected),'fixture');
  await page.mouse.wheel(0,-120);
  await page.waitForTimeout(20);
  await page.mouse.down();await page.mouse.move(440,320,{steps:3});await page.mouse.up();
  await page.waitForTimeout(400);
  assert.equal(await page.locator('#map').evaluate(e=>e.classList.contains('atlas-wheel-zoom')),false);
  await page.evaluate(()=>{document.querySelector('#map').style.width='700px';window.fixture.map.invalidateSize();});
  await page.waitForTimeout(200);
  assert.equal(await page.evaluate(()=>window.fixture.map.getSize().x),700);
  await page.mouse.wheel(0,-120);
  await page.evaluate(()=>window.fixture.map.remove());
  await page.waitForTimeout(100);
  assert.deepEqual(errors,[]);
  await page.close();
  console.log(renderer+': pointer anchor, cumulative input, reversal, external camera, buttons, wheel units, browser zoom and cached ownership passed');
 }
}finally{await browser.close();await server.close();}
