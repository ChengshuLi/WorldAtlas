export const CONTINENT_ORDER=Object.freeze(['Africa','Asia','Europe','North America','South America','Oceania']);

// Zero-based ordinal to spreadsheet-style lowercase letter (a..z, aa..).
export function itemLetter(index){
  if(!Number.isInteger(index)||index<0)throw Error('Item index must be a non-negative integer');
  let n=index+1,out='';while(n){n--;out=String.fromCharCode(97+n%26)+out;n=Math.floor(n/26);}return out;
}
function cmp(a,b){const x=String(a).toLowerCase(),y=String(b).toLowerCase();return x<y?-1:x>y?1:String(a)<String(b)?-1:String(a)>String(b)?1:0;}
function reference(list,continent,reason,item){return `List ${list} · ${continent} · Reason ${reason} · Item ${item}`;}

// Component IDs and source-crosswalk mechanics are useful audit metadata but
// make poor public list labels. Keep those IDs in source_member_id/source_group_id
// and expose the geographic name in the visible leaf instead.
export function publicIslandMemberName(group,member){
  if(typeof member.display_name==='string'&&member.display_name.trim())return member.display_name.trim();
  const original=String(member.name||'').trim();
  let label=original
    .replace(/\b(?:represented land |source-connected physical |physical )?component\s+\d+\b/gi,'')
    .replace(/\bwhole component\s+\d+\b/gi,'')
    .replace(/\bfully contained in relation\s+\d+\b/gi,'')
    .replace(/\broot\s+\d+\b/gi,'')
    .replace(/\s*[,;|/]\s*(?=[,;|/])/g,' ')
    .replace(/[\s,;|/–-]+$/g,'').trim();
  if(label.includes('/')&&!/\bAsia\s*\/\s*Oceania\b/i.test(label))label=label.split('/').map(x=>x.trim()).find(Boolean)||label;
  label=label.replace(/\s*→\s*[^→]+$/,'').trim();
  if(label&& !/^(?:represented land|source-connected physical|physical|whole|component|fully contained)$/i.test(label))return label;
  const title=publicIslandTitle(group).split(' · ')
    .map(s=>s.trim())
    .filter(s=>s&&!/connected source-land polygon fragments inherit|whole component|component\s+\d+/i.test(s));
  if(title.length)return title.join(' · ');
  return original.replace(/\b(?:represented land |source-connected physical |physical )?component\s+\d+\b/gi,'').trim()||'Named island group';
}

export function publicIslandTitle(group){
  const parts=String(group.title||'').split(';')
    .map(s=>s.replace(/\s*→\s*[^;]+$/,'').trim())
    .filter(s=>s&&!/connected source-land polygon fragments inherit|whole component|component\s+\d+/i.test(s));
  return (parts.length?parts:[String(group.title||'Island group').replace(/\s*→\s*[^;]+$/,'').trim()])
    .map(s=>s.replace(/and source-connected land fragments/i,'and nearby land fragments'))
    .join(' · ');
}

export function publicIslandReason(group){
  const reason=String(group.reason||'').trim();
  if(/source-connected land fragments|same continuous physical/i.test(reason)){
    return 'Nearby land fragments are grouped with the named island because the source land polygons show physical continuity. This is a geography rule, not a political boundary.';
  }
  return reason;
}

