// Real-browser startup/list integration using local, preverified inputs.
// Only the final assignment-grid load and map rendering are short-circuited.
const fs=require('fs'),http=require('http'),path=require('path'),crypto=require('crypto');
const {pathToFileURL}=require('url'),{chromium}=require('playwright');
const [root,ui,inputs,manifestPath,snapshotPath,manifestSha,snapshotSha,releaseId]=process.argv.slice(2);
if(!releaseId||process.env.V7_PREVERIFIED_HANDOFF!=='1')throw Error('a separately authenticated private handoff is required');
const read=p=>fs.readFileSync(p),hash=b=>crypto.createHash('sha256').update(b).digest('hex');
if(hash(read(manifestPath))!==manifestSha||hash(read(snapshotPath))!==snapshotSha)throw Error('handoff mismatch');
const manifest=JSON.parse(read(manifestPath)),snapshot=JSON.parse(read(snapshotPath));
for(const [k,n] of [['proposal','proposal.json'],['water_presentation','water-presentation.json'],['references','review-references.json'],['records','presentation-records-local.json'],['original_module','original-review.mjs'],['candidate_module','data-driven-review.mjs'],['parity_checker','verify_presentation_parity.mjs']])if(hash(read(path.join(inputs,n)))!==manifest.assets[k])throw Error('asset mismatch: '+k);
const source=process.env.V7_SOURCE_ROOT||path.join(root,'source-custody-cleanup-20261105');
const prototype=process.env.V7_PROTO_ROOT||path.join(root,'v7-neon-ui-prototype-20261105');
const local=path.join(source,'r2-read'),deps=path.join(prototype,'dependency-readbacks');
const ending="resize();mode='';const requested=new URLSearchParams(location.search).get('version');await switchMode(requested===candidateVersionKey?candidateVersionKey:'v2');fitWorld();";
function instrument(code){if(code.split(ending).length!==2)throw Error('unexpected startup anchor');return code.replace(ending,'resize();window.__listStartupReady=true;')}
const oldApp=instrument(read(path.join(local,'app.js')).toString()),newApp=instrument(read(path.join(ui,'app-neon.js')).toString());
const oldHtml=read(path.join(local,'index.html')).toString(),newHtml=read(path.join(ui,'index.html')).toString();
let mode='good',createHandler,createLookup,seenTamperedProposal=false;
const server=http.createServer((req,res)=>{
 const u=new URL(req.url,'http://localhost'),name=path.basename(u.pathname);
 if(u.pathname==='/api/presentation'){
  let row=structuredClone(snapshot.release);if(mode==='tamper')row.records.groups[0].display.title+=' changed';
  const lookup=createLookup(async(sql,args)=>({rows:[row]}));const handler=createHandler({fetchRelease:lookup,expectedManifestSha256:manifestSha,expectedReleaseId:releaseId});
  return handler(new Request('http://localhost/api/presentation')).then(async r=>{res.statusCode=r.status;for(const [k,v] of r.headers)res.setHeader(k,v);res.end(await r.text())}).catch(()=>{res.statusCode=500;res.end()});
 }
 if(u.pathname==='/old/'||u.pathname==='/old/index.html'){res.setHeader('content-type','text/html');return res.end(oldHtml)}
 if(u.pathname==='/new/'||u.pathname==='/new/index.html'){res.setHeader('content-type','text/html');return res.end(newHtml)}
 if(u.pathname==='/old/app.js'||u.pathname==='/new/app-neon.js'){res.setHeader('content-type','application/javascript');return res.end(u.pathname.startsWith('/old/')?oldApp:newApp)}
 if(name==='review-references.js'){res.setHeader('content-type','application/javascript');return res.end(read(path.join(inputs,'original-review.mjs')))}
 if(name==='data-driven-review.mjs'||name==='presentation-client.mjs'){res.setHeader('content-type','application/javascript');return res.end(read(path.join(ui,name)))}
 if(['proposal.json','water-presentation.json','review-references.json'].includes(name)){
  const tamper=mode==='bad-source'&&u.pathname==='/new/proposal.json';if(tamper)seenTamperedProposal=true;
  res.setHeader('content-type','application/json');return res.end(tamper?'{}':read(path.join(inputs,name)));
 }
 if(name==='accounting.json'||name==='legend-counts.json'){res.setHeader('content-type','application/json');return res.end(read(path.join(deps,name)))}
 if(['local-grid.js','review-model.js','legend-model.js'].includes(name)){res.setHeader('content-type','application/javascript');return res.end(read(path.join(deps,name)))}
 res.statusCode=404;res.end();
});
(async()=>{
 createHandler=(await import(pathToFileURL(path.join(prototype,'presentation-service.mjs')))).createPresentationHandler;
 createLookup=(await import(pathToFileURL(path.join(prototype,'neon-release-lookup.mjs')))).createNeonReleaseLookup;
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const options={headless:true,args:['--no-sandbox','--disable-dev-shm-usage']};if(process.env.CHROMIUM_PATH)options.executablePath=process.env.CHROMIUM_PATH;
 const browser=await chromium.launch(options);
 try{
  for(const width of [1280,390]){
   const snapshots=[];
   for(const which of ['old','new']){
    mode='good';const pg=await browser.newPage({viewport:{width,height:800}});await pg.goto(`http://127.0.0.1:${server.address().port}/${which}/index.html`);
    await pg.waitForFunction(()=>window.__listStartupReady||document.querySelector('#status')?.classList.contains('error'),null,{timeout:60000});
    const result=await pg.evaluate(()=>({ready:window.__listStartupReady===true,status:document.querySelector('#status').textContent,islands:document.querySelector('#islands').innerHTML,water:document.querySelector('#water').innerHTML,count:document.querySelectorAll('#islands .member').length}));
    if(!result.ready||result.count!==108)throw Error(which+' startup failed '+JSON.stringify({status:result.status,count:result.count}));
    if(width<500)await pg.locator('#sidebar').click();await pg.locator('#islands details > summary').first().click();
    if(!(await pg.locator('#islands details').first().evaluate(e=>e.open)))throw Error('details interaction failed');
    snapshots.push(result);await pg.close();
   }
   if(snapshots[0].islands!==snapshots[1].islands||snapshots[0].water!==snapshots[1].water)throw Error('startup DOM differs');
   for(const bad of ['tamper','bad-source']){
    mode=bad;seenTamperedProposal=false;const pg=await browser.newPage({viewport:{width,height:800}});await pg.goto(`http://127.0.0.1:${server.address().port}/new/index.html`);
    await pg.waitForFunction(()=>window.__listStartupReady||document.querySelector('#status')?.classList.contains('error'),null,{timeout:60000});
    const rejection=await pg.evaluate(()=>({failed:!window.__listStartupReady&&document.querySelector('#status').classList.contains('error')&&document.querySelectorAll('#islands .member').length===0,message:document.querySelector('#status').textContent}));
    if(!rejection.failed||(bad==='bad-source'&&(!seenTamperedProposal||!rejection.message.includes('Presentation source mismatch: proposal'))))throw Error('negative startup did not fail for expected reason: '+bad+' '+JSON.stringify(rejection));await pg.close();
   }
   console.log(JSON.stringify({width,status:'actual-list-startup-parity',members:108,dom_equal:true,negative_cases:2,map_grid_load:'short-circuited'}));
  }
 }finally{await browser.close();server.close()}
})().catch(e=>{console.error(e);server.close();process.exitCode=1});
