// Real production bundle, isolated browser profiles, and an owned ephemeral server.
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import {chromium} from '@playwright/test';
import {requirePlainExecution,committedPreparationFiles} from '../../../scripts/native-ownership/native-preparation-guards.mjs';

requirePlainExecution();
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const options={};
for(let i=2;i<process.argv.length;i+=2){
  assert.ok(['--dist','--out'].includes(process.argv[i])&&process.argv[i+1]&&!options[process.argv[i]],'Use --dist isolated/static/dist --out fresh/owned/output');
  options[process.argv[i]]=process.argv[i+1];
}
assert.ok(options['--dist']&&options['--out']);
const dist=fs.realpathSync(path.resolve(root,options['--dist']));
const out=path.resolve(root,options['--out']);
assert.ok(out.startsWith(path.join(root,prefix)+path.sep)&&!fs.existsSync(out),'Fresh owned output required');
const head=execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
const producer=committedPreparationFiles(root,head,[prefix+'/verify-offline-map.mjs','scripts/native-ownership/native-preparation-guards.mjs','package.json','package-lock.json']);
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const MAX=32*1024*1024,files=new Map();
function asset(name){
  assert.ok(!path.isAbsolute(name)&&name.split('/').every(p=>p&&p!=='.'&&p!=='..'));
  const filename=path.join(dist,name),size=fs.statSync(filename).size;assert.ok(size<=MAX);
  const raw=fs.readFileSync(filename);files.set(name,{path:name,bytes:raw.length,sha256:sha(raw)});return raw;
}
function parsed(name){const raw=asset(name);return JSON.parse(name.endsWith('.gz')?gunzipSync(raw,{maxOutputLength:MAX}):raw);}
function blob(name){const raw=execFileSync('git',['-C',root,'show',head+':'+name],{maxBuffer:MAX});return {raw,pin:{commit:head,path:name,bytes:raw.length,sha256:sha(raw)}};}
const atlasBytes=asset('atlas-geography.json'),atlas=JSON.parse(atlasBytes);
const expected={release:'geography:review:2632d51da0efa5574c74638afe441c4efd5f29e93804c507a24cc6dbb56c0199',
  footprints:'6ea7c3613759d7b747c800c399b70c1be24e1f6aea21fc81c389cfdcc78d3eb1',
  native:'70204c43deefd1af97c898f120d3638d4b8a3953445df37036d5771a54d718cc'};
