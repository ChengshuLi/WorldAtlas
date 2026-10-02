// Explicit expensive benchmark, not part of routine unit test discovery.
import fs from 'node:fs';
import path from 'node:path';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
import {createServer} from 'vite';
import {chromium} from '@playwright/test';
import {loadFeatures,indexAt,compileSparse} from '../scripts/audit-grid-resolutions.mjs';
import {createGridIndex} from '../src/pixel-grid.js';
import {packOwnership,ownershipRun} from '../src/pixel-ownership.js';
import {footprintHash} from '../scripts/check-prepared.mjs';
const directory='.cache/compact-ownership-benchmark';fs.mkdirSync(directory,{recursive:true});
if(process.argv.includes('--candidate')){
 const zoom=Number(process.argv.find(a=>a.startsWith('--zoom=')).slice(7)),started=performance.now(),features=loadFeatures(),hash=footprintHash(features);
 const grid=compileSparse(indexAt(createGridIndex(features),zoom),256*2**zoom),compiled=performance.now(),packed=packOwnership(grid),packing=performance.now();
 const dest=path.join(directory,String(zoom));fs.mkdirSync(dest,{recursive:true});const parts=[];let gzipBytes=0;
 for(const kind of ['rows','runs'])for(let offset=0;offset<packed[kind].length;offset+=1048576){
  const words=packed[kind].subarray(offset,offset+1048576),raw=Buffer.from(words.buffer,words.byteOffset,words.byteLength),bytes=gzipSync(raw,{level:9}),filename=kind+'-'+offset+'.gz';fs.writeFileSync(path.join(dest,filename),bytes);gzipBytes+=bytes.length;parts.push({kind,offset,words:words.length,path:filename,sha256:createHash('sha256').update(raw).digest('hex')});
 }
 const samples=[];for(let y=0;y<packed.size;y+=Math.max(1,Math.floor(packed.size/1024))){const count=packed.rows[y*2+1];if(count){const r=ownershipRun(packed,packed.rows[y*2]+Math.floor(count/2));samples.push({x:Math.floor((r.start+r.end-1)/2),y,id:r.id});}}
 const result={zoom,footprints_sha256:hash,locations:features.length,runs:grid.runs,raw_bytes:packed.rows.byteLength+packed.runs.byteLength,gzip_bytes:gzipBytes,gpu_texture_width:2048,gpu_runs_texture_height:Math.ceil(grid.runs/2/2048),gpu_rows_texture_height:Math.ceil(packed.size/2048),gpu_padded_ownership_bytes:2048*Math.ceil(grid.runs/2/2048)*16+2048*Math.ceil(packed.size/2048)*8,compile_ms:Math.round(compiled-started),pack_ms:Math.round(packing-compiled),total_prepare_ms:Math.round(performance.now()-started),peak_rss_bytes:process.resourceUsage().maxRSS*1024};
 fs.writeFileSync(path.join(dest,'manifest.json'),JSON.stringify({version:packed.version,coordinateBits:packed.coordinateBits,size:packed.size,runWords:packed.runs.length,parts,samples,stats:result}));console.log(JSON.stringify(result));
}else{
 const zooms=(process.argv.find(a=>a.startsWith('--zooms='))?.slice(8)??'7,8,10').split(',').map(Number),transport=process.argv.find(a=>a.startsWith('--transport='))?.slice(12)??'';if(!process.argv.includes('--assets-only'))for(const zoom of zooms)await new Promise((resolve,reject)=>{const child=spawn(process.execPath,['--max-old-space-size=4096','test/compact-ownership-benchmark.mjs','--candidate','--zoom='+zoom],{stdio:'inherit'});child.on('error',reject);child.on('exit',code=>code?reject(Error('Candidate failed '+code)):resolve());});
 const server=await createServer({server:{port:3295,strictPort:true},logLevel:'error'});await server.listen();const browser=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});const results=[];
 try{for(const zoom of zooms){const page=await browser.newPage();await page.goto('http://localhost:3295/src/pixel-ownership.js');const result=await page.evaluate(async zoom=>{
   const {PixelGPU}=await import('/src/pixel-gpu.js'),{loadOwnershipAssets}=await import('/src/ownership-assets.js'),{pickOwnership,samplePackedOwnership}=await import('/src/pixel-ownership.js');
   const prefix='/.cache/compact-ownership-benchmark/'+zoom.zoom+'/'+(zoom.transport?zoom.transport+'/':''),manifest=await fetch(prefix+'manifest.json').then(r=>r.json());const started=performance.now(),grid=await loadOwnershipAssets(manifest,p=>fetch(prefix+p.slice(2))),loaded=performance.now();
   let sampleMismatch=0;for(const s of manifest.samples)if(pickOwnership(grid,s.x,s.y)!==s.id)sampleMismatch++;
   const canvas=document.createElement('canvas');document.body.replaceChildren(canvas);canvas.width=1280;canvas.height=720;const gpu=new PixelGPU(canvas),gl=gpu.gl;gpu.ownership('location',grid);const colors=new Uint8Array((manifest.stats.locations+1)*4),metadata=new Uint32Array((manifest.stats.locations+1)*2);for(let i=1;i<=manifest.stats.locations;i++){colors.set([i%239,127,211,255],i*4);metadata.set([Math.ceil(i/10),Math.ceil(i/100)],i*2);}gpu.upload('colors',colors);gpu.upload('metadata',metadata,2);gl.finish();const uploaded=performance.now(),navigation=[];
   const before=gpu.uploads;for(const [width,height,label] of [[1280,720,'desktop'],[390,844,'mobile viewport']]){canvas.width=width;canvas.height=height;const frames=[],submission=[],cpu=[];for(let k=0;k<5;k++){const at=performance.now();gpu.draw({origin:{x:grid.size*.45+k*grid.size*.0001,y:grid.size*.25},scale:width/grid.size*(1+k*.08),zoom:3,localBorders:true,selected:0,hasPolitical:false,dpr:1});submission.push(performance.now()-at);const sync=new Uint8Array(4);gl.readPixels(Math.floor(width/2),Math.floor(height/2),1,1,gl.RGBA,gl.UNSIGNED_BYTE,sync);frames.push(performance.now()-at);const cpuAt=performance.now();samplePackedOwnership(grid,{x:Math.floor(grid.size*.45),y:Math.floor(grid.size*.25),width,height,stride:Math.max(1,Math.floor(grid.size/width))});cpu.push(performance.now()-cpuAt);}navigation.push({label,width,height,submission_ms:submission.map(x=>Math.round(x*100)/100),completed_frame_with_readback_ms:frames.map(x=>Math.round(x*100)/100),cpu_fallback_sampling_ms:cpu.map(x=>Math.round(x*100)/100)});}
   // Actual rendered interior source cell rather than only packed CPU samples.
   const sample=manifest.samples[Math.floor(manifest.samples.length*.5)];canvas.width=16;canvas.height=16;gpu.draw({origin:{x:sample.x,y:sample.y},scale:16,zoom:10,localBorders:false,selected:0,hasPolitical:false,dpr:1});const rgba=new Uint8Array(4);gl.readPixels(8,8,1,1,gl.RGBA,gl.UNSIGNED_BYTE,rgba);const framebufferMatches=rgba.every((x,k)=>x===colors[sample.id*4+k]);
   const output={...manifest.stats,actual_loaded_bytes:grid.rows.byteLength+grid.runs.byteLength,load_and_decompression_ms:Math.round(loaded-started),gpu_upload_ms:Math.round(uploaded-loaded),max_texture_size:gl.getParameter(gl.MAX_TEXTURE_SIZE),sample_queries:manifest.samples.length,sample_mismatch:sampleMismatch,framebuffer_matches:framebufferMatches,webgl_error:gl.getError(),navigation_ownership_uploads:gpu.uploads-before,navigation,js_heap_bytes:performance.memory?.usedJSHeapSize??null};gpu.destroy();return output;
  },{zoom,transport});if(result.sample_mismatch||!result.framebuffer_matches||result.webgl_error||result.navigation_ownership_uploads)throw Error(JSON.stringify(result));results.push(result);console.log(JSON.stringify(result));await page.close();}
  fs.writeFileSync(path.join(directory,transport?transport+'-results.json':'results.json'),JSON.stringify({method:'Full-world source polygons compiled sequentially; real gzip loading, CPU checks and WebGL uploads/drawing on Chromium SwiftShader. Mobile viewport emulation is not physical mobile hardware validation.',results},null,2));
 }finally{await browser.close();await server.close();}
}
