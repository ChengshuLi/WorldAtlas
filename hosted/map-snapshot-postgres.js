// PostgreSQL renders the same bounded metadata proof as the SQLite reader.
// JSON columns stay original text; casts here only inspect evidence.
const proofFlags=['estimate','estimated','is_estimate','modeled','modelled','rounded','legacy_snapshot','legacy_attributes'];
const extract=(column,key)=>`json_extract(${column},'$.${key}')`;
const type=(column,key)=>`json_type(${column},'$.${key}')`;
const truth=(column,key)=>`CASE ${type(column,key)} WHEN 'array' THEN 1 WHEN 'object' THEN 1 WHEN 'text' THEN CASE WHEN ${extract(column,key)}!='' THEN 1 ELSE 0 END WHEN 'true' THEN 1 WHEN 'false' THEN 0 WHEN 'null' THEN 0 ELSE CASE WHEN coalesce(${extract(column,key)}::numeric,0)!=0 THEN 1 ELSE 0 END END`;
const proofMetadata=column=>`json_build_object(${proofFlags.map(key=>`'${key}',${truth(column,key)}`).join(',')},'rounding',CASE WHEN ${type(column,'rounding')} IS NOT NULL AND ${type(column,'rounding')}!='null' THEN 1 ELSE NULL END,'model',CASE WHEN ${type(column,'model')} IS NOT NULL AND ${type(column,'model')}!='null' THEN 1 ELSE NULL END,'precision',CASE WHEN ${type(column,'precision')}='object' THEN to_jsonb('[object Object]'::text) WHEN ${type(column,'precision')}='array' THEN ${extract(column,'precision')}::jsonb WHEN lower(coalesce(${extract(column,'precision')},'')) LIKE '%round%' OR lower(coalesce(${extract(column,'precision')},'')) LIKE '%model%' OR lower(coalesce(${extract(column,'precision')},'')) LIKE '%estimate%' OR lower(coalesce(${extract(column,'precision')},'')) LIKE '%approx%' THEN to_jsonb('approximate; original precision retained in evidence'::text) ELSE to_jsonb(substr(${extract(column,'precision')},1,256)) END)::text`;
const boundedMetadata=(alias,bytes,proof=false)=>`CASE WHEN octet_length(${alias}.metadata)<=${bytes} THEN ${alias}.metadata ELSE ${proof?proofMetadata(`${alias}.metadata`):"'{}'"} END metadata,CASE WHEN octet_length(${alias}.metadata)>${bytes} THEN 1 ELSE 0 END metadata_truncated`;

export function postgresMapQueries(sqliteQueries){
 const aliases={attributes:[['r',1024,true]],names:[['n',1024,false]],retirements:[['t',1024,false]],sources:[['s',2048,false]]};
 return Object.fromEntries(Object.entries(sqliteQueries).map(([kind,sql])=>{
  for(const [alias,bytes,proof] of aliases[kind]??[]){
   const start=`CASE WHEN length(CAST(${alias}.metadata AS BLOB))<=${bytes}`;
   const end=` THEN 1 ELSE 0 END metadata_truncated`;
   let offset=0;
   while(true){const first=sql.indexOf(start,offset);if(first<0)break;const last=sql.indexOf(end,first);if(last<0)throw Error('Incomplete metadata query template');const replacement=boundedMetadata(alias,bytes,proof);sql=sql.slice(0,first)+replacement+sql.slice(last+end.length);offset=first+replacement.length;}
  }
  // SQLite allows an ON clause on CROSS JOIN; PostgreSQL requires ordinary JOIN.
  sql=sql.replace(/CROSS JOIN (atlas_\w+ \w+)(?: INDEXED BY \w+)? ON/g,'JOIN $1 ON');
  return [kind,sql];
 }));
}
