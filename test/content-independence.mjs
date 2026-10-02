import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {chromium} from '@playwright/test';
import {categoryColor} from '../src/model.js';

const origin=process.env.ATLAS_CONTENT_TEST_ORIGIN??'http://localhost:3197';
if(!['localhost','127.0.0.1'].includes(new URL(origin).hostname))throw Error('Content-only QA must use an isolated local Worker; production is prohibited');
const location='atlas:city:GBR-Greater London',tag=`content-qa:${Date.now()}`,sha=b=>createHash('sha256').update(b).digest('hex');
async function post(payload){const response=await fetch(origin+'/api/records/import',{method:'POST',headers:{'Content-Type':'application/json',Origin:origin},body:JSON.stringify(payload)});assert.equal(response.status,200,await response.clone().text());return response.json();}
async function year(page,selected=2021){await page.locator('#year-input').fill(String(selected));await page.locator('#year-form button').click();await page.locator('#loading').waitFor({state:'hidden',timeout:90000});await page.locator('#search').fill('London');await page.locator(`[data-result="${location}"]`).click();}
async function field(page,label){return page.locator('#details dl > div').filter({has:page.locator('dt',{hasText:new RegExp('^'+label+'$')})}).locator('dd').textContent();}
async function palette(page){return page.evaluate(()=>{const canvas=document.querySelector('.atlas-pixel-canvas'),gl=canvas.getContext('webgl2'),program=gl.getParameter(gl.CURRENT_PROGRAM),u=name=>gl.getUniform(program,gl.getUniformLocation(program,name)),selected=u('selected'),old=gl.getParameter(gl.FRAMEBUFFER_BINDING),active=gl.getParameter(gl.ACTIVE_TEXTURE),fb=gl.createFramebuffer();gl.activeTexture(gl.TEXTURE0+u('colors'));const texture=gl.getParameter(gl.TEXTURE_BINDING_2D);gl.bindFramebuffer(gl.FRAMEBUFFER,fb);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,texture,0);const rgba=new Uint8Array(4);gl.readPixels(selected%2048,Math.floor(selected/2048),1,1,gl.RGBA,gl.UNSIGNED_BYTE,rgba);gl.bindFramebuffer(gl.FRAMEBUFFER,old);gl.activeTexture(active);gl.deleteFramebuffer(fb);gl.drawArrays(gl.TRIANGLES,0,3);return [...rgba];});}

