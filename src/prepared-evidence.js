import {validYear,ranks} from './model.js';
const dateOK=y=>validYear(y)||y===2027;
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
export const preparedEvidenceJSON=v=>JSON.stringify(canonical(v));
export function validatePreparedEvidenceIndex(index,expected={}){
 if(index?.version!==1||!Array.isArray(index.parts)||!Array.isArray(index.sources))throw Error('Invalid prepared evidence manifest');
 for(const key of ['footprints_sha256','hierarchy_sha256']){if(!/^[a-f0-9]{64}$/.test(index[key]))throw Error(`Missing evidence ${key}`);if(expected[key]&&index[key]!==expected[key])throw Error(`Stale prepared evidence ${key}`);}
 const sources=new Map();for(const s of index.sources){if(sources.has(s.id))throw Error('Duplicate prepared source identity');if(typeof s.id!=='string'||!s.id.trim()||!s.name||!s.license||!s.vintage||!['historical','reference','estimate','example'].includes(s.status)||s.metadata!=null&&(typeof s.metadata!=='object'||Array.isArray(s.metadata)))throw Error('Invalid prepared source provenance');if(s.url!=null){let url;try{url=new URL(s.url);}catch{throw Error('Invalid prepared source URL');}if(!['https:','http:'].includes(url.protocol))throw Error('Invalid prepared source URL');}if(!dateOK(s.supported_from)||!dateOK(s.supported_to)||s.supported_from>=s.supported_to)throw Error('Invalid prepared source interval');sources.set(s.id,s);}
 const paths=new Set();for(const p of index.parts){if(paths.has(p.path)||!/^part-\d+\.json\.gz$/.test(p.path)||!['records','names'].includes(p.kind)||!dateOK(p.valid_from)||!dateOK(p.valid_to)||p.valid_from>=p.valid_to||!Number.isSafeInteger(p.records)||p.records<1||!/^[a-f0-9]{64}$/.test(p.sha256)||!/^[a-f0-9]{64}$/.test(p.decoded_sha256))throw Error('Invalid prepared evidence part');paths.add(p.path);}
 return sources;
}
export async function verifyPreparedEvidenceIndexBytes(bytes,expected={}){
 if(expected.index_sha256){const hash=await crypto.subtle.digest('SHA-256',bytes);if([...new Uint8Array(hash)].map(b=>b.toString(16).padStart(2,'0')).join('')!==expected.index_sha256)throw Error('Prepared evidence index hash mismatch');}
 const index=JSON.parse(new TextDecoder().decode(bytes));validatePreparedEvidenceIndex(index,expected);return index;
}
export function preparedEvidencePartsAt(index,year){if(!validYear(year))throw Error('Invalid selected year');validatePreparedEvidenceIndex(index);return index.parts.filter(p=>p.valid_from<=year&&year<p.valid_to);}
export function normalizePreparedEvidence(row,kind,sources){
 const source=sources.get(row.source_id);if(!source)throw Error(`Unknown prepared source: ${row.source_id}`);
 if(!dateOK(row.valid_from)||!dateOK(row.valid_to)||row.valid_from>=row.valid_to||row.valid_from<source.supported_from||row.valid_to>source.supported_to)throw Error(`Prepared evidence exceeds supported source interval: ${row.id}`);
 if(!row.id||typeof row.id!=='string'||!row.id.trim()||row.metadata!=null&&(typeof row.metadata!=='object'||Array.isArray(row.metadata))||![0,1].includes(row.is_example??0)||source.status==='example'&&!row.is_example)throw Error('Invalid prepared evidence identity/example status');
 const provenance={source:source.name,source_url:source.url,source_license:source.license,source_vintage:source.vintage,source_from:source.supported_from,source_to:source.supported_to,source_status:source.status,source_metadata:source.metadata??{}};
 if(kind==='names'){if(!row.entity_id||typeof row.name!=='string'||!row.name.trim()||!['preferred','alias'].includes(row.role??'preferred'))throw Error('Invalid prepared name');return {...row,metadata:row.metadata??{},...provenance,field:'name',value:row.name,name_role:row.role??'preferred',language:row.language??'und',method:source.status==='reference'?'reference':'direct',status:source.status==='reference'?'reference':'sourced',is_example:row.is_example??0};}
 if(kind!=='records'||!row.location_id||!['owner','population','culture','religion','rank','topography','vegetation','climate','habitation'].includes(row.attribute)||!Object.hasOwn(row,'value'))throw Error('Invalid prepared attribute');
 if(row.attribute==='population'&&row.value!=null&&(!Number.isSafeInteger(row.value)||row.value<0))throw Error('Invalid prepared population');
 if(row.value!=null&&row.attribute!=='population'&&(typeof row.value!=='string'||!row.value.trim()))throw Error('Invalid prepared scalar');
 if(['owner','culture','religion'].includes(row.attribute)&&((row.value!=null)!==Boolean(row.category_id)))throw Error('Prepared categorical values require a stable identity');
 if(row.attribute==='rank'&&row.value!=null&&!ranks.includes(row.value)||row.attribute==='habitation'&&row.value!=null&&!['inhabited','uninhabited','unknown'].includes(row.value))throw Error('Invalid prepared rank or habitation');
 if(!['direct','majority-area','derived','reference','estimate'].includes(row.method)||!['sourced','derived','reference','estimate','unknown','disputed','no-majority','example'].includes(row.status))throw Error('Invalid prepared evidence method/status');
 if(source.status==='estimate'&&row.method!=='estimate'||source.status==='reference'&&row.method!=='reference')throw Error('Prepared source class does not match evidence method');
 return {...row,metadata:row.metadata??{},...provenance,is_example:row.is_example??0};
}
export async function verifyPreparedEvidencePart(part,rows){
 if(!Array.isArray(rows)||rows.length!==part.records)throw Error('Prepared evidence part count mismatch');
 const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(preparedEvidenceJSON(rows)));
 if([...new Uint8Array(hash)].map(b=>b.toString(16).padStart(2,'0')).join('')!==part.decoded_sha256)throw Error(`Prepared evidence content hash mismatch: ${part.path}`);
}
export function selectPreparedEvidence(index,parts,year,{examples=false,expected={}}={}){
 if(!validYear(year))throw Error('Invalid selected year');const sources=validatePreparedEvidenceIndex(index,expected),out={records:[],names:[]},seen=new Map();
 for(const part of parts){const meta=index.parts.find(p=>p.path===part.path);if(!meta)throw Error('Unlisted prepared evidence part');if(meta.valid_from>year||year>=meta.valid_to)continue;if(part.rows.length!==meta.records)throw Error('Prepared evidence part count mismatch');for(const raw of part.rows){const row=normalizePreparedEvidence(raw,meta.kind,sources);if(row.valid_from!==meta.valid_from||row.valid_to!==meta.valid_to)throw Error('Prepared part interval mismatch');const key=`${meta.kind}:${row.id}`,value=preparedEvidenceJSON(row);if(seen.has(key)){if(seen.get(key)!==value)throw Error('Conflicting prepared evidence identity');continue;}seen.set(key,value);if(!row.is_example||examples)out[meta.kind].push(row);}}
 return out;
}
export function mergePreparedEvidence(records=[],names=[],prepared={records:[],names:[]},{retirements=[]}={}){
 const merge=(first,second,kind)=>{
  const retired=new Set(retirements.filter(r=>r.collection===kind).map(r=>r.target_id)),fallback=new Map(second.map(r=>[r.id,r])),ids=new Set();
  const result=first.filter(r=>!retired.has(r.id)).map(r=>{ids.add(r.id);return {...fallback.get(r.id),...r};});
  return [...result,...second.filter(r=>!ids.has(r.id)&&!retired.has(r.id))];
 };
 return {records:merge(records,prepared.records,'records'),names:merge(names,prepared.names,'names')};
}

