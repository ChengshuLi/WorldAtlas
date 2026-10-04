import path from 'node:path';
import {createHash} from 'node:crypto';
import http from 'node:http';
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {chromium} from '@playwright/test';
const previewDirectory=process.argv[4],bundleDirectory=process.argv[5];
const origin=new URL(process.argv[2]??''),output=process.argv[3];if(origin.protocol!=='https:'||origin.pathname!=='/'||origin.username||origin.password||origin.search||origin.hash||!output||!process.stdin.isTTY)throw Error('Supply Site and receipt with hidden terminal input');
process.stdin.setRawMode(true);console.log('Ready for private browser credential on hidden stdin.');
const token=await new Promise(resolve=>{let value='';process.stdin.on('data',chunk=>{value+=chunk.toString();if(!/[\r\n]/.test(value))return;process.stdin.pause();process.stdin.setRawMode(false);resolve(JSON.parse(value.trim()).token);});});
// Local GET-only transport lets headless Chromium use the session's authorized
// Node proxy/TLS configuration. It never exposes the credential to the browser.
const server=http.createServer(async(req,res)=>{try{if(req.method!=='GET'||req.url.startsWith('//')){res.writeHead(405);return res.end();}const url=new URL(req.url,origin);if(url.origin!==origin.origin)throw Error('Unsupported route');const local=previewDirectory&&(url.pathname==='/'?'index.html':/^\/assets\/[a-zA-Z0-9._-]+$/.test(url.pathname)?url.pathname.slice(1):null);
      if(local&&fs.existsSync(path.join(previewDirectory,local))){const bytes=fs.readFileSync(path.join(previewDirectory,local));res.writeHead(200,{'Content-Type':local.endsWith('.js')?'text/javascript':local.endsWith('.css')?'text/css':'text/html'});return res.end(bytes);}
const bundled=bundleDirectory&&(url.pathname==='/reference-attributes/startup-bundle.json.gz'?'reference-attributes/startup-bundle.json.gz':/^\/ownership\/startup-runs-[0-9]+\.bin\.gz$/.test(url.pathname)?url.pathname.slice(1):null);
if(bundled){const bytes=fs.readFileSync(path.join(bundleDirectory,bundled));res.writeHead(200,{'Content-Type':'application/gzip'});return res.end(bytes);}
const remote=await fetch(url,{headers:{'OAI-Sites-Authorization':'Bearer '+token},redirect:'error',signal:AbortSignal.timeout(60000)}),headers={};for(const key of ['content-type','cache-control','etag','last-modified'])if(remote.headers.has(key))headers[key]=remote.headers.get(key);let bytes=Buffer.from(await remote.arrayBuffer());
if(bundleDirectory&&url.pathname==='/atlas-geography.json'){
 const proof=JSON.parse(fs.readFileSync(path.join(bundleDirectory,'preview-root-proof.json')));
 if(remote.status!==200||createHash('sha256').update(bytes).digest('hex')!==proof.original_sha256)throw Error('Actual root changed');
 bytes=fs.readFileSync(path.join(bundleDirectory,'atlas-geography.json'));
 if(createHash('sha256').update(bytes).digest('hex')!==proof.candidate_sha256)throw Error('Candidate root changed');
 delete headers.etag;delete headers['last-modified'];
}
res.writeHead(remote.status,headers);res.end(bytes);}catch{if(!res.headersSent)res.writeHead(502);res.end('Verification transport unavailable');}});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));let browser;const profileReadbacks=[],modeReadbacks=[];
try{
 browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:'+server.address().port);await page.locator('#loading').waitFor({state:'hidden',timeout:120000});await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.rendered==='true',null,{timeout:120000});assert.equal(await page.locator('#year-error').textContent(),'');
 const positive=await page.locator('.atlas-pixel-canvas').evaluate(c=>({...c.dataset}));
 const controls=[];
 for(const [name,pattern,body,status] of [
  ['reference-corruption','**/reference-attributes/startup-bundle.json.gz','corrupt bundle',200],
  ['ownership-unavailable','**/ownership/startup-runs-0.bin.gz','missing ownership',404],
 ]){
  await page.route(pattern,route=>route.fulfill({status,contentType:'application/gzip',body}));
  await page.reload();
  await page.waitForFunction(()=>document.querySelector('#loading')?.textContent.includes('could not load')||document.querySelector('#year-error')?.textContent.includes('unavailable'),null,{timeout:120000});
  const readback=await page.evaluate(()=>({loading:document.querySelector('#loading')?.textContent,error:document.querySelector('#year-error')?.textContent,rendered:document.querySelector('.atlas-pixel-canvas')?.dataset.rendered??null,loading_hidden:document.querySelector('#loading')?.hidden}));
  assert.equal(readback.loading_hidden,false);if(name==='ownership-unavailable')assert.notEqual(readback.rendered,'true');else assert.match(readback.error,/unavailable/i);controls.push({name,status,readback,outcome:'passed'});
  await page.unroute(pattern);
 }
 await page.addInitScript(()=>{const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return type==='webgl2'?null:get.call(this,type,...args);};});
 await page.reload();await page.locator('#loading').waitFor({state:'hidden',timeout:120000});await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.rendered==='true',null,{timeout:120000});
 const fallback=await page.locator('.atlas-pixel-canvas').evaluate(c=>({...c.dataset}));
 const fallback_pixels=await page.locator('.atlas-pixel-canvas').evaluate(c=>{const ctx=c.getContext('2d');if(!ctx)return {context:false};const bytes=ctx.getImageData(0,0,c.width,c.height).data;let painted=0;for(let i=3;i<bytes.length;i+=4)if(bytes[i])painted++;return {context:true,width:c.width,height:c.height,painted_pixels:painted};});assert.equal(fallback_pixels.context,true);assert.ok(fallback_pixels.painted_pixels>0);assert.notEqual(fallback.renderer,'webgl2');assert.equal(await page.locator('#year-error').textContent(),'');assert.deepEqual(errors,[]);
 fs.writeFileSync(output,JSON.stringify({verified_at_utc:new Date().toISOString(),read_only:true,site:origin.origin,positive,controls,fallback,fallback_pixels,page_errors:errors,performance_proof:false,transport_limit:'New reference and ownership blobs local; actual pinned production root and remaining data GET-only. Full selected content; no hosted latency claim.'},null,2)+'\n');console.log(JSON.stringify({verified:true,negative_controls:controls.length,fallback:fallback.renderer}));
}finally{await browser?.close();await new Promise(resolve=>server.close(resolve));}
