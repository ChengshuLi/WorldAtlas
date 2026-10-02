import {validYear,formatYear,ranks} from './model.js';
import {requireEnvironmentalClassification,environmentClassifications} from './environment-classifications.js';
import {locationAttributes,unresolvedAttributeStatuses} from './attributes.js';
const collections=new Set(['sources','entity_types','entities','categories','records','names','relationships','media_links','units','attribute_entities','attribute_records','retirements']);
const aliases={units:'entities',attribute_entities:'categories',attribute_records:'records'};
const text=(value,label)=>{if(typeof value!=='string'||!value.trim())throw Error(`${label} must be nonempty text.`);};
function interval(from,to,label,optional=false){
 if(optional&&from==null&&to==null)return;
 if(!validYear(from)||!(validYear(to)||to===2027)||to<=from)throw Error(`${label}: use an included start year and an excluded end year between 3000 BC and 2026 AD, with 2027 allowed as the end. There is no year zero.`);
}
export function previewImport(raw){
 if(new TextEncoder().encode(raw).length>1024*1024)throw Error('Choose a JSON batch no larger than 1 MiB.');
 let payload;try{payload=JSON.parse(raw);}catch{throw Error('The records must be valid JSON.');}
 if(!payload||typeof payload!=='object'||Array.isArray(payload))throw Error('Use a JSON object containing record collections.');
 const counts={},rows=[],ids=new Map(),sources=new Map();
 for(const [key,list] of Object.entries(payload)){
  if(key==='ingestion_id'){text(list,'Import ID');continue;}
  if(!collections.has(key)||!Array.isArray(list))throw Error(`Unsupported collection: ${key}.`);
  const kind=aliases[key]||key;counts[kind]=(counts[kind]||0)+list.length;
  for(const row of list){
   if(!row||typeof row!=='object'||Array.isArray(row))throw Error(`Each ${key} row must be an object.`);
   text(row.id,'Stable record ID');const keyId=`${kind}/${row.id}`;if(ids.has(keyId))throw Error(`Duplicate ${kind} ID: ${row.id}.`);ids.set(keyId,true);
   if(kind==='sources'){
    text(row.name,'Source title');text(row.license,'Source license');text(String(row.vintage??''),'Source vintage');
    interval(row.supported_from??row.valid_from,row.supported_to??row.valid_to,'Source interval');
    if(!['historical','reference','estimate','example'].includes(row.status))throw Error('Sources must declare historical, reference, estimate or example status.');
    sources.set(row.id,row);
   }else if(!['entities','entity_types'].includes(kind))text(row.source_id,'Source ID');
   if(kind==='records'){
    text(row.location_id,'Location ID');if(!locationAttributes.includes(row.attribute)||!Object.hasOwn(row,'value'))throw Error('Each attribute record needs a known attribute and one value, or null for unknown.');
    interval(row.valid_from,row.valid_to,'Attribute interval');
    if(unresolvedAttributeStatuses.includes(row.status)&&(row.value!==null||row.category_id!=null))throw Error('Unresolved attribute status requires null value and category_id.');
    if(row.value!=null){
     if(row.attribute==='population'){if(!Number.isSafeInteger(row.value)||row.value<0)throw Error('Population must be a nonnegative whole number.');}
     else text(row.value,'Attribute value');
     requireEnvironmentalClassification(row.attribute,row.value);
     if(['owner','culture','religion'].includes(row.attribute))text(row.category_id,'Stable category ID');
     if(row.attribute==='rank'&&!ranks.includes(row.value))throw Error('Rank must be unsettled, rural settlement, town, city or metropolis.');
     if(row.attribute==='habitation'&&!['inhabited','uninhabited','unknown'].includes(row.value))throw Error('Habitation must be inhabited, uninhabited or unknown.');
    }
   }
   if(kind==='retirements'){
    if(!['records','names','relationships','media_links'].includes(row.collection))throw Error('Corrections must identify records, names, relationships or media_links.');
    text(row.target_id,'Existing evidence ID');text(row.reason,'Correction reason');if(row.replacement_id!=null)text(row.replacement_id,'Replacement evidence ID');
   }
   if(kind==='names'){text(row.entity_id,'Entity ID');text(row.name,'Dated name');interval(row.valid_from,row.valid_to,'Name interval');}
   if(['relationships','media_links'].includes(kind))interval(row.valid_from,row.valid_to,'Relationship interval',true);
   rows.push({kind,id:row.id,subject:row.target_id??row.location_id??row.entity_id??row.source_entity_id??row.name??row.id,attribute:row.attribute??(kind==='names'?'dated name':kind==='retirements'?'evidence correction':kind),value:kind==='retirements'?(row.replacement_id?`supersede with ${row.replacement_id}`:'withdraw'):kind==='records'?row.value:row.name??row.relationship_type??null,from:row.valid_from??row.supported_from,to:row.valid_to??row.supported_to,source:row.source_id??(kind==='sources'?row.id:null)});
  }
 }
 if(!rows.length||rows.length>250)throw Error('Each batch must contain 1–250 rows, including source and identity definitions.');
 for(const [key,list] of Object.entries(payload))if(['records','attribute_records','names'].includes(key))for(const row of list){
  const source=sources.get(row.source_id);if(source&&((source.supported_from??source.valid_from)>row.valid_from||(source.supported_to??source.valid_to)<row.valid_to))throw Error(`Record ${row.id} extends beyond its source’s supported interval.`);
 }
 return {payload,counts,rows};
}
export async function submitImport(payload,fetcher=fetch){
 const response=await fetcher('/api/records/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
 let result;try{result=await response.json();}catch{throw Error('The database did not return an import result. Please retry.');}
 if(!response.ok)throw Error(result.error||'The database rejected these records.');
 return result;
}
export function installRecordImport({getContext,refresh,enabled=import.meta.env.VITE_HOSTED_DATABASE==='true'}){
 if(!enabled)return;
 const button=document.createElement('button');button.id='import-records-button';button.className='quiet';button.textContent='Add historical records';document.querySelector('header').classList.add('has-record-import');document.querySelector('header').insertBefore(button,document.querySelector('#about'));
 const dialog=document.createElement('dialog');dialog.id='import-records-dialog';dialog.className='coverage-dialog';
 dialog.innerHTML='<button class="dialog-close" aria-label="Close historical record import">×</button><div class="eyebrow">ADD EVIDENCE</div><h2>Import historical records</h2><p>Upload or paste sourced attributes, dated names or relationships. Existing identities and evidence are retained. Source-backed corrections can withdraw or supersede earlier evidence without deleting it. Each batch accepts up to 250 rows and 1 MiB.</p><p id="import-records-context"></p><label for="import-records-file">Choose a JSON file</label><input id="import-records-file" type="file" accept=".json,application/json"><label for="import-records-json">JSON records</label><textarea id="import-records-json" rows="12" style="display:block;width:100%;box-sizing:border-box;font:13px monospace" spellcheck="false"></textarea><details><summary>Record format</summary><p>Use stable IDs and cite a source with its license, vintage and supported interval. Start years are included; end years are excluded. Negative years mean BC. There is no year zero. Replace the source placeholders before importing.</p><pre id="import-records-format" style="overflow:auto;max-height:240px"></pre></details><button id="import-records-review">Review records</button><div id="import-records-preview"></div><p id="import-records-status" role="status" aria-live="polite"></p><button id="import-records-submit" disabled>Import reviewed records</button>';
 document.body.append(dialog);const textarea=dialog.querySelector('textarea'),file=dialog.querySelector('input[type=file]'),review=dialog.querySelector('#import-records-review'),submit=dialog.querySelector('#import-records-submit'),status=dialog.querySelector('#import-records-status'),preview=dialog.querySelector('#import-records-preview');let checked;
 const classifications=document.createElement('details'),summary=document.createElement('summary'),explanation=document.createElement('p');
 summary.textContent='Fixed environmental classifications';explanation.textContent='Use one listed ID for topography, vegetation or climate. Use null when unknown. Original source descriptions belong in evidence metadata.';
 classifications.append(summary,explanation);
 for(const [attribute,entries]of Object.entries(environmentClassifications)){
  const heading=document.createElement('p'),list=document.createElement('pre');heading.textContent=attribute[0].toUpperCase()+attribute.slice(1);
  list.style.cssText='overflow:auto;max-height:200px;font-size:12px';list.textContent=entries.map(entry=>`${entry.id} — ${entry.label}`).join('\n');classifications.append(heading,list);
 }
 dialog.querySelector('#import-records-review').before(classifications);
 const reset=()=>{checked=null;submit.disabled=true;preview.replaceChildren();status.textContent='';};
 textarea.addEventListener('input',reset);
 file.addEventListener('change',async()=>{reset();const selected=file.files[0];if(!selected)return;if(selected.size>1024*1024){status.textContent='Choose a JSON batch no larger than 1 MiB.';return;}try{textarea.value=await selected.text();}catch{status.textContent='The file could not be read.';}});
 dialog.querySelector('.dialog-close').onclick=()=>dialog.close();
 button.onclick=()=>{
  const {year,selected,feature}=getContext(),end=year===-1?1:year+1;
  dialog.querySelector('#import-records-context').textContent=`Current view: ${formatYear(year)}${selected?` · ${feature?.properties.name||'Selected territory'} · location ID: ${selected}`:''}. Records appear only in their supported years.`;
  dialog.querySelector('#import-records-format').textContent=JSON.stringify({sources:[{id:'source:replace-with-id',name:'Replace with source title',url:'https://example.org/replace-with-source',license:'Replace with source license',vintage:'Replace with source vintage',supported_from:year,supported_to:end,status:'historical'}],records:[{id:'record:replace-with-id',location_id:selected||'Replace with location ID',attribute:'population',value:null,valid_from:year,valid_to:end,source_id:'source:replace-with-id',method:'direct'}]},null,2);
  dialog.showModal();
 };
 review.onclick=()=>{reset();try{
  checked=previewImport(textarea.value);
  const heading=document.createElement('p');heading.textContent=`${checked.rows.length} rows ready for database validation: ${Object.entries(checked.counts).map(([kind,count])=>`${count} ${kind}`).join(', ')}.`;preview.append(heading);
  const list=document.createElement('div');list.style.maxHeight='240px';list.style.overflow='auto';
  for(const row of checked.rows.slice(0,30)){const line=document.createElement('p');line.textContent=`${row.subject} · ${row.attribute} · ${row.value==null?'unknown':row.value}${row.from!=null?` · ${formatYear(row.from)} to before ${formatYear(row.to)}`:''}${row.source?` · source: ${row.source}`:''}`;list.append(line);}
  if(checked.rows.length>30){const note=document.createElement('p');note.textContent=`${checked.rows.length-30} additional rows included.`;list.append(note);}preview.append(list);submit.disabled=false;
  status.textContent='Source references, existing IDs, overlap and date constraints are checked by the database when you import.';
 }catch(error){status.textContent=error.message;}};
 submit.onclick=async()=>{
  if(!checked)return;submit.disabled=true;review.disabled=true;textarea.disabled=true;file.disabled=true;status.textContent='Saving sourced records…';
  try{
   const result=await submitImport(checked.payload);status.textContent=result.duplicate?'This identical evidence was already saved.':'Records saved.';
   try{await refresh();status.textContent+=' The selected year has been refreshed.';}catch{status.textContent+=' The map could not refresh. Select the year again to reload it.';}
   checked=null;
  }catch(error){status.textContent=error.message;submit.disabled=false;}
  finally{review.disabled=false;textarea.disabled=false;file.disabled=false;}
 };
}
