// Local headless browser evidence; no physical-device or live publication claim.
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {chromium} from '@playwright/test';
const root=process.cwd(),dist=path.join(root,'dist'),output=path.dirname(new URL(import.meta.url).pathname);
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const atlas=JSON.parse(fs.readFileSync(path.join(dist,'atlas-geography.json')));
const read=name=>JSON.parse(gunzipSync(fs.readFileSync(path.join(dist,name))));
const features=atlas.parts.flatMap(read),byId=new Map(features.map(row=>[row.id,row])),units=new Map(atlas.units.map(row=>[row.id,row]));
const ids={monaco:'gb:MCO:ADM1:64170238B96397749018979',luxembourg:'atlas:territory:LUX',hancock:'gb:USA:ADM2:52423323B20661288428578',retained:'framework:province:west-virginia:4c9dc6438fb1',retired:'framework:province:west-virginia:8d71dccb3165',monacoArea:'framework:area:france:a85924a668ef',luxembourgArea:'framework:area:belgium:3a14f80912de'};
assert.equal(atlas.reference_release.version,6);assert.equal(features.length,49625);assert.equal(units.get(ids.monacoArea).name,'Monaco');assert.equal(units.get(ids.luxembourgArea).name,'Luxembourg');assert.equal(byId.get(ids.hancock).properties.parent_id,ids.retained);assert.equal(units.has(ids.retired),false);assert.equal(features.filter(row=>row.properties.parent_id===ids.retained).length,55);
assert.equal(atlas.preparedEvidence.hierarchy_sha256,atlas.reference_release.hierarchy_sha256);
const manifest=JSON.parse(fs.readFileSync('data/canonical-grid/manifest.json'));
assert.equal(manifest.hierarchy_sha256,atlas.reference_release.hierarchy_sha256);assert.equal(manifest.footprints_sha256,atlas.reference_release.footprints_sha256);
const server=http.createServer((req,res)=>{
 const name=decodeURIComponent(new URL(req.url,'http://localhost').pathname),file=path.resolve(dist,'.'+(name==='/'?'/index.html':name));
 if(!file.startsWith(dist+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);res.end('Missing local asset');return;}
 res.setHeader('Content-Type',({'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.gz':'application/gzip'})[path.extname(file)]??'application/octet-stream');fs.createReadStream(file).pipe(res);
});
await new Promise(resolve=>server.listen(32106,'127.0.0.1',resolve));let browser;
try{
 browser=await chromium.launch({args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1440,height:1080}}),errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('http://127.0.0.1:32106');await page.locator('#loading').waitFor({state:'hidden',timeout:120000});
 await page.waitForFunction(()=>document.querySelector('.atlas-pixel-canvas')?.dataset.rendered==='true',null,{timeout:120000});
 const checks=[];
 for(const [key,search,expected] of [['monaco','Monaco','Monaco'],['luxembourg','Luxembourg','Luxembourg'],['hancock','Hancock','West Virginia']]){
  await page.locator('#search').fill(search);await page.locator(`[data-result="${ids[key]}"]`).click();
  assert.equal(await page.locator('.breadcrumbs [data-unit]').count(),6);const chain=await page.locator('.breadcrumbs').textContent();assert.ok(chain.includes(expected));
  if(key==='hancock')assert.equal(await page.locator(`.breadcrumbs [data-unit="${ids.retained}"]`).count(),1);
  const name=await page.locator('#details h3').textContent();
  for(const mode of ['province','area','region','subcontinent','continent']){
   await page.locator(`[data-mode="${mode}"]`).click();assert.equal(await page.locator(`[data-mode="${mode}"]`).getAttribute('aria-pressed'),'true');assert.equal(await page.locator('#legend-items .unknown').count(),0);
  }
  checks.push({id:ids[key],name,chain,complete_tiers:6,modes_checked:5});
 }
 await page.screenshot({path:path.join(output,'hancock-local-static.png')});assert.deepEqual(errors,[]);
 const result={version:1,verified:true,headless_local_browser:true,physical_device_verified:false,live_publication:false,release_id:atlas.reference_release.id,release_version:6,hierarchy_sha256:atlas.reference_release.hierarchy_sha256,footprints_sha256:atlas.reference_release.footprints_sha256,locations:features.length,provinces:atlas.units.filter(row=>row.level==='province').length,west_virginia_locations:55,retired_parent_active:false,inspector_checks:checks,console_errors:errors,browser_version:browser.version(),static_atlas_sha256:sha(fs.readFileSync(path.join(dist,'atlas-geography.json')))};
 fs.writeFileSync(path.join(output,'browser-check.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result));
}finally{await browser?.close();await new Promise(resolve=>server.close(resolve));}
