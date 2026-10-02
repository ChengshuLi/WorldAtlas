import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import {findHistoricalMapCase,checkHistoricalMapCase} from './historical-map-check.mjs';
import {borderSamples,readBorderPixels} from './border-map-check.mjs';
import { chromium } from '@playwright/test';
import { parseYear, formatYear } from '../src/model.js';
const port=process.env.ATLAS_TEST_PORT||'3198';
let server,browser,page;
const errors=[];
before(async()=>{
  server=spawn(process.execPath,['server.mjs'],{env:{...process.env,PORT:port,ATLAS_TEST_MODE:'1'},stdio:['ignore','pipe','pipe']});
  let serverError='';server.stderr.on('data',b=>{serverError=(serverError+String(b)).slice(-4000);});
  await new Promise((resolve,reject)=>{server.stdout.on('data',b=>{if(String(b).includes('listening'))resolve();});server.once('exit',code=>reject(new Error(`Server exited: ${code}\n${serverError}`)));});
  browser=await chromium.launch(); page=await browser.newPage({viewport:{width:1440,height:1080}});
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto(`http://localhost:${port}`); await page.locator('#loading').waitFor({state:'hidden'});
  await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.rendered==='true',null,{timeout:60000});
});
after(async()=>{await browser?.close();server?.kill('SIGTERM');});
async function goYear(input) {
 const year=parseYear(input);
 const response=year===null?null:page.waitForResponse(r=>{const url=new URL(r.url());return url.pathname==='/api/snapshot'&&Number(url.searchParams.get('year'))===year&&r.status()===200;});
 await page.locator('#year-input').fill(input);await page.locator('#year-form button').click();
 if(response)await response;
 if(year===null)await page.waitForFunction(()=>document.querySelector('#year-error').textContent.length>0);
 else{await page.waitForFunction(expected=>document.querySelector('#map-year').textContent===expected,formatYear(year));await page.locator('#loading').waitFor({state:'hidden'});}
}
test('world renders at full scale with every map mode',async()=>{
  assert.match(await page.locator('#coverage').textContent(),/[\d,]+ geographic locations/);
  for (const mode of ['owner','population','culture','religion','rank','topography','vegetation','climate','location','province','area','region','subcontinent','continent']) {
    await page.locator(`[data-mode="${mode}"]`).click();assert.equal(await page.locator(`[data-mode="${mode}"]`).getAttribute('aria-pressed'),'true');
  }
  await page.locator('[data-mode="owner"]').click();
  await page.screenshot({path:'/workspace/atlas-desktop.png',fullPage:true});
});
test('search, region selection, hierarchy, and examples show the requested London record',async()=>{
  await page.locator('#search').fill('London'); await page.locator('[data-result="atlas:city:GBR-Greater London"]').click();
  assert.equal(await page.locator('#details h3').textContent(),'London');
  assert.match(await page.locator('.breadcrumbs').textContent(),/Europe.*Northern Europe.*Britain.*London and South East England.*Greater London.*London/);
  await page.locator('#example-tour').click();await page.locator('#loading').waitFor({state:'hidden'});
  assert.match(await page.locator('#details').textContent(),/42,054/);assert.match(await page.locator('#details').textContent(),/ILLUSTRATIVE EXAMPLE/);
  assert.match(await page.locator('#map-note').textContent(),/Whole-location ownership/);
  await page.locator('#examples').uncheck();await page.locator('#loading').waitFor({state:'hidden'});
  assert.match(await page.locator('#details').textContent(),/DERIVED OWNERSHIP|NO DATED RECORD/);assert.doesNotMatch(await page.locator('#details').textContent(),/42,054/);
});
test('Huidong inspector and hierarchy modes contain every tier',async()=>{
  await page.locator('#search').fill('Huidongxian');
  const buttons=await page.locator('[data-result]').all();assert.equal(buttons.length,2);
  const ids=await Promise.all(buttons.map(b=>b.getAttribute('data-result')));
  for(const id of ids){
    await page.locator('#search').fill('Huidongxian');await page.locator(`[data-result="${id}"]`).click();
    assert.equal(await page.locator('.breadcrumbs [data-unit]').count(),6);
    assert.doesNotMatch(await page.locator('.breadcrumbs').textContent(),/Not mapped|Unknown/);
    for(const mode of ['province','area','region','subcontinent','continent']){
      await page.locator(`[data-mode="${mode}"]`).click();
      assert.equal(await page.locator('#legend-items .unknown').count(),0);
    }
  }
});

