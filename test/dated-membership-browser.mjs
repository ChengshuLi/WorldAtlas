// Exercise actual WebGL/Canvas rendering with explicitly synthetic, adjacent
// territories. Fixtures never enter the database or published history.
import {spawn} from 'node:child_process';
import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
import {projectCell} from '../src/pixel-grid.js';
import {formatYear} from '../src/model.js';

const port=process.env.ATLAS_MEMBERSHIP_TEST_PORT||'3207';
const server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',port,'--strictPort'],{stdio:['ignore','pipe','pipe']});
const units=[['continent','continent',null,'Europe'],['subcontinent','subcontinent','continent','Northern Europe'],['region','region','subcontinent','Britain'],['area','area','region','Reference area'],['dated-area','area','region','Dated area fixture'],['province','province','area','Reference province'],['other-province','province','area','Other province fixture']].map(([id,level,parent_id,name])=>({id,level,parent_id,name,metadata:{basis:'Explicit synthetic browser fixture'}}));
const polygon=(left,right)=>({type:'Polygon',coordinates:[[[left,51.4],[right,51.4],[right,51.6],[left,51.6],[left,51.4]]]});
const identity='atlas:city:GBR-Greater London',neighbor='fixture:neighbor';
const features=[[identity,'London','province',polygon(-.25,-.1)],[neighbor,'Neighbor fixture','other-province',polygon(-.1,.05)]].map(([id,name,parent_id,geometry])=>({id,type:'Feature',geometry,properties:{id,name,parent_id,reference_owner:'Fixture polity',metadata:{source_name:'Explicit synthetic browser fixture',source_url:'https://example.com/browser-fixture',reference_year:2026}}}));
const history=[{id:'fixture:dated-membership',entity_id:identity,field:'parent',value:'other-province'},{id:'fixture:dated-area-membership',entity_id:'other-province',field:'parent',value:'dated-area'}].map(r=>({...r,valid_from:1000,valid_to:1100,source:'Synthetic browser membership; not historical evidence',method:'direct',is_example:0}));
const geography={type:'FeatureCollection',units,features,temporal:{entities:[...units.map(u=>({...u,kind:u.level})),...features.map(f=>({id:f.id,kind:'location',name:f.properties.name,parent_id:f.properties.parent_id}))],history,links:[]}};
const snapshot=year=>({year,states:[],polities:[],boundaries:[],temporal_history:[],attributes:features.map(f=>({id:'fixture:owner:'+f.id,location_id:f.id,attribute:'owner',value:'Fixture polity',category_id:'owner:fixture',method:'direct',status:'sourced',source:'Synthetic browser ownership; not historical evidence',valid_from:-3000,valid_to:2027,is_example:0}))});
let browser;
try{
 await new Promise((resolve,reject)=>{let output='';server.stdout.on('data',chunk=>{output+=String(chunk);if(output.includes(`http://127.0.0.1:${port}`))resolve();});server.once('exit',code=>reject(Error(`Vite exited ${code}`)));});
 browser=await chromium.launch();
 for(const fallback of [false,true]){
  const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.addInitScript(({fallback})=>{
   window.membershipAudit={workers:0,compileMessages:0,strokes:[]};
   const NativeWorker=window.Worker;
   window.Worker=class extends NativeWorker{
    constructor(...args){super(...args);window.membershipAudit.workers++;}
    postMessage(message,...args){if(['locations','political'].includes(message.type)&&message.index?.length)window.membershipAudit.compileMessages++;return super.postMessage(message,...args);}
   };
   if(fallback){
    const get=HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext=function(type,...args){return type==='webgl2'?null:get.call(this,type,...args);};
    const NativePath=window.Path2D;
    window.Path2D=class extends NativePath{constructor(...args){super(...args);this.testSegments=0;}lineTo(...args){this.testSegments++;return super.lineTo(...args);}};
    const stroke=CanvasRenderingContext2D.prototype.stroke;
    CanvasRenderingContext2D.prototype.stroke=function(path,...args){if(this.canvas.classList.contains('atlas-pixel-canvas'))window.membershipAudit.strokes.push({width:this.lineWidth,segments:path?.testSegments??0});return stroke.call(this,path,...args);};
   }
  },{fallback});
  await page.route('**/api/geography',route=>route.fulfill({json:geography}));
  await page.route('**/api/snapshot?*',route=>route.fulfill({json:snapshot(Number(new URL(route.request().url()).searchParams.get('year')))}));
  await page.goto(`http://127.0.0.1:${port}`);
  await page.locator('#loading').waitFor({state:'hidden',timeout:60000});
  await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.rendered==='true',null,{timeout:60000});
  const settle=()=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  const openLocation=async()=>{await page.locator('#search').fill('London');await page.locator(`[data-result="${identity}"]`).click();};
  const goYear=async year=>{await page.locator('#year-input').fill(String(year));await page.locator('#year-form button').click();await page.waitForFunction(expected=>document.querySelector('#map-year').textContent===expected,formatYear(year));await page.locator('#loading').waitFor({state:'hidden'});await settle();};
  const gpuValues=()=>page.evaluate(()=>{
   const canvas=document.querySelector('.atlas-pixel-canvas'),gl=canvas.getContext('webgl2');if(!gl)return null;
   const program=gl.getParameter(gl.CURRENT_PROGRAM),unit=name=>gl.getUniform(program,gl.getUniformLocation(program,name)),active=gl.getParameter(gl.ACTIVE_TEXTURE),previous=gl.getParameter(gl.FRAMEBUFFER_BINDING),fb=gl.createFramebuffer();
   const read=(name,integer)=>{gl.activeTexture(gl.TEXTURE0+unit(name));gl.bindFramebuffer(gl.FRAMEBUFFER,fb);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,gl.getParameter(gl.TEXTURE_BINDING_2D),0);const bytes=integer?new Uint32Array(8):new Uint8Array(8);gl.readPixels(1,0,2,1,integer?gl.RGBA_INTEGER:gl.RGBA,integer?gl.UNSIGNED_INT:gl.UNSIGNED_BYTE,bytes);return [...bytes];};
   const metadata=read('metadata',true),colors=read('colors',false);gl.bindFramebuffer(gl.FRAMEBUFFER,previous);gl.activeTexture(active);gl.deleteFramebuffer(fb);gl.drawArrays(gl.TRIANGLES,0,3);return {metadata,colors,error:gl.getError()};
  });
  await openLocation();await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas').dataset.locationBorders==='true');await page.locator('#close-details').click();
  await page.locator('[data-mode="province"]').click();await settle();
  const baseline=await page.evaluate(()=>{
   const canvas=document.querySelector('.atlas-pixel-canvas');window.membershipAudit.canvas=canvas;
   const gl=canvas.getContext('webgl2');if(gl){const program=gl.getParameter(gl.CURRENT_PROGRAM),active=gl.getParameter(gl.ACTIVE_TEXTURE);window.membershipAudit.program=program;window.membershipAudit.ownershipTextures=['locationRows','locationRuns'].map(name=>{gl.activeTexture(gl.TEXTURE0+gl.getUniform(program,gl.getUniformLocation(program,name)));return gl.getParameter(gl.TEXTURE_BINDING_2D);});gl.activeTexture(active);}
   return {data:{...canvas.dataset},workers:window.membershipAudit.workers,compileMessages:window.membershipAudit.compileMessages,provinceSegments:window.membershipAudit.strokes.filter(s=>s.width===1.5).at(-1)?.segments};
  });
  const initialGPU=await gpuValues();
  if(initialGPU){assert.notEqual(initialGPU.metadata[0],initialGPU.metadata[4]);assert.notDeepEqual(initialGPU.colors.slice(0,4),initialGPU.colors.slice(4));assert.equal(initialGPU.error,0);}
  else assert.ok(baseline.provinceSegments>0,'Canvas initially draws a real provincial boundary');
  for(const year of [1000,1050,1100,1000,2026]){
   await goYear(year);await openLocation();
   const dated=year>=1000&&year<1100;
   assert.equal(await page.locator(`.breadcrumbs [data-unit="${dated?'other-province':'province'}"]`).count(),1);
   assert.equal(await page.locator(`.breadcrumbs [data-unit="${dated?'dated-area':'area'}"]`).count(),1);
   assert.equal(await page.locator('.profile-attributes > div').filter({has:page.locator('dt',{hasText:/^Owner$/})}).locator('dd').textContent(),'Fixture polity');
   if(dated)assert.match(await page.locator('.profile-evidence').textContent(),/Includes sourced membership/);
   await page.locator('#close-details').click();await settle();
   const state=await page.evaluate(()=>{
    const canvas=document.querySelector('.atlas-pixel-canvas'),audit=window.membershipAudit,gl=canvas.getContext('webgl2');let sameTextures=true;
    if(gl){const program=gl.getParameter(gl.CURRENT_PROGRAM),active=gl.getParameter(gl.ACTIVE_TEXTURE);sameTextures=program===audit.program&&['locationRows','locationRuns'].every((name,i)=>{gl.activeTexture(gl.TEXTURE0+gl.getUniform(program,gl.getUniformLocation(program,name)));return gl.getParameter(gl.TEXTURE_BINDING_2D)===audit.ownershipTextures[i];});gl.activeTexture(active);}
    return {sameCanvas:canvas===audit.canvas,sameTextures,data:{...canvas.dataset},workers:audit.workers,compileMessages:audit.compileMessages,provinceSegments:audit.strokes.filter(s=>s.width===1.5).at(-1)?.segments};
   });
   assert.equal(state.sameCanvas,true,'Membership change retains the live renderer');assert.equal(state.sameTextures,true,'Membership cannot replace ownership textures');assert.equal(state.workers,baseline.workers);assert.equal(state.compileMessages,baseline.compileMessages);assert.equal(state.data.compilations,baseline.data.compilations);assert.equal(state.data.ownershipUploads,baseline.data.ownershipUploads);
   const gpu=await gpuValues();if(gpu){assert.equal(gpu.metadata[0]===gpu.metadata[4],dated);assert.equal(JSON.stringify(gpu.colors.slice(0,4))===JSON.stringify(gpu.colors.slice(4)),dated);assert.equal(gpu.error,0);}else assert.equal(state.provinceSegments===0,dated,'Canvas province lookup changes the actual drawn boundary');
   // Click an interior geographic cell: picking must keep its location identity,
   // owner and dated chain even though only metadata changed.
   const point=await page.evaluate(projected=>{
    const canvas=document.querySelector('.atlas-pixel-canvas'),box=canvas.getBoundingClientRect(),gl=canvas.getContext('webgl2');let x,y;
    if(gl){const p=gl.getParameter(gl.CURRENT_PROGRAM),u=n=>gl.getUniform(p,gl.getUniformLocation(p,n)),origin=u('origin'),scale=u('scale');x=(projected[0]-origin[0])*scale;y=(projected[1]-origin[1])*scale;}
    else{const [left,top,width,,stride]=canvas.dataset.frame.split('/').map(Number),scale=box.width/(width*stride);x=(projected[0]-left)*scale;y=(projected[1]-top)*scale;}
    return {x:box.left+x,y:box.top+y};
   },projectCell(-.175,51.5));
   await page.mouse.click(point.x,point.y);assert.equal(await page.locator('#details h3').textContent(),'London');assert.equal(await page.locator(`.breadcrumbs [data-unit="${dated?'other-province':'province'}"]`).count(),1);await page.locator('#close-details').click();
  }
  const beforeNavigation=await page.locator('.atlas-pixel-canvas').evaluate(c=>({...c.dataset}));
  await page.locator('#zoom-out').click();await page.waitForFunction(frame=>document.querySelector('.atlas-pixel-canvas').dataset.frame!==frame,beforeNavigation.frame);await page.setViewportSize({width:1200,height:900});await settle();
  const afterNavigation=await page.locator('.atlas-pixel-canvas').evaluate(c=>({...c.dataset}));assert.equal(afterNavigation.compilations,baseline.data.compilations);assert.equal(afterNavigation.ownershipUploads,baseline.data.ownershipUploads);assert.deepEqual(errors,[]);
  console.log(`PASS ${fallback?'Canvas':'WebGL'}: dated location/higher membership updates province fills/borders and actual picking, restores reference chains, and performs zero ownership recompilations/uploads or renderer replacement.`);
  await page.close();
 }
}finally{await browser?.close();server.kill('SIGTERM');}
