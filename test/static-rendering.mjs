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
 const storageRoutes=/\/api\/map\/snapshot(?:\?|$)/;
 if(apiBase)await page.route(storageRoutes,route=>route.fulfill({status:503,json:{error:'Historical database temporarily unavailable'}}));
 await page.goto('http://localhost:3199');await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.rendered==='true',null,{timeout:60000});
 const data=()=>page.locator('.atlas-pixel-canvas').evaluate(c=>({...c.dataset}));
 await page.locator('#loading').waitFor({state:'hidden',timeout:60000});
 const initialRequests=[...requests];
 if(apiBase){
  assert.match(await page.locator('#year-error').textContent(),/Historical content could not load.*Dated attribute values are unavailable.*labeled reference context and geography remain browsable/);
  assert.equal(await page.locator('#map-year').textContent(),'2,026 AD');assert.equal((await data()).rendered,'true');
  assert.match(await page.locator('#coverage').textContent(),/[\d,]+ geographic locations.*0 locations with ownership/);
  assert.equal(await page.locator('#borders').count(),0,'border checkbox must remain removed');
  await page.locator('#search').fill('London');await page.locator('[data-result="atlas:city:GBR-Greater London"]').click();
  assert.equal(await page.locator('.breadcrumbs [data-unit]').count(),6);
  assert.equal(await page.locator('.profile-name-context').textContent(),'Present-day reference: London');
  const assertEnvironmentalContext=async()=>{
   const values=await page.locator('.profile-attributes dd').allTextContents();
   assert.equal(values.length,8);
   for(let index=5;index<8;index++){
    assert.ok(values[index].trim()&&!values[index].includes('Unknown'),'London has a classified environmental reference');
    assert.equal(await page.locator('.profile-attributes dd').nth(index).locator('.reference-badge').textContent(),'Reference');
   }
  };
  assert.deepEqual((await page.locator('.profile-attributes dd').allTextContents()).slice(0,5),Array(5).fill('Unknown'),'cold outage cannot restore potentially withdrawn prepared values or modern ownership');
  await assertEnvironmentalContext();
  await page.unroute(storageRoutes);
  const recovered=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/map/snapshot'&&r.status()===200);
  await page.locator('#year-form button').click();await recovered;await page.locator('#loading').waitFor({state:'hidden'});
  assert.equal(await page.locator('#year-error').textContent(),'','retry clears the database outage notice');
  assert.equal((await data()).rendered,'true');
  const completeValues=await page.locator('.profile-attributes dd').allTextContents();assert.notEqual(completeValues[0],'Unknown','a complete API snapshot permits the modern reference owner');
  await page.route(storageRoutes,route=>new URL(route.request().url()).searchParams.has('cursor')?route.fulfill({status:503,json:{error:'Temporary failure after a partial snapshot'}}):route.fallback());
  await page.locator('#year-form button').click();await page.locator('#loading').waitFor({state:'hidden'});
  assert.match(await page.locator('#year-error').textContent(),/Historical content could not refresh.*last complete snapshot for this year/);
  assert.deepEqual(await page.locator('.profile-attributes dd').allTextContents(),completeValues,'a failed later page reuses only a complete consistent snapshot');
  await page.locator('#year-input').fill('2025');await page.locator('#year-form button').click();await page.locator('#loading').waitFor({state:'hidden'});
  assert.match(await page.locator('#year-error').textContent(),/Dated attribute values are unavailable/);
  assert.deepEqual((await page.locator('.profile-attributes dd').allTextContents()).slice(0,5),Array(5).fill('Unknown'),'a different year cannot reuse the previous complete snapshot');
  await assertEnvironmentalContext();
  await page.unroute(storageRoutes);
  for(const selectedYear of ['2025','3000 BC']){
   await page.locator('#year-input').fill(selectedYear);await page.locator('#year-form button').click();await page.locator('#loading').waitFor({state:'hidden'});
   assert.equal(await page.locator('#year-error').textContent(),'');
   await assertEnvironmentalContext();
   const evidence=page.locator('.profile-evidence');
   assert.equal(await evidence.evaluate(element=>element.open),false);
   await evidence.locator(':scope > summary').click();
   assert.equal(await evidence.locator('p').filter({hasText:'Reference context; the historical state for this year remains unknown.'}).count(),3,'reference presentation must not imply supported historical environmental claims');
   assert.match(await evidence.textContent(),/Climate normal: 1991–2020/);
   await evidence.locator(':scope > summary').click();
   for(const attribute of ['topography','vegetation','climate']){
    await page.locator(`[data-mode="${attribute}"]`).click();
    assert.match(await page.locator('#legend-items').textContent(),/[\d,]+ locations show reference context/);
   }
   await page.locator('[data-mode="owner"]').click();
  }
  await page.locator('#year-input').fill('2026');await page.locator('#year-form button').click();await page.locator('#loading').waitFor({state:'hidden'});
  assert.equal(await page.locator('#year-error').textContent(),'');
  assert.deepEqual(await page.locator('.profile-attributes dd').allTextContents(),completeValues);
  const hostedRequests=requests.filter(url=>storageRoutes.test(url));assert.ok(hostedRequests.length>=6);
  assert.ok(hostedRequests.every(url=>{const params=new URL(url).searchParams;return params.has('year')&&params.has('examples')&&Number(params.get('limit'))>0&&Number(params.get('limit'))<=1000;}),'compact pages have a bounded entity limit and explicit year/example scope');
  assert.ok(!requests.some(url=>/\/api\/(?:attributes|names|retirements)(?:\?|$)/.test(url)),'the built map uses the shared compact snapshot rather than legacy claim streams');
  assert.deepEqual(errors,[]);console.log('PASS: cold outages preserve geography and separately labeled environmental context; partial snapshot-page failures retain complete same-year values; 2025/3000 BC profiles, evidence and legends keep reference context explicit.');
 }
 const fields=['Owner','Population','Primary culture','Primary religion','Location rank','Topography','Vegetation','Climate'];
 const profiles=[['Hong Kong','atlas:territory:HKG','Asia'],['London','atlas:city:GBR-Greater London','Europe'],['New York City','atlas:city:USA-New-York-City','North America'],['São Paulo','gb:BRA:ADM2:56859067B92864763247255','South America'],['Cairo','atlas:city:EGY-1533','Africa'],['Melbourne','gb:AUS:ADM2:25037944B74771981745191','Oceania'],['Kabe','gb:NAM:ADM2:8085530B93169958876618','Africa']];
 for(const viewport of [{width:1440,height:1080},{width:390,height:844}]){
  await page.setViewportSize(viewport);
  for(const [query,id,continent] of profiles){
   await page.locator('#search').fill(query);await page.locator(`[data-result="${id}"]`).click();
   const main=page.locator('.profile-main'),evidence=page.locator('.profile-evidence');
   assert.equal(await main.locator('.breadcrumbs [data-unit]').count(),6);assert.match(await main.locator('.breadcrumbs').textContent(),new RegExp(continent));
   assert.deepEqual(await main.locator('dt').allTextContents(),fields);assert.equal(await main.locator('dd').count(),8);
   assert.ok((await main.locator('dd').allTextContents()).every(value=>value.trim().length));
   assert.match(await main.locator('.profile-name-context').textContent(),/^Present-day reference: .+/);
   assert.doesNotMatch(await main.innerText(),/Historical name unknown|Reference location|Habitation|Source date|Source coverage|Method:|License:|review notes|source geometry|ILLUSTRATIVE|DERIVED OWNERSHIP|NO DATED RECORD|\bNAM\b/);
   assert.equal(await page.locator('#details details').count(),1);assert.equal(await evidence.evaluate(element=>element.open),false);
   assert.equal(await evidence.locator('.profile-evidence-content').isVisible(),false);assert.ok(await evidence.locator('a').count()>0);
   await evidence.locator(':scope > summary').click();assert.equal(await evidence.locator('.profile-evidence-content').isVisible(),true);
   assert.ok((await evidence.locator('a').evaluateAll(items=>items.map(item=>item.href))).every(url=>/^https?:\/\//i.test(url)));
   assert.equal(await page.locator('#details').evaluate(element=>element.scrollWidth<=element.clientWidth),true);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await evidence.locator(':scope > summary').click();
  }
 }
 await page.setViewportSize({width:1440,height:1080});
 for(const mode of ['owner','population','culture','religion','rank','topography','vegetation','climate','location','province','area','region','subcontinent','continent']){
  await page.locator(`[data-mode="${mode}"]`).click();assert.equal(await page.locator(`[data-mode="${mode}"]`).getAttribute('aria-pressed'),'true');
 }
 await page.locator('[data-mode="owner"]').click();assert.deepEqual(errors,[]);
 console.log('PASS: built profiles across all six continents and Namibia keep exactly eight attributes, six tiers and collapsed citations without desktop/mobile overflow; all 14 modes respond.');
 if(process.env.ATLAS_TEST_STORAGE_ONLY!=='1'){
 assert.ok(initialRequests.some(url=>url.endsWith('/ownership-runtime/index.json')),'modern view checks the ownership coverage interval');
 assert.ok(!initialRequests.some(url=>/ownership-(?:history\/(?:part-|evidence)|runtime\/century)/.test(url)),'the initial 2026 view must not download historical intervals or evidence');
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
