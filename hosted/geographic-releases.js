/** Immutable geographic identities plus separately published reference memberships.
 * None of these rows asserts geographic membership at a historical year.
 */
export class GeographicReleaseError extends Error{constructor(message,status=400){super(message);this.status=status;}}
const fail=(message,status=400)=>{throw new GeographicReleaseError(message,status);};
const tiers=['location','province','area','region','subcontinent','continent'];
const text=(value,label)=>{if(typeof value!=='string'||!value.trim()||value.length>2000)fail(`Invalid ${label}`);return value;};
const object=(value={})=>{if(!value||typeof value!=='object'||Array.isArray(value))fail('Expected an evidence/metadata object');if(JSON.stringify(value).length>16384)fail('Evidence/metadata exceeds 16 KiB');return value;};
const canonical=value=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])])):value;
const json=value=>JSON.stringify(canonical(value));
const digest=value=>{if(typeof value!=='string'||!/^[0-9a-f]{64}$/.test(value))fail('Expected a SHA-256 digest');return value;};
const rows=async statement=>(await statement.all()).results||[];
const first=statement=>statement.first();
const clean=row=>row?Object.fromEntries(Object.entries(row).map(([k,v])=>[k,['metadata','expected_counts','evidence','counts'].includes(k)&&typeof v==='string'?JSON.parse(v):v])):null;
async function hash(value){const result=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(json(value)));return [...new Uint8Array(result)].map(v=>v.toString(16).padStart(2,'0')).join('');}
// Match SQLite's binary UTF-8 ordering, including non-BMP stable identifiers.
const binaryCompare=(a,b)=>{const aa=Array.from(a),bb=Array.from(b);for(let i=0;i<Math.min(aa.length,bb.length);i++){const delta=aa[i].codePointAt(0)-bb[i].codePointAt(0);if(delta)return delta;}return aa.length-bb.length;};
const hashMember=r=>({entity_id:r.entity_id??r.id,kind:r.kind??r.level,parent_id:r.parent_id??null,reference_name:r.reference_name??null,active:r.active??1,source_id:r.source_id,evidence:object(typeof r.evidence==='string'?JSON.parse(r.evidence):r.evidence??{})});
const hashChange=r=>({id:r.id,old_entity_id:r.old_entity_id??null,new_entity_id:r.new_entity_id??null,change_type:r.change_type,source_id:r.source_id,evidence:object(typeof r.evidence==='string'?JSON.parse(r.evidence):r.evidence??{})});
async function streamedArrayHash(iterable,transform){
 const encoder=new TextEncoder(),stream=typeof crypto.DigestStream==='function'?new crypto.DigestStream('SHA-256'):null,writer=stream?.getWriter(),pieces=[];
 const write=async value=>{const bytes=encoder.encode(value);if(writer)await writer.write(bytes);else pieces.push(bytes);};
 await write('[');let comma='';for await(const row of iterable){await write(comma+json(transform(row)));comma=',';}await write(']');
 let result;if(writer){await writer.close();result=await stream.digest;}else{const bytes=new Uint8Array(pieces.reduce((n,p)=>n+p.length,0));let offset=0;for(const piece of pieces){bytes.set(piece,offset);offset+=piece.length;}result=await crypto.subtle.digest('SHA-256',bytes);}
 return [...new Uint8Array(result)].map(v=>v.toString(16).padStart(2,'0')).join('');
}
const memberFields=['release_id','entity_id','parent_id','reference_name','active','source_id','evidence'];
const releaseFields=['id','source_id','version','reference_date','status','hierarchy_sha256','footprints_sha256','membership_sha256','location_ids_sha256','changes_sha256','expected_counts','metadata','published_at'];
const changeFields=['id','release_id','old_entity_id','new_entity_id','change_type','source_id','evidence'];
function member(row,release){return {release_id:release.id,entity_id:text(row.entity_id??row.id,'entity ID'),parent_id:row.parent_id==null?null:text(row.parent_id,'parent ID'),reference_name:row.reference_name==null?null:text(row.reference_name,'reference name'),active:row.active??1,source_id:text(row.source_id??release.source_id,'source ID'),evidence:object(row.evidence??{})};}
function change(row,release){
 const result={id:text(row.id,'change ID'),release_id:release.id,old_entity_id:row.old_entity_id==null?null:text(row.old_entity_id,'old entity ID'),new_entity_id:row.new_entity_id==null?null:text(row.new_entity_id,'new entity ID'),change_type:text(row.change_type,'change type'),source_id:text(row.source_id??release.source_id,'source ID'),evidence:object(row.evidence)};
 const creation=result.evidence.geometry_creation;if(creation){const proof=creation.creation_proof,source=proof?.source;
  if(result.change_type!=='create'||result.old_entity_id!==null||creation.old_entity_id!==null||creation.new_entity_id!==result.new_entity_id||proof?.location_id!==result.new_entity_id||creation.history_transfer!=='none')fail('Invalid source-backed creation endpoints/history');
  if(!source||!/^https?:\/\//.test(source.url??''))fail('Creation requires source evidence');digest(source.sha256);text(source.identity,'source identity');text(source.license,'source license');text(source.attribution,'source attribution');
  if(!Number.isSafeInteger(source.supported_from)||!Number.isSafeInteger(source.supported_to)||source.supported_from===0||source.supported_to===0||source.supported_from>=source.supported_to||source.supported_from< -3000||source.supported_to>2027)fail('Invalid creation source interval');
  if(!Array.isArray(proof.parent_chain)||proof.parent_chain.length!==5||new Set(proof.parent_chain).size!==5)fail('Invalid creation parent chain');for(const id of proof.parent_chain)text(id,'creation parent ID');
 }
 return result;
}
export async function geographicMembershipHash(input){return hash(input.map(hashMember).sort((a,b)=>binaryCompare(a.entity_id,b.entity_id)));}
export async function geographicLocationIdsHash(input){return hash(input.filter(r=>(r.active??1)===1&&(r.kind??r.level)==='location').map(r=>r.entity_id??r.id).sort(binaryCompare));}
export async function geographicChangesHash(input){return hash(input.map(hashChange).sort((a,b)=>binaryCompare(a.id,b.id)));}
async function normalizeRelease(row){
 const expected=object(row.expected_counts);if(Object.keys(expected).length!==6||tiers.some(k=>!Number.isSafeInteger(expected[k])||expected[k]<0)||expected.continent!==6)fail('Manifest must specify all six tier counts and six continents');
 if(!Number.isSafeInteger(row.version)||row.version<1)fail('Release version must be a positive safe integer');
 text(row.reference_date,'reference date label');const calendarDate=new Date(row.reference_date+'T00:00:00Z');if(!/^\d{4}-\d{2}-\d{2}$/.test(row.reference_date)||Number.isNaN(calendarDate.getTime())||calendarDate.toISOString().slice(0,10)!==row.reference_date)fail('Reference date must be an ISO calendar date, not a historical interval');
 return {id:text(row.id,'release ID'),source_id:text(row.source_id,'release source'),version:row.version,reference_date:row.reference_date,status:'staged',hierarchy_sha256:digest(row.hierarchy_sha256),footprints_sha256:digest(row.footprints_sha256),membership_sha256:digest(row.membership_sha256),location_ids_sha256:digest(row.location_ids_sha256),changes_sha256:digest(row.changes_sha256??await geographicChangesHash([])),expected_counts:expected,metadata:object(row.metadata??{}),published_at:null};
}
function insert(db,table,fields,row){return db.prepare(`INSERT INTO ${table}(${fields.join(',')}) VALUES(${fields.map(()=>'?').join(',')}) ON CONFLICT DO NOTHING`).bind(...fields.map(k=>['evidence','metadata','expected_counts'].includes(k)?json(row[k]):row[k]));}
export async function geographicRelease(db,id=null,{includeStaged=false}={}){
 if(id!=null)text(id,'release ID');
 return clean(await first(id!=null?db.prepare(`SELECT * FROM atlas_geographic_releases WHERE id=?${includeStaged?'':" AND status='published'"}`).bind(id):db.prepare("SELECT * FROM atlas_geographic_releases WHERE status='published' ORDER BY version DESC LIMIT 1")));
}
export async function stageGeographicRelease(db,payload){
 if(!payload||typeof payload!=='object'||Array.isArray(payload))fail('Expected a release import object');
 const inputMembers=payload.memberships??[],inputChanges=payload.changes??[];if(!Array.isArray(inputMembers)||!Array.isArray(inputChanges))fail('Release rows must be arrays');
 if(inputMembers.length+inputChanges.length+Number(Boolean(payload.release))>250)fail('At most 250 release input rows per atomic batch');if(new TextEncoder().encode(JSON.stringify(payload)).length>1048576)fail('Release import exceeds 1 MiB',413);
 let release=payload.release?await normalizeRelease(payload.release):await geographicRelease(db,text(payload.release_id,'release ID'),{includeStaged:true});if(!release)fail('Unknown staged release',404);
 if(payload.release_id!=null&&payload.release_id!==release.id)fail('Conflicting release IDs');
 const memberships=inputMembers.map(row=>member(row,release)),changes=inputChanges.map(row=>change(row,release));
 if(memberships.some(r=>![0,1].includes(r.active)))fail('Membership active must be 0 or 1');
 for(const collection of [memberships.map(r=>r.entity_id),changes.map(r=>r.id)])if(new Set(collection).size!==collection.length)fail('Duplicate release row identity in batch');
 const fingerprint=await hash({release:payload.release?release:null,release_id:release.id,memberships,changes}),id=text(payload.ingestion_id??`geographic:${release.id}:${fingerprint}`,'ingestion ID');
 const receipt=clean(await first(db.prepare('SELECT * FROM atlas_ingestions WHERE id=?').bind(id)));if(receipt){if(receipt.fingerprint!==fingerprint)fail('Ingestion ID already identifies different release input',409);return {...receipt,duplicate:true};}
 const prior=await geographicRelease(db,release.id,{includeStaged:true});if(prior?.status==='published')fail('Published geographic releases are immutable; stage a new version',409);
 const statements=[];if(payload.release)statements.push(insert(db,'atlas_geographic_releases',releaseFields,release));
 for(const row of memberships)statements.push(insert(db,'atlas_geographic_memberships',memberFields,row));for(const row of changes)statements.push(insert(db,'atlas_geographic_changes',changeFields,row));
 const counts={geographic_release_id:release.id,memberships:memberships.length,changes:changes.length};statements.push(db.prepare('INSERT INTO atlas_ingestions(id,fingerprint,counts,created_at) VALUES(?,?,?,?)').bind(id,fingerprint,json(counts),Date.now()));
 try{await db.batch(statements);}catch(error){fail(error.message,409);}return {id,fingerprint,counts,duplicate:false};
}
async function* memberRows(db,id,locationsOnly=false){let cursor='';for(;;){const part=await rows(db.prepare(`SELECT m.*,e.kind FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id WHERE m.release_id=? AND m.entity_id>? ${locationsOnly?"AND m.active=1 AND e.kind='location'":''} ORDER BY m.entity_id LIMIT 500`).bind(id,cursor));for(const row of part)yield clean(row);if(part.length<500)return;cursor=part.at(-1).entity_id;}}
async function* changeRows(db,id){let cursor='';for(;;){const part=await rows(db.prepare('SELECT * FROM atlas_geographic_changes WHERE release_id=? AND id>? ORDER BY id LIMIT 500').bind(id,cursor));for(const row of part)yield clean(row);if(part.length<500)return;cursor=part.at(-1).id;}}
export async function finalizeGeographicRelease(db,id){
 text(id,'release ID');const release=await geographicRelease(db,id,{includeStaged:true});if(!release)fail('Unknown geographic release',404);if(release.status==='published')return {...release,duplicate:true};
 const nodeTotal=(await first(db.prepare('SELECT count(*) n FROM atlas_geographic_memberships WHERE release_id=?').bind(id))).n,changeTotal=(await first(db.prepare('SELECT count(*) n FROM atlas_geographic_changes WHERE release_id=?').bind(id))).n;
 const counts=Object.fromEntries(tiers.map(k=>[k,0]));for(const row of await rows(db.prepare('SELECT e.kind,count(*) n FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id WHERE m.release_id=? AND m.active=1 GROUP BY e.kind').bind(id)))counts[row.kind]=row.n;
 if(await first(db.prepare("SELECT m.entity_id FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id LEFT JOIN atlas_geographic_memberships p ON p.release_id=m.release_id AND p.entity_id=m.parent_id AND p.active=1 WHERE m.release_id=? AND m.active=1 AND e.kind!='continent' AND p.entity_id IS NULL LIMIT 1").bind(id)))fail('Incomplete active same-release adjacent-tier parent chain');
 if(await first(db.prepare("SELECT m.entity_id FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id WHERE m.release_id=? AND m.active=1 AND e.kind!='location' AND NOT EXISTS(SELECT 1 FROM atlas_geographic_memberships c WHERE c.release_id=m.release_id AND c.parent_id=m.entity_id AND c.active=1) LIMIT 1").bind(id)))fail('Active geographic group has no member territory');
 if(tiers.some(k=>counts[k]!==release.expected_counts[k]))fail('Reference release node counts do not match pinned manifest',409);
 for await(const row of changeRows(db,id))if(row.evidence.geometry_creation){const proof=row.evidence.geometry_creation.creation_proof,chain=[row.new_entity_id,...proof.parent_chain];
  const nodes=await rows(db.prepare(`SELECT m.entity_id,m.parent_id,e.kind FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id WHERE m.release_id=? AND m.active=1 AND m.entity_id IN (${chain.map(()=>'?').join(',')})`).bind(id,...chain)),byId=new Map(nodes.map(n=>[n.entity_id,n]));
  if(chain.some((entity,index)=>byId.get(entity)?.kind!==tiers[index]||byId.get(entity)?.parent_id!==(chain[index+1]??null)))fail('Creation proof does not match the published parent chain',409);
 }
 const membershipHash=await streamedArrayHash(memberRows(db,id),hashMember),locationsHash=await streamedArrayHash(memberRows(db,id,true),r=>r.entity_id),changesHash=await streamedArrayHash(changeRows(db,id),hashChange);
 if(membershipHash!==release.membership_sha256||locationsHash!==release.location_ids_sha256||changesHash!==release.changes_sha256)fail('Reference release content hash does not match pinned manifest',409);
 // Count predicates close the staging/read race: append-only rows cannot change
 // while the single atomic publication statement performs SQL integrity checks.
 const result=await db.batch([db.prepare("UPDATE atlas_geographic_releases SET status='published',published_at=? WHERE id=? AND status='staged' AND (SELECT count(*) FROM atlas_geographic_memberships WHERE release_id=?)=? AND (SELECT count(*) FROM atlas_geographic_changes WHERE release_id=?)=?").bind(Date.now(),id,id,nodeTotal,id,changeTotal)]);
 if(!result[0]?.meta?.changes){const current=await geographicRelease(db,id,{includeStaged:true});if(current?.status==='published')return {...current,duplicate:true};fail('Release changed during verification; retry finalization',409);}
 return {...await geographicRelease(db,id),duplicate:false};
}
export async function geographicMembershipPage(db,{releaseId=null,cursor='',limit=250,active=true,parentId=null}={}){
 if(cursor)text(cursor,'cursor');limit=Math.max(1,Math.min(250,Number.isInteger(limit)?limit:250));const release=await geographicRelease(db,releaseId);if(!release)return {release:null,records:[],next_cursor:null};if(parentId!=null)text(parentId,'parent ID');
 const predicates=['m.release_id=?','m.entity_id>?'],values=[release.id,cursor];if(active!=null){predicates.push('m.active=?');values.push(Number(Boolean(active)));}if(parentId!=null){predicates.push('m.parent_id=?');values.push(parentId);}values.push(limit+1);
 const page=await rows(db.prepare(`SELECT m.*,e.kind,e.name original_reference_name,e.parent_id original_parent_id FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id WHERE ${predicates.join(' AND ')} ORDER BY m.entity_id LIMIT ?`).bind(...values));
 return {release,reference_only:true,records:page.slice(0,limit).map(clean),next_cursor:page.length>limit?page[limit-1].entity_id:null};
}
export async function referenceMembership(db,entityId,{releaseId=null}={}){
 text(entityId,'entity ID');const release=await geographicRelease(db,releaseId);if(!release)return null;
 const member=clean(await first(db.prepare('SELECT m.*,e.kind,e.name original_reference_name,e.parent_id original_parent_id,e.active original_active FROM atlas_geographic_memberships m JOIN atlas_entities e ON e.id=m.entity_id WHERE m.release_id=? AND m.entity_id=?').bind(release.id,entityId)));
 return {release,reference_only:true,membership:member?{...member,resolved_reference_name:member.reference_name??member.original_reference_name}:null};
}
export async function geographicChangePage(db,{releaseId=null,cursor='',limit=250}={}){
 if(cursor)text(cursor,'cursor');limit=Math.max(1,Math.min(250,Number.isInteger(limit)?limit:250));const release=await geographicRelease(db,releaseId);if(!release)return {release:null,records:[],next_cursor:null};
 const page=await rows(db.prepare('SELECT * FROM atlas_geographic_changes WHERE release_id=? AND id>? ORDER BY id LIMIT ?').bind(release.id,cursor,limit+1));return {release,reference_only:true,records:page.slice(0,limit).map(clean),next_cursor:page.length>limit?page[limit-1].id:null};
}
