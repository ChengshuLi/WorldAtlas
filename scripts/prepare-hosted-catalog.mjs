import fs from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const hash=value=>createHash('sha256').update(value).digest('hex');
export function prepareHostedCatalog({databasePath='data/atlas.sqlite',output='data/hosted-catalog',archivePath='data/geographic-migration-archive.json.gz',typesPath='data/hosted-type-catalog.json'}={}){
 const db=new DatabaseSync(databasePath,{readOnly:true});
 try{
 fs.mkdirSync(output,{recursive:true});
 const locations=new Map(db.prepare('SELECT id,active,reference_owner,metadata FROM locations').all().map(r=>[r.id,{...r,metadata:JSON.parse(r.metadata)}]));
 const units=new Map(db.prepare('SELECT id,metadata FROM units').all().map(r=>[r.id,JSON.parse(r.metadata)]));
 const rows=db.prepare('SELECT * FROM entities WHERE is_example=0').all();
 const activeUnits=new Set(db.prepare('WITH RECURSIVE used(id) AS (SELECT parent_id FROM locations WHERE active=1 UNION SELECT u.parent_id FROM units u JOIN used ON u.id=used.id WHERE u.parent_id IS NOT NULL) SELECT id FROM used').all().map(row=>row.id));
 for(const file of fs.readdirSync(output))if(/^batch-\d+\.json$/.test(file))fs.unlinkSync(`${output}/${file}`);
 const ids=new Set(rows.map(r=>r.id));for(const e of rows)if(e.parent_id&&!ids.has(e.parent_id))throw Error(`Missing source parent: ${e.id}`);
 const archiveHash=hash(fs.readFileSync(archivePath));
 const sources=new Map(),sourceFor=(name,url,license,vintage,status='reference',from=2026,to=2027,extraMetadata={})=>{
  const metadata={reference_context:true,...extraMetadata},key=hash(JSON.stringify([name,url,license,vintage,status,from,to,metadata]));
  const id=`source:atlas:${key}`;
  sources.set(id,{id,name,url:url&&/^https?:\/\//i.test(url)?url:null,license:license||'License not supplied by retained source; inspect archived evidence',vintage:String(vintage||'Undated source reference'),status,supported_from:from,supported_to:to,metadata});return id;
 };
 const entities=rows.map(e=>{
  const loc=locations.get(e.id),m=loc?.metadata||units.get(e.id)||{},lifetime=e.valid_from!=null||e.valid_to!=null;
  const source_id=sourceFor(m.source_name||e.source||'Retained atlas reference registry',m.source_url,m.license,m.reference_year,lifetime?'historical':'reference',lifetime?(e.valid_from??-3000):2026,lifetime?(e.valid_to??2027):2027);
  const active=loc?loc.active:units.has(e.id)?Number(activeUnits.has(e.id)):e.kind==='settlement'&&e.parent_id?locations.get(e.parent_id)?.active??1:1;
  return {id:e.id,kind:e.kind,name:e.name,parent_id:e.parent_id,valid_from:e.valid_from,valid_to:e.valid_to,source_id,reference_owner:loc?.reference_owner??null,active,is_example:0,metadata:{reference_context:true,source_metadata:{source_id:m.source_id,administrative_level:m.administrative_level,reference_year:m.reference_year,location_basis:m.location_basis,semantic_status:'open'},archived:active===0,original_geometry_archive:active===0?archiveHash:null}};
 });
 const tiers=['continent','subcontinent','region','area','province','location','settlement'];entities.sort((a,b)=>tiers.indexOf(a.kind)-tiers.indexOf(b.kind)||a.id.localeCompare(b.id));
 const categories=db.prepare('SELECT * FROM attribute_entities ORDER BY id').all().map(r=>({id:r.id,kind:r.kind,name:r.name,source_id:sourceFor(r.source,null,'See cited original source','Undated identity registry published in modern reference','reference',2026,2027,{identity_only:true,dated_label_not_asserted:true,attribute_coverage_not_asserted:true,historical_existence_not_asserted:true,interval_semantics:'Registry publication context only; not historical name, existence, or attribute evidence coverage'}),metadata:{identity_only:true,dated_label_not_asserted:true,attribute_coverage_not_asserted:true,historical_existence_not_asserted:true}}));
 const batches=[];let n=0;
 for(const [kind,values] of [['entity_types',JSON.parse(fs.readFileSync(typesPath,'utf8')).entity_types],['sources',[...sources.values()]],['entities',entities],['categories',categories]]){
  for(let i=0;i<values.length;i+=200){const payload={[kind]:values.slice(i,i+200)},raw=JSON.stringify(payload),path=`batch-${n++}.json`;payload.ingestion_id=`catalog:${hash(raw)}`;const bytes=JSON.stringify(payload);if(Buffer.byteLength(bytes)>1024*1024)throw Error(`Catalog import exceeds bounded size: ${path}`);fs.writeFileSync(`${output}/${path}`,bytes);batches.push({path,kind,rows:values.slice(i,i+200).length,sha256:hash(bytes)});}
 }
 const manifest={version:1,counts:{entities:entities.length,sources:sources.size,categories:categories.length,active_entities:entities.filter(e=>e.active===1).length,archived_entities:entities.filter(e=>e.active===0).length,active_units:entities.filter(e=>units.has(e.id)&&e.active===1).length,archived_units:entities.filter(e=>units.has(e.id)&&e.active===0).length},batches,archive_sha256:archiveHash,scope:'Retained source identities and undated reference parent chains. Existing historical records remain on original IDs in the immutable archive; no evidence transfers or invented historic memberships.'};
 fs.writeFileSync(`${output}/index.json`,JSON.stringify(manifest,null,2));return manifest;
 }finally{db.close();}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))console.log(prepareHostedCatalog().counts);