test('input and slider cover the full interval, reject zero, and never skip BC/AD',async()=>{
  await goYear('3000 BC');assert.equal(await page.locator('#year-slider').inputValue(),'0');
  await goYear('0');assert.match(await page.locator('#year-error').textContent(),/no year zero/);
  await goYear('1 BC');await page.locator('#next').click();await page.waitForFunction(()=>document.querySelector('#map-year').textContent==='1 AD');await page.locator('#loading').waitFor({state:'hidden'});assert.equal(await page.locator('#map-year').textContent(),'1 AD');
  await page.locator('#year-slider').fill('5025');await page.waitForFunction(()=>document.querySelector('#map-year').textContent==='2,026 AD');
  await goYear('2027');assert.match(await page.locator('#year-error').textContent(),/2026 AD/);
  await goYear('2026');
});
test('mobile layout, data information, zoom, fit, and default borders work without browser errors',async()=>{
  await page.locator('#about').click();assert.equal(await page.locator('#data-dialog').evaluate(e=>e.open),true);await page.keyboard.press('Escape');
  await page.locator('#zoom-in').click();await page.locator('#zoom-out').click();await page.locator('#home').click();
  await page.setViewportSize({width:390,height:844});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
  await page.screenshot({path:'/workspace/atlas-mobile.png',fullPage:true});
  assert.deepEqual(errors,[]);
});

test('Hong Kong and Xianggang search return the same single coherent territory',async()=>{
  for(const name of ['Hong Kong','Xianggang']){
    await page.locator('#search').fill(name);
    const ids=await page.locator('[data-result]').evaluateAll(nodes=>nodes.map(n=>n.dataset.result));
    assert.deepEqual(ids,['atlas:territory:HKG']);

  }
  await page.locator('[data-result]').first().click();
  assert.equal(await page.locator('.breadcrumbs [data-unit]').count(),6);
});

test('pixel map uses the same cell for hover and selection, with zoom-aware hierarchy borders',async()=>{
  await page.setViewportSize({width:1440,height:1080});
  await page.locator('[data-mode="location"]').click();
  await page.locator('#search').fill('Hong Kong');await page.locator('[data-result]').first().click();
  await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.locationBorders==='true');
  assert.equal(await page.locator('.atlas-pixel-canvas').getAttribute('data-grid-zoom'),'7');
  assert.equal(await page.locator('.atlas-pixel-canvas').getAttribute('data-province-borders'),'true');
  await page.screenshot({path:'/workspace/atlas-pixel-hong-kong.png',fullPage:true});
  await page.locator('#close-details').click();
  const box=await page.locator('#map').boundingBox();let hit=false;
  for(const [dx,dy] of [[0,0],[-40,0],[40,0],[0,-40],[0,40],[-80,-60],[80,60]]){
    const x=box.x+box.width*.5+dx,y=box.y+box.height*.5+dy;
    await page.mouse.move(x,y);
    if(await page.locator('.leaflet-tooltip').count()){
      const name=await page.locator('.leaflet-tooltip').textContent();await page.mouse.click(x,y);
      assert.equal(await page.locator('#details h3').textContent(),name);hit=true;break;
    }
  }
  assert.ok(hit,'a visible land cell should be pickable');
  await page.locator('#home').click();
  await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.locationBorders==='false');
  assert.equal(await page.locator('.atlas-pixel-canvas').getAttribute('data-province-borders'),'true');
  assert.deepEqual(errors,[]);
});