// Presentation-only semantic buckets. Source groups, member IDs and exact spans stay intact.
// Release-specific island presentation is supplied by a versioned data export.
function recordsFor(meta, source, records) {
  if (!records || Object.keys(records).sort().join(',') !== 'groups,leaves,schema,source' || records.schema !== 'worldatlas-island-presentation-v1' ||
      canonical(records.source) !== canonical(source) ||
      !Array.isArray(records.groups) || !Array.isArray(records.leaves))
    throw Error('Missing or mismatched presentation release');
  const groups=new Map(), leaves=new Map();
  for (const g of records.groups) {
    if (!g || Object.keys(g).sort().join(',') !== 'display,id' || typeof g.id !== 'string' || !g.id || groups.has(g.id) ||
        !g.display || Object.keys(g.display).sort().join(',') !== 'key,reason,title' || !['key','title','reason'].every(k=>typeof g.display[k] === 'string' && g.display[k]))
      throw Error('Invalid or duplicate presentation group');
    groups.set(g.id,g.display);
  }
  for (const l of records.leaves) {
    const id=JSON.stringify([l?.group_id,l?.member_id]);
    if (!l || Object.keys(l).sort().join(',') !== 'display,group_id,member_id' || typeof l.group_id !== 'string' || typeof l.member_id !== 'string' ||
        !l.group_id || !l.member_id || leaves.has(id) || !l.display ||
        !['name','justification','geographic_basis_status'].every(k=>typeof l.display[k] === 'string') ||
        Object.keys(l.display).sort().join(',') !== 'geographic_basis_status,justification,name')
      throw Error('Invalid or duplicate presentation leaf');
    leaves.set(id,l.display);
  }
  return {groups,leaves,usedGroups:new Set(),usedLeaves:new Set()};
}

export function waterReviewReason(group){
  if(group?.type==='ocean-boundary-correction'||group?.review_reason==='ocean-boundary-correction')return 'ocean-boundary-correction';
  if(group?.type==='ocean-boundary-correction'||group?.review_reason==='ocean-boundary-correction')return 'ocean-boundary-correction';
  if(group?.type==='ocean-boundary-correction'||group?.review_reason==='ocean-boundary-correction')return 'ocean-boundary-correction';
  if(group?.type==='ocean-boundary-correction'||group?.review_reason==='ocean-boundary-correction')return 'ocean-boundary-correction';
  if(group?.type==='ocean-boundary-correction'||group?.review_reason==='ocean-boundary-correction')return 'ocean-boundary-correction';
  if(group?.type==='ocean-boundary-correction'||group?.review_reason==='ocean-boundary-correction')return 'ocean-boundary-correction';
  if(group?.review_reason==='ordinary-nearshore-band')return 'ordinary-nearshore-band';
  if(group?.review_reason==='isolated-water-without-geographic-support')return 'isolated-water-without-geographic-support';
  return group?.type==='enclosed-ocean-pocket'?'enclosed-ocean-pocket-filled':group?.destination==='nearest_revised_shoreline'?'shared-basin-nearest-shore':'named-basin-assigned-to-continent';
}

