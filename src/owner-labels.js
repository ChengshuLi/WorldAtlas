// Current owner-category names are a generated replica, never a mutable
// parallel registry. Source feature labels remain evidence, not a fallback.
export function readOwnerLabels(snapshot){
 const fail=()=>{throw Error('Invalid canonical owner-label snapshot');};
 const keys=(value,expected)=>value&&typeof value==='object'&&!Array.isArray(value)
  &&Object.keys(value).sort().join(',')===expected.split(',').sort().join(',');
 const text=value=>typeof value==='string'&&value.trim().length>0;
 const hash=value=>typeof value==='string'&&/^[0-9a-f]{64}$/.test(value);
 if(!keys(snapshot,'version,kind,revision,capture_reference,owners')||snapshot.version!==1
  ||snapshot.kind!=='neon-owner-label-replica-v1'||!Number.isSafeInteger(snapshot.revision)||snapshot.revision<0
  ||!keys(snapshot.capture_reference,'id,hierarchy_sha256,footprints_sha256')
  ||!text(snapshot.capture_reference.id)||!hash(snapshot.capture_reference.hierarchy_sha256)
  ||!hash(snapshot.capture_reference.footprints_sha256)||!Array.isArray(snapshot.owners))fail();
 const labels=new Map();
 for(const row of snapshot.owners){
  if(!keys(row,'id,kind,name,source_id')||!text(row.id)||row.kind!=='owner'
   ||!text(row.name)||!text(row.source_id)||labels.has(row.id))fail();
  labels.set(row.id,Object.freeze({...row}));
 }
 return labels;
}

// The existing temporal resolver has already applied date/language/source
// precedence. Do not replace geographic membership names with category names.
export function ownerDisplayName(id,{labels,nameRecord}={}){
 if(typeof id!=='string'||!id)return null;
 const named=nameRecord;
 if(named?.entity_id===id&&typeof named.value==='string'&&named.value.trim())return named.value;
 return labels?.get(id)?.name??null;
}