test('default local borders change real same-province pixels and province borders are stronger',async()=>{
 await page.setViewportSize({width:1440,height:1080});await goYear('2026 AD');await page.locator('[data-mode="owner"]').click();
 let samples;
 for(const [name,id]of [['Rome','atlas:location:ITA:SLL:1209'],['São Paulo','gb:BRA:ADM2:56859067B92864763247255'],['Melbourne','gb:AUS:ADM2:25037944B74771981745191']]){
  await page.locator('#search').fill(name);await page.locator(`[data-result="${id}"]`).click();
  await page.locator('.breadcrumbs button').filter({has:page.locator('small',{hasText:/^province$/})}).click();
  await page.waitForFunction(()=>Number(document.querySelector('.atlas-pixel-canvas')?.dataset.cellPixels)>=1);
  await page.waitForTimeout(400);samples=await borderSamples(page);
  if(samples.found.location&&samples.found.province)break;
 }
 assert.ok(samples.found.location&&samples.found.province,'actual viewport must contain same-owner local and province boundaries');assert.equal(samples.error,0);assert.ok(samples.zoom>=7);
 const on=await readBorderPixels(page,samples);const off=await readBorderPixels(page,samples,false);
 assert.equal(on.localBorders,true);assert.equal(off.localBorders,false);assert.equal(on.error,0);assert.equal(off.error,0);
 const differences=on.pixels.location.map((p,i)=>p.slice(0,3).reduce((sum,v,c)=>sum+Math.abs(v-off.pixels.location[i][c]),0));
 assert.ok(differences.some(n=>n>0),`local boundary pixels must visibly change: ${differences}`);
 assert.deepEqual(on.pixels.province,off.pixels.province,'province line remains when local borders are switched off');
 console.log(`Actual default geographic border at zoom ${samples.zoom}: local RGB changes ${differences}; province pixels unchanged.`);
 const ink=pixels=>pixels.reduce((sum,p)=>sum+p.slice(0,3).reduce((n,v,c)=>n+Math.max(0,off.pixels.location[0][c]-v),0),0);
 assert.ok(ink(on.pixels.province)>ink(on.pixels.location),'province stroke is stronger than the thin local stroke');
 // Antialiasing can spread both subpixel strokes into the same two pixels.
 // Normalize their integrated ink by opacity to compare actual stroke width.
 assert.ok(ink(on.pixels.province)/.8>ink(on.pixels.location)/Math.min(.6,(samples.zoom-6)*.12),'province stroke has greater integrated width than the local stroke');
 assert.equal(await page.locator('#borders').count(),0,'no border checkbox remains');
 await page.locator('#home').click();await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas').dataset.locationBorders==='false');
 assert.equal(await page.locator('.atlas-pixel-canvas').getAttribute('data-province-borders'),'true');
 assert.deepEqual(errors,[]);
});


test('historical names use recognizable reference fallback without losing date evidence and Roma has a district polygon',async()=>{
 await goYear('1000 AD');await page.locator('#search').fill('Shenzhenshi');
 const found=await page.locator('[data-result]').count();assert.ok(found>0);await page.locator('[data-result]').first().click();
 assert.equal(await page.locator('#details h3').textContent(),'Shenzhenshi');assert.equal(await page.locator('.profile-name-context').textContent(),'Present-day reference: Shenzhenshi');assert.match(await page.locator('.profile-evidence').textContent(),/No dated location name covers 1,000 AD; the reference name Shenzhenshi is shown/);assert.match(await page.locator('.profile-evidence').textContent(),/Reference parent chain; historical membership for 1,000 AD is unknown/);assert.doesNotMatch(await page.locator('.profile-main').innerText(),/Historical name unknown|Reference location|Present-day reference.* area|historical membership|Habitation|Source date|Whole-territory|source geometry/);assert.match(await page.locator('.profile-evidence').textContent(),/Habitation:\s*Unknown/);assert.equal(await page.locator('.profile-evidence').evaluate(e=>e.open),false);
 const chainIds=await page.locator('.breadcrumbs [data-unit]').evaluateAll(items=>items.map(button=>button.dataset.unit)),hierarchy=JSON.parse(fs.readFileSync('data/hierarchy.json','utf8'));
 const reviewedSources=hierarchy.filter(unit=>chainIds.includes(unit.id)).flatMap(unit=>unit.metadata?.semantic_review?.evidence||[]).filter(source=>/^https?:\/\//i.test(source.url));
 await page.locator('.profile-evidence>summary').click();const exposedURLs=new Set(await page.locator('.profile-evidence a').evaluateAll(items=>items.map(a=>a.href)));
 for(const source of reviewedSources)assert.ok(exposedURLs.has(new URL(source.url).href),`new grouping citation retained: ${source.url}`);
 await page.locator('.profile-evidence>summary').click();
 await goYear('2026 AD');await page.locator('#search').fill('Rome');
 await page.locator('[data-result="atlas:location:ITA:SLL:1209"]').click();
 assert.equal(await page.locator('#details h3').textContent(),'Roma');assert.match(await page.locator('.breadcrumbs').textContent(),/Italy.*Lazio.*Roma/);
 await page.locator('#home').click();await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.worker==='true');
 const canvas=page.locator('.atlas-pixel-canvas');assert.equal(await canvas.getAttribute('data-renderer'),'webgl2');assert.equal(await canvas.getAttribute('data-stride'),'1');assert.deepEqual(errors,[]);
});