assert.equal(atlas.reference_release.id,expected.release);assert.equal(atlas.reference_release.footprints_sha256,expected.footprints);
assert.equal(atlas.pixelMap.canonical_grid_sha256,expected.native);assert.equal(atlas.pixelMap.method,'native-linear-evenodd-first-owner-v1');
assert.equal(atlas.preparedEvidence.footprints_sha256,expected.footprints);
assert.ok(atlas.nativeContextInputStage&&atlas.gridVerification,'Mandatory actual build context/selection receipts must be present');
const subjects=[{id:'gb:IRN:ADM2:26516999B17111396986996',query:'Saravan'},{id:'gb:PAK:ADM2:60131773B78019453337506',query:'Panjgur'}];
const targets=new Map(subjects.map(s=>[s.id,s]));
for(const name of atlas.parts)for(const f of parsed(name))if(targets.has(f.id))Object.assign(targets.get(f.id),{name:f.properties.name,pixelIndex:f.pixelIndex,gridBounds:f.gridBounds});
const candidates=blob('coordination/engineering/iran-pakistan-native-joint-991-20261006-local21/results-v3/candidates.json');
const repaired=JSON.parse(candidates.raw),found=new Set();
for(const name of atlas.geometryParts)for(const f of parsed(name))if(targets.has(f.id)){assert.deepEqual(f.geometry,repaired[f.id],'Built geometry must equal exact reviewed source arrays');found.add(f.id);}
assert.equal(found.size,2);for(const s of subjects)assert.ok(s.pixelIndex&&s.name&&s.gridBounds);
const deltaInput=blob('coordination/engineering/iran-pakistan-native-joint-991-20261006-local21/native-v1/native-cells.json');
const delta=JSON.parse(deltaInput.raw),cells=[];
for(const run of delta.changed_runs){assert.deepEqual(run.before,[]);assert.equal(run.after.length,1);assert.equal(run.component,true);for(let x=run.start;x<run.end;x++)cells.push({x:x+.5,y:run.y+.5,owner:run.after[0]});}
assert.equal(cells.length,954);assert.ok(cells.every(c=>subjects.some(s=>s.pixelIndex===c.owner)));
const lock=JSON.parse(fs.readFileSync(path.join(root,'package-lock.json')));
const playwrightPackage=JSON.parse(fs.readFileSync(path.join(root,'node_modules/@playwright/test/package.json')));
assert.equal(playwrightPackage.version,lock.packages['node_modules/@playwright/test'].version);
const mime={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.gz':'application/gzip','.svg':'image/svg+xml','.png':'image/png','.woff2':'font/woff2'};
const server=http.createServer((req,res)=>{
  try{
    const name=decodeURIComponent(new URL(req.url,'http://localhost').pathname),filename=path.resolve(dist,'.'+(name==='/'?'/index.html':name));
    if(name==='/favicon.ico'&&!fs.existsSync(filename)){res.writeHead(204);res.end();return;}
    if(!filename.startsWith(dist+path.sep)||!fs.statSync(filename).isFile()){res.writeHead(404);res.end();return;}
    const real=fs.realpathSync(filename);assert.ok(real.startsWith(dist+path.sep));
    res.writeHead(200,{'Content-Type':mime[path.extname(real)]??'application/octet-stream','Cache-Control':'no-store'});
    fs.createReadStream(real).on('error',()=>res.destroy()).pipe(res);
  }catch{res.writeHead(404);res.end();}
});
let browser;const results=[];
async function settled(page){
  await page.locator('#loading').waitFor({state:'hidden',timeout:120000});
  await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.rendered==='true',null,{timeout:120000});
  // Leaflet camera animations can finish after the loading indicator.
  await page.waitForFunction(()=>!document.querySelector('#map.leaflet-zoom-anim,#map .leaflet-zoom-anim,#map .leaflet-pan-anim'));
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
}
async function gpuOwners(page){
  return page.evaluate(cells=>{
    const canvas=document.querySelector('.atlas-pixel-canvas'),gl=canvas.getContext('webgl2'),program=gl.getParameter(gl.CURRENT_PROGRAM);
    const uniform=name=>gl.getUniform(program,gl.getUniformLocation(program,name));
    const previousFramebuffer=gl.getParameter(gl.FRAMEBUFFER_BINDING),previousActive=gl.getParameter(gl.ACTIVE_TEXTURE),framebuffer=gl.createFramebuffer();
    const read=(name,index)=>{
      gl.activeTexture(gl.TEXTURE0+uniform(name));const texture=gl.getParameter(gl.TEXTURE_BINDING_2D);
      gl.bindFramebuffer(gl.FRAMEBUFFER,framebuffer);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,texture,0);
      if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE)throw Error('Actual ownership texture cannot be read');
      const raw=new Uint32Array(4);gl.readPixels(index%2048,Math.floor(index/2048),1,1,gl.RGBA_INTEGER,gl.UNSIGNED_INT,raw);return raw;
    };
    const rows=new Map(),runs=new Map(),bits=uniform('locationCoordinateBits'),mask=2**bits-1;
    const run=i=>{if(!runs.has(i)){const raw=read('locationRuns',Math.floor(i/2)),at=(i%2)*2,a=raw[at],b=raw[at+1];runs.set(i,[a&mask,(b&mask)+1,(a>>>bits)+(b>>>bits)*2**(32-bits)]);}return runs.get(i);};
    try{
      if(!uniform('locationCompact'))throw Error('Expected actual compact native ownership textures');
      return cells.map(c=>{const y=Math.floor(c.y),x=Math.floor(c.x);if(!rows.has(y))rows.set(y,read('locationRows',y));const row=rows.get(y);let lo=row[0],hi=lo+row[1],end=hi;while(lo<hi){const mid=Math.floor((lo+hi)/2);if(run(mid)[1]<=x)lo=mid+1;else hi=mid;}return lo<end&&run(lo)[0]<=x?run(lo)[2]:0;});
    }finally{gl.bindFramebuffer(gl.FRAMEBUFFER,previousFramebuffer);gl.activeTexture(previousActive);gl.deleteFramebuffer(framebuffer);}
  },cells);
}
async function screenSamples(page,renderer,samples){
  return page.evaluate(({renderer,samples})=>{
    const canvas=document.querySelector('.atlas-pixel-canvas'),rect=canvas.getBoundingClientRect(),map=document.querySelector('#map').getBoundingClientRect();
    let origin,scale,gl;
    if(renderer==='webgl2'){
      gl=canvas.getContext('webgl2');const p=gl.getParameter(gl.CURRENT_PROGRAM),u=n=>gl.getUniform(p,gl.getUniformLocation(p,n));origin=[...u('origin')];scale=u('scale');gl.drawArrays(gl.TRIANGLES,0,3);
    }else{
      const [x,y,width,,stride]=canvas.dataset.frame.split('/').map(Number);origin=[x,y];scale=rect.width/(width*stride);
    }
    const projected=samples.map(c=>{
      const x=rect.left+(c.x-origin[0])*scale,y=rect.top+(c.y-origin[1])*scale;
      if(x<Math.max(rect.left,map.left)+2||x>=Math.min(rect.right,map.right)-2||y<Math.max(rect.top,map.top)+2||y>=Math.min(rect.bottom,map.bottom)-2)return null;
      const cx=Math.min(canvas.width-1,Math.max(0,Math.floor((x-rect.left)/rect.width*canvas.width))),cy=Math.min(canvas.height-1,Math.max(0,Math.floor((y-rect.top)/rect.height*canvas.height)));
      const rgba=new Uint8Array(4);
      if(gl)gl.readPixels(cx,canvas.height-1-cy,1,1,gl.RGBA,gl.UNSIGNED_BYTE,rgba);else rgba.set(canvas.getContext('2d').getImageData(cx,cy,1,1).data);
      return {...c,screen:[x,y],rgba:[...rgba]};
    }).filter(Boolean);
    return {origin,scale,rect:{left:rect.left,top:rect.top,width:rect.width,height:rect.height},frame:canvas.dataset.frame,samples:projected};
  },{renderer,samples});
}
try{
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  const base='http://127.0.0.1:'+server.address().port;
  browser=await chromium.launch({headless:true,args:['--enable-unsafe-swiftshader']});
  fs.mkdirSync(out);
  for(const renderer of ['webgl2','canvas']){
    const context=await browser.newContext({viewport:{width:1440,height:1080},deviceScaleFactor:1});
    let activePage,lastProbe;
    try{
      // Chrome's inspector drops bodies above its per-resource cache limit.
      // Hash a clone of the actual browser response without changing app bytes.
      await context.addInitScript(()=>{
        const original=window.fetch.bind(window);
        window.fetch=async(...args)=>{
          const response=await original(...args);
          if(new URL(response.url).pathname==='/atlas-geography.json'){
            response.clone().arrayBuffer().then(bytes=>crypto.subtle.digest('SHA-256',bytes))
              .then(hash=>{window.__testedAtlasSHA=[...new Uint8Array(hash)].map(b=>b.toString(16).padStart(2,'0')).join('');})
              .catch(error=>{window.__testedAtlasError=String(error);});
          }
          return response;
        };
      });
      if(renderer==='canvas')await context.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(kind,...args){return kind==='webgl2'?null:original.call(this,kind,...args);};});
      const page=await context.newPage(),errors=[],httpErrors=[],requests=[],consoleErrors=[],failedLocalRequests=[];
      activePage=page;
      const network=await context.newCDPSession(page);
      await network.send('Network.enable',{maxTotalBufferSize:128*1024*1024,maxResourceBufferSize:32*1024*1024});
      page.on('pageerror',e=>errors.push(e.message));page.on('response',response=>{if(response.url().startsWith(base)&&response.status()>=400)httpErrors.push({url:response.url(),status:response.status()});});
      page.on('console',message=>{if(message.type()==='error')consoleErrors.push(message.text());});
      page.on('requestfailed',request=>{if(request.url().startsWith(base))failedLocalRequests.push({url:request.url(),error:request.failure()?.errorText});});
      page.on('request',request=>requests.push(request.url()));
      await page.route('**/*',route=>{const url=route.request().url();if(url.startsWith('https://fonts.googleapis.com/'))return route.fulfill({status:200,contentType:'text/css',body:''});return url.startsWith(base+'/')||url.startsWith('data:')?route.continue():route.abort();});
      await page.goto(base,{waitUntil:'domcontentloaded'});
      await page.waitForFunction(()=>window.__testedAtlasSHA||window.__testedAtlasError,null,{timeout:120000});
      assert.equal(await page.evaluate(()=>window.__testedAtlasSHA),sha(atlasBytes),'Browser consumed the exact built atlas manifest');await settled(page);
      const startup=await page.locator('.atlas-pixel-canvas').evaluate(c=>({...c.dataset}));
      if(renderer==='webgl2'){assert.equal(startup.renderer,'webgl2');assert.equal(startup.precompiled,'true');assert.equal(startup.compilations,'0');assert.equal(startup.coverageUploads,'2','The complete checksum-validated physical grid must be uploaded');assert.deepEqual(await gpuOwners(page),cells.map(c=>c.owner),'Actual uploaded GPU native ownership covers all 954 supported additions');}
      else {assert.equal(await page.locator('.atlas-pixel-canvas').evaluate(c=>!!c.getContext('2d')),true);assert.equal(startup.compilations,'0');}
      const profileResults=[];
      for(const subject of subjects){
        await page.locator('#search').fill(subject.query);await page.locator(`[data-result="${subject.id}"]`).click();await settled(page);
        assert.equal(await page.locator('#details').getAttribute('data-profile-key'),subject.id+':2026');
        assert.equal(await page.locator('.profile-name-context').textContent(),'Present-day reference: '+subject.name);
        assert.equal(await page.locator('.breadcrumbs [data-unit]').count(),6);
        const values=await page.locator('.profile-attributes dd').allTextContents();assert.equal(values.length,8);
        const environments=[];
        for(let i=5;i<8;i++){assert.ok(values[i].trim()&&!values[i].includes('Unknown'),'Recomputed environmental reference must be visible');assert.equal(await page.locator('.profile-attributes dd').nth(i).locator('.reference-badge').textContent(),'Reference');environments.push(values[i]);}
        await page.locator('[data-mode="location"]').click();await page.locator('#close-details').click();await settled(page);
        const eligible=cells.filter(c=>c.owner===subject.pixelIndex);
        let camera=await screenSamples(page,renderer,eligible);
        assert.ok(camera.samples.length,'Reviewed new cells must be visible at the actual source-location camera');
        if(camera.scale<4){
          // Mouse client coordinates are integer screen pixels. A cell smaller
          // than a pixel cannot be a reliable independent click probe.
          const box=await page.locator('#map').boundingBox(),center=[box.x+box.width/2,box.y+box.height/2];
          const nearest=[...camera.samples].sort((a,b)=>Math.hypot(a.screen[0]-center[0],a.screen[1]-center[1])-Math.hypot(b.screen[0]-center[0],b.screen[1]-center[1]))[0];
          await page.mouse.move(...center);await page.mouse.down();
          await page.mouse.move(center[0]+center[0]-nearest.screen[0],center[1]+center[1]-nearest.screen[1],{steps:12});await page.mouse.up();await settled(page);
          for(let step=0;step<8;step++){
            camera=await screenSamples(page,renderer,eligible);if(camera.scale>=4)break;
            const frame=await page.locator('.atlas-pixel-canvas').getAttribute('data-frame');await page.locator('#zoom-in').click();
            await page.waitForFunction(old=>document.querySelector('.atlas-pixel-canvas').dataset.frame!==old,frame);await settled(page);
          }
        }
        assert.ok(camera.scale>=4&&camera.samples.length,'Independent click probes require visible cells at least four screen pixels wide');
        const probes=[camera.samples[0],camera.samples[Math.floor(camera.samples.length/2)],camera.samples.at(-1)];
        const picks=[];
        for(const probe of probes){
          lastProbe={...probe,subject:subject.id};
          await page.mouse.move(...probe.screen);await page.locator('.leaflet-tooltip').waitFor({state:'visible'});
          assert.equal(await page.locator('.leaflet-tooltip').textContent(),subject.name,'Actual pointer hover picks the supported new native owner');
          await page.mouse.click(...probe.screen);await page.locator('#details').waitFor({state:'visible'});
          assert.equal(await page.locator('#details').getAttribute('data-profile-key'),subject.id+':2026','Real UI click opens the expected repaired native owner');
          picks.push({cell:[probe.x,probe.y],owner:subject.id,rgba:probe.rgba});await page.locator('#close-details').click();await settled(page);
        }
        await page.screenshot({path:path.join(out,renderer+'-'+subject.query.toLowerCase()+'.png')});
        profileResults.push({id:subject.id,name:subject.name,environments,camera,picks});
      }
      assert.deepEqual(errors,[]);assert.deepEqual(httpErrors,[]);assert.deepEqual(consoleErrors,[]);
      // Stream reader cancellation can surface as ERR_ABORTED after the checked
      // grid has loaded. Retain those events and reject other transport failures.
      assert.deepEqual(failedLocalRequests.filter(r=>r.error!=='net::ERR_ABORTED'),[]);
      assert.ok(!requests.some(url=>new URL(url).pathname.startsWith('/api/')),'Offline static app must not require hosted API');
      results.push({renderer,startup,profiles:profileResults,page_errors:errors,http_errors:httpErrors,console_errors:consoleErrors,failed_local_requests:failedLocalRequests,local_requests:requests.filter(url=>url.startsWith(base)).map(url=>new URL(url).pathname)});
    }catch(error){
      if(activePage){
        const state=await activePage.evaluate(probe=>{
          const element=probe&&document.elementFromPoint(...probe.screen);
          return {canvas:document.querySelector('.atlas-pixel-canvas')?.dataset,
            details:{hidden:document.querySelector('#details')?.hidden,key:document.querySelector('#details')?.dataset.profileKey},
            tooltip:document.querySelector('.leaflet-tooltip')?.textContent,
            hit:element?{tag:element.tagName,id:element.id,className:element.className,ancestors:[...function*(e){while(e){yield e.tagName+'#'+e.id+'.'+e.className;e=e.parentElement;}}(element)]}:null};
        },lastProbe);
        fs.writeFileSync(path.join(out,renderer+'-failure.json'),JSON.stringify({error:String(error),lastProbe,state})+'\n',{flag:'wx'});
        await activePage.screenshot({path:path.join(out,renderer+'-failure.png')});
      }
      throw error;
    }finally{await context.close();}
  }
  const comparisons=subjects.map((subject,i)=>{
    const gpu=results[0].profiles[i],cpu=results[1].profiles[i];assert.deepEqual(gpu.environments,cpu.environments);
    assert.ok(Math.abs(gpu.camera.scale-cpu.camera.scale)<1e-6,'Search produced the same map scale in both renderers');
    // Canvas aligns its cached frame to stride boundaries; compare implied screen
    // placement rather than requiring its internal origin to equal GPU origin.
    const gpuCell=gpu.camera.samples.find(s=>cpu.camera.samples.some(t=>t.x===s.x&&t.y===s.y));assert.ok(gpuCell);
    const cpuCell=cpu.camera.samples.find(s=>s.x===gpuCell.x&&s.y===gpuCell.y);
    assert.ok(Math.abs(gpuCell.screen[0]-cpuCell.screen[0])<=2&&Math.abs(gpuCell.screen[1]-cpuCell.screen[1])<=2,'Same geographic cell occupies the same searched camera');
    const paired=gpu.camera.samples.flatMap(g=>{const c=cpu.camera.samples.find(c=>c.x===g.x&&c.y===g.y);return c?[{cell:[g.x,g.y],gpu:g.rgba,canvas:c.rgba,equal:g.rgba.every((v,k)=>Math.abs(v-c.rgba[k])<=1)}]:[];});
    return {id:subject.id,matching_ui_owner:true,matching_reference_values:true,paired_visible_cells:paired.length,matching_rgba_cells:paired.filter(p=>p.equal).length,paired};
  });
  const report={version:1,execution_commit:head,producer,dist,expected,atlas_manifest_sha256:sha(atlasBytes),inputs:[candidates.pin,deltaInput.pin],built_assets:[...files.values()],
    playwright_version:playwrightPackage.version,browser_version:browser.version(),owned_browser_contexts:true,optional_remote_font_css_disabled:true,all_954_gpu_owners_checked:true,results,comparisons,
    limits:['Isolated headless Chromium checks the actual built production application; this is not a personal-browser or hardware-device certification.',
      'Canvas UI hover/click checks sample supported additions; all 954 additions are checked against actual uploaded GPU ownership textures.',
      'RGBA comparisons are reported, not falsely certified identical: Canvas sampled fills/strokes and GPU borders differ at narrow subpixel edges.',
      'Geographic/source authority, historical completeness and public delivery are outside this browser verification.']};
  fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(report)+'\n',{flag:'wx'});
  console.log(JSON.stringify({renderers:results.length,targets:subjects.length,gpu_checked_new_cells:954,ui_pick_checks:results.reduce((n,r)=>n+r.profiles.reduce((k,p)=>k+p.picks.length,0),0),out}));
}finally{await browser?.close();await new Promise(resolve=>server.listening?server.close(resolve):resolve());}
