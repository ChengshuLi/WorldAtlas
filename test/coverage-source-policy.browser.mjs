import {test,before,after} from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {chromium} from '@playwright/test';
const port=process.env.ATLAS_SOURCE_POLICY_TEST_PORT||'3218';
const read=path=>JSON.parse(fs.readFileSync(new URL('../data/'+path,import.meta.url)));
const units=read('hierarchy.json'),bundle=JSON.parse(gunzipSync(fs.readFileSync(new URL('../data/source-policy-corrections/europe-v1.json.gz',import.meta.url))));
const owners={ITA:'Italy',ESP:'Spain',XKX:'Kosovo'};
const features=bundle.location_annotations.map(row=>({id:row.location_id,properties:{reference_owner:owners[row.profile_iso],parent_id:row.parent_chain[0]}}));
let server,browser,page;const errors=[];
before(async()=>{
 server=spawn(process.execPath,['server.mjs'],{cwd:new URL('..',import.meta.url),env:{...process.env,PORT:port,ATLAS_TEST_MODE:'1'},stdio:['ignore','pipe','pipe']});
 let stderr='';server.stderr.on('data',bytes=>{stderr=(stderr+String(bytes)).slice(-4000);});
 await new Promise((resolve,reject)=>{server.stdout.on('data',bytes=>{if(String(bytes).includes('listening'))resolve();});server.once('exit',code=>reject(Error(`Server exited ${code}: ${stderr}`)));});
 browser=await chromium.launch();page=await browser.newPage();page.on('pageerror',error=>errors.push(error.message));
 // Exercise the real coverage component and report transport without loading a map.
 await page.route('**/__coverage-test',route=>route.fulfill({contentType:'text/html',body:'<!doctype html><html><head></head><body><header><button id="about">About</button></header></body></html>'}));
 await page.goto(`http://localhost:${port}/__coverage-test`);
 await page.evaluate(async ({features,units})=>{const {installCoverage}=await import('/src/coverage.js');installCoverage(()=>({data:{features},states:new Map(),year:1800,parents:new Map(units.map(unit=>[unit.id,unit]))}));},{features,units});
});
after(async()=>{await browser?.close();server?.kill('SIGTERM');});

test('coverage keeps frozen reports readable during correction failure and retries the actual asset',async()=>{
 await page.route('**/source-policy-corrections/summary.json',route=>route.fulfill({status:503,body:'Temporary source-role report failure'}),{times:1});
 await page.locator('#coverage-button').click();
 await page.waitForFunction(()=>document.querySelector('#coverage-source-policy-notice').textContent.includes('are unavailable'));
 assert.equal(await page.locator('#coverage-tree>details').count(),6);
 assert.match(await page.locator('#coverage-reviews').textContent(),/Earlier|Province \/ metropolitan city/);
 await page.locator('#coverage-dialog').evaluate(dialog=>dialog.close());
 await page.locator('#coverage-button').click();
 await page.waitForFunction(()=>document.querySelector('#coverage-source-policy-notice').textContent.includes('include sourced corrections'));
 assert.match(await page.locator('#coverage-reviews').textContent(),/Local labour systems \(ISTAT SLL 2011\/2018\)/);
 assert.equal(await page.locator('#coverage-reviews>details').count(),3);
 assert.equal(await page.locator('#coverage-reviews details details').filter({has:page.locator('summary', {hasText:'Correction evidence and earlier source description'})}).evaluateAll(nodes=>nodes.every(node=>!node.open)),true);
});

test('correction role counts follow selected continent membership and retain evidence below the readable description',async()=>{
 await page.locator('#coverage-territory').selectOption('Spain');await page.locator('#coverage-continent').selectOption('Europe');
 let text=await page.locator('#coverage-reviews').textContent();assert.match(text,/372 locations in selection/);assert.match(text,/agricultural district adaptation: 333 locations/);assert.match(text,/Municipality territory: 39 locations/);
 await page.locator('#coverage-continent').selectOption('Africa');text=await page.locator('#coverage-reviews').textContent();assert.match(text,/12 locations in selection/);assert.match(text,/agricultural district adaptation: 8 locations/);assert.match(text,/Municipality territory: 4 locations/);
 await page.locator('#coverage-continent').selectOption('Europe');await page.locator('#coverage-territory').selectOption('Kosovo');
 const profile=page.locator('#coverage-reviews>details');await profile.locator(':scope>summary').click();
 const visible=await profile.locator(':scope>p').allTextContents();assert.match(visible.join(' '),/district/i);assert.doesNotMatch(visible.join(' '),/Source role: Municipalities/);
 await profile.locator('details>summary').filter({hasText:'Correction evidence and earlier source description'}).click();
 assert.match(await profile.textContent(),/seven named district features/);assert.match(await profile.textContent(),/Earlier description: Municipalities/);
 assert.deepEqual(errors,[]);
});
