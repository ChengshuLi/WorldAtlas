const evidenceCaches=new WeakMap();
export function ownershipEvidence(index,key){
 if(index.version!==2)return key;
 let cache=evidenceCaches.get(index);if(!cache){cache=new Map();evidenceCaches.set(index,cache);}
 if(!cache.has(key)){const [name,share,coverage,candidates,sources,dated]=index.evidence[key];cache.set(key,{owner_name:name==null?null:index.labels[name],share,coverage,candidates:candidates.map(([i,s])=>[index.owner_ids[i],s]),source_record_ids:sources.map(i=>index.source_ids[i]),footprint:dated?'dated':'reference'});}
 return cache.get(key);
}
export function ownershipInterval(index,row){
 const [valid_from,valid_to,owner,status,evidence]=row,category_id=index.version===2?(owner==null?null:index.owner_ids[owner]):owner;
 return {valid_from,valid_to,category_id,status:index.version===2?index.statuses_order[status]:status,metadata:ownershipEvidence(index,evidence)};
}
export function decodeDerived(parts,index,year){
 const records=[];
 for(const part of parts)for(const [location_id,intervals] of part){
  let lo=0,hi=intervals.length;
  while(lo<hi){const mid=(lo+hi)>>>1;if(intervals[mid][0]<=year)lo=mid+1;else hi=mid;}
  const row=intervals[lo-1];
  if(row&&year<row[1]){const r=ownershipInterval(index,row);records.push({...r,id:`ownership:${location_id}:${r.valid_from}`,location_id,attribute:'owner',value:r.category_id?(r.metadata.owner_name||index.entities[r.category_id].name):null,method:'majority-area',source:index.source,source_url:index.source_url});}
 }
 return records;
}
