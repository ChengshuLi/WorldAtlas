// Compact references share source metadata; resolve only records needed at this date.
export function decodeReferences(parts,index,year){
 if(index.version===1)return parts.flat().filter(r=>r.valid_from<=year&&year<r.valid_to);
 const active=new Map(index.types.map((t,i)=>[i,t]).filter(([,t])=>t.valid_from<=year&&year<t.valid_to));
 const records=[];
 for(const part of parts)for(const [location_id,values] of part)for(const [type,value,share,coverage] of values){const t=active.get(type);if(t)records.push({...t,id:`reference:${location_id}:${t.attribute}:${t.valid_from}`,location_id,value:index.values[value],metadata:{...t.metadata,share,coverage}});}
 return records;
}
