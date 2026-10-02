// Source role annotations are reference evidence, independent of geometry,
// dated claims and the immutable original country source-selection policy.
function canonical(value){
 if(Array.isArray(value))return `[${value.map(canonical).join(',')}]`;
 if(value&&typeof value==='object')return `{${Object.keys(value).sort().map(k=>`${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
 return JSON.stringify(value);
}
export function effectiveSourcePolicies(base,bundle){
 if(!base?.countries||bundle?.version!==1||!Array.isArray(bundle.policy_corrections))throw Error('Invalid source-policy correction bundle');
 const countries={...base.countries},seen=new Set();
 for(const correction of bundle.policy_corrections){
  const iso=correction.profile_iso;if(seen.has(iso)||!iso||!correction.id)throw Error('Duplicate or missing source-policy correction identity');seen.add(iso);
  const current=countries[iso],retained=correction.before_policy,after=correction.after_policy;
  if(!retained||!after||typeof after.role!=='string'||!after.role.trim()||typeof after.effective_level!=='string'||!after.effective_level.trim())throw Error('Corrected source policy requires a role and effective level');
  const withoutAnnotation=current&&Object.fromEntries(Object.entries(current).filter(([key])=>key!=='source_policy_correction'));
  if(canonical(withoutAnnotation)!==canonical(retained)&&canonical(withoutAnnotation)!==canonical(after))throw Error(`Source policy changed since correction: ${iso}`);
  countries[iso]={...after,source_policy_correction:{id:correction.id,bundle_id:bundle.id,status:'source-role-corrected-semantic-open',evidence_ids:[...correction.evidence_ids],local_granularity_approved:false}};
 }
 return {...base,countries};
}
const locationIndexes=new WeakMap();
export function correctedLocationSourceRole(locationId,bundle){
 if(!bundle||typeof bundle!=='object')return null;
 let index=locationIndexes.get(bundle);
 if(!index){index=new Map();for(const row of bundle.location_annotations??[]){if(!row?.location_id||index.has(row.location_id))throw Error('Duplicate or missing source-role location identity');index.set(row.location_id,row.after_annotation);}locationIndexes.set(bundle,index);}
 return index.get(locationId)??null;
}
const summaryIndexes=new WeakMap();
function summaryRoleIndex(summary){
 let index=summaryIndexes.get(summary);if(index)return index;
 if(summary?.version!==1||!Array.isArray(summary.role_groups))throw Error('Invalid bounded source-policy summary');
 index=new Map();
 for(const group of summary.role_groups){
  if(!group.profile_iso||!group.classification||typeof group.effective_source_role!=='string'||!group.effective_source_role.trim()||!Array.isArray(group.location_ids))throw Error('Invalid summarized source-role group');
  for(const id of group.location_ids){if(typeof id!=='string'||!id||index.has(id))throw Error('Duplicate or missing summarized location identity');index.set(id,group);}
 }
 summaryIndexes.set(summary,index);return index;
}
/** Count the actual selected location IDs, including territories across continents. */
export function selectedSourcePolicyRoles(features,summary){
 const index=summaryRoleIndex(summary),profiles=new Map();
 for(const feature of features){
  const group=index.get(feature.id);if(!group)continue;
  if(!profiles.has(group.profile_iso))profiles.set(group.profile_iso,new Map());
  const roles=profiles.get(group.profile_iso),entry=roles.get(group.classification)||{role:group.effective_source_role,count:0};entry.count++;roles.set(group.classification,entry);
 }
 return profiles;
}
/** Frozen review notes retain their dates and decisions; only the presented role changes. */
export function coverageSourcePolicy(profile,summary,selectedRoles){
 const correction=summary?.policy_corrections?.find(row=>row.profile_iso===profile.iso);
 if(!correction)return {policy:profile.policy,correction:null,roles:[]};
 const effective=effectiveSourcePolicies({countries:{[profile.iso]:profile.policy}}, {...summary,policy_corrections:[correction]});
 return {policy:effective.countries[profile.iso],correction,roles:[...(selectedRoles?.get(profile.iso)?.values()||[])]};
}
const html=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function sourcePolicyCoverageHTML(presentation,summary){
 const {policy,correction,roles}=presentation;
 const role=`<p><strong>Source role:</strong> ${html(policy?.role||'Territorial source requires separate review')}</p>`;
 if(!correction)return role;
 const evidence=(summary.source_evidence||[]).filter(row=>correction.evidence_ids.includes(row.id));
 return role+`<p><strong>Reference geography:</strong> ${html(policy.effective_level)}</p><p>${roles.map(row=>`${html(row.role)}: ${row.count.toLocaleString()} locations`).join(' · ')} in this selection.</p><p>Source description corrected ${html(summary.reviewed_at)}. Location scale and geographic boundaries remain under review.</p><details><summary>Correction evidence and earlier source description</summary><p>${html(policy.reason)}</p><p><strong>Earlier description:</strong> ${html(correction.before_policy.role)} · ${html(correction.before_policy.level)} administrative source selection. Earlier review notes and source metadata below are retained as context.</p>${evidence.map(row=>`<p>${html(row.fact)}${(row.urls||[]).filter(url=>/^https?:\/\//.test(url)).map(url=>`<br><a href="${html(url)}" target="_blank" rel="noreferrer">Source evidence</a>`).join('')}</p>`).join('')}</details>`;
}
