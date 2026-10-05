import fs from 'node:fs';
import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
const [url,output]=process.argv.slice(2);
if(!['http://127.0.0.1:3886','https://worldatlas-explorer.chengshu-worldatlas.workers.dev'].includes(new URL(url).origin)||!output)throw Error('Use approved read-only atlas URL and owned output path');
const result={url,started_at:new Date().toISOString(),errors:[],modes:[],years:[],completed:false};
const browser=await chromium.launch({args:process.env.ATLAS_BENCH_ANGLE?['--use-angle='+process.env.ATLAS_BENCH_ANGLE]:[]});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1080}});
 if(process.env.ATLAS_BENCH_CANVAS==='1')await page.addInitScript(()=>{const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return type==='webgl2'?null:get.call(this,type,...args);};});
 page.on('pageerror',e=>result.errors.push(e.message));
 await page.goto(url);await page.locator('#loading').waitFor({state:'hidden',timeout:180000});
 await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.rendered==='true');
 const dataset=()=>page.locator('.atlas-pixel-canvas').evaluate(c=>({...c.dataset}));
 result.before=await dataset();
 const bounds=await page.locator('#map').boundingBox();await page.mouse.move(bounds.x+bounds.width*.6,bounds.y+bounds.height*.45);
 for(const mode of ['owner','population','culture','religion','rank','topography','vegetation','climate','location','province','area','region','subcontinent','continent']){
  await page.mouse.move(bounds.x+bounds.width*.6,bounds.y+bounds.height*.45);
  await page.mouse.wheel(0,-6);
  await page.locator(`[data-mode="${mode}"]`).click();
  await page.waitForTimeout(120);
  assert.equal(await page.locator(`[data-mode="${mode}"]`).getAttribute('aria-pressed'),'true');
  result.modes.push({mode,canvas:await dataset()});
 }
 // Start a dated request while the camera is moving, then supersede it.
 for(const year of ['2020','2021','2022']){
  await page.mouse.move(bounds.x+bounds.width*.6,bounds.y+bounds.height*.45);
  await page.mouse.wheel(0,12);
  await page.locator('#year-input').fill(year);await page.locator('#year-form button').click();
 }
 await page.waitForFunction(()=>document.querySelector('#map-year').textContent==='2,022 AD',null,{timeout:180000});
 await page.locator('#loading').waitFor({state:'hidden',timeout:180000});
 assert.equal(await page.locator('#year-error').textContent(),'');
 result.years.push({latest_year:await page.locator('#map-year').textContent(),canvas:await dataset()});
 await page.locator('#search').fill('London');await page.locator('[data-result="atlas:city:GBR-Greater London"]').click();
 await page.waitForTimeout(600);
 assert.equal(await page.locator('#details h3').textContent(),'London');
 assert.equal(await page.locator('.breadcrumbs [data-unit]').count(),6);
 result.selected={name:await page.locator('#details h3').textContent(),hierarchy:await page.locator('.breadcrumbs').textContent()};
 await page.locator('#close-details').click();
 const box=await page.locator('#map').boundingBox();let picked=false;
 for(const [dx,dy] of [[0,0],[-40,0],[40,0],[0,-40],[0,40],[-80,-60],[80,60]]){
  const x=box.x+box.width*.5+dx,y=box.y+box.height*.5+dy;await page.mouse.move(x,y);
  if(await page.locator('.leaflet-tooltip').count()){
   const name=await page.locator('.leaflet-tooltip').textContent();await page.mouse.click(x,y);
   assert.equal(await page.locator('#details h3').textContent(),name);result.picked=name;picked=true;break;
  }
 }
 assert.ok(picked,'Visible land must be pickable with matching inspector');
 await page.locator('#home').click();await page.waitForTimeout(600);
 await page.setViewportSize({width:1360,height:1000});await page.waitForTimeout(250);
 result.after=await dataset();
 assert.equal(result.after.compilations,result.before.compilations);
 assert.equal(result.after.ownershipUploads,result.before.ownershipUploads);
 assert.deepEqual(result.errors,[]);
 result.completed=true;
}catch(e){result.failure={name:e.name,message:e.message};throw e;}
finally{result.completed_at=new Date().toISOString();fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');await browser.close();}
console.log('All 14 modes, latest-year race, six-tier inspector, hover/click, resize and cached ownership passed');
