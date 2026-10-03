import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
import {categoryColor,formatYear} from '../src/model.js';
import {displayCategoryKey,cssRGB} from '../src/color-perception.js';

const output=process.argv[2];
if(!output||!output.startsWith('data/engineering/'))throw Error('Owned engineering receipt path required');
const supplied=process.argv[3],origin=new URL(supplied??'http://127.0.0.1:3203');
if(origin.protocol!=='http:'||origin.hostname!=='127.0.0.1'||origin.pathname!=='/'||origin.search||origin.hash||origin.username||origin.password)throw Error('Use only a local static server or fixed-origin private verification proxy');
if(!supplied&&fs.existsSync('dist/client/index.html'))throw Error('A hosted build needs its local Worker or private verification proxy; use the static build for standalone checks');
const receipt={version:1,started_at_utc:new Date().toISOString(),conditions:(supplied?'Actual deployed client/API through provided local private verification proxy':'Local committed static build, actual prepared data')+'; Linux headless Chromium, not physical-device or color-vision certification',page_errors:[],renderers:[]};
const server=supplied?null:spawn('python3',['-u','-m','http.server','3203','--bind','127.0.0.1','--directory','dist'],{stdio:['ignore','pipe','pipe']});
let browser;
const save=()=>{fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(receipt,null,2)+'\n');};
try{
  if(server)await new Promise((resolve,reject)=>{server.stdout.on('data',d=>{if(String(d).includes('Serving HTTP'))resolve();});server.once('exit',()=>reject(Error('Static server unavailable')));});
  browser=await chromium.launch();receipt.browser_version=browser.version();
  for(const renderer of ['webgl2','canvas']){
    const page=await browser.newPage({viewport:{width:1440,height:1080}});
    page.on('pageerror',e=>receipt.page_errors.push(e.message));
    if(renderer==='canvas')await page.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return type==='webgl2'?null:original.call(this,type,...args);};});
    const ready=async()=>{await page.locator('#loading').waitFor({state:'hidden',timeout:180000});await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.rendered==='true',null,{timeout:180000});await page.waitForTimeout(100);};
    await page.goto(origin.href);await ready();
    const canvas=()=>page.locator('.atlas-pixel-canvas').evaluate(c=>({...c.dataset}));
    const initial=await canvas(),run={renderer,initial,samples:[],modes:[],profiles:[]};receipt.renderers.push(run);
    const legend=()=>page.locator('#legend-items .legend-item').evaluateAll(rows=>rows.map(r=>({name:r.querySelector('span')?.textContent??r.textContent.trim(),rgb:r.querySelector('i')?getComputedStyle(r.querySelector('i')).backgroundColor:null})));
    for(const year of [1950,1951,2020,1950]){
      await page.locator('#year-input').fill(String(year));await page.locator('#year-form button').click();
      await page.waitForFunction(expected=>document.querySelector('#map-year').textContent===expected,formatYear(year),{timeout:180000});await ready();
      assert.equal(await page.locator('#year-error').textContent(),'');
      const rows=await legend();
      for(const name of ["People's Republic of China",'Republic of China']){
        const row=rows.find(r=>r.name===name);assert.ok(row,'Independent legend row required: '+name);
        const rgb=cssRGB(categoryColor(displayCategoryKey('owner:Q148',name)));
        assert.equal(row.rgb,`rgb(${rgb.join(', ')})`);
      }
      run.samples.push({year,legend:rows,canvas:await canvas()});save();
    }
    const cases=[{query:'Beijing',id:'gb:CHN:ADM2:17275852B40522342172572',name:"People's Republic of China"},{query:'Taipei',id:'atlas:city:TWN-1166',name:'Republic of China'}];
    for(const example of cases){
      await page.locator('#search').fill(example.query);await page.locator(`[data-result="${example.id}"]`).click();await page.waitForTimeout(500);
      const expected=cssRGB(categoryColor(displayCategoryKey('owner:Q148',example.name)));
      const pixels=await page.locator('.atlas-pixel-canvas').evaluate((c,{expected,renderer})=>{
        let data,palette=null;
        if(renderer==='webgl2'){
          const gl=c.getContext('webgl2'),program=gl.getParameter(gl.CURRENT_PROGRAM),u=name=>gl.getUniform(program,gl.getUniformLocation(program,name));
          const previous=gl.getParameter(gl.FRAMEBUFFER_BINDING),active=gl.getParameter(gl.ACTIVE_TEXTURE),fb=gl.createFramebuffer();
          gl.activeTexture(gl.TEXTURE0+u('colors'));const texture=gl.getParameter(gl.TEXTURE_BINDING_2D);
          gl.bindFramebuffer(gl.FRAMEBUFFER,fb);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,texture,0);
          const id=u('selected'),rgba=new Uint8Array(4);gl.readPixels(id%2048,Math.floor(id/2048),1,1,gl.RGBA,gl.UNSIGNED_BYTE,rgba);palette=[...rgba];
          gl.bindFramebuffer(gl.FRAMEBUFFER,previous);gl.activeTexture(active);gl.deleteFramebuffer(fb);gl.drawArrays(gl.TRIANGLES,0,3);
          data=new Uint8Array(c.width*c.height*4);gl.readPixels(0,0,c.width,c.height,gl.RGBA,gl.UNSIGNED_BYTE,data);
        }else data=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
        let matching=0;for(let i=0;i<data.length;i+=4)if(data[i]===expected[0]&&data[i+1]===expected[1]&&data[i+2]===expected[2]&&data[i+3]===255)matching++;
        return {palette,matching_pixels:matching};
      },{expected,renderer});
      if(renderer==='webgl2')assert.deepEqual(pixels.palette,[...expected,255]);
      assert.ok(pixels.matching_pixels>20,'Actual visible fill pixels required');
      const values=await page.locator('.profile-attributes dd').allTextContents();assert.equal(values[0],example.name);
      const screenshot=output.replace(/\.json$/,'')+'-'+renderer+'-'+example.query.toLowerCase()+'.png';await page.screenshot({path:screenshot});
      run.profiles.push({...example,original_category_id:'owner:Q148',expected_rgb:expected,...pixels,values,screenshot});
      await page.locator('#close-details').click();save();
    }
    for(const mode of ['population','culture','religion','rank','topography','vegetation','climate','location','province','area','region','subcontinent','continent']){
      await page.locator(`[data-mode="${mode}"]`).click();await page.waitForTimeout(150);
      assert.equal(await page.locator(`[data-mode="${mode}"]`).getAttribute('aria-pressed'),'true');
      const rows=await legend();
      for(const row of rows.filter(row=>row.name.startsWith('Unknown')&&row.rgb))assert.equal(row.rgb,'rgb(83, 97, 92)');
      run.modes.push({mode,legend:rows,canvas:await canvas()});
    }
    await page.locator('[data-mode="owner"]').click();
    const final=await canvas();assert.equal(final.compilations,initial.compilations);
    if(renderer==='webgl2')assert.equal(final.ownershipUploads,initial.ownershipUploads);
    run.navigation_ownership_delta=0;
    await page.reload();await ready();
    await page.locator('#year-input').fill('1950');await page.locator('#year-form button').click();await page.waitForFunction(()=>document.querySelector('#map-year').textContent==='1,950 AD',null,{timeout:180000});await ready();
    const reloaded=await legend();assert.deepEqual(reloaded,run.samples.at(-1).legend);run.reload_stable=true;
    await page.close();save();
  }
  assert.deepEqual(receipt.page_errors,[]);receipt.completed=true;receipt.completed_at_utc=new Date().toISOString();save();console.log(JSON.stringify({completed:true,renderers:receipt.renderers.length,output}));
}catch(e){receipt.completed=false;receipt.failure=e.message;save();throw e;}
finally{await browser?.close();server?.kill('SIGTERM');}