function consolidateLandLeaf(item,parentReason){
  const joined=(...values)=>values.flatMap(v=>typeof v==='string'?[v]:Array.isArray(v)?v.map(String):v&&typeof v==='object'?Object.values(v).map(String):[]).join(' ');
  const evidence=joined(item.id,item.source_member_id,item.source_group_id,item.rule_ids,item.name,item.geographic_group,item.justification,item.source_reason,item.source_policy,parentReason.title,parentReason.reason,parentReason.display_title,parentReason.display_reason);
  const itemText=joined(item.justification,item.source_reason,item.source_policy);
  const parentText=joined(parentReason.title,parentReason.reason,parentReason.display_title,parentReason.display_reason);
  const mainland=/mainland.{0,45}(?:boundary|divide)|(?:boundary|divide).{0,45}mainland|continental boundary.{0,45}(?:mainland|divide)|ural and eastern caucasus|main canal separates africa from asia|canal boundary side takes priority|geographic side of the main canal/i.test(evidence);
  const textContinuity=/physical land continuity|physical continuity|continuous physical|connected source[- ]land|source polygon continuity|source land polygons show physical continuity|land fragments inherit/i.test(itemText+' '+parentText);
  const continuityMarker=/source[_-]continuity/i.test(joined(item.rule_ids,item.source_group_id));
  const continuity=textContinuity||(continuityMarker&&/physical continuity|continuous physical|source-connected/i.test(parentText));
  const otherGeography=/archipelago|island[- ]arc group|island\/site membership|geographically associated with|shelf affiliation|shelf or plateau affiliation|regional convention|geographic side.{0,30}takes priority|for land separated by the main .* canal/i.test(itemText);
  if(mainland&&continuity)return 'mainland-boundary';
  if(continuity&&otherGeography)return 'grid-fragment';
  if(mainland)return 'mainland-boundary';
  if(continuity)return 'grid-fragment';
  return 'island-affiliation';
}
function consolidateLandList1(list1){
  const order=['island-affiliation','mainland-boundary','grid-fragment'];
  const meta={
    'island-affiliation':{title:'Geographic island affiliation',reason:'These land assignments follow their stated island group, geographic region, or shelf affiliation. Each item retains its specific basis, source evidence, and highlighted changed cells; political ownership is not inferred.'},
    'mainland-boundary':{title:'Mainland continental boundary corrections',reason:'Only land cells explicitly changed by a reviewed mainland divide are listed; this is not a complete redrawing of a continental boundary.'},
    'grid-fragment':{title:'Grid-fragment corrections',reason:'These corrections group grid fragments with a named landmass where the source land geometry supports physical continuity. Each item retains its specific continuity explanation and highlighted changed cells.'}
  };
  const out=[];
  for(const section of list1.continents){
    const buckets=new Map(order.map(k=>[k,[]]));
    const groups=new Map(order.map(k=>[k,new Set()]));
    for(const parent of section.reasons)for(const item of parent.items){
      const category=consolidateLandLeaf(item,parent);
      buckets.get(category).push(item);groups.get(category).add(item.source_group_id||'');
    }
    const reasons=[];
    for(const category of order){
      const items=buckets.get(category);if(!items.length)continue;
      items.sort((a,b)=>cmp(a.name,b.name)||cmp(a.source_member_id,b.source_member_id));
      const number=reasons.length+1,definition=meta[category];
      const outItems=items.map((item,index)=>({...item,letter:itemLetter(index),reference:reference(1,section.continent,number,itemLetter(index))}));
      const source_group_ids=[...groups.get(category)].sort(cmp);
      reasons.push({title:definition.title,reason:definition.reason,display_title:definition.title,display_reason:definition.reason,source_group_ids,items:outItems,number});
    }
    out.push({continent:section.continent,reasons});
  }
  list1.continents=out;
}

