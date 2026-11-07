import { cellValue, createRenderer, wrapColumn } from '/review/osm-v6-ui-satellite-fixes-20261102/local-grid.js';
import { canonicalStringify, createReviewInteraction, createSingleGridSlot, normalizeExtent, validateRows, verifyBufferChecksum } from '/review/osm-v6-ui-satellite-fixes-20261102/review-model.js';
import { buildReferenceIndex, validateReferenceIndex, waterReviewReason } from './review-references.js';
import { activeCategoryMask, clearLegendSelection, collapseLegendHover, makeLegendItems, matchingLegendItems, toggleSelection } from '/review/osm-v6-ui-satellite-fixes-20261102/legend-model.js';

const $=s=>document.querySelector(s), canvas=$('#canvas'), map=$('#map'), aside=$('#aside');
let meta, paintMeta, renderer, legendItems=[], legendCounts, selectedContinents=new Set(), hoveredContinent=null, mode='v2', candidateVersionKey='v3', candidateVersionLabel='V3', scale=1, ox=0, oy=0, dpr=1, drag=null, hot=null, loadSeq=0, hoverSeq=0, hoverController=null, pinSeq=0, categoryIds=new Set();
const interaction=createReviewInteraction();
const gridSlot=createSingleGridSlot();
const overlay=document.createElement('canvas'); overlay.style.cssText='position:absolute;inset:0;width:100%;height:100%;pointer-events:none'; map.append(overlay);
const dataBase=new URL(document.documentElement.dataset.dataBase||'./',document.baseURI), metaBase=new URL('./',document.baseURI), UI_CACHE_REV='reviewed-v7-ocean-boundaries'; let drawing=false;
const versionedAsset=name=>new URL(`${name}?rev=${UI_CACHE_REV}`,metaBase);
function status(s,error=false){$('#status').textContent=s;$('#status').classList.toggle('error',error)}
function updateLegendFilter(){
 const mask=activeCategoryMask(legendItems,selectedContinents,hoveredContinent);
 $('#legend-clear').hidden=selectedContinents.size===0;
 for(const button of $('#legend-list').querySelectorAll('.legend-item'))button.setAttribute('aria-pressed',String(selectedContinents.has(button.dataset.id)));
 requestDraw();return mask;
}
function renderLegend(){
 const list=$('#legend-list'),query=$('#legend-search').value;list.replaceChildren();
 const visible=matchingLegendItems(legendItems,query);
 if(!visible.length){const empty=document.createElement('div');empty.className='legend-empty';empty.textContent='No matching continents.';list.append(empty);return;}
 for(const item of visible){
  const button=document.createElement('button');button.type='button';button.className='legend-item';button.dataset.id=item.id;button.setAttribute('aria-pressed',String(selectedContinents.has(item.id)));
  const swatch=document.createElement('i');swatch.className='swatch';swatch.style.backgroundColor=`rgb(${item.color.join(',')})`;swatch.setAttribute('aria-hidden','true');
  const name=document.createElement('span');name.className='legend-name';name.textContent=item.name;
  const count=document.createElement('span');count.className='legend-count';count.textContent=Number(item.count).toLocaleString()+' cells';
  button.append(swatch,name,count);
  button.addEventListener('pointerenter',()=>{hoveredContinent=item.id;updateLegendFilter()});
  button.addEventListener('pointerleave',()=>{if(hoveredContinent===item.id){hoveredContinent=null;updateLegendFilter()}});
  button.addEventListener('focus',()=>{hoveredContinent=item.id;updateLegendFilter()});
  button.addEventListener('blur',()=>{if(hoveredContinent===item.id){hoveredContinent=null;updateLegendFilter()}});
  button.addEventListener('click',()=>{selectedContinents=toggleSelection(selectedContinents,item.id);updateLegendFilter()});
  list.append(button);
 }
}
function clearLegendFilter(){selectedContinents=clearLegendSelection();hoveredContinent=collapseLegendHover();updateLegendFilter()}
function setLegendPanel(open){$('#legend-panel').hidden=!open;$('#legend-toggle').setAttribute('aria-expanded',String(open));if(!open&&hoveredContinent){hoveredContinent=collapseLegendHover();updateLegendFilter()}if(open)$('#legend-search').focus({preventScroll:true})}
function setLegendCounts(version){hoveredContinent=collapseLegendHover();const def=legendCounts?.versions?.[version];if(!def||def.rows_sha256!==meta.versions[version].local_grid.rows_sha256||def.runs_sha256!==meta.versions[version].local_grid.runs_sha256)throw Error(`Verified legend counts do not match ${version.toUpperCase()} assignment RLE`);legendItems=makeLegendItems(meta.categories,def.counts);$('#legend-version').textContent=version.toUpperCase();renderLegend();updateLegendFilter()}

