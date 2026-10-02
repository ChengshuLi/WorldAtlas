import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
const browser=await chromium.launch();
try{
 const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[],posts=[];page.on('pageerror',error=>errors.push(error.message));
 await page.route('http://atlas-import.test/**',async route=>{
  const path=new URL(route.request().url()).pathname;
  if(path.startsWith('/src/'))return route.fulfill({contentType:'text/javascript',body:await fs.readFile(`.${path}`,'utf8')});
  if(path==='/api/records/import'){posts.push(route.request().postDataJSON());return route.fulfill({json:{duplicate:false,counts:{records:1},revision:1}});}
  return route.fulfill({contentType:'text/html',body:'<header><button id="about">About the data</button></header>'});
 });
 await page.goto('http://atlas-import.test');
 await page.evaluate(async()=>{const {installRecordImport}=await import('/src/import-records.js');installRecordImport({enabled:true,getContext:()=>({year:1000,selected:'location',feature:{properties:{name:'Selected place'}}}),refresh:async()=>{window.refreshCount=(window.refreshCount||0)+1;}});});
 await page.locator('#import-records-button').click();await page.locator('#import-records-json').fill('{');await page.locator('#import-records-review').click();
 assert.match(await page.locator('#import-records-status').textContent(),/valid JSON/);assert.equal(await page.locator('#import-records-submit').isDisabled(),true);assert.equal(posts.length,0);
 const payload={records:[{id:'source-record',location_id:'location',attribute:'population',value:42,valid_from:1000,valid_to:1100,source_id:'source'}]};
 await page.locator('#import-records-json').fill(JSON.stringify(payload));await page.locator('#import-records-review').click();assert.equal(posts.length,0);assert.equal(await page.locator('#import-records-submit').isEnabled(),true);
 await page.locator('#import-records-json').fill(JSON.stringify({...payload,ingestion_id:'another'}));assert.equal(await page.locator('#import-records-submit').isDisabled(),true);
 await page.locator('#import-records-review').click();await page.locator('#import-records-submit').click();await page.waitForFunction(()=>window.refreshCount===1);
 assert.equal(posts.length,1);assert.equal(posts[0].records[0].value,42);assert.match(await page.locator('#import-records-status').textContent(),/Records saved.*refreshed/);
 assert.deepEqual(errors,[]);console.log('PASS: import preview, edit invalidation, explicit submission, saved evidence and current-year refresh.');
}finally{await browser.close();}
