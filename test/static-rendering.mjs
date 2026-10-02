import {spawn} from 'node:child_process';
import fs from 'node:fs/promises';
import {gunzipSync} from 'node:zlib';
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {snapshot} from '../database.mjs';
import {findHistoricalMapCase,checkHistoricalMapCase} from './historical-map-check.mjs';
const assetRoot=await fs.stat('dist/client').then(()=> 'dist/client').catch(()=> 'dist');
const server=spawn('python3',['-u','-m','http.server','3199','--directory',assetRoot],{stdio:['ignore','pipe','pipe']});
const apiBase=process.env.ATLAS_TEST_API_URL;
if(assetRoot.endsWith('/client')&&!apiBase){server.kill('SIGTERM');throw Error('Hosted browser verification needs ATLAS_TEST_API_URL pointing at the local Worker API.');}
async function proxyAPI(page){if(!apiBase)return;await page.route('**/api/**',async route=>{const original=new URL(route.request().url()),url=new URL(original.pathname+original.search,apiBase);const response=await route.fetch({url:String(url),headers:{...route.request().headers(),origin:url.origin}});await route.fulfill({response});});}
let browser;
try{
 await new Promise((resolve,reject)=>{server.stdout.on('data',d=>{if(String(d).includes('Serving HTTP'))resolve();});server.once('exit',c=>reject(new Error(`Server exited ${c}`)));});
 browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[],requests=[];page.on('request',r=>requests.push(r.url()));page.on('pageerror',e=>errors.push(e.message));
 await proxyAPI(page);
 const storageRoutes=/\/api\/(?:attributes|names)(?:\?|$)/;
 if(apiBase)await page.route(storageRoutes,route=>route.fulfill({status:503,json:{error:'Historical database temporarily unavailable'}}));
 await page.goto('http://localhost:3199');await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.rendered==='true',null,{timeout:60000});
 const data=()=>page.locator('.atlas-pixel-canvas').evaluate(c=>({...c.dataset}));
 await page.locator('#loading').waitFor({state:'hidden',timeout:60000});
 if(apiBase){
  assert.match(await page.locator('#year-error').textContent(),/Historical database unavailable.*Showing prepared source data/);
  assert.equal(await page.locator('#map-year').textContent(),'2,026 AD');assert.equal((await data()).rendered,'true');
  assert.match(await page.locator('#coverage').textContent(),/49,614 geographic locations/);
  assert.equal(await page.locator('#borders').count(),0,'border checkbox must remain removed');
  await page.unroute(storageRoutes);
  const recovered=Promise.all(['attributes','names'].map(endpoint=>page.waitForResponse(r=>new URL(r.url()).pathname===`/api/${endpoint}`&&r.status()===200)));
  await page.locator('#year-form button').click();await recovered;await page.locator('#loading').waitFor({state:'hidden'});
  assert.equal(await page.locator('#year-error').textContent(),'','retry clears the database outage notice');
  assert.equal((await data()).rendered,'true');
  const hostedRequests=requests.filter(url=>storageRoutes.test(url));assert.ok(hostedRequests.length>=4);
  assert.ok(hostedRequests.every(url=>new URL(url).searchParams.get('scope')==='map'),'atlas queries only map-relevant names and attributes');
  assert.deepEqual(errors,[]);console.log('PASS: prepared map survives historical database 503s and recovers through the real Worker API; default borders have no checkbox.');
 }
 if(process.env.ATLAS_TEST_STORAGE_ONLY!=='1'){
 assert.ok(requests.some(url=>url.endsWith('/ownership-runtime/index.json')),'modern view checks the ownership coverage interval');
 assert.ok(!requests.some(url=>/ownership-(?:history\/(?:part-|evidence)|runtime\/century)/.test(url)),'2026 must not download historical intervals or evidence');
 const baseline=await data();assert.equal(baseline.precompiled,'true');assert.equal(baseline.compilations,'0');assert.ok(!requests.some(url=>/geography\/part-/.test(url)));assert.equal(baseline.renderer,'webgl2');assert.equal(baseline.stride,'1');
 await page.locator('#zoom-in').click();await page.waitForFunction(k=>document.querySelector('.atlas-pixel-canvas').dataset.frame!==k,baseline.frame);
 const next=await data();assert.equal(next.uploads,baseline.uploads);assert.equal(next.compilations,baseline.compilations);
 await page.locator('#search').fill('Hong Kong');await page.locator('[data-result="atlas:territory:HKG"]').click();
 await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas').dataset.locationBorders==='true');
 assert.equal(await page.locator('.breadcrumbs [data-unit]').count(),6);
 const geometryCheck=await page.evaluate(async()=>{const manifest=await(await fetch('./atlas-geography.json')).json();const bytes=await(await fetch('./'+manifest.geometryParts[0])).arrayBuffer();const decoded=JSON.parse(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text());return decoded.length>0&&decoded.every(f=>f.id&&f.geometry?.type);});assert.equal(geometryCheck,true);
 await page.screenshot({path:'/workspace/atlas-fixed-grid-hong-kong.png'});
 const db=new DatabaseSync('data/atlas.sqlite',{readOnly:true});let example;
 try{example=await findHistoricalMapCase(year=>snapshot(db,year,false));}finally{db.close();}
 const historical=await checkHistoricalMapCase(page,example);
 assert.equal(historical.hasPolitical,false);assert.ok(historical.tested>=12);assert.equal(historical.eligible,historical.totalCells);assert.equal(historical.tested,historical.eligible);assert.equal(historical.mismatches,0);assert.equal(historical.error,0);assert.equal(historical.legend,historical.expected);
 const expected=historical.expected.match(/\d+/g).slice(0,3).map(Number);assert.ok(expected.every((channel,i)=>Math.abs(channel-historical.palette[i])<=1));
 assert.ok(requests.some(url=>/ownership-runtime\/century/.test(url)),'historical selection loads cached location intervals');
 assert.equal((await data()).compilations,baseline.compilations,'changing ownership does not recompile geographic cells');
 console.log(`Historical static fill: ${example.name}, ${example.year}, ${example.record.value}, ${historical.tested} canonical cells checked.`);
 const beforeMobile=await data();await page.setViewportSize({width:390,height:844});await page.waitForFunction(frame=>document.querySelector('.atlas-pixel-canvas').dataset.frame!==frame,beforeMobile.frame);
 const mobile=await data();assert.equal(mobile.compilations,beforeMobile.compilations);assert.equal(mobile.uploads,beforeMobile.uploads);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
 await page.screenshot({path:'/workspace/atlas-hosted-mobile.png',fullPage:true});
 if(assetRoot.endsWith('/client')){
  assert.equal(await page.locator('#import-records-button').count(),1);await page.locator('#import-records-button').click();await page.locator('#import-records-json').fill('{');await page.locator('#import-records-review').click();assert.match(await page.locator('#import-records-status').textContent(),/valid JSON/);assert.equal(await page.locator('#import-records-submit').isDisabled(),true);assert.ok(!requests.some(url=>url.includes('/api/records/import')));await page.screenshot({path:'/workspace/atlas-import-mobile.png'});await page.locator('#import-records-dialog .dialog-close').click();
 }
 console.log(`Hosted mobile navigation: ${mobile.renderMs} ms submission; ownership compilations ${mobile.compilations}, uploads unchanged.`);
 await page.close();
 const fallback=await browser.newPage();fallback.on('pageerror',e=>errors.push(e.message));
 await fallback.addInitScript(()=>{const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return type==='webgl2'?null:get.call(this,type,...args);};});
 await proxyAPI(fallback);
 await fallback.goto('http://localhost:3199');await fallback.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.rendered==='true',null,{timeout:60000});
 assert.ok(await fallback.locator('.atlas-pixel-canvas').evaluate(c=>!!c.getContext('2d')));
 await fallback.locator('#search').fill('Hong Kong');await fallback.locator('[data-result="atlas:territory:HKG"]').click();assert.equal(await fallback.locator('#details h3').textContent(),'Hong Kong');
 await fallback.close();
 const dated=await browser.newPage();dated.on('pageerror',e=>errors.push(e.message));
 const history=JSON.parse(gunzipSync(await fs.readFile(`${assetRoot}/atlas-history.json.gz`)));
 history.boundaries.push({location_id:'atlas:city:GBR-Greater London',valid_from:2026,valid_to:2027,is_example:0,source:'Boundary-loading test fixture',geometry:{type:'Polygon',coordinates:[[[-.2,51.4],[.1,51.4],[.1,51.6],[-.2,51.6],[-.2,51.4]]]}});
 await dated.route('**/atlas-history.json.gz',route=>route.fulfill({json:history}));
 await proxyAPI(dated);
 await dated.goto('http://localhost:3199');await dated.locator('#loading').waitFor({state:'hidden',timeout:60000});
 await dated.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.rendered==='true',null,{timeout:60000});
 assert.notEqual(await dated.locator('.atlas-pixel-canvas').getAttribute('data-precompiled'),'true');
 await dated.locator('#search').fill('London');await dated.locator('[data-result="atlas:city:GBR-Greater London"]').click();
 assert.match(await dated.locator('#details').textContent(),/Boundary-loading test fixture/);
 assert.deepEqual(errors,[]);console.log('PASS: production WebGL worker, fixed grid, cached navigation, picking/search, and Canvas fallback.');
 }
}finally{await browser?.close();server.kill('SIGTERM');}