async function readGrid(block,signal){
  async function read(name){
    const spec=block.local_grid, response=await fetch(new URL(spec[name],dataBase),{signal});
    if(!response.ok)throw Error(`Could not load ${spec[name]}`);
    const bytes=await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
    try{await verifyBufferChecksum(bytes,spec[name+'_sha256'])}catch{throw Error(`${name} checksum mismatch`)}
    if(bytes.byteLength%4)throw Error(`${name} is not a u32 stream`);
    return new Uint32Array(bytes);
  }
  const [rows,runs]=await Promise.all([read('rows'),read('runs')]);
  const out={rows,runs,width:block.width,height:block.height};
  validateRows(out,rows,runs,{strictSize:true}); return out;
}
function dimensions(){return {w:map.clientWidth,h:map.clientHeight}}
function minScale(){const {w,h}=dimensions();return Math.max(w/meta.width,h/meta.height)}
function constrain(){if(!meta)return;const {w,h}=dimensions(),min=minScale();if(scale<min){const cx=(w/2-ox)/scale,cy=(h/2-oy)/scale;scale=min;ox=w/2-cx*scale;oy=h/2-cy*scale}const period=meta.width*scale;ox%=period;if(ox>0)ox-=period;oy=Math.min(0,Math.max(h-meta.height*scale,oy))}
function fitWorld(){if(!meta)return;scale=minScale();const {w,h}=dimensions();ox=(w-meta.width*scale)/2;oy=(h-meta.height*scale)/2;constrain();requestDraw()}
function zoom(f,x=map.clientWidth/2,y=map.clientHeight/2){if(!meta)return;const n=Math.max(minScale(),Math.min(36,scale*f));ox=x-(x-ox)*n/scale;oy=y-(y-oy)*n/scale;scale=n;constrain();requestDraw()}
// Keep keyboard map controls scoped to the focused canvas. This leaves typing,
// list/button shortcuts, and modifier/browser commands untouched.
// BEGIN MAP KEY COMMAND MAPPER
function mapKeyboardCommand(event){
 if(!event||event.defaultPrevented||event.isComposing||event.ctrlKey||event.metaKey||event.altKey)return null;
 const target=event.target;
 if(!target||!['canvas','map'].includes(target.id)||target.isContentEditable)return null;
 if(['INPUT','TEXTAREA','SELECT','BUTTON','A','SUMMARY'].includes(String(target.tagName||'').toUpperCase())||target.closest?.('input,textarea,select,button,a,summary,[contenteditable="true"]'))return null;
 const key=String(event.key||'').toLowerCase();
 const pans={w:'pan-up',a:'pan-left',s:'pan-down',d:'pan-right'};
 if(pans[key])return pans[key];
 if(key==='+'||key==='=')return 'zoom-in';
 if(key==='-')return 'zoom-out';
 return null;
}
// Keyboard panning moves the geographic viewpoint in the named compass
// direction, so the displayed map image must move in the opposite direction.
function keyboardPanDelta(command,step=64){
 return {
  x:command==='pan-left'?step:command==='pan-right'?-step:0,
  y:command==='pan-up'?step:command==='pan-down'?-step:0,
 };
}
// END MAP KEY COMMAND MAPPER
function requestDraw(){if(drawing)return;drawing=true;requestAnimationFrame(()=>{drawing=false;draw()})}
function resize(){dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(map.clientWidth*dpr);canvas.height=Math.round(map.clientHeight*dpr);overlay.width=canvas.width;overlay.height=canvas.height;requestDraw()}
function draw(){if(!renderer||!gridSlot.current)return;constrain();renderer.draw({scale,ox,oy,dpr,selected:interaction.pinned?.cell||null,activeMask:activeCategoryMask(legendItems,selectedContinents,hoveredContinent)});drawHighlights()}
function cellAt(px,py){const x=wrapColumn(Math.floor((px-ox)/scale),meta.width),y=Math.floor((py-oy)/scale);return y>=0&&y<meta.height?{x,y}:null}
function highlightSpans(){return interaction.highlight()}
function drawHighlights(){const ctx=overlay.getContext('2d');ctx.clearRect(0,0,overlay.width,overlay.height);const spans=highlightSpans();if(!spans?.length&&!interaction.pinned?.cell)return;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.strokeStyle='#ffbf45';ctx.lineWidth=2;const period=meta.width*scale;
  for(const s of spans){const y=oy+s.row*scale;for(let cycle=Math.floor(-ox/period)-1;cycle<=Math.ceil((map.clientWidth-ox)/period)+1;cycle++){let x=ox+(s.start+cycle*meta.width)*scale,w=(s.end-s.start)*scale;if(x+w<0||x>map.clientWidth)continue;ctx.strokeRect(x+.5,y+.5,Math.max(1,w-1),Math.max(1,scale-1));}}
  if(interaction.pinned?.cell&&!spans?.length){const {x,y}=interaction.pinned.cell;const period=meta.width*scale;ctx.strokeStyle='#162f3d';ctx.lineWidth=2;for(let c=Math.floor(-ox/period)-1;c<=Math.ceil((map.clientWidth-ox)/period)+1;c++)ctx.strokeRect(ox+(x+c*meta.width)*scale,oy+y*scale,Math.max(scale,3),Math.max(scale,3));}
}
function centerCell(x,y,s){const {w,h}=dimensions();scale=Math.min(36,Math.max(minScale(),s));ox=w/2-(x+.5)*scale;oy=h/2-(y+.5)*scale;constrain();requestDraw()}
function fitSpans(spans){if(!spans?.length)return;const extent=normalizeExtent(spans,meta.width);if(!extent)return;let x0=extent.x[0][0],x1=extent.x[extent.x.length-1][1];if(extent.x.length===2&&extent.x[0][0]===0){x0=extent.x[1][0];x1=extent.x[0][1]+meta.width;}const cx=(x0+x1)/2,cy=(extent.y[0]+extent.y[1])/2,ww=Math.max(1,x1-x0),hh=Math.max(1,extent.y[1]-extent.y[0]);const {w,h}=dimensions();scale=Math.min(36,Math.max(minScale(),Math.min(w/ww,h/hh)*.78));ox=w/2-cx*scale;oy=h/2-cy*scale;constrain();requestDraw()}
function fitExtent(extent){if(!extent)return;const cx=(extent.x_start+extent.x_end)/2,cy=(extent.y_start+extent.y_end)/2,ww=Math.max(1,extent.x_end-extent.x_start),hh=Math.max(1,extent.y_end-extent.y_start),{w,h}=dimensions();scale=Math.min(36,Math.max(minScale(),Math.min(w/ww,h/hh)*.78));ox=w/2-cx*scale;oy=h/2-cy*scale;constrain();requestDraw()}
function describeCell(c){if(!c)return 'Outside review latitude band';const data=gridSlot.current,v=cellValue(data.rows,data.runs,c.x,c.y);const category=meta.categories.find(x=>x.id===v);return `Cell ${c.x}, ${c.y} · ${(-180+(c.x+.5)*meta.step).toFixed(5)}°, ${(90-(c.y+.5)*meta.step).toFixed(5)}° · ${category?.name||'Unknown'}`}
function setHover(c){hot=null;hoverSeq++;interaction.hover(null);$('#tip').style.display=c?'block':'none';if(c){$('#tip').textContent=describeCell(c);requestAnimationFrame(()=>{const t=$('#tip');t.style.left='12px';t.style.top='48px';});}requestDraw()}
async function readMemberSpans(member,signal){
 const response=await fetch(new URL(member.span_file.url,dataBase),{signal});if(!response.ok)throw Error(`Could not load spans for ${member.name}`);
 const bytes=await response.arrayBuffer();await verifyBufferChecksum(bytes,member.span_file.sha256);
 const payload=JSON.parse(new TextDecoder().decode(bytes));if((payload.member_id!==member.id&&payload.item_id!==member.id)||!Array.isArray(payload.spans))throw Error('Exception span file does not match its member');
 for(const s of payload.spans)if(!Number.isInteger(s.row)||s.row<0||s.row>=meta.height||!Number.isInteger(s.start)||!Number.isInteger(s.end)||s.start<0||s.end<=s.start||s.end>meta.width)throw Error('Invalid exception cell span');
 return payload.spans;
}
async function hoverMember(group,member){const seq=++hoverSeq;hoverController?.abort();hoverController=new AbortController();try{const spans=await readMemberSpans(member,hoverController.signal);if(seq!==hoverSeq||interaction.pinned)return;hot={spans,record:{group,member}};interaction.hover(hot);requestDraw()}catch(e){if(seq===hoverSeq&&e.name!=='AbortError')status(e.message,true)}}
async function pinMember(group,member){const seq=++pinSeq;const cached=hot?.record?.group?.id===group.id&&hot?.record?.member?.id===member.id?hot.spans:null;hoverSeq++;hoverController?.abort();try{const spans=cached||await readMemberSpans(member);if(seq!==pinSeq)return;interaction.click({spans,group,member});fitSpans(spans);$('#selection').textContent=`Pinned exact V2→${candidateVersionLabel} changed cells for ${member.name} · ${group.destination}`;requestDraw()}catch(e){if(seq===pinSeq)status(e.message,true)}}