function consolidateWaterList2(list2,presentation){
  const order=['continental-seas-and-bays','shared-seas','water-assignment-corrections','enclosed-ocean-pockets'];
  const sourceToGroup={
    'named-basin-assigned-to-continent':'continental-seas-and-bays',
    'shared-basin-nearest-shore':'shared-seas',
    'ordinary-nearshore-band':'water-assignment-corrections',
    'isolated-water-without-geographic-support':'water-assignment-corrections',
    'ocean-boundary-correction':'water-assignment-corrections',
    'ocean-boundary-correction':'water-assignment-corrections',
    'ocean-boundary-correction':'water-assignment-corrections',
    'ocean-boundary-correction':'water-assignment-corrections',
    'ocean-boundary-correction':'water-assignment-corrections',
    'ocean-boundary-correction':'water-assignment-corrections',
    'enclosed-ocean-pocket-filled':'enclosed-ocean-pockets'
  };
  const titles={
    'continental-seas-and-bays':'Continental seas and bays',
    'shared-seas':'Shared seas',
    'water-assignment-corrections':'Water-assignment corrections',
    'enclosed-ocean-pockets':'Enclosed ocean pockets'
  };
  const continents=[];
  for(const section of list2.continents){
    const grouped=new Map(order.map(k=>[k,[]]));
    const sourceKeys=new Map(order.map(k=>[k,new Set()]));
    for(const parent of section.reasons)for(const raw of parent.items){
      const sourceKey=raw.source_reason_key||parent.key;
      const key=sourceToGroup[sourceKey];
      if(!key)throw Error(`Unknown List 2 source reason key ${sourceKey} for ${raw.id}`);
      const item=raw.source_reason_key?raw:{...raw,source_reason_key:sourceKey};
      grouped.get(key).push(item);sourceKeys.get(key).add(sourceKey);
      if(!item.span_file?.url||!item.span_file?.sha256)throw Error(`List 2 item lacks span URL/hash: ${item.id}`);
    }
    const reasons=[];
    for(const key of order){
      const items=grouped.get(key);if(!items.length)continue;
      items.sort((a,b)=>cmp(a.name,b.name)||cmp(a.source_member_id,b.source_member_id));
      const number=reasons.length+1;
      const leaves=items.map((item,index)=>({...item,letter:itemLetter(index),reference:reference(2,section.continent,number,itemLetter(index))}));
      reasons.push({number,title:titles[key],key,source_keys:[...sourceKeys.get(key)].sort(cmp),items:leaves});
    }
    continents.push({continent:section.continent,reasons});
    const displaySection=presentation.continents.find(c=>c.continent===section.continent);
    if(!displaySection)throw Error(`Missing water presentation section ${section.continent}`);
    const byId=new Map(reasons.flatMap(reason=>reason.items.map(item=>[item.id,{number:reason.number,letter:item.letter,reference:item.reference}])));
    for(const item of displaySection.items){
      const ref=byId.get(item.id);if(!ref)throw Error(`Missing consolidated List 2 reference for ${item.id}`);
      item.reason_number=ref.number;item.item_letter=ref.letter;item.reference=ref.reference;
    }
    if(byId.size!==displaySection.items.length)throw Error(`List 2 display/reference membership mismatch in ${section.continent}`);
  }
  list2.continents=continents;
  const oceanItems=presentation.ocean_items||[];
  if(oceanItems.length){
    const seen=new Set(),items=[...oceanItems].sort((a,b)=>cmp(a.name,b.name)||cmp(a.source_member_id,b.source_member_id)).map((item,index)=>{
      if(item.review_reason!=='ocean-boundary-correction')throw Error(`Unknown ocean-boundary source key for ${item.id}`);
      if('continent_id' in item)throw Error(`Ocean-boundary item must not claim a continent: ${item.id}`);
      if(!item.source_coordinates||!item.boundary_method||!item.source_ocean_label||!item.target_ocean_label)throw Error(`Ocean-boundary item lacks endpoints/method/ocean labels: ${item.id}`);
      if(!item.span_file?.url||!item.span_file?.sha256)throw Error(`Ocean-boundary item lacks exact spans: ${item.id}`);
      if(seen.has(item.id))throw Error(`Duplicate ocean-boundary item ${item.id}`);seen.add(item.id);
      const letter=itemLetter(index),reference=`List 2 · Ocean boundaries · Water-assignment corrections · Item ${letter}`;
      item.item_letter=letter;item.reference=reference;
      return {...item,source_reason_key:'ocean-boundary-correction',letter,reference,
        justification:item.justification||`${item.source_ocean_label} → ${item.target_ocean_label}; ${item.boundary_method}. Source endpoints: ${JSON.stringify(item.source_coordinates)}.`};
    });
    list2.ocean_boundaries={title:'Ocean boundaries',key:'water-assignment-corrections',source_keys:['ocean-boundary-correction'],items};
  }else delete list2.ocean_boundaries;
}

