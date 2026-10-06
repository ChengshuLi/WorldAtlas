import {readJSON} from './data-client.js';
import {presentedAttribute} from './reference-context.js';
import {attributes,formatYear} from './model.js';
import {coverageScope} from './coverage-scope.js';
import {selectedSourcePolicyRoles,coverageSourcePolicy,sourcePolicyCoverageHTML} from './source-policy-corrections.js';
const safe=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function installCoverage(getContext){
 const button=document.createElement('button');button.id='coverage-button';button.className='quiet';button.textContent='Coverage and review';document.querySelector('header').insertBefore(button,document.querySelector('#about'));
 const dialog=document.createElement('dialog');dialog.id='coverage-dialog';dialog.className='coverage-dialog';dialog.innerHTML=`<button class="dialog-close" aria-label="Close coverage">×</button><div class="eyebrow">ATLAS COVERAGE</div><h2>Evidence and geographic review</h2><p id="coverage-context"></p><div class="coverage-filters"><label>Continent<select id="coverage-continent"><option value="">All continents</option></select></label><label>Reference territory<select id="coverage-territory"><option value="">All territories</option></select></label><label>Attribute<select id="coverage-attribute">${attributes.map(a=>`<option value="${a}">${a}</option>`).join('')}</select></label></div><div id="coverage-summary" class="coverage-stats"></div><h3>Top-down geographic audit</h3><p>Continent → subcontinent → region → area → province → location. Each branch shows its own boundary review and child coverage. Source checks alone do not close semantic reviews.</p><div id="coverage-levels"></div><div id="coverage-tree"></div><h3>Geographic research</h3><details id="coverage-macro-research"><summary>Continent, subcontinent and regional evidence</summary><div id="coverage-macro-evidence"><p>Open this section to inspect the research. Unfinished boundary and member reviews remain open in the hierarchy above.</p></div></details><h3>Changes to reference territories</h3><p>Earlier geographic identities and their records are retained. Relationships between territories describe revisions to the reference map; they do not establish historical border changes or transfer historical attributes.</p><p><a href="./geographic-migration-review.json.gz" download>Download every geographic change</a> · <a href="./geographic-migration-archive.json.gz" download>Download earlier territories and retained history</a></p><h3>Worldwide source review</h3><p>Regional research now inventories every region and all its areas, provinces and member locations across all six continents. Source-role assessments and proposed corrections are documented; unfinished semantic reviews remain open.</p><p><a href="./region-semantic-review.json.gz" download>Download the complete regional research and proposals</a></p><p><a href="./granularity-review-evidence.json.gz" download>Download location-scale assessments for every territory</a></p><p>Source-assessed means the source role, date, license and current coverage were inspected. Open semantic decisions remain listed individually.</p><p id="coverage-source-policy-notice" role="status"></p><div id="coverage-reviews"></div><h3>Source inventory</h3><div id="coverage-sources"></div><p><a href="./world-review.json" target="_blank">All geographic decisions</a> · <a href="./pixel-audit.json.gz" download>Every location’s pixel representation</a></p>`;document.body.append(dialog);
 dialog.querySelector('.dialog-close').onclick=()=>dialog.close();let request,review,inventory,pixels,macroRequest,macroEvidence,policyRequest,policySummary,policyLoadWarning;const locationRequests=new Map();
 const loadMembers=path=>{if(!locationRequests.has(path))locationRequests.set(path,readJSON('./'+path).catch(error=>{locationRequests.delete(path);throw error;}));return locationRequests.get(path);};
 const renderResearch=()=>{
  if(!macroEvidence)return;
  const continent=dialog.querySelector('#coverage-continent').value,owner=dialog.querySelector('#coverage-territory').value;
  const sources=new Map(macroEvidence.sources.map(source=>[source.id,source]));
  const sourceLinks=ids=>(ids||[]).map(id=>sources.get(id)).filter(Boolean).map(source=>`<a href="${safe(source.url)}" target="_blank" rel="noreferrer">${safe(source.id.replaceAll('-',' '))}</a> (${source.inspected?'inspected':'not inspected'})`).join(' · ');
  const row=(record,level)=>`<details><summary>${safe(record.name)} (${level}) · ${safe(record.assessment_status.replaceAll('-',' '))}</summary><p>${safe(record.assessment||'Member coverage inventoried; semantic review remains open.')}</p><p>${record.semantic_approved?'This specific geographic assessment is approved.':'Geographic meaning and boundaries remain open for review.'}</p>${(record.unresolved_work||record.review_reasons||[]).map(note=>`<p>${safe(note)}</p>`).join('')}<p>${sourceLinks(record.source_ids)}</p>${record.areas?.length?`<details><summary>${record.areas.length.toLocaleString()} areas inventoried</summary>${record.areas.map(area=>row(area,'area')).join('')}</details>`:''}</details>`;
  const continents=macroEvidence.continents.filter(record=>!continent||record.name===continent),continentIds=new Set(continents.map(record=>record.id));
  const subcontinents=macroEvidence.subcontinents.filter(record=>continentIds.has(record.parent_id));
  const regions=macroEvidence.regions.filter(record=>(!continent||record.continent===continent)&&(!owner||record.reference_territories?.[owner]));
  dialog.querySelector('#coverage-macro-evidence').innerHTML=`<p>Research inventories all ${macroEvidence.counts.continents} continents, ${macroEvidence.counts.subcontinents} subcontinents and ${macroEvidence.counts.regions} regions. Examining sources and finding problems does not approve their geographic boundaries. Some findings concern earlier versions of the map; the hierarchy above shows the current review status.</p>${macroEvidence.snapshot_relation?`<p>${safe(macroEvidence.snapshot_relation)}</p>`:''}${macroEvidence.corrections_applied?`<p><strong>${macroEvidence.corrections_applied.cases} source-supported corrections applied</strong> · ${macroEvidence.corrections_applied.changed_locations.toLocaleString()} location memberships and ${macroEvidence.corrections_applied.changed_groups.toLocaleString()} geographic groups updated. Geographic boundaries remain under semantic review. <a href="./${safe(macroEvidence.corrections_applied.report)}" download>Inspect the corrections</a></p>`:''}${Object.values(macroEvidence.source_assessment||{}).map(note=>`<p>${safe(note)}</p>`).join('')}<h4>Continents</h4>${continents.map(record=>row(record,'continent')).join('')}<h4>Subcontinents</h4>${subcontinents.map(record=>row(record,'subcontinent')).join('')}<h4>Regions</h4>${regions.map(record=>row(record,'region')).join('')}<details><summary>Inspected and unavailable sources</summary>${macroEvidence.sources.map(source=>`<p><a href="${safe(source.url)}" target="_blank" rel="noreferrer">${safe(source.id.replaceAll('-',' '))}</a> · ${source.inspected?'Inspected':'Not inspected'}${source.error?`<br>${safe(source.error)}`:''}</p>`).join('')}</details><p><a href="./macro-review-evidence.json" target="_blank">Download all geographic research findings</a></p>`;
 };
 dialog.querySelector('#coverage-macro-research').addEventListener('toggle',async event=>{
  if(!event.target.open)return;
  if(macroEvidence){renderResearch();return;}
  dialog.querySelector('#coverage-macro-evidence').textContent='Loading geographic research…';
  try{macroRequest ||= readJSON('./macro-review-evidence.json').catch(error=>{macroRequest=null;throw error;});macroEvidence=await macroRequest;renderResearch();}
  catch{dialog.querySelector('#coverage-macro-evidence').textContent='Research findings could not load. Close and reopen this section to retry.';}
 });
 const render=()=>{
  const {data,states,year,parents}=getContext(),continent=dialog.querySelector('#coverage-continent').value,owner=dialog.querySelector('#coverage-territory').value,attribute=dialog.querySelector('#coverage-attribute').value;
  const {profiles,features}=coverageScope(data.features,parents,review.territories,{continent,owner});
  const policies=new Map();let policyWarning=policyLoadWarning;
  if(policySummary)try{const selectedRoles=selectedSourcePolicyRoles(features,policySummary);for(const profile of profiles)policies.set(profile.owner,coverageSourcePolicy(profile,policySummary,selectedRoles));}
  catch{policies.clear();policyWarning='Source-role corrections could not be verified against this review. Descriptions below use the earlier review; geographic decisions remain unchanged.';}
  dialog.querySelector('#coverage-source-policy-notice').textContent=policyWarning||(policySummary?'Source descriptions include sourced corrections. Earlier review notes remain available; these corrections do not approve location scale or boundaries.':'');
  let known=0,derived=0,reference=0,referenceContext=0,disputed=0,unrepresented=0;const missingPixels=new Set(pixels?.missing?.map(p=>p.id)||[]);
  for(const f of features){const r=states.get(f.id),p=r?.provenance?.[attribute];if(r?.[attribute]!=null)known++;if(p?.method==='majority-area')derived++;if(p?.status==='reference')reference++;const shown=presentedAttribute(r,attribute);if(shown.value!=null&&shown.provenance?.context_only)referenceContext++;if(p?.status==='disputed')disputed++;if(missingPixels.has(f.id))unrepresented++;}
  dialog.querySelector('#coverage-context').textContent=`${formatYear(year)} · Attribute counts use the selected year and whole-location records. Territory filters use reference geography.`;
  dialog.querySelector('#coverage-summary').innerHTML=[['Locations',features.length],['Known '+attribute,known],['Unknown '+attribute,features.length-known],['Derived assignments',derived],['Dated reference values',reference],['Separate reference context',referenceContext],['Conflicting claims',disputed],['Missing grid representation',unrepresented]].map(([label,n])=>`<div><strong>${n.toLocaleString()}</strong><span>${safe(label)}</span></div>`).join('');
  const groups=new Map(review.groups.map(g=>[g.id,g]));
  dialog.querySelector('#coverage-levels').textContent=Object.entries(review.level_progress||{}).map(([level,p])=>`${level}: ${p.total.toLocaleString()} inventoried, ${(p.boundary_reviewed??p.semantic_reviewed??0).toLocaleString()} ${level==='location'?'locations':'boundaries'} reviewed, ${(p.pending??p.pending_semantic_review??0).toLocaleString()} awaiting complete review`).join(' · ');
  const tree=dialog.querySelector('#coverage-tree');tree.replaceChildren();
  const addBranch=(id,target)=>{
   const g=groups.get(id);if(!g||owner&&!g.owners.includes(owner))return;
   const details=document.createElement('details'),summary=document.createElement('summary');
   summary.textContent=`${g.name} (${g.level}) · ${g.locations.toLocaleString()} locations · ${g.semantic_status||'pending'}`;
   details.dataset.groupId=id;details.append(summary);target.append(details);let loaded=false;
   const loadBranch=async()=>{
    if(loaded)return;loaded=true;
    details.querySelector(':scope > .coverage-branch')?.remove();
    const body=document.createElement('div');body.className='coverage-branch';details.append(body);
    const note=document.createElement('p');note.textContent=`Boundary: ${g.checks?.boundary_review||'pending'}. ${g.basis||''}`;body.append(note);
    if(g.source_url){const link=document.createElement('a');link.href=g.source_url;link.textContent='Geographic source';link.target='_blank';link.rel='noreferrer';body.append(link);}
    for(const child of g.child_ids||[])addBranch(child,body);
    if(g.level!=='province')return;
    const message=document.createElement('p');message.textContent='Loading every member location…';body.append(message);
    try{
     const rows=(await Promise.all((g.location_parts||[]).map(loadMembers))).flat().filter(l=>l.parent_id===g.id&&(!owner||l.owner===owner));
     message.textContent=`${rows.length} members · ${rows.filter(l=>l.semantic_status==='supported').length} fully reviewed`;
     for(const l of rows){const line=document.createElement('p');line.textContent=`${l.name} · ${l.area_km2?.toLocaleString()??'Unknown'} km² · ${l.semantic_status||'pending'}${l.reasons?.length?' · '+l.reasons.join('; '):''}`;body.append(line);}
    }catch{
     message.textContent='Member records unavailable. Close and reopen this branch to retry.';loaded=false;
    }
   };
   // Add children during activation so the next branch is available immediately.
   // Native toggle also handles programmatic expansion and accessibility tools.
   summary.addEventListener('click',()=>{if(!details.open)void loadBranch();});
   details.addEventListener('toggle',()=>{if(details.open)void loadBranch();});
  };
  for(const id of review.root_ids||[])if(!continent||groups.get(id)?.name===continent)addBranch(id,tree);
  dialog.querySelector('#coverage-reviews').innerHTML=`<p>${profiles.length} territories shown · ${review.policy_profiles} source policies crosswalked to ${review.reference_owner_groups} reference groups · ${review.semantic_complete?'Semantic review complete':'Semantic review in progress'}</p>`+profiles.map(p=>{
   const assessment=policies.get(p.owner)||{policy:p.policy,correction:null,roles:[]};
   const sourceRows=new Map();for(const source of p.sources??[]){const key=assessment.correction?JSON.stringify([source.url,source.role||source.id,source.year,source.license]):source.id;const row=sourceRows.get(key)||{source,count:0};row.count++;sourceRows.set(key,row);}
   const retainedSources=[...sourceRows.values()].map(({source:s,count})=>`<p>${count>1?`${count.toLocaleString()} retained source entries · `:''}<a href="${safe((s.url||'').startsWith('http')?s.url:'https://'+s.url)}" target="_blank" rel="noreferrer">${safe(s.role||s.id)}</a> · ${safe(s.year)} · ${safe(s.license)}</p>`).join('');
   return `<details><summary>${safe(p.owner??'Unassigned reference territory')} · ${p.selected_locations.toLocaleString()} locations in selection · ${safe(p.status)}</summary>${sourcePolicyCoverageHTML(assessment,policySummary)}${assessment.correction&&p.issues?.length?'<p><strong>Earlier review notes:</strong></p>':''}${(p.issues??[]).map(i=>`<p>${safe(i)}</p>`).join('')}<p>${p.open_group_ids.length} groups have open notes.</p>${p.candidate_refinement?`<p>Finer source assessment: ${safe(p.candidate_refinement.status)}</p>`:''}${assessment.correction?`<details><summary>Retained source metadata</summary>${retainedSources}</details>`:retainedSources}<details><summary>Group decisions</summary>${p.open_group_ids.map(id=>{const g=groups.get(id);return g?`<p><strong>${safe(g.name)}</strong> (${safe(g.level)}): ${(g.reasons??[g.basis||'Review notes unavailable in this report.']).map(safe).join('; ')}<br><small>${safe(g.basis)}</small></p>`:`<p>Retained group ${safe(id)}: review notes unavailable in this report.</p>`;}).join('')}</details></details>`;
  }).join('');
  renderResearch();
  dialog.querySelector('#coverage-sources').innerHTML=inventory.sources.filter(s=>s.attributes.includes(attribute)).map(s=>`<p><a href="${safe(s.url)}" target="_blank" rel="noreferrer">${safe(s.name)}</a> · ${safe(s.status)}<br>${safe(s.scope)}<br><small>${safe(s.license)} · ${safe(s.limitation)}</small></p>`).join('');
 };
 button.onclick=async()=>{dialog.showModal();dialog.querySelector('#coverage-context').textContent='Loading coverage reports…';try{
  request ||= Promise.all(['world-review.json','source-inventory.json','pixel-audit.json.gz'].map(p=>readJSON('./'+p))).catch(e=>{request=null;throw e;});
  policyRequest ||= readJSON('./source-policy-corrections/summary.json').catch(error=>{policyRequest=null;throw error;});
  const [reports,corrections]=await Promise.allSettled([request,policyRequest]);if(reports.status==='rejected')throw reports.reason;[review,inventory,pixels]=reports.value;
  policySummary=corrections.status==='fulfilled'?corrections.value:null;policyLoadWarning=corrections.status==='rejected'?'Source-role corrections are unavailable. Descriptions below use the earlier review. Close and reopen to retry; geographic decisions remain unchanged.':null;
  if(dialog.querySelector('#coverage-territory').options.length===1){for(const c of Object.keys(review.batches).sort())dialog.querySelector('#coverage-continent').add(new Option(c,c));for(const p of review.territories)dialog.querySelector('#coverage-territory').add(new Option(p.owner,p.owner));}
  render();
 }catch{dialog.querySelector('#coverage-context').textContent='Coverage reports could not load. Close and reopen to retry.';}};
 dialog.querySelectorAll('select').forEach(s=>s.onchange=render);
}
