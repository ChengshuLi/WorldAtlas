import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {chromium} from '@playwright/test';
import {wheelTiming} from './wheel-measurement.mjs';

const [site,output]=process.argv.slice(2);
if(!site||!output)throw Error('Use URL output.json; isolated headless browser only');
const origin=new URL(site);
if(!['https://worldatlas-explorer.chengshu-worldatlas.workers.dev','https://eu5db.com','http://127.0.0.1:3886'].includes(origin.origin))throw Error('Unexpected benchmark target');
const atlas=origin.hostname!=='eu5db.com',errors=[],requests=[],trace=[];
const receipt={version:1,site,started_at:new Date().toISOString(),conditions:{platform:os.platform(),arch:os.arch(),cpus:os.cpus().map(c=>c.model),viewport:{width:1440,height:1080},device_scale_factor:1,browser:'isolated Playwright headless Chromium; fresh context, no user profile',input:'synthetic trusted Playwright mouse.wheel; synthetic dispatch for deltaMode controls, no physical device certificate',network:'no artificial throttle; public host direct GET; localhost variant retains same public APIs/static data',cache:'cold context startup, warmed assets during sequential wheel samples; provider cache/wake unknown'},errors,requests,samples:[],limits:['rAF intervals and first observed canvas CSS transform/draw measure browser work, not photon latency or physical scroll-device feel','EU5 comparison measures frame/long-task behavior under same synthetic input; no claims about its data/implementation','No universal hardware/FPS or mobile certificate']};
const save=()=>{fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(receipt,null,2)+'\n');};
const args=process.env.ATLAS_BENCH_ANGLE?['--use-angle='+process.env.ATLAS_BENCH_ANGLE]:[];
receipt.conditions.launch_args=args;
const browser=await chromium.launch({args});
try{
 receipt.conditions.browser_version=browser.version();
 const context=await browser.newContext({viewport:receipt.conditions.viewport,deviceScaleFactor:1}),page=await context.newPage();
 page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>requests.push({url:r.url(),status:r.status()}));
 await page.addInitScript(()=>{
  window.__wheelProbe={draws:[],longTasks:[],events:[]};
  for(const type of [window.WebGLRenderingContext,window.WebGL2RenderingContext])if(type)for(const method of ['drawArrays','drawElements']){
   const original=type.prototype[method];type.prototype[method]=function(...args){window.__wheelProbe.draws.push(performance.now());return original.apply(this,args);};
  }
  new PerformanceObserver(list=>{for(const e of list.getEntries())window.__wheelProbe.longTasks.push({start:e.startTime,duration:e.duration});}).observe({type:'longtask',buffered:true});
  document.addEventListener('wheel',e=>window.__wheelProbe.events.push({time:performance.now(),deltaY:e.deltaY,deltaMode:e.deltaMode,trusted:e.isTrusted}),{capture:true,passive:true});
 });
 if(process.env.ATLAS_BENCH_CANVAS==='1'){
  receipt.conditions.renderer='forced Canvas fallback';
  await page.addInitScript(()=>{const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return type==='webgl2'?null:get.call(this,type,...args);};});
 }
 const cdp=await context.newCDPSession(page);await cdp.send('Performance.enable');
 const start=Date.now();await page.goto(site,{waitUntil:'domcontentloaded',timeout:120000});
 if(atlas){await page.locator('#loading').waitFor({state:'hidden',timeout:180000});await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.rendered==='true',null,{timeout:180000});}
 else{await page.locator('canvas').first().waitFor({timeout:120000});await page.waitForTimeout(5000);}
 receipt.initial_ms=Date.now()-start;
 receipt.initial=await page.evaluate(()=>({canvas:[...document.querySelectorAll('canvas')].map(c=>({className:c.className,width:c.width,height:c.height,dataset:{...c.dataset}})),scripts:[...document.scripts].map(s=>s.src).filter(Boolean)}));
 if(atlas){const response=await page.request.get(new URL('/atlas-geography.json',site).href);const bytes=await response.body();receipt.asset_sha256=crypto.createHash('sha256').update(bytes).digest('hex');receipt.reference_release=(JSON.parse(bytes)).reference_release;}
 try{receipt.gpu=(await (await browser.newBrowserCDPSession()).send('SystemInfo.getInfo')).gpu;}catch{receipt.gpu='unavailable';}
 cdp.on('Tracing.dataCollected',d=>trace.push(...d.value));await cdp.send('Tracing.start',{categories:'devtools.timeline,blink.user_timing',transferMode:'ReportEvents'});
 const selector=atlas?'#map':'canvas';
 async function sample(label,deltas,spacing=60,reset=true){
  if(atlas&&reset){await page.locator('#home').click();await page.waitForTimeout(500);}
  const bounds=await page.locator(selector).first().boundingBox(),pointer={x:bounds.x+bounds.width*.60,y:bounds.y+bounds.height*.45};
  await page.mouse.move(pointer.x,pointer.y);
  const before=await page.evaluate(()=>({...document.querySelector('.atlas-pixel-canvas')?.dataset})),from=requests.length;
  await page.evaluate(()=>{
   const p=window.__wheelProbe;p.frames=[];p.transforms=[];p.draws=[];p.longTasks=[];p.events=[];p.running=true;p.started=performance.now();
   const frame=time=>{if(!p.running)return;p.frames.push(time);const c=document.querySelector('.atlas-pixel-canvas')||document.querySelector('canvas');p.transforms.push({time,transform:c?getComputedStyle(c).transform:null,pane:document.querySelector('.leaflet-map-pane')?getComputedStyle(document.querySelector('.leaflet-map-pane')).transform:null,frame:c?.dataset.frame});requestAnimationFrame(frame);};requestAnimationFrame(frame);
  });
  for(const delta of deltas){await page.mouse.wheel(0,delta);await page.waitForTimeout(spacing);}
  await page.waitForTimeout(500);
  const data=await page.evaluate(()=>{window.__wheelProbe.running=false;return window.__wheelProbe;});
  const after=await page.evaluate(()=>({...document.querySelector('.atlas-pixel-canvas')?.dataset}));
  const timing=wheelTiming(data);if(!atlas)timing.first_observed_transform_ms=null;
  const result={label,spacing_ms:spacing,deltas,pointer,before,after,...timing,long_tasks:data.longTasks.filter(task=>task.start>=data.started),ownership_compilation_delta:Number(after.compilations)-Number(before.compilations),ownership_upload_delta:Number(after.ownershipUploads)-Number(before.ownershipUploads),new_requests:requests.slice(from),raw:data};
  receipt.samples.push(result);save();console.log(JSON.stringify({label,first_ms:result.first_observed_transform_ms,p95_ms:result.raf_p95_ms,zoom:after.frame,compile:result.ownership_compilation_delta,ownership:result.ownership_upload_delta}));
 }
 for(let i=1;i<=3;i++)await sample('notched-in-'+i,Array(8).fill(-120));
 await sample('high-resolution',Array(60).fill(-6),8);
 await sample('rapid-reversal',[-120,-120,-120,-120,120,120,120,120],25);
 await sample('notched-out',Array(8).fill(120));
 if(atlas){
  for(let i=0;i<13;i++){await page.locator('#zoom-out').click();await page.waitForTimeout(280);}
  await sample('full-range-in',Array(8).fill(-120),60,false);
  for(let i=0;i<13;i++){await page.locator('#zoom-in').click();await page.waitForTimeout(280);}
  await sample('full-range-out',Array(8).fill(120),60,false);
 }
 const complete=new Promise(resolve=>cdp.once('Tracing.tracingComplete',resolve));await cdp.send('Tracing.end');await complete;
 fs.writeFileSync(output.replace(/\.json$/,'')+'-trace.json.gz',gzipSync(JSON.stringify({traceEvents:trace}),{level:9}));
 await page.screenshot({path:output.replace(/\.json$/,'')+'.png'});
 receipt.completed=true;receipt.completed_at=new Date().toISOString();save();
}catch(e){receipt.completed=false;receipt.failure={name:e.name,message:e.message};save();throw e;}
finally{await browser.close();}
