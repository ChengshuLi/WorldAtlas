// Isolated browser/DOM integration. Inputs are supplied at runtime and never committed.
const fs=require('fs');
const http=require('http');
const path=require('path');
const crypto=require('crypto');
const {execFileSync}=require('child_process');
const {pathToFileURL}=require('url');
const {chromium}=require('playwright');

const [root,ui,manifestPath,snapshotPath,inputs,manifestSha,snapshotSha,releaseId,codeRevision]=process.argv.slice(2);
if (!codeRevision) throw Error('missing test arguments');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const canon=x=>x===null||typeof x!=='object'?JSON.stringify(x):Array.isArray(x)?'['+x.map(canon).join(',')+']':'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canon(x[k])).join(',')+'}';
const read=p=>fs.readFileSync(p);
const source=process.env.V7_SOURCE_ROOT||path.join(root,'source-custody-cleanup-20261105');
const prototype=process.env.V7_PROTO_ROOT||path.join(root,'v7-neon-ui-prototype-20261105');
const verifier=path.join(source,'neon-only-prototype','verify_neon_presentation_export.py');
// Authenticate the supplied connector export and original readbacks outside this
// script. On Linux, run the sealed full-index verifier before serving. For a
// separately verified handoff on non-Linux, check exact bytes and say explicitly
// that this local browser run did not repeat the Linux sealed verifier.
if(process.env.V7_PREVERIFIED_HANDOFF==='1') {
 if(hash(read(snapshotPath))!==snapshotSha||hash(read(manifestPath))!==manifestSha)throw Error('handoff snapshot/manifest mismatch');
 const m=JSON.parse(read(manifestPath));for(const [k,n] of [['proposal','proposal.json'],['water_presentation','water-presentation.json'],['references','review-references.json'],['records','presentation-records-local.json'],['original_module','original-review.mjs'],['candidate_module','data-driven-review.mjs'],['parity_checker','verify_presentation_parity.mjs']])if(hash(read(path.join(inputs,n)))!==m.assets[k])throw Error('handoff asset mismatch: '+k);
 console.error('Preverified handoff: Linux sealed verifier was not rerun here; connector and pin authentication remain external.');
} else {
 const {V7_PROJECT_ID:project,V7_BRANCH_ID:branch,V7_DATABASE:database}=process.env;
 if(!project||!branch||!database)throw Error('missing authenticated Neon origin assertions');
 execFileSync('python3',[verifier,'--snapshot',snapshotPath,'--snapshot-sha256',snapshotSha,'--manifest',manifestPath,'--manifest-sha256',manifestSha,'--input-dir',inputs,'--project',project,'--branch',branch,'--database',database,'--code-revision',codeRevision],{stdio:'pipe'});
}
const snapshot=JSON.parse(read(snapshotPath)), manifest=JSON.parse(read(manifestPath));
if(hash(Buffer.from(canon(manifest)+'\n'))!==manifestSha)throw Error('manifest canonicalization mismatch');
const app=read(path.join(ui,'app-neon.js')).toString();
const start=app.indexOf('function esc(s)'), end=app.indexOf('async function switchMode(next)');
if(start<0||end<start)throw Error('historical DOM functions missing');
const exactFunctions=app.slice(start,end);
const originalApp=read(path.join(source,'r2-read','app.js')).toString();
if(exactFunctions!==originalApp.slice(originalApp.indexOf('function esc(s)'),originalApp.indexOf('async function switchMode(next)')))throw Error('DOM functions changed');
let page=read(path.join(ui,'index.html')).toString().replace('<script type="module" src="./app-neon.js"></script>','<script type="module" src="./harness.mjs"></script>');
const harness=`import * as old from './original-review.mjs';\nimport * as next from './data-driven-review.mjs';\nimport {loadPresentationEnvelope,readPinnedJSON} from './presentation-client.mjs';\nconst $=s=>document.querySelector(s);let meta,candidateVersionLabel='V7',hoverSeq=0,hoverController=null,hot=null;let actions=[];const interaction={hover:()=>{}};function requestDraw(){}function hoverMember(g,m){actions.push(['hover',m.id])}function pinMember(g,m){actions.push(['click',m.id])}\n${exactFunctions}\nwindow.runReview=async function(mode){\n const get=async n=>(await fetch('/source/'+n)).arrayBuffer(); const [pb,wb,rb]=await Promise.all(['proposal.json','water-presentation.json','review-references.json'].map(get));\n meta=JSON.parse(new TextDecoder().decode(pb));const water=JSON.parse(new TextDecoder().decode(wb)),refs=JSON.parse(new TextDecoder().decode(rb));\n const original=old.buildReferenceIndex(meta,water,water.source);renderIslandPresentation(original);renderWaterPresentation(water,original);const before=[$('#islands').innerHTML,$('#water').innerHTML,$('#island-count').textContent,$('#water-count').textContent];\n const config={endpoint:'/api/presentation?case='+mode,expectedManifestSha256:${JSON.stringify(manifestSha)},expectedReleaseId:${JSON.stringify(releaseId)}};if(mode==='no-pin')config.expectedManifestSha256='';if(mode==='cross-origin')config.endpoint='https://example.com/';\n const e=await loadPresentationEnvelope(config);meta=await readPinnedJSON(e,'proposal',new Response(mode==='bad-source'?'changed':pb));await readPinnedJSON(e,'water_presentation',new Response(wb));await readPinnedJSON(e,'references',new Response(rb));const migrated=next.buildReferenceIndex(meta,water,water.source,e.records);if(!next.validateReferenceIndex(refs,migrated))throw Error('reference mismatch');renderIslandPresentation(migrated);renderWaterPresentation(water,migrated);const after=[$('#islands').innerHTML,$('#water').innerHTML,$('#island-count').textContent,$('#water-count').textContent];\n const button=$('#islands .member');button.dispatchEvent(new PointerEvent('pointerenter'));button.click();return {equal:JSON.stringify(before)===JSON.stringify(after),actions,land:$('#island-count').textContent,water:$('#water-count').textContent,memberCount:document.querySelectorAll('#islands .member').length,viewport:innerWidth};};\n`;
const map={'/':'index.html','/presentation-client.mjs':'presentation-client.mjs','/data-driven-review.mjs':'data-driven-review.mjs'};
let createHandler,createLookup;
const server=http.createServer((req,res)=>{
 const u=new URL(req.url,'http://localhost');
 if(u.pathname==='/harness.mjs'){res.setHeader('content-type','application/javascript');return res.end(harness)}
 if(u.pathname==='/original-review.mjs'){res.setHeader('content-type','application/javascript');return res.end(read(path.join(inputs,'original-review.mjs')))}
 if(u.pathname.startsWith('/source/')){const name=u.pathname.slice(8);if(!['proposal.json','water-presentation.json','review-references.json'].includes(name)){res.statusCode=404;return res.end()}res.setHeader('content-type','application/json');return res.end(read(path.join(inputs,name)))}
 if(u.pathname==='/api/presentation'){
  const mode=u.searchParams.get('case');if(mode==='offline'){res.statusCode=503;return res.end()}
  let row=structuredClone(snapshot.release);
  if(mode==='tamper')row.records.groups[0].display.title+=' changed';
  if(mode==='stale')row.manifest.release_id+='-stale';
  if(mode==='duplicate')return res.end('{"schema":"x","schema":"y"}\n');
  if(mode==='oversized')return res.end('x'.repeat(2*1024*1024+1));
  const lookup=createLookup(async(sql,args)=>{if(!sql.includes('release_id=$1')||args.length!==1||args[0]!==releaseId)throw Error('bad query');return {rows:[row]}});
  const handle=createHandler({fetchRelease:lookup,expectedManifestSha256:manifestSha,expectedReleaseId:releaseId});
  return handle(new Request('http://localhost/api/presentation')).then(async response=>{res.statusCode=response.status;for(const [key,value] of response.headers)res.setHeader(key,value);res.end(await response.text())}).catch(()=>{res.statusCode=500;res.end()});
 }
 if(!map[u.pathname]){res.statusCode=404;return res.end()}const file=map[u.pathname];res.setHeader('content-type',file.endsWith('.html')?'text/html':'application/javascript');return res.end(file==='index.html'?page:read(path.join(ui,file)));
});
(async()=>{createHandler=(await import(pathToFileURL(path.join(prototype,'presentation-service.mjs')))).createPresentationHandler;createLookup=(await import(pathToFileURL(path.join(prototype,'neon-release-lookup.mjs')))).createNeonReleaseLookup;await new Promise(r=>server.listen(0,'127.0.0.1',r));const options={headless:true,args:['--no-sandbox','--disable-dev-shm-usage']};if(process.env.CHROMIUM_PATH)options.executablePath=process.env.CHROMIUM_PATH;const browser=await chromium.launch(options);try{
 for(const width of [1280,390]){const pg=await browser.newPage({viewport:{width,height:800}});await pg.goto(`http://127.0.0.1:${server.address().port}/`);await pg.waitForFunction(()=>typeof window.runReview==='function');let result=await pg.evaluate(()=>window.runReview('good'));if(!result.equal||result.memberCount!==108||!result.actions.some(x=>x[0]==='hover')||!result.actions.some(x=>x[0]==='click'))throw Error('DOM parity or interactions failed: '+JSON.stringify(result));
  for(const mode of ['tamper','stale','duplicate','oversized','offline','bad-source','no-pin','cross-origin']){const err=await pg.evaluate(async m=>{try{await window.runReview(m);return null}catch(e){return e.message}},mode);if(!err)throw Error('case accepted: '+mode)}await pg.close();console.log(JSON.stringify({width,...result,negative_cases:8}));}
 }finally{await browser.close();server.close()}})().catch(e=>{console.error(e);server.close();process.exitCode=1});
