// Authenticated snapshot + exact historical source bytes, with a DOM-shaped
// in-process harness. This does not claim real-browser or map-rendering parity.
const fs=require('fs'), crypto=require('crypto'), path=require('path'), vm=require('vm');
const {pathToFileURL}=require('url');
const {execFileSync}=require('child_process');
const [root,ui,manifestPath,snapshotPath,inputs,manifestSha,snapshotSha,releaseId,codeRevision]=process.argv.slice(2);
if(!codeRevision)throw Error('missing integration arguments');
const {V7_PROJECT_ID:project,V7_BRANCH_ID:branch,V7_DATABASE:database}=process.env;
if(!project||!branch||!database)throw Error('missing authenticated Neon origin assertions');
const source=process.env.V7_SOURCE_ROOT||path.join(root,'source-custody-cleanup-20261105');
const prototype=process.env.V7_PROTO_ROOT||path.join(root,'v7-neon-ui-prototype-20261105');
const verifier=path.join(source,'neon-only-prototype','verify_neon_presentation_export.py');
execFileSync('python3',[verifier,'--snapshot',snapshotPath,'--snapshot-sha256',snapshotSha,'--manifest',manifestPath,'--manifest-sha256',manifestSha,'--input-dir',inputs,'--project',project,'--branch',branch,'--database',database,'--code-revision',codeRevision],{stdio:'pipe'});
console.error('Pinned snapshot verified; starting in-process UI integration.');
const read=p=>fs.readFileSync(p), parse=p=>JSON.parse(read(p));
const canon=x=>x===null||typeof x!=='object'?JSON.stringify(x):Array.isArray(x)?'['+x.map(canon).join(',')+']':'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canon(x[k])).join(',')+'}';
const snapshot=parse(snapshotPath),manifest=parse(manifestPath),sourceBytes=['proposal.json','water-presentation.json','review-references.json'].map(n=>read(path.join(inputs,n)));
const exactBuffer=b=>b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength);
const originals=sourceBytes.map(b=>exactBuffer(b));
global.crypto=crypto.webcrypto;global.location={href:'http://localhost/ui/',origin:'http://localhost'};
let mode='good',createHandler,createLookup;
global.fetch=async()=>{
 if(mode==='offline')return new Response('',{status:503});
 if(mode==='oversized')return new Response('x'.repeat(2*1024*1024+1));
 if(mode==='duplicate')return new Response('{"schema":"a","schema":"b"}\n');
 let row=structuredClone(snapshot.release);
 if(mode==='tamper')row.records.groups[0].display.title+=' changed';
 if(mode==='stale')row.manifest.release_id+='-stale';
 const fetchRelease=createLookup(async(sql,args)=>{
  if(!sql.includes('release_id=$1')||args.length!==1||args[0]!==releaseId)throw Error('invalid query');
  return {rows:[row]};
 });
 return createHandler({fetchRelease,expectedManifestSha256:manifestSha,expectedReleaseId:releaseId})(new Request('http://localhost/api/presentation'));
};
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.attrs={};this._html='';this._text='';this.className='';this.dataset={};}
 set innerHTML(v){this._html=String(v);this.children=[]}
 get innerHTML(){return this._html+this.children.map(x=>x.serial()).join('')}
 set textContent(v){this._text=String(v);this.children=[]}
 get textContent(){return this._text}
 append(...xs){this.children.push(...xs)} replaceChildren(...xs){this.children=[...xs];this._html='';this._text=''}
 querySelector(sel){if(sel!=='.member-list')throw Error('unexpected selector '+sel);if(!this.list){this.list=new Element('div');this.list.className='member-list';this.children.push(this.list)}return this.list}
 serial(){return {tag:this.tag,className:this.className,html:this._html,text:this._text,title:this.title||'',children:this.children.map(x=>x.serial())}}
}
const elements={};for(const id of ['islands','water','island-count','water-count'])elements['#'+id]=new Element('root');
const ctx={document:{createElement:t=>new Element(t),createTextNode:t=>{const e=new Element('#text');e.textContent=t;return e},querySelector:s=>elements[s]},meta:parse(path.join(inputs,'proposal.json')),candidateVersionLabel:'V7',hoverSeq:0,hoverController:null,hot:null,interaction:{hover(){}},requestDraw(){},actions:[],hoverMember(g,m){ctx.actions.push(['hover',m.id])},pinMember(g,m){ctx.actions.push(['click',m.id])},console};
const app=read(path.join(ui,'app-neon.js')).toString(), original=read(path.join(source,'r2-read','app.js')).toString();
const startup=app.indexOf('const envelope=await loadPresentationEnvelope'), proposal=app.indexOf("meta=await readPinnedJSON(envelope,'proposal',r)"), waterRead=app.indexOf("readPinnedJSON(envelope,'water_presentation'"), refsRead=app.indexOf("readPinnedJSON(envelope,'references'"), build=app.indexOf('const expectedReferences=buildReferenceIndex'), render=app.indexOf('renderIslandPresentation(references)');
if(!(startup>=0&&startup<proposal&&proposal<waterRead&&waterRead<refsRead&&refsRead<build&&build<render))throw Error('fail-closed startup order changed');
const snippet=s=>s.slice(s.indexOf('function esc(s)'),s.indexOf('async function switchMode(next)'));
if(snippet(app)!==snippet(original)||!snippet(app).startsWith('function esc'))throw Error('historical render functions changed');
vm.createContext(ctx);vm.runInContext('const $=s=>document.querySelector(s);'+snippet(app),ctx);
(async()=>{
 const old=await import(pathToFileURL(path.join(inputs,'original-review.mjs'))), next=await import(pathToFileURL(path.join(ui,'data-driven-review.mjs'))),client=await import(pathToFileURL(path.join(ui,'presentation-client.mjs')));createHandler=(await import(pathToFileURL(path.join(prototype,'presentation-service.mjs')))).createPresentationHandler;createLookup=(await import(pathToFileURL(path.join(prototype,'neon-release-lookup.mjs')))).createNeonReleaseLookup;
 const water=parse(path.join(inputs,'water-presentation.json')),refs=parse(path.join(inputs,'review-references.json'));
 const oldIndex=old.buildReferenceIndex(ctx.meta,water,water.source);ctx.renderIslandPresentation(oldIndex);ctx.renderWaterPresentation(water,oldIndex);
 console.error('Historical index rendered.');
 const oldDom=JSON.stringify(Object.values(elements).map(e=>e.serial()));
 const config={endpoint:'/api/presentation',expectedManifestSha256:manifestSha,expectedReleaseId:releaseId};
 const load=()=>client.loadPresentationEnvelope(config);
 const envelope=await load();for(const [i,n] of ['proposal','water_presentation','references'].entries()){
   await client.verifyPresentationSource(envelope,n,originals[i]);
   const parsed=await client.readPinnedJSON(envelope,n,new Response(sourceBytes[i]));
   if(JSON.stringify(parsed)!==JSON.stringify(JSON.parse(sourceBytes[i])))throw Error('pinned source parsing mismatch');
 }
 console.error('Presentation transport and source bytes verified.');
 const index=next.buildReferenceIndex(ctx.meta,water,water.source,envelope.records);
 if(JSON.stringify(index)!==JSON.stringify(oldIndex)||!next.validateReferenceIndex(refs,index))throw Error('full index mismatch');
 ctx.renderIslandPresentation(index);ctx.renderWaterPresentation(water,index);
 if(JSON.stringify(Object.values(elements).map(e=>e.serial()))!==oldDom)throw Error('rendered DOM model differs');
 const find=(n,p)=>p(n)?n:n.children.map(c=>find(c,p)).find(Boolean);const button=find(elements['#islands'],e=>e.className==='member');
 if(!button||!button.onpointerenter||!button.onclick)throw Error('missing interactions');button.onpointerenter();button.onclick();if(ctx.actions.length!==2)throw Error('interactions did not fire');
 let checked=0;for(mode of ['offline','oversized','duplicate','tamper','stale']){let rejected=false;try{await load()}catch{rejected=true}if(!rejected)throw Error('accepted '+mode);checked++}
 for(const cfg of [{...config,expectedManifestSha256:''},{...config,endpoint:'https://example.com/'}]){let rejected=false;try{await client.loadPresentationEnvelope(cfg)}catch{rejected=true}if(!rejected)throw Error('accepted invalid config');checked++}
 let bad=false;try{await client.verifyPresentationSource(envelope,'proposal',new TextEncoder().encode('changed').buffer)}catch{bad=true}if(!bad)throw Error('accepted changed source');checked++;
 bad=false;try{await client.readPinnedJSON(envelope,'proposal',new Response('x'.repeat(8*1024*1024+1)))}catch{bad=true}if(!bad)throw Error('accepted oversized source');checked++;
 console.log(JSON.stringify({status:'node-dom-model-integration-passed',full_index_equal:true,dom_model_equal:true,land_leaves:index.lists.find(x=>x.number===1).continents.reduce((a,c)=>a+c.reasons.reduce((b,r)=>b+r.items.length,0),0),interaction_callbacks:ctx.actions.length,negative_cases:checked,limitations:['not a real browser','map and full UI startup not exercised']}));
})().catch(e=>{console.error(e);process.exitCode=1});