async function verifyAccounting(){
 const ref=meta.accounting;if(!ref?.url||!/^([a-f0-9]{64})$/.test(ref.sha256||''))throw Error('Missing build-time accounting QA proof');
 const response=await fetch(versionedAsset(ref.url));if(!response.ok)throw Error('Build-time accounting proof is not available');
 const bytes=await response.arrayBuffer();await verifyBufferChecksum(bytes,ref.sha256);
 const proof=JSON.parse(new TextDecoder().decode(bytes));
 if(proof.schema_version!=='worldatlas-review-accounting-v1'||proof.status!=='passed'||proof.width!==meta.width||proof.height!==meta.height||proof.physical_mask_invariance!=='passed')throw Error('Build-time accounting QA proof is invalid');
 if(proof.physical_mask_sha256!==meta.physical_mask.mask_sha256)throw Error('QA proof references a different physical mask');
 for(const key of ['rows_sha256','runs_sha256']){
  if(proof.physical_mask?.[key]!==meta.physical_mask.local_grid[key])throw Error('QA proof physical-mask stream checksum mismatch');
  for(const name of ['v2',candidateVersionKey])if(proof.versions?.[name]?.[key]!==meta.versions[name].local_grid[key])throw Error(`QA proof ${name.toUpperCase()} stream checksum mismatch`);
 }
 const indexBytes=new TextEncoder().encode(canonicalStringify(meta.exceptions));
 await verifyBufferChecksum(indexBytes.buffer,proof.exception_index_sha256);
 const semanticBytes=new TextEncoder().encode(canonicalStringify({width:meta.width,height:meta.height,categories:meta.categories,rule_records:meta.rule_records,physical_mask:{id:meta.physical_mask.id,mask_sha256:meta.physical_mask.mask_sha256,land_values:meta.physical_mask.land_values,water_values:meta.physical_mask.water_values}}));
 await verifyBufferChecksum(semanticBytes.buffer,proof.semantics_sha256);
 if(proof.changed_cells!==proof.attributed_cells||proof.exception_groups!==meta.exceptions.length)throw Error('QA proof accounting totals do not match review index');
 return proof;
}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function memberCard(target,g,m,leaf){
 const card=document.createElement('div');card.className='member-card';
 const b=document.createElement('button');b.className='member';b.innerHTML=`Item ${esc(leaf.letter)} · ${esc(m.name)}<span class="count">${Number(m.changed_cells||0).toLocaleString()} changed cells</span>`;b.title=`${leaf.reference} · ${g.title} · exact V2→${candidateVersionLabel} changed-cell spans`;b.onpointerenter=()=>hoverMember(g,m);b.onpointerleave=()=>{hoverSeq++;hoverController?.abort();hot=null;interaction.hover(null);requestDraw()};b.onclick=()=>pinMember(g,m);
 const ref=document.createElement('small');ref.className='leaf-reference';ref.textContent=leaf.reference;card.append(b,ref);
 if(leaf.justification){const detail=document.createElement('details');detail.className='member-justification';const summary=document.createElement('summary');summary.textContent='Why this group?';const text=document.createElement('p');text.textContent=leaf.justification;detail.append(summary,text);card.append(detail);}
 if(leaf.source_reason&&leaf.source_reason!==leaf.justification){const detail=document.createElement('details');detail.className='member-justification';const summary=document.createElement('summary');summary.textContent='Source record note (provenance)';const text=document.createElement('p');text.textContent=leaf.source_reason;detail.append(summary,text);card.append(detail);}
 if(leaf.source_policy&&leaf.source_policy!==leaf.justification){const detail=document.createElement('details');detail.className='member-justification';const summary=document.createElement('summary');summary.textContent='Approved geographic policy note';const text=document.createElement('p');text.textContent=leaf.source_policy;detail.append(summary,text);card.append(detail);}
 if(leaf.boundary_method||leaf.source_coordinates){const detail=document.createElement('details');detail.className='member-justification';const summary=document.createElement('summary');summary.textContent='Boundary method and source endpoints';const text=document.createElement('p');text.textContent=`${leaf.boundary_method||''} · ${JSON.stringify(leaf.source_coordinates||{})}`;detail.append(summary,text);card.append(detail);}
 if(Array.isArray(leaf.source_evidence)&&leaf.source_evidence.length){const detail=document.createElement('details');detail.className='member-justification';const summary=document.createElement('summary');summary.textContent='Source evidence';const ul=document.createElement('ul');for(const e of leaf.source_evidence){const li=document.createElement('li');if(/^https?:\/\//.test(e.uri||'')){const a=document.createElement('a');a.href=e.uri;a.target='_blank';a.rel='noopener noreferrer';a.textContent=e.name||e.uri;li.append(a);}else li.textContent=e.name||e.uri||'Source';if(e.details){const d=typeof e.details==='string'?e.details:JSON.stringify(e.details);li.append(document.createTextNode(` — ${d}`));}ul.append(li);}detail.append(summary,ul);card.append(detail);}
 target.append(card);
}
function renderIslandPresentation(index){
 const target=$('#islands'),listDef=index.lists.find(x=>x.number===1);target.replaceChildren();$('#island-count').textContent=`(${listDef.continents.reduce((n,c)=>n+c.reasons.reduce((a,r)=>a+r.items.length,0),0)} items)`;
 for(const continentData of listDef.continents){
  const continent=document.createElement('details');continent.className='exception continent-section';continent.innerHTML=`<summary><h3>${esc(continentData.continent)} <span class="count">${continentData.reasons.reduce((n,r)=>n+r.items.length,0)} items</span></h3></summary><div class="member-list"></div>`;const list=continent.querySelector('.member-list');
  for(const reason of continentData.reasons){const rule=document.createElement('details');rule.className='exception rule-section';rule.innerHTML=`<summary><h3>Reason ${reason.number} · ${esc(reason.display_title||reason.title)} <span class="count">${reason.items.length} items</span></h3><p>${esc(reason.display_reason||reason.reason)}</p></summary><div class="member-list"></div>`;const ruleList=rule.querySelector('.member-list');
   for(const leaf of reason.items){const sourceGroup=meta.exceptions.find(g=>g.id===leaf.source_group_id),sourceMember=sourceGroup?.members.find(m=>m.id===leaf.source_member_id);if(!sourceGroup||!sourceMember)throw Error(`Unknown island leaf ${leaf.source_member_id}`);const g={...sourceGroup,title:reason.display_title||reason.title,destination:continentData.continent},displayMember={...sourceMember,name:leaf.name};memberCard(ruleList,g,displayMember,leaf);}
   list.append(rule);
  }
  target.append(continent);
 }
}
function renderWaterPresentation(view,index){
 const target=$('#water'),waterIndex=index.lists.find(x=>x.number===2),oceanCount=(view.ocean_items||[]).length;target.replaceChildren();$('#water-count').textContent=`(${view.totals.display_items} items · ${view.continents.length} continents${oceanCount?` · ${oceanCount} ocean boundaries`:''})`;
 const itemMap=new Map([...view.continents.flatMap(section=>section.items.map(item=>[item.id,{item,section}])),...(view.ocean_items||[]).map(item=>[item.id,{item,section:null}])]);
 for(const continentData of waterIndex.continents){const section=view.continents.find(c=>c.continent===continentData.continent);if(!section)throw Error(`Missing water continent ${continentData.continent}`);
  const box=document.createElement('details');box.className='exception continent-section';box.innerHTML=`<summary><h3>${esc(continentData.continent)} <span class="count">${continentData.reasons.reduce((n,r)=>n+r.items.length,0)} items</span></h3></summary><div class="member-list"></div>`;const list=box.querySelector('.member-list');
  for(const reason of continentData.reasons){const ruleBox=document.createElement('details');ruleBox.className='exception rule-section';ruleBox.innerHTML=`<summary><h3>Reason ${reason.number} · ${esc(reason.title)} <span class="count">${reason.items.length} items</span></h3></summary><div class="member-list"></div>`;const ruleList=ruleBox.querySelector('.member-list');
   for(const leaf of reason.items){const entry=itemMap.get(leaf.id);if(!entry||entry.item.reference!==leaf.reference||entry.item.reason_number!==reason.number||entry.item.item_letter!==leaf.letter)throw Error(`Reference mapping does not match water leaf ${leaf.id}`);const item=entry.item,sourceGroup=meta.exceptions.find(g=>g.id===item.source_group_id),sourceMember=sourceGroup?.members.find(m=>m.id===item.source_member_id);if(!sourceGroup||!sourceMember)throw Error(`Unknown water leaf ${item.source_member_id}`);const g={...sourceGroup,title:item.name,destination:continentData.continent},m={...sourceMember,id:item.id,name:item.name,changed_cells:item.changed_cells,span_file:item.span_file};memberCard(ruleList,g,m,leaf);itemMap.delete(leaf.id);}
   list.append(ruleBox);
  }
  target.append(box);
 }
 if(waterIndex.ocean_boundaries?.items?.length){
  const oceanBox=document.createElement('details');oceanBox.className='exception continent-section';oceanBox.innerHTML=`<summary><h3>Ocean boundaries <span class="count">${waterIndex.ocean_boundaries.items.length} items</span></h3></summary><div class="member-list"></div>`;const list=oceanBox.querySelector('.member-list');
  const rule=waterIndex.ocean_boundaries,ruleBox=document.createElement('details');ruleBox.className='exception rule-section';ruleBox.innerHTML=`<summary><h3>Water-assignment corrections <span class="count">${rule.items.length} items</span></h3><p>Global ocean-boundary assignments. Fresh seed-fill items show prior and target labels plus the complete source-barrier network; they are not attributed to any one boundary arc.</p></summary><div class="member-list"></div>`;const ruleList=ruleBox.querySelector('.member-list');
  for(const leaf of rule.items){const entry=itemMap.get(leaf.id);if(!entry||entry.item.reference!==leaf.reference||entry.item.item_letter!==leaf.letter||entry.item.review_reason!==leaf.source_reason_key||leaf.source_reason_key!=='ocean-boundary-correction'||entry.item.continent_id!==undefined)throw Error(`Ocean-boundary reference mapping is invalid for ${leaf.id}`);const sourceGroup=meta.exceptions.find(g=>g.id===leaf.source_group_id),sourceMember=sourceGroup?.members.find(m=>m.id===leaf.source_member_id);if(!sourceGroup||!sourceMember||sourceGroup.type!=='ocean-boundary-correction')throw Error(`Unknown ocean-boundary source ${leaf.source_member_id}`);const g={...sourceGroup,title:leaf.name,destination:entry.item.target_ocean_label},m={...sourceMember,id:leaf.id,name:leaf.name,changed_cells:leaf.changed_cells,span_file:entry.item.span_file};memberCard(ruleList,g,m,leaf);itemMap.delete(leaf.id);}
  list.append(ruleBox);target.append(oceanBox);
 }
 if(itemMap.size)throw Error('Water reference index does not list every display item');
}
async function switchMode(next){
 if(!meta)return;
 if(next!=='v2'&&next!==candidateVersionKey)throw Error(`Unknown assignment version ${next}`);
 const url=new URL(location.href);url.searchParams.set('version',next);history.replaceState(null,'',url);
 if(next===mode&&gridSlot.name===mode)return;
 const seq=++loadSeq;
 status(`Loading and verifying ${next.toUpperCase()} assignment grid…`);
 renderer?.destroy?.();renderer=null;gridSlot.clear();pinSeq++;hoverSeq++;hoverController?.abort();hot=null;interaction.hover(null);interaction.clear();clearLegendFilter();
 overlay.getContext('2d').clearRect(0,0,overlay.width,overlay.height);
 try{
  const loaded=await gridSlot.load(next,(name,signal)=>readGrid(meta.versions[name],signal));
  if(!loaded||seq!==loadSeq)return;
  const selected=gridSlot.current;
  for(let i=1;i<selected.runs.length;i+=2)if(!categoryIds.has(selected.runs[i]))throw Error(`Unknown assignment category ${selected.runs[i]}`);
  renderer=createRenderer(canvas,paintMeta,selected);
  mode=next;hot=null;hoverSeq++;hoverController?.abort();pinSeq++;interaction.hover(null);interaction.clear();setLegendCounts(next);
  $('#v2').classList.toggle('active',next==='v2');$('#candidate').classList.toggle('active',next===candidateVersionKey);
  $('#version-note').textContent=next==='v2'?`Fixed V2 baseline; no ${candidateVersionLabel} overrides.`:`${candidateVersionLabel} candidate assignments; every difference from fixed V2 has build-time-verified attribution in the visible lists.`;
  status(`${next.toUpperCase()} native grid verified. V2/${candidateVersionLabel}/physical-mask accounting passed build-time QA. Only the active assignment grid is held in memory.`);requestDraw();
 }catch(e){if(seq===loadSeq&&e.name!=='AbortError'){renderer?.destroy?.();renderer=null;gridSlot.clear();status(e.message,true)}}
}
$('#legend-toggle').addEventListener('click',()=>setLegendPanel($('#legend-panel').hidden));$('#legend-search').addEventListener('input',()=>{hoveredContinent=null;renderLegend();updateLegendFilter()});$('#legend-clear').addEventListener('click',clearLegendFilter);
canvas.addEventListener('pointerdown',e=>{if(!renderer||!gridSlot.current)return;canvas.setPointerCapture(e.pointerId);drag={id:e.pointerId,x:e.offsetX,y:e.offsetY,ox,oy,moved:0}});
canvas.addEventListener('pointermove',e=>{if(!gridSlot.current)return;if(drag?.id===e.pointerId){const dx=e.offsetX-drag.x,dy=e.offsetY-drag.y;drag.moved=Math.max(drag.moved,Math.hypot(dx,dy));ox=drag.ox+dx;oy=drag.oy+dy;requestDraw();return}const c=cellAt(e.offsetX,e.offsetY);setHover(c)});
canvas.addEventListener('pointerup',e=>{if(drag?.id===e.pointerId&&drag.moved<5){const c=cellAt(e.offsetX,e.offsetY);pinSeq++;interaction.click(c?{cell:c}:null);$('#selection').textContent=describeCell(c);requestDraw()}drag=null});canvas.addEventListener('pointercancel',()=>drag=null);
canvas.addEventListener('pointerleave',()=>{if(!drag){hoverSeq++;hoverController?.abort();hot=null;interaction.hover(null);$('#tip').style.display='none';requestDraw()}});
canvas.addEventListener('wheel',e=>{e.preventDefault();zoom(Math.exp(-e.deltaY*.002),e.offsetX,e.offsetY)},{passive:false});
document.addEventListener('keydown',e=>{
 if(e.key==='Escape'){e.preventDefault();clearLegendFilter();return;}
 const command=mapKeyboardCommand(e);if(!command)return;e.preventDefault();
 if(command==='zoom-in'){zoom(2);return}if(command==='zoom-out'){zoom(.5);return}
 const delta=keyboardPanDelta(command);ox+=delta.x;oy+=delta.y;constrain();requestDraw();
});
$('#v2').onclick=()=>switchMode('v2');$('#candidate').onclick=()=>switchMode(candidateVersionKey);$('#clear').onclick=()=>{pinSeq++;interaction.clear();$('#selection').textContent='Pin cleared. Hover to inspect a cell.';requestDraw()};$('#world').onclick=$('#tool-world').onclick=fitWorld;$('#zoom-in').onclick=$('#tool-in').onclick=()=>zoom(2);$('#zoom-out').onclick=$('#tool-out').onclick=()=>zoom(.5);$('#sidebar').onclick=$('#list-toggle').onclick=()=>aside.classList.toggle('open');
$('#jump').onchange=e=>{if(!meta)return;const points={eurasia:[55,55,.6],pacific:[179,-8,.6],med:[18,36,1.8],caribbean:[-75,18,1.8]},p=points[e.target.value];if(p){const x=(p[0]+180)/meta.step,y=(90-p[1])/meta.step;centerCell(x,y,p[2])}};
new ResizeObserver(resize).observe(map);
try{
 const r=await fetch(versionedAsset('proposal.json'));if(!r.ok)throw Error('Review proposal.json is not available');meta=await r.json();
 candidateVersionKey=String(meta.candidate_version_key||'v3');
 if(!/^v[0-9]+$/.test(candidateVersionKey)||Number(candidateVersionKey.slice(1))<3)throw Error('Invalid candidate version key');
 candidateVersionLabel=String(meta.candidate_version_label||candidateVersionKey.toUpperCase());
 $('#candidate').textContent=`${candidateVersionLabel} · reviewed`;
 if(meta.schema_version!=='worldatlas-assignment-review-v1')throw Error('Unsupported review input schema');
 if(meta.width!==131072||meta.height!==54614)throw Error('Review must use the fixed 131072 × 54614 grid');
 if(!meta.versions?.v2||!meta.versions?.[candidateVersionKey]||!meta.physical_mask||!meta.physical_mask.id||!/^([a-f0-9]{64})$/.test(meta.physical_mask.mask_sha256||''))throw Error(`Missing V2/${candidateVersionLabel} or shared physical-mask manifest`);
 if(!Array.isArray(meta.exceptions))throw Error(`Missing ${candidateVersionLabel} exception lists`);
 if(Object.keys(meta.versions).length!==2||!meta.versions.v2||!meta.versions[candidateVersionKey])throw Error(`Review bundle must contain only fixed V2 and ${candidateVersionLabel}`);
 if(meta.versions.v2.physical_mask_sha256!==meta.physical_mask.mask_sha256||meta.versions[candidateVersionKey].physical_mask_sha256!==meta.physical_mask.mask_sha256)throw Error(`V2/${candidateVersionLabel} do not declare the same OSM physical-mask checksum`);
 if(!Array.isArray(meta.rule_records)||!meta.rule_records.length)throw Error('Missing known rule records');
 const ruleIds=new Set(meta.rule_records.map(x=>x.id));if(meta.rule_records.some(x=>!x.id||!x.title)||ruleIds.size!==meta.rule_records.length)throw Error('Invalid rule record index');
 for(const g of meta.exceptions){const e=g.extent;if(!g.id||!['island-convention','satellite-island','continental-water-22.224km','enclosed-ocean-pocket','ocean-boundary-correction'].includes(g.type)||!g.title||!g.reason||!g.destination||!g.members||!Array.isArray(g.members)||!g.ruleIds?.length||g.ruleIds.some(id=>!ruleIds.has(id))||!e||![e.x_start,e.x_end,e.y_start,e.y_end].every(Number.isInteger)||e.x_end<=e.x_start||e.x_end-e.x_start>meta.width||e.y_start<0||e.y_end>meta.height||e.y_end<=e.y_start)throw Error('Invalid exception index or unknown rule attribution');for(const m of g.members)if(!m.id||!m.name||!Number.isInteger(m.changed_cells)||m.changed_cells<1||!m.span_file?.url||!/^([a-f0-9]{64})$/.test(m.span_file.sha256||''))throw Error('Invalid lazy exception span reference')}
 const countsResponse=await fetch(new URL('legend-counts.json',dataBase));if(!countsResponse.ok)throw Error('Exact legend counts are not available');legendCounts=await countsResponse.json();if(legendCounts.schema_version!=='worldatlas-legend-counts-v1'||legendCounts.method!=='exact-assignment-rle-run-width-sums'||legendCounts.width!==meta.width||legendCounts.height!==meta.height||['v2',candidateVersionKey].some(v=>!legendCounts.versions?.[v]||legendCounts.versions[v].rows_sha256!==meta.versions[v].local_grid.rows_sha256||legendCounts.versions[v].runs_sha256!==meta.versions[v].local_grid.runs_sha256||Object.values(legendCounts.versions[v].counts||{}).reduce((a,b)=>a+Number(b),0)!==meta.width*meta.height))throw Error('Exact legend-count manifest does not match the active assignment grids');
 const proof=await verifyAccounting();
 if(!Array.isArray(meta.categories)||!meta.categories.length||meta.categories.some(c=>!Number.isInteger(c.id)||c.id<0||c.id>31||!c.name||!Array.isArray(c.rgb)||c.rgb.length!==3||c.rgb.some(v=>!Number.isInteger(v)||v<0||v>255))||new Set(meta.categories.map(c=>c.id)).size!==meta.categories.length)throw Error('Invalid assignment categories');
 const presResponse=await fetch(versionedAsset('water-presentation.json'));if(!presResponse.ok)throw Error('Validated continent presentation index is not available');const presentation=await presResponse.json();
 const presentationRuns=presentation.source?.candidate_runs_sha256||presentation.source?.v3_runs_sha256;
 const presentationMethod=presentation.validation?.method;
 if(presentation.schema_version!=='worldatlas-water-presentation-v1'||(presentation.source?.candidate_version_key||(candidateVersionKey==='v3'?'v3':null))!==candidateVersionKey||presentation.source?.exception_index_sha256!==proof.exception_index_sha256||presentationRuns!==meta.versions[candidateVersionKey].local_grid.runs_sha256||presentation.source?.physical_mask_sha256!==meta.physical_mask.mask_sha256||presentation.validation?.status!=='passed'||!['exact-member-interval-union-and-actual-v3-rle','exact-member-interval-union-and-actual-candidate-rle'].includes(presentationMethod)||presentation.validation?.source_cells!==presentation.validation?.displayed_cells)throw Error('Water presentation index or exact RLE partition validation is invalid');
 const expectedContinents=[{id:1,name:'Africa'},{id:2,name:'Asia'},{id:3,name:'Europe'},{id:4,name:'North America'},{id:5,name:'South America'},{id:6,name:'Oceania'}];
 if(!Array.isArray(presentation.continents)||presentation.continents.length!==6||presentation.continents.some((c,i)=>c.continent_id!==expectedContinents[i].id||c.continent!==expectedContinents[i].name||!Array.isArray(c.items)))throw Error('Water presentation must contain exactly six continent sections');
 const isOceanBoundary=g=>g.type==='ocean-boundary-correction'||g.review_reason==='ocean-boundary-correction';const sourceMembers=new Map(meta.exceptions.filter(g=>['continental-water-22.224km','enclosed-ocean-pocket'].includes(g.type)||isOceanBoundary(g)).flatMap(g=>g.members.map(m=>[m.id,{group:g,member:m}]))),seenItems=new Set(),shownCells=new Map();let shownTotal=0;
 for(const section of presentation.continents)for(const item of section.items){const source=sourceMembers.get(item.source_member_id),reason=waterReviewReason(source?.group);if(!source||source.group.id!==item.source_group_id||source.member.name!==item.name||item.source_destination!==source.group.destination||item.review_reason!==reason||item.continent_id!==section.continent_id||item.id!==`${item.source_member_id}@${item.continent_id}`||!Number.isInteger(item.changed_cells)||item.changed_cells<1||!item.span_file?.url||!/^([a-f0-9]{64})$/.test(item.span_file.sha256||'')||seenItems.has(item.id))throw Error('Invalid water presentation item');seenItems.add(item.id);shownCells.set(item.source_member_id,(shownCells.get(item.source_member_id)||0)+item.changed_cells);shownTotal+=item.changed_cells;}
 const oceanDisplayItems=presentation.ocean_items||[];for(const item of oceanDisplayItems){const source=sourceMembers.get(item.source_member_id);if(!source||!isOceanBoundary(source.group)||source.group.id!==item.source_group_id||item.review_reason!=='ocean-boundary-correction'||item.id!==`${item.source_member_id}@ocean`||('continent_id' in item)||!Array.isArray(item.source_ocean_codes)||!item.source_ocean_codes.length||!Array.isArray(item.source_ocean_labels)||item.source_ocean_labels.length!==item.source_ocean_codes.length||!item.source_ocean_label||!item.target_ocean_label||!Number.isInteger(item.target_ocean_code)||![7,8,9,10].includes(item.target_ocean_code)||item.source_ocean_codes.some(c=>!Number.isInteger(c)||(item.boundary_method==='fresh-ocean-seed-floodfill-v1'?![1,2,3,4,5,6,7,8,9,10].includes(c):![7,8,9,10].includes(c))||c===item.target_ocean_code)||typeof item.boundary_method!=='string'||!item.boundary_method||!item.source_coordinates||!Number.isInteger(item.changed_cells)||item.changed_cells<1||!item.span_file?.url||!/^([a-f0-9]{64})$/.test(item.span_file.sha256||'')||seenItems.has(item.id))throw Error('Invalid ocean-boundary presentation item');const targetCategory=meta.categories.find(c=>c.id===item.target_ocean_code),sourceCategories=item.source_ocean_codes.map(c=>meta.categories.find(x=>x.id===c));if(!targetCategory||targetCategory.physical_class!=='water'||targetCategory.name!==item.target_ocean_label||sourceCategories.some((c,i)=>!c||c.physical_class!=='water'||(item.boundary_method==='fresh-ocean-seed-floodfill-v1'?item.source_ocean_labels[i]!==`V2 prior water code ${item.source_ocean_codes[i]}: ${c.name}`:c.name!==item.source_ocean_labels[i]))||(item.boundary_method==='fresh-ocean-seed-floodfill-v1'?item.source_ocean_label!==item.source_ocean_labels.join(' / '):item.source_ocean_label!==item.source_ocean_labels.join(' / '))||(item.source_ocean_codes.length===1?item.source_ocean_code!==item.source_ocean_codes[0]:item.source_ocean_code!==null))throw Error('Ocean-boundary ocean label/code mismatch');const coords=item.source_coordinates;const validPoint=p=>p&&Number.isFinite(p.longitude_deg)&&Number.isFinite(p.latitude_deg)&&p.longitude_deg>=-180&&p.longitude_deg<=180&&p.latitude_deg>=-90&&p.latitude_deg<=90;const cropMethod='extend-existing-meridian-partition-through-cropped-edge';if(item.boundary_method==='fresh-ocean-seed-floodfill-v1'){if(!Array.isArray(coords.seed_points)||coords.seed_points.length!==4||coords.seed_points.some(p=>!validPoint(p)||![7,8,9,10].includes(p.ocean_code))||!coords.barrier_network_manifest||!/^([a-f0-9]{64})$/.test(coords.barrier_network_sha256||'')||!/^([a-f0-9]{64})$/.test(coords.barrier_edge_file_sha256||'')||!Array.isArray(coords.boundary_route_ids)||coords.boundary_route_ids.length!==9)throw Error('Invalid fresh ocean seed/barrier metadata');}else if(item.boundary_method===cropMethod){if(!Array.isArray(coords.meridian_longitudes)||coords.meridian_longitudes.length!==3||coords.meridian_longitudes.some(x=>!Number.isFinite(x)||x< -180||x>180))throw Error('Invalid crop-edge meridian coordinates');}else if(!/wgs.?84.*geodesic/i.test(item.boundary_method)||!Array.isArray(coords.endpoints)||coords.endpoints.length!==2||coords.endpoints.some(p=>!p||!Number.isFinite(p.lon)||!Number.isFinite(p.lat)||p.lon< -180||p.lon>180||p.lat< -90||p.lat>90))throw Error('Ocean arcs require two valid WGS84 geodesic endpoints');seenItems.add(item.id);shownCells.set(item.source_member_id,(shownCells.get(item.source_member_id)||0)+item.changed_cells);shownTotal+=item.changed_cells;}
 const sourceCells=[...sourceMembers.values()].reduce((n,x)=>n+x.member.changed_cells,0);
 if(sourceMembers.size!==presentation.totals?.source_members||presentation.totals?.display_items!==seenItems.size||presentation.totals?.source_cells!==sourceCells||presentation.totals?.display_cells!==sourceCells||shownTotal!==sourceCells||[...sourceMembers].some(([id,x])=>shownCells.get(id)!==x.member.changed_cells))throw Error('Water presentation does not exhaustively partition the original water exceptions');
 const refResponse=await fetch(versionedAsset('review-references.json'));if(!refResponse.ok)throw Error('List-reference mapping index is not available');const references=await refResponse.json();
 const expectedReferences=buildReferenceIndex(meta,presentation,presentation.source);
 if(!validateReferenceIndex(references,expectedReferences))throw Error('List-reference index does not cover the current source leaves or contains invalid reference metadata');
 categoryIds=new Set(meta.categories.map(c=>c.id));if(meta.categories.some(c=>!['land','water'].includes(c.physical_class)))throw Error('Every assignment category must declare physical_class land or water');

 renderIslandPresentation(references);renderWaterPresentation(presentation,references);
 // Native lossless row-run renderer. Only one assignment stream is loaded at a time.
 paintMeta={width:meta.width,height:meta.height,palette:Array.from({length:32},(_,i)=>meta.categories.find(c=>c.id===i)?.rgb||[0,0,0])};
 status(`Build-time QA passed: ${Number(proof.changed_cells).toLocaleString()} ${candidateVersionLabel} changes accounted vs fixed V2. Shared OSM physical mask ${meta.physical_mask.id} · ${meta.physical_mask.mask_sha256.slice(0,16)}…`);
 resize();mode='';const requested=new URLSearchParams(location.search).get('version');await switchMode(requested===candidateVersionKey?candidateVersionKey:'v2');fitWorld();
}catch(e){status(e?.message||String(e),true)}
canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();renderer?.destroy?.();renderer=null;gridSlot.clear();status('Graphics context lost. Reload the review to restore the map.',true)});
window.addEventListener('pagehide',()=>{renderer?.destroy?.();renderer=null;gridSlot.clear();hoverController?.abort()},{once:true});