export function buildReferenceIndex(meta,presentation,source,records){
  const data=recordsFor(meta,source,records);
  // Route every canonical exception group before rendering. The reference UI
  // is not an eligibility filter: a novel/unroutable group must stop the
  // generator rather than silently disappear from the review lists.
  const groupById=new Map(meta.exceptions.map(g=>[g.id,g]));
  if(groupById.size!==meta.exceptions.length)throw Error('Duplicate canonical exception group ID');
  const landGroups=new Set(),waterGroups=new Set();
  for(const g of meta.exceptions){
    const classes=new Set((g.members||[]).map(m=>m.physical_class).filter(Boolean));
    if(classes.size>1)throw Error(`Mixed physical classes in exception group ${g.id}`);
    let route=classes.size===1?[...classes][0]:null;
    if(!route){
      const t=String(g.type||'').toLowerCase();
      if(/water|pocket/.test(t)||g.destination==='nearest_revised_shoreline'||['ordinary-nearshore-band','isolated-water-without-geographic-support'].includes(g.review_reason))route='water';
      else if(/island|archipelago|mainland/.test(t)&&CONTINENT_ORDER.includes(g.destination))route='land';
    }
    if(route==='land')landGroups.add(g.id);
    else if(route==='water')waterGroups.add(g.id);
    else throw Error(`Unroutable canonical exception group ${g.id} (type=${g.type||'missing'}, destination=${g.destination||'missing'}); refusing to omit it from review lists`);
    if(!Array.isArray(g.members)||!g.members.length)throw Error(`Canonical exception group has no members: ${g.id}`);
  }
  const lists=[];
  const islands=meta.exceptions.filter(g=>landGroups.has(g.id));
  const islandContinents=[];
  for(const continent of CONTINENT_ORDER){
    const groups=islands.filter(g=>g.destination===continent);if(!groups.length)continue;
    const reasonMap=new Map();
    for(const g of groups){const bucket=data.groups.get(g.id);if(!bucket)throw Error('Missing presentation group');data.usedGroups.add(g.id);const title=bucket.title,reason=bucket.reason,key=bucket.key;let item=reasonMap.get(key);if(!item)reasonMap.set(key,item={title,reason,display_title:bucket.title,display_reason:bucket.reason,source_group_ids:[],items:[]});item.source_group_ids.push(g.id);
      for(const m of g.members){const k=JSON.stringify([g.id,m.id]),display=data.leaves.get(k);if(!display)throw Error('Missing presentation leaf');data.usedLeaves.add(k);const byId=new Map((meta.rule_records||[]).map(x=>[x.id,x])), policies=(g.ruleIds||[]).map(x=>byId.get(x)).filter(Boolean),leaf={...display,source_reason:String(g.reason||'').trim(),source_policy:policies.map(x=>x.text||'').filter(Boolean).join('\n'),source_evidence:policies.flatMap(x=>x.source_evidence||[])};item.items.push({id:m.id,source_member_id:m.id,source_group_id:g.id,name:leaf.name,geographic_group:publicIslandTitle(g),justification:leaf.justification,source_reason:leaf.source_reason,source_policy:leaf.source_policy,source_evidence:leaf.source_evidence,geographic_basis_status:leaf.geographic_basis_status,rule_ids:[...g.ruleIds],changed_cells:m.changed_cells,span_file:m.span_file});}
    }
    const reasons=[...reasonMap.values()].sort((a,b)=>cmp(a.title,b.title)||cmp(a.source_group_ids[0],b.source_group_ids[0]));
    reasons.forEach((r,ri)=>{r.number=ri+1;r.items.sort((a,b)=>cmp(a.name,b.name)||cmp(a.source_member_id,b.source_member_id));r.items.forEach((item,ii)=>{item.letter=itemLetter(ii);item.reference=reference(1,continent,r.number,item.letter);});});
    islandContinents.push({continent,reasons});
  }
  lists.push({number:1,title:'Land and island geography',continents:islandContinents});

  const waterContinents=[];
  for(const section of presentation.continents){
    const definitions=[
      {key:'named-basin-assigned-to-continent',title:'Named bounded basin assigned to a continent'},
      {key:'shared-basin-nearest-shore',title:'Shared water body · nearest revised shoreline portion'},
      {key:'ordinary-nearshore-band',title:'Coastal water following revised island geography'},{key:'isolated-water-without-geographic-support',title:'Isolated continental-water patches restored to ocean'},
      {key:'enclosed-ocean-pocket-filled',title:'Closed water pockets surrounded by continental water'}
    ];
    const reasons=[];
    const sourceByMember=new Map(meta.exceptions.flatMap(g=>g.members.map(m=>[m.id,{group:g,member:m}])));
    for(const def of definitions){const items=section.items.filter(i=>i.review_reason===def.key).sort((a,b)=>cmp(a.name,b.name)||cmp(a.source_member_id,b.source_member_id));if(!items.length)continue;
      const number=reasons.length+1;
      const leaves=items.map((item,index)=>{
        const source=sourceByMember.get(item.source_member_id);
        if(!source||source.group.id!==item.source_group_id)throw Error(`Missing water source justification ${item.source_member_id}`);
        const letter=itemLetter(index),ref=reference(2,section.continent,number,letter);
        return {id:item.id,source_member_id:item.source_member_id,source_group_id:item.source_group_id,name:item.name,changed_cells:item.changed_cells,continent_id:item.continent_id,span_file:item.span_file,source_title:source.group.title,source_destination:source.group.destination,source_reason:source.group.reason,justification:`${source.group.reason} Source group: ${source.group.title} → ${source.group.destination}.`,source_evidence:source.group.source_evidence||[],source_policy:source.group.assignment_method||'',letter,reference:ref};
      });
      items.forEach((item,index)=>{item.reason_number=number;item.item_letter=leaves[index].letter;item.reference=leaves[index].reference;});
      reasons.push({number,title:def.title,key:def.key,items:leaves});
    }
    if(reasons.length)waterContinents.push({continent:section.continent,reasons});
  }
  lists.push({number:2,title:'Continental and ocean water',continents:waterContinents});










  consolidateLandList1(lists[0]);
  consolidateWaterList2(lists[1],presentation);
  const displayedLand=new Set(lists[0].continents.flatMap(c=>c.reasons.flatMap(r=>r.items.map(x=>`${x.source_group_id}\u0000${x.source_member_id}`))));
  const expectedLand=new Set(meta.exceptions.filter(g=>landGroups.has(g.id)).flatMap(g=>g.members.map(m=>`${g.id}\u0000${m.id}`)));
  const displaySources=new Set([...presentation.continents.flatMap(c=>c.items.map(x=>`${x.source_group_id}\u0000${x.source_member_id}`)),...(presentation.ocean_items||[]).map(x=>`${x.source_group_id}\u0000${x.source_member_id}`)]);
  const expectedWater=new Set(meta.exceptions.filter(g=>waterGroups.has(g.id)).flatMap(g=>g.members.map(m=>`${g.id}\u0000${m.id}`)));
  const referenceSources=new Set([...lists[1].continents.flatMap(c=>c.reasons.flatMap(r=>r.items.map(x=>`${x.source_group_id}\u0000${x.source_member_id}`))),...(lists[1].ocean_boundaries?.items||[]).map(x=>`${x.source_group_id}\u0000${x.source_member_id}`)]);
  const same=(a,b)=>a.size===b.size&&[...a].every(x=>b.has(x));
  if(!same(displayedLand,expectedLand))throw Error('List 1 canonical exception membership mismatch; refusing to generate incomplete references');
  if(!same(displaySources,expectedWater))throw Error('Water presentation omits or duplicates canonical water source members');
  if(!same(referenceSources,expectedWater))throw Error('List 2 references omit or duplicate canonical water source members');
  const allContinents=new Set(CONTINENT_ORDER);
  for(const [n,list] of lists.entries()){
    const present=new Set(list.continents.map(c=>c.continent));
    if(!same(present,allContinents))throw Error(`List ${n+1} must contain all six continents`);
  }
  if(data.usedGroups.size!==data.groups.size||data.usedLeaves.size!==data.leaves.size)throw Error('Unused presentation record');
  return {schema_version:'worldatlas-review-reference-index-v1',source,lists};
}