test('local API content imports and retirements update the existing UI and political color without rebuilding',async()=>{
 const browser=await chromium.launch(),page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const assetRoot=fs.existsSync('dist/client/index.html')?'dist/client':'dist';
 const builtFiles=[`${assetRoot}/index.html`,...fs.readdirSync(`${assetRoot}/assets`).map(p=>`${assetRoot}/assets/`+p)].filter(f=>fs.statSync(f).isFile()),buildProof=builtFiles.map(f=>[f,sha(fs.readFileSync(f))]);
 const source={id:tag+':source',name:'Local automated QA fixture, not historical evidence',url:'https://example.org/test-only-source',license:'CC0 test fixture',vintage:'Automated local test',supported_from:2021,supported_to:2022,status:'historical',metadata:{local_qa_only:true}},category={id:tag+':polity',kind:'owner',name:'Local QA polity',source_id:source.id,metadata:{local_qa_only:true}},base={location_id:location,valid_from:2021,valid_to:2022,source_id:source.id,method:'direct',status:'sourced',is_example:0,metadata:{local_qa_only:true}},records=[{...base,id:tag+':owner',attribute:'owner',value:category.name,category_id:category.id},{...base,id:tag+':population',attribute:'population',value:1234567,category_id:null}],name={id:tag+':name',entity_id:location,name:'Local QA dated London',language:'en',role:'preferred',valid_from:2021,valid_to:2022,source_id:source.id,is_example:0,metadata:{local_qa_only:true}};
 let claimsImported=false;
 try{
  await page.goto(origin);await page.locator('#loading').waitFor({state:'hidden',timeout:90000});await year(page);await page.locator('[data-mode="owner"]').click();const beforeOwner=await field(page,'Owner'),beforeColor=await palette(page);
  await page.locator('#import-records-button').click();await page.locator('#import-records-json').fill(JSON.stringify({sources:[source],categories:[category],records,names:[name],ingestion_id:tag+':import'}));assert.equal(await page.locator('#import-records-submit').isDisabled(),true);await page.locator('#import-records-review').click();assert.match(await page.locator('#import-records-preview').textContent(),/5 rows ready for database validation/);assert.equal(await page.locator('#import-records-submit').isDisabled(),false);const saved=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/records/import'&&r.request().method()==='POST');await page.locator('#import-records-submit').click();const response=await saved;assert.equal(response.status(),200,await response.text());claimsImported=true;await page.waitForFunction(()=>document.querySelector('#import-records-status').textContent.includes('The selected year has been refreshed.'),null,{timeout:90000});await page.locator('#import-records-dialog .dialog-close').click();
  await year(page);assert.equal(await page.locator('#details h3').textContent(),name.name);assert.equal(await page.locator('.profile-name-context').textContent(),'Present-day reference: London');assert.equal(await field(page,'Owner'),category.name);assert.equal(await field(page,'Population'),'1,234,567');assert.equal(await page.locator('.profile-evidence').getAttribute('open'),null);
  const expected=await page.evaluate(css=>{const element=document.createElement('canvas'),context=element.getContext('2d');context.fillStyle=css;context.fillRect(0,0,1,1);return [...context.getImageData(0,0,1,1).data];},categoryColor(category.id));assert.deepEqual(await palette(page),expected);assert.notDeepEqual(await palette(page),beforeColor);
  await page.locator('.profile-evidence summary').click();assert.match(await page.locator('.profile-evidence').textContent(),/Local automated QA fixture/);
  // Retire a real prepared checkpoint claim in this isolated database to prove
  // that absence from /api/attributes cannot restore it from shipped caches.
  const directory='data/demographic-evidence',index=JSON.parse(fs.readFileSync(`${directory}/index.json`)),checkpoint=JSON.parse(fs.readFileSync(`${directory}/religion-records.json`)).find(r=>r.location_id===location);assert.ok(checkpoint);assert.equal(index.records,396);
  await post({sources:JSON.parse(fs.readFileSync(`${directory}/sources.json`)),categories:JSON.parse(fs.readFileSync(`${directory}/categories.json`)),ingestion_id:tag+':checkpoint-identities'});await post({records:[checkpoint],ingestion_id:tag+':checkpoint-claim'});
  await post({retirements:[{id:tag+':religion-withdrawal',collection:'records',target_id:checkpoint.id,source_id:source.id,reason:'Isolated automated QA withdrawal; never production'}],ingestion_id:tag+':retire-checkpoint'});
  await year(page);assert.equal(await field(page,'Primary religion'),'Unknown');
  await post({retirements:[...records.map(r=>({id:tag+':retire:'+r.id,collection:'records',target_id:r.id,source_id:source.id,reason:'Remove local automated QA fixture'})),{id:tag+':retire-name',collection:'names',target_id:name.id,source_id:source.id,reason:'Remove local automated QA fixture'}],ingestion_id:tag+':retire-fixtures'});claimsImported=false;
  await year(page);assert.equal(await page.locator('#details h3').textContent(),'London');assert.equal(await field(page,'Owner'),beforeOwner);assert.notEqual(await field(page,'Population'),'1,234,567');assert.deepEqual(await palette(page),beforeColor);
  await year(page,2022);assert.notEqual(await field(page,'Owner'),category.name);assert.notEqual(await page.locator('#details h3').textContent(),name.name);assert.deepEqual(errors,[]);
  for(const [file,digest]of buildProof)assert.equal(sha(fs.readFileSync(file)),digest,`Website asset changed during content-only test: ${file}`);
 }finally{
  if(claimsImported)await post({retirements:[...records.map(r=>({id:tag+':cleanup:'+r.id,collection:'records',target_id:r.id,source_id:source.id,reason:'Cleanup failed local QA test'})),{id:tag+':cleanup-name',collection:'names',target_id:name.id,source_id:source.id,reason:'Cleanup failed local QA test'}],ingestion_id:tag+':cleanup'}).catch(()=>{});
  await browser.close();
 }
});