test('location profiles keep only requested fields visible and preserve citations in one evidence section',async()=>{
 const fields=['Owner','Population','Primary culture','Primary religion','Location rank','Topography','Vegetation','Climate'];
 const cases=[['London','atlas:city:GBR-Greater London'],['Hong Kong','atlas:territory:HKG'],['Barkly',null]];
 for(const viewport of [{width:1440,height:1080},{width:390,height:844}]){
  await page.setViewportSize(viewport);
  for(const selectedYear of ['2026 AD','1000 AD','1800 AD']){
   await goYear(selectedYear);
   for(const [query,id] of cases){
    await page.locator('#search').fill(query);const result=id?page.locator(`[data-result="${id}"]`):page.locator('[data-result]').first();assert.ok(await result.count(),`${query} search result`);await result.click();
    const main=page.locator('.profile-main'),evidence=page.locator('.profile-evidence');
    assert.equal(await main.locator('.breadcrumbs [data-unit]').count(),6);
    assert.deepEqual(await main.locator('dt').allTextContents(),fields);
    assert.equal(await main.locator('dd').count(),8);assert.ok((await main.locator('dd').allTextContents()).every(value=>value.trim().length),'each scalar has a value or explicit unknown');
    assert.equal(await main.locator('.profile-year').textContent(),formatYear(parseYear(selectedYear)));
    assert.match(await main.locator('.profile-name-context').textContent(),/^Present-day reference: .+/);
    assert.doesNotMatch(await main.innerText(),/Historical name unknown|Reference location|Habitation|Source date|Source coverage|Method:|License:|review notes|source geometry|ILLUSTRATIVE|DERIVED OWNERSHIP|NO DATED RECORD/);
    assert.equal(await page.locator('#details details').count(),1,'one evidence accordion, no nested source accordions');assert.equal(await evidence.evaluate(e=>e.open),false,'new year/location starts with evidence collapsed');
    assert.equal(await evidence.locator('.profile-evidence-content').isVisible(),false);
    assert.match(await evidence.textContent(),/Geography.*Source date:.*License:.*Attributes.*Habitation:/s);
    const links=await evidence.locator('a').count();assert.ok(links>0,'boundary and attribute source citations retained');
    await evidence.locator(':scope > summary').click();assert.equal(await evidence.locator('.profile-evidence-content').isVisible(),true);assert.ok(await evidence.locator('a').first().isVisible());
    assert.ok((await evidence.locator('a').evaluateAll(items=>items.map(a=>a.href))).every(url=>/^https?:\/\//i.test(url)));
    assert.equal(await page.locator('#details').evaluate(e=>e.scrollWidth<=e.clientWidth),true,'profile fits its desktop/mobile width');
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'no page overflow');
    await evidence.locator(':scope > summary').click();
   }
  }
 }
 await page.screenshot({path:'/workspace/atlas-location-profile-mobile.png',fullPage:true});
 await page.setViewportSize({width:1440,height:1080});assert.deepEqual(errors,[]);
});

test('profile and search prefer dated names and fall back after the supported interval',async()=>{
 const pattern='**/api/snapshot?*';
 await page.route(pattern,async route=>{
  const response=await route.fetch(),payload=await response.json();
  if(new URL(route.request().url()).searchParams.get('year')==='1000')payload.temporal_history=[...(payload.temporal_history||[]),{id:'test:profile:dated-name',entity_id:'atlas:city:GBR-Greater London',field:'name',value:'Dated name browser fixture',valid_from:1000,valid_to:1001,language:'en',name_role:'preferred',source:'Explicit UI-only test fixture; not published historical evidence',is_example:0}];
  await route.fulfill({response,json:payload});
 });
 try{
  await goYear('1000 AD');await page.locator('#search').fill('London');const result=page.locator('[data-result="atlas:city:GBR-Greater London"]');assert.match(await result.textContent(),/Dated name browser fixture/);await result.click();
  assert.equal(await page.locator('#details h3').textContent(),'Dated name browser fixture');assert.equal(await page.locator('.profile-name-context').textContent(),'Present-day reference: London');assert.doesNotMatch(await page.locator('.profile-evidence').textContent(),/No dated location name covers/);assert.match(await page.locator('.profile-evidence').textContent(),/Explicit UI-only test fixture/);
  await goYear('1001 AD');await page.locator('#search').fill('London');await result.click();assert.equal(await page.locator('#details h3').textContent(),'London');assert.equal(await page.locator('.profile-name-context').textContent(),'Present-day reference: London');assert.match(await page.locator('.profile-evidence').textContent(),/No dated location name covers 1,001 AD; the reference name London is shown/);
 }finally{await page.unroute(pattern);}
 await goYear('2026 AD');assert.deepEqual(errors,[]);
});

test('unsettled rank uses explicit evidence while estimated zero remains unknown',async()=>{
 const pattern='**/api/snapshot?*',identity='atlas:city:GBR-Greater London';
 await page.route(pattern,async route=>{
  const response=await route.fetch(),payload=await response.json(),year=Number(new URL(route.request().url()).searchParams.get('year'));
  if([1000,1001,1002].includes(year)){
   payload.states=(payload.states||[]).filter(record=>record.location_id!==identity);
   payload.attributes=(payload.attributes||[]).filter(record=>record.location_id!==identity||!['population','rank','habitation'].includes(record.attribute));
   payload.attributes.push({id:`test:profile:no-inhabitants:${year}`,location_id:identity,attribute:year===1002?'habitation':'population',value:year===1002?'uninhabited':0,source:'Explicit UI-only fixture; not published historical evidence',valid_from:year,valid_to:year+1,method:year===1001?'estimate':'direct',status:year===1001?'estimate':'sourced',is_example:0,metadata:year===1001?{estimate:true,precision:'Modeled count rounded to whole people'}:{}});
  }
  await route.fulfill({response,json:payload});
 });
 try{
  for(const year of [1000,1001,1002]){
   await goYear(String(year));await page.locator('#search').fill('London');await page.locator(`[data-result="${identity}"]`).click();
   const rank=page.locator('.profile-attributes > div').filter({has:page.locator('dt',{hasText:/^Location rank$/})}).locator('dd');
   assert.equal(await rank.textContent(),year===1001?'Unknown':'unsettled');
   assert.equal(await page.locator('.profile-evidence').evaluate(element=>element.open),false);
   assert.match(await page.locator('.profile-evidence').textContent(),/Explicit UI-only fixture/);
  }
 }finally{await page.unroute(pattern);}
 await goYear('2026 AD');assert.deepEqual(errors,[]);
});


test('zoom buttons, wheel, panning and resize reuse compiled ownership',async()=>{
  await goYear('2026 AD');await page.locator('[data-mode="location"]').click();
  await page.locator('#home').click();
  await page.waitForFunction(()=>{const data=document.querySelector('.atlas-pixel-canvas')?.dataset;return data?.compilations&&Number(data.cellPixels)<1;});
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  const read=()=>page.locator('.atlas-pixel-canvas').evaluate(e=>({...e.dataset}));
  const baseline=await read(),times=[];
  assert.equal(baseline.renderer,'webgl2');assert.equal(baseline.stride,'1');
  assert.ok(Number(baseline.cellPixels)<1,'world view shows subpixel canonical cells, not enlarged blocks');
  const changed=async(action)=>{
    const before=await read();await action();
    await page.waitForFunction(key=>document.querySelector('.atlas-pixel-canvas')?.dataset.frame!==key,before.frame);
    const after=await read();
    assert.equal(after.compilations,baseline.compilations,'navigation must not recompile polygons');
    assert.equal(after.compileMs,baseline.compileMs);
    assert.equal(after.uploads,baseline.uploads,'navigation must not rebuild or upload map textures');
    assert.equal(after.stride,'1','canonical pixel resolution never changes');
    times.push(Number(after.renderMs));
  };
  for(let i=0;i<3;i++)await changed(()=>page.locator('#zoom-in').click());
  for(let i=0;i<3;i++)await changed(()=>page.locator('#zoom-out').click());
  const box=await page.locator('#map').boundingBox();
  await page.mouse.move(box.x+box.width*.5,box.y+box.height*.5);
  await changed(()=>page.mouse.wheel(0,-240));
  await changed(async()=>{await page.mouse.down();await page.mouse.move(box.x+box.width*.5+120,box.y+box.height*.5+50,{steps:10});await page.mouse.up();});
  await changed(()=>page.setViewportSize({width:1280,height:900}));
  assert.ok(times.every(ms=>ms<50),`navigation main-thread submission times: ${times}`);
  console.log(`Cached grid navigation: ${times.join(', ')} ms; polygon compilations unchanged (${baseline.compilations}).`);
  assert.deepEqual(errors,[]);
});

test('GPU colors match canonical ownership, including holes and individual cells',async()=>{
  const result=await page.evaluate(async()=>{
    const {PixelGPU}=await import('/src/pixel-gpu.js');
    const {compileOwnership,packOwnership,pickOwnership}=await import('/src/pixel-ownership.js');
    const ring=(a,b,c,d)=>new Float64Array([a,b,c,b,c,d,a,d,a,b]);
    const index=[{index:1,polygons:[[ring(0,0,16,32),ring(4,4,8,8)]],bounds:[0,0,16,32]},
      {index:2,polygons:[[ring(16,0,32,32)]],bounds:[16,0,32,32]},
      {index:3,polygons:[[ring(5,5,6,6)]],bounds:[5,5,6,6]}];
    const grid=packOwnership(compileOwnership(index,32)),canvas=document.createElement('canvas');canvas.width=128;canvas.height=128;
    const gpu=new PixelGPU(canvas);gpu.ownership('location',grid);
    const colors=new Uint8Array([0,0,0,0,255,0,0,255,0,255,0,255,0,0,255,255]);
    gpu.upload('colors',colors);gpu.upload('metadata',new Uint32Array([0,0,1,1,2,1,1,1]),2);
    gpu.draw({origin:{x:0,y:0},scale:4,zoom:9,localBorders:true,selected:0,hasPolitical:false,dpr:1});
    const pixels=new Uint8Array(128*128*4);gpu.gl.readPixels(0,0,128,128,gpu.gl.RGBA,gpu.gl.UNSIGNED_BYTE,pixels);
    let mismatches=0;
    for(let y=0;y<32;y++)for(let x=0;x<32;x++){
      const id=pickOwnership(grid,x,y),offset=((127-(y*4+2))*128+x*4+2)*4;
      if([...colors.slice(id*4,id*4+4)].some((v,k)=>v!==pixels[offset+k]))mismatches++;
    }
    const error=gpu.gl.getError();gpu.destroy();return {mismatches,error};
  });
  assert.deepEqual(result,{mismatches:0,error:0});
});

test('GPU context recovery keeps compiled geography and restores drawing',async()=>{
  const canvas=page.locator('.atlas-pixel-canvas'),before=await canvas.getAttribute('data-compilations');
  await canvas.evaluate(c=>{window.contextExtension=c.getContext('webgl2').getExtension('WEBGL_lose_context');window.contextExtension.loseContext();});
  await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas').getContext('webgl2').isContextLost());
  await page.evaluate(()=>window.contextExtension.restoreContext());
  await page.waitForFunction(()=>!document.querySelector('.atlas-pixel-canvas').getContext('webgl2').isContextLost());
  const frame=await canvas.getAttribute('data-frame');await page.locator('#zoom-in').click();
  await page.waitForFunction(k=>document.querySelector('.atlas-pixel-canvas').dataset.frame!==k,frame);
  assert.equal(await canvas.getAttribute('data-compilations'),before);
  assert.equal(await canvas.evaluate(c=>c.getContext('webgl2').getError()),0);
  assert.deepEqual(errors,[]);
});


test('coverage ledger exposes every continent and every geographic tier',async t=>{
 t.after(()=>page.locator('#coverage-dialog').evaluate(dialog=>dialog.close()));
 const researchRequests=[];const recordResearch=request=>{const path=new URL(request.url()).pathname;if(/macro-review-evidence|macro-corrections|granularity-review-evidence|region-semantic-review|geographic-migration/.test(path))researchRequests.push(path);};
 page.on('request',recordResearch);t.after(()=>page.off('request',recordResearch));
 await goYear('2026 AD');await page.locator('#coverage-button').click();
 await page.waitForFunction(()=>document.querySelector('#coverage-tree').children.length===6);
 assert.equal(await page.locator('#coverage-continent option').count(),7);assert.equal(await page.locator('#coverage-territory option').count(),253);
 const report=await page.evaluate(async()=>await(await fetch('./world-review.json')).json());
 assert.deepEqual(report.audit_order,['continent','subcontinent','region','area','province','location']);
 assert.equal(report.semantic_complete,false);assert.equal(report.locations,report.level_progress.location.total);
 const geography=await page.evaluate(async()=>{const data=await(await fetch('/api/geography')).json();return {units:data.units.map(unit=>({level:unit.level})),locations:data.features.length};});
 for(const level of ['continent','subcontinent','region','area','province'])assert.equal(report.level_progress[level].total,geography.units.filter(unit=>unit.level===level).length,`${level} coverage must follow the current dataset`);
 assert.equal(report.level_progress.location.total,geography.locations);
 assert.match(await page.locator('#coverage-levels').textContent(),new RegExp(`province: ${report.level_progress.province.total.toLocaleString()} inventoried`));
 assert.match(await page.locator('#coverage-levels').textContent(),new RegExp(`area: ${report.level_progress.area.total.toLocaleString()} inventoried`));
 assert.deepEqual(researchRequests,[],'research and migration downloads must remain optional');
 for(const c of ['Africa','Asia','Europe','North America','Oceania','South America']){await page.locator('#coverage-continent').selectOption(c);assert.equal(await page.locator('#coverage-tree>details').count(),1);assert.match(await page.locator('#coverage-tree').textContent(),new RegExp(c));}
 await page.locator('#coverage-continent').selectOption('Asia');await page.locator('#coverage-territory').selectOption('Japan');
 await page.route('**/world-review-locations-*.json.gz',route=>route.fulfill({status:503,body:'Temporary report failure'}),{times:1});
 let branch=page.locator('#coverage-tree > details').first();
 for(let depth=0;depth<5;depth++){await branch.locator(':scope > summary').click();if(depth<4)branch=branch.locator(':scope > .coverage-branch > details').first();}
 await page.waitForFunction(()=>document.querySelector('#coverage-tree').textContent.includes('Member records unavailable'));
 await branch.locator(':scope > summary').click();await branch.locator(':scope > summary').click();
 await page.waitForFunction(()=>/\d+ members · \d+ fully reviewed/.test(document.querySelector('#coverage-tree').textContent));
 assert.doesNotMatch(await page.locator('#coverage-tree').textContent(),/Member records unavailable/);
 const researchResponse=page.waitForResponse(response=>response.url().endsWith('/macro-review-evidence.json'));
 await page.locator('#coverage-macro-research > summary').click();
 const research=await(await researchResponse).json();
 await page.waitForFunction(()=>document.querySelector('#coverage-macro-evidence').textContent.includes('Research inventories all 6 continents'));
 assert.match(await page.locator('#coverage-macro-evidence').textContent(),/Japan.*boundaries remain open/s);
 assert.deepEqual(researchRequests,['/macro-review-evidence.json']);
 assert.equal(await page.locator('a[href="./geographic-migration-review.json.gz"]').getAttribute('download'),'');
 assert.equal(await page.locator('a[href="./geographic-migration-archive.json.gz"]').getAttribute('download'),'');
 assert.equal(await page.locator('a[href="./granularity-review-evidence.json.gz"]').getAttribute('download'),'');
 assert.equal(await page.locator('a[href="./region-semantic-review.json.gz"]').getAttribute('download'),'');
 assert.equal(await page.locator('a[href="./macro-corrections.json"]').getAttribute('download'),'');
 const researchText=await page.locator('#coverage-macro-evidence').textContent();
 assert.ok(researchText.includes(`${research.corrections_applied.cases} source-supported corrections applied`));
 assert.ok(researchText.includes(`${research.corrections_applied.changed_locations.toLocaleString()} location memberships`));
 await page.keyboard.press('Escape');assert.deepEqual(errors,[]);
});


test('representative location profiles render across every continent',async()=>{
 await goYear('2026 AD');
 for(const [name,id,continent] of [['Hong Kong','atlas:territory:HKG','Asia'],['London','atlas:city:GBR-Greater London','Europe'],['New York City','atlas:city:USA-New-York-City','North America'],['São Paulo','gb:BRA:ADM2:56859067B92864763247255','South America'],['Cairo','atlas:city:EGY-1533','Africa'],['Melbourne','gb:AUS:ADM2:25037944B74771981745191','Oceania']]){
  await page.locator('#search').fill(name);await page.locator(`[data-result="${id}"]`).click();
  assert.equal(await page.locator('.breadcrumbs [data-unit]').count(),6);assert.match(await page.locator('.breadcrumbs').textContent(),new RegExp(continent));
  assert.doesNotMatch(await page.locator('#details').textContent(),/Not mapped in source/);
 }
 assert.deepEqual(errors,[]);
});


test('prepared historical ownership colors every sampled location cell with its resolved owner',async t=>{
 if(!fs.existsSync('data/ownership-history/index.json')){t.skip('Historical ownership preparation is still running');return;}
 const example=await findHistoricalMapCase(async year=>{const response=await fetch(`http://localhost:${port}/api/snapshot?year=${year}&examples=0`);assert.equal(response.status,200);return response.json();});
 const check=await checkHistoricalMapCase(page,example);
 assert.equal(check.hasPolitical,false,'normal Political mode cannot use a separate political polygon fill');
 assert.ok(check.selected>0);assert.ok(check.tested>=12,`need enough canonical cells across ${example.name}, found ${check.tested}`);
 assert.equal(check.eligible,check.totalCells,'every canonical interior cell belongs to this location');
 assert.equal(check.tested,check.eligible,'every canonical interior cell is checked');
 assert.equal(check.mismatches,0,'every location interior pixel must match its single owner palette');
 assert.equal(check.error,0);assert.equal(check.legend,check.expected,'legend must use the same stable owner color');
 const expected=check.expected.match(/\d+/g).slice(0,3).map(Number);
 assert.ok(expected.every((channel,i)=>Math.abs(channel-check.palette[i])<=1),'map palette must match the resolved owner category');
 console.log(`Historical whole-location fill: ${example.name}, ${formatYear(example.year)}, ${example.record.value}, ${(example.record.metadata.share*100).toFixed(1)}% source share, ${check.tested} canonical cells checked.`);
 await page.screenshot({path:'/workspace/atlas-historical-majority.png'});
 assert.deepEqual(errors,[]);
});