// Validate a persisted stable reference index against the deterministic set of
// current leaves while allowing existing reason numbers/item letters to remain
// stable when new reviewed exceptions are added. Dataset hashes remain bound
// separately through `source`; semantic leaf fields must still match exactly.
export function validateReferenceIndex(actual,expected){
  if(!actual||actual.schema_version!==expected.schema_version||canonical(actual.source)!==canonical(expected.source))return false;
  if(!Array.isArray(actual.lists)||actual.lists.length!==expected.lists.length)return false;
  for(let li=0;li<expected.lists.length;li++){
    const a=actual.lists[li],e=expected.lists[li];
    if(a.number!==e.number||a.title!==e.title||!Array.isArray(a.continents)||a.continents.length!==e.continents.length)return false;
    const actualContinents=new Map(a.continents.map(c=>[c.continent,c]));
    for(const ec of e.continents){
      const ac=actualContinents.get(ec.continent);if(!ac||!Array.isArray(ac.reasons)||ac.reasons.length!==ec.reasons.length)return false;
      const reasonKey=r=>JSON.stringify([r.title,r.reason,r.key]);
      const ar=new Map(ac.reasons.map(r=>[reasonKey(r),r]));
      if(ar.size!==ec.reasons.length)return false;
      const reasonNumbers=new Set();
      for(const er of ec.reasons){
        const r=ar.get(reasonKey(er));if(!r||!Array.isArray(r.items)||r.items.length!==er.items.length||!Number.isInteger(r.number)||r.number<1||reasonNumbers.has(r.number))return false;
        reasonNumbers.add(r.number);
        if(canonical(Object.keys(r).sort())!==canonical(Object.keys(er).sort()))return false;
        for(const field of Object.keys(er))if(field!=='number'&&field!=='items'&&canonical(r[field])!==canonical(er[field]))return false;
        const itemKey=x=>li===0?String(x.source_member_id):String(x.id);
        const ai=new Map(r.items.map(x=>[itemKey(x),x]));if(ai.size!==er.items.length)return false;
        const letters=new Set();
        for(const ei of er.items){
          const item=ai.get(itemKey(ei));if(!item||!/^[a-z]+$/.test(item.letter||'')||letters.has(item.letter))return false;
          if(canonical(Object.keys(item).sort())!==canonical(Object.keys(ei).sort()))return false;
          letters.add(item.letter);
          const expectedRef=`List ${a.number} · ${ec.continent} · Reason ${r.number} · Item ${item.letter}`;
          if(item.reference!==expectedRef)return false;
          for(const field of Object.keys(ei))if(field!=='letter'&&field!=='reference'&&canonical(item[field])!==canonical(ei[field]))return false;
        }
      }
    }
  }
  const actualList2=actual.lists.find(x=>x.number===2),expectedList2=expected.lists.find(x=>x.number===2);
      const ao=actualList2?.ocean_boundaries,eo=expectedList2?.ocean_boundaries;
      if(Boolean(ao)!==Boolean(eo))return false;
      if(eo){
        if(canonical(Object.keys(ao).sort())!==canonical(Object.keys(eo).sort()))return false;
        for(const field of Object.keys(eo))if(field!=='items'&&canonical(ao[field])!==canonical(eo[field]))return false;
        if(!Array.isArray(ao.items)||ao.items.length!==eo.items.length)return false;
        const ai=new Map(ao.items.map(x=>[String(x.id),x]));if(ai.size!==eo.items.length)return false;const letters=new Set();
        for(const expectedItem of eo.items){
          const item=ai.get(String(expectedItem.id));if(!item||!/^[a-z]+$/.test(item.letter||'')||letters.has(item.letter))return false;letters.add(item.letter);
          if(canonical(Object.keys(item).sort())!==canonical(Object.keys(expectedItem).sort()))return false;
          if(item.reference!==`List 2 · Ocean boundaries · Water-assignment corrections · Item ${item.letter}`)return false;
          if('continent_id' in item||'continent_id' in expectedItem)return false;
          for(const field of Object.keys(expectedItem))if(field!=='letter'&&field!=='reference'&&canonical(item[field])!==canonical(expectedItem[field]))return false;
        }
      }
  return true;
}

function canonical(x){
  if(Array.isArray(x))return `[${x.map(canonical).join(',')}]`;
  if(x&&typeof x==='object')return `{${Object.keys(x).sort().map(k=>`${JSON.stringify(k)}:${canonical(x[k])}`).join(',')}}`;
  return JSON.stringify(x);
}
