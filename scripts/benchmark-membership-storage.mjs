/** Offline-only membership prototype. No network, credentials or production driver. */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {performance} from 'node:perf_hooks';
import {gunzipSync} from 'node:zlib';
import {PGlite} from '@electric-sql/pglite';
import {readGeographicReleaseManifest,decodeGeographicReleaseBatch} from './read-geographic-release-manifest.mjs';

export const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key,canonical(value[key])])) : value;
export const canonicalJSON = value => JSON.stringify(canonical(value));
const need = (ok,message) => {if (!ok) throw Error(message);};
const columns = ['release_id','entity_id','parent_id','reference_name','active','source_id','evidence'];
export function membershipRow(releaseId,row) {
  const value={release_id:releaseId,entity_id:row.entity_id ?? row.id,parent_id:row.parent_id ?? null,
    reference_name:row.reference_name ?? null,active:row.active ?? 1,source_id:row.source_id,
    evidence:typeof row.evidence === 'string' ? row.evidence : canonicalJSON(row.evidence ?? {})};
  need(typeof value.release_id==='string' && value.release_id && typeof value.entity_id==='string' && value.entity_id &&
    typeof value.source_id==='string' && value.source_id && [0,1].includes(value.active),'Invalid membership identity/active');
  const evidence=JSON.parse(value.evidence);
  need(evidence && typeof evidence==='object' && !Array.isArray(evidence),'Evidence must remain a JSON object');
  return value;
}

export function originalDDL(schema) {
  const table=schema.match(/CREATE TABLE atlas_geographic_memberships \([\s\S]*?\n\);/)?.[0];
  const indexes=[...schema.matchAll(/CREATE INDEX[^\n]* ON "atlas_geographic_memberships"[^\n]*/g)].map(x=>x[0]);
  need(table && indexes.length===2,'Original membership schema/index inventory changed');
  return `CREATE FUNCTION json_valid(value text) RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$
    BEGIN PERFORM value::json; RETURN value IS NOT NULL; EXCEPTION WHEN invalid_text_representation THEN RETURN false; END $$;
    CREATE FUNCTION json_type(value text) RETURNS text LANGUAGE sql IMMUTABLE AS $$ SELECT json_typeof(value::json) $$;
    CREATE TABLE atlas_entities(id text COLLATE "C" PRIMARY KEY,kind text COLLATE "C" NOT NULL);
    CREATE TABLE atlas_sources(id text COLLATE "C" PRIMARY KEY);
    CREATE TABLE atlas_geographic_releases(id text COLLATE "C" PRIMARY KEY);
    ${table}\n${indexes.join('\n')}`;
}

export const candidateDDL = `
CREATE TABLE release_keys(key integer PRIMARY KEY,id text COLLATE "C" UNIQUE NOT NULL);
CREATE TABLE entity_keys(key integer PRIMARY KEY,id text COLLATE "C" UNIQUE NOT NULL,kind text COLLATE "C" NOT NULL);
CREATE TABLE source_keys(key integer PRIMARY KEY,id text COLLATE "C" UNIQUE NOT NULL);
CREATE TABLE evidence_values(key integer PRIMARY KEY,sha256 text COLLATE "C" UNIQUE NOT NULL,
  raw text COLLATE "C" NOT NULL CHECK(json_typeof(raw::json)='object'),CHECK(sha256 ~ '^[a-f0-9]{64}$'));
CREATE TABLE membership_values(
  release_key integer NOT NULL REFERENCES release_keys(key),entity_key integer NOT NULL REFERENCES entity_keys(key),
  parent_key integer REFERENCES entity_keys(key),reference_name text COLLATE "C",
  active integer NOT NULL CHECK(active IN (0,1)),source_key integer NOT NULL REFERENCES source_keys(key),
  evidence_key integer NOT NULL REFERENCES evidence_values(key),PRIMARY KEY(release_key,entity_key),
  CHECK(reference_name IS NULL OR length(trim(reference_name))>0));
CREATE INDEX membership_parent ON membership_values(release_key,active,parent_key,entity_key);
CREATE INDEX membership_page ON membership_values(release_key,active,entity_key);
CREATE VIEW atlas_geographic_memberships AS SELECT r.id AS release_id,e.id AS entity_id,p.id AS parent_id,
  m.reference_name,m.active,s.id AS source_id,v.raw AS evidence
  FROM membership_values m JOIN release_keys r ON r.key=m.release_key JOIN entity_keys e ON e.key=m.entity_key
  LEFT JOIN entity_keys p ON p.key=m.parent_key JOIN source_keys s ON s.key=m.source_key
  JOIN evidence_values v ON v.key=m.evidence_key;
`;

const insertJSON = async (db,table,fields,rows,types) => {
  if (!rows.length) return;
  await db.query(`INSERT INTO ${table} (${fields.join(',')}) SELECT ${fields.join(',')}
    FROM json_to_recordset($1::json) AS x(${fields.map((field,i)=>`${field} ${types[i]}`).join(',')})`,[JSON.stringify(rows)]);
};
const rawTypes=['text','text','text','text','integer','text','text'];
export const insertOriginal = (db,rows) => insertJSON(db,'atlas_geographic_memberships',columns,rows,rawTypes);

/** The digest is an index; byte comparison is authoritative even on a collision. */
export function dictionaryEntry(dictionary,raw,hash=digest) {
  const sha256=hash(raw),previous=dictionary.get(sha256);
  if (previous) {need(previous.raw===raw,'Evidence digest collision or changed original bytes');return {entry:previous,fresh:false};}
  const entry={key:dictionary.size+1,sha256,raw};dictionary.set(sha256,entry);return {entry,fresh:true};
}
export async function insertCandidate(db,rows,keys,evidence) {
  need(typeof db.transaction==='function','Candidate writer must own the transaction, not receive a transaction handle');
  const values=[],fresh=[];
  const staged=new Map();
  for (const row of rows) {
    const sha256=digest(row.evidence),existing=evidence.get(sha256);
    if(existing)need(existing.raw===row.evidence,'Evidence digest collision or changed original bytes');
    const found=existing?{entry:existing,fresh:false}:dictionaryEntry(staged,row.evidence);
    if(found.fresh){found.entry.key+=evidence.size;fresh.push(found.entry);}
    const resolve=(map,id)=>{if(id===null)return null;need(map.has(id),'Missing stable identity mapping');return map.get(id);};
    values.push({release_key:resolve(keys.releases,row.release_id),entity_key:resolve(keys.entities,row.entity_id),
      parent_key:resolve(keys.entities,row.parent_id),reference_name:row.reference_name,active:row.active,
      source_key:resolve(keys.sources,row.source_id),evidence_key:found.entry.key});
  }
  await db.transaction(async tx=>{
    await insertJSON(tx,'evidence_values',['key','sha256','raw'],fresh,['integer','text','text']);
    await insertJSON(tx,'membership_values',Object.keys(values[0] ?? {}),values,
      ['integer','integer','integer','text','integer','integer','integer']);
  });
  for(const entry of fresh)evidence.set(entry.sha256,entry);
}

export function immutableDDL(tables) {
  return `CREATE FUNCTION benchmark_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'Benchmark original history is append-only'; END $$;\n`+
    tables.map(table=>`CREATE TRIGGER benchmark_append_only BEFORE UPDATE OR DELETE ON ${table}
      FOR EACH ROW EXECUTE FUNCTION benchmark_append_only();`).join('\n');
}
export async function verifyEvidenceDictionary(db) {
  let cursor=0,count=0;
  for(;;) {
    const rows=(await db.query('SELECT key,sha256,raw FROM evidence_values WHERE key>$1 ORDER BY key LIMIT 1000',[cursor])).rows;
    if(!rows.length)break;
    for(const row of rows){need(digest(row.raw)===row.sha256,'Damaged evidence payload/digest');count++;}
    cursor=rows.at(-1).key;
  }
  return count;
}

export function* preparedBatches(directory,manifest) {
  const releases=new Set(manifest.releases.map(r=>r.id));
  for (const part of manifest.batches) {
    const raw=fs.readFileSync(path.join(directory,part.path)),payload=decodeGeographicReleaseBatch(raw,part),value=JSON.parse(payload);
    if (!value.memberships) continue;
    need(releases.has(value.release_id),'Undeclared release');
    need(value.memberships.length<=200,'Prepared membership batch exceeds bound');
    yield {part,raw,payload,value,rows:value.memberships.map(row=>membershipRow(value.release_id,row))};
  }
}

export function inspectInputs(directory) {
  const manifest=readGeographicReleaseManifest(directory),parts=[],entities=new Map(),sources=new Set(),counts={};
  let count=0,bytes=0;
  for (const batch of preparedBatches(directory,manifest)) {
    const {part,raw,payload,value,rows}=batch;count+=rows.length;bytes+=payload.length;
    counts[value.release_id]=(counts[value.release_id]??0)+rows.length;
    parts.push({path:part.path,bytes:raw.length,sha256:digest(raw),payload_bytes:payload.length,payload_sha256:digest(payload),rows:rows.length});
    for (let i=0;i<rows.length;i++) {
      const row=rows[i],kind=value.memberships[i].kind;
      need(typeof kind==='string' && kind,'Missing original entity kind');
      need(!entities.has(row.entity_id)||entities.get(row.entity_id)===kind,'Conflicting entity kind');
      entities.set(row.entity_id,kind);sources.add(row.source_id);
    }
  }
  for (const batch of preparedBatches(directory,manifest))for(const row of batch.rows)
    need(row.parent_id===null || entities.has(row.parent_id),'Missing parent in declared original membership inputs');
  const filePin=name=>{const raw=fs.readFileSync(path.join(directory,name));return {path:name,bytes:raw.length,sha256:digest(raw)};};
  const chain=[filePin('index.json')];
  if(fs.existsSync(path.join(directory,'current-manifest.json'))) {
    chain.push(filePin('current-manifest.json'));
    chain.push(filePin(JSON.parse(fs.readFileSync(path.join(directory,'current-manifest.json'))).path));
  }
  const predecessors=[];let previous=JSON.parse(fs.readFileSync(path.join(directory,'index.json')));
  const extensions=fs.readdirSync(directory).filter(name=>/^releases-v[0-9]+-gzip\.json\.gz$/.test(name))
    .sort((a,b)=>Number(a.match(/v([0-9]+)/)[1])-Number(b.match(/v([0-9]+)/)[1]));
  for(const name of extensions) {
    const next=JSON.parse(gunzipSync(fs.readFileSync(path.join(directory,name)),{maxOutputLength:64*1024**2}));
    if(next.releases.at(-1).version>manifest.releases.at(-1).version)continue;
    need(canonicalJSON(next.releases.slice(0,previous.releases.length))===canonicalJSON(previous.releases)
      && canonicalJSON(next.batches.slice(0,previous.batches.length))===canonicalJSON(previous.batches),'Predecessor manifest bytes/rows changed');
    predecessors.push({...filePin(name),release_versions:next.releases.map(r=>r.version),predecessor_prefix_verified:true});previous=next;
  }
  need(canonicalJSON(previous)===canonicalJSON(manifest),'Declared predecessor chain does not reach selected manifest');
  const sourcePins=manifest.sources_batches.map(filePin);
  return {manifest,entities,sources,inventory:{chain,predecessors,source_pins:sourcePins,releases:manifest.releases,counts,membership_rows:count,
    expanded_payload_bytes:bytes,parts,part_inventory_sha256:digest(canonicalJSON(parts)),
    limits:['Immutable prepared releases only; no private production export, deployed status or geography approval claimed.',
      'All retained extension manifests have verified release/batch predecessor prefixes. This verifies prepared provenance retention, not independent scientific validation of the original external source archives.',
      'Original file bytes/hashes are retained in Git. Evidence strings use exactly the service canonical encoding of prepared objects; arbitrary production raw strings require a separate export.']}};
}

const sizesSQL=`SELECT c.relname AS relation,pg_relation_size(c.oid)::text AS heap_main_bytes,
  CASE WHEN c.reltoastrelid=0 THEN '0' ELSE pg_total_relation_size(c.reltoastrelid)::text END AS toast_bytes,
  pg_table_size(c.oid)::text AS table_bytes,pg_indexes_size(c.oid)::text AS index_bytes,
  pg_total_relation_size(c.oid)::text AS total_bytes
  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='public' AND c.relkind='r' ORDER BY c.relname`;
export async function measureRelations(db) {
  const relations=(await db.query(sizesSQL)).rows.map(row=>Object.fromEntries(Object.entries(row).map(([k,v])=>[k,k==='relation'?v:Number(v)])));
  const indexes=(await db.query(`SELECT t.relname AS relation,i.relname AS name,pg_relation_size(i.oid)::text AS bytes,
    pg_get_indexdef(i.oid) AS definition FROM pg_index x JOIN pg_class t ON t.oid=x.indrelid
    JOIN pg_class i ON i.oid=x.indexrelid JOIN pg_namespace n ON n.oid=t.relnamespace
    WHERE n.nspname='public' ORDER BY t.relname,i.relname`)).rows.map(row=>({...row,bytes:Number(row.bytes)}));
  return {relations,indexes,total_relation_bytes:relations.reduce((n,row)=>n+row.total_bytes,0)};
}
export function allocatedBytes(directory) {
  let bytes=0;
  for(const name of fs.readdirSync(directory)){const p=path.join(directory,name),s=fs.lstatSync(p);
    if(s.isDirectory())bytes+=allocatedBytes(p);else if(s.isFile())bytes+=s.blocks*512;else throw Error('Unexpected target symlink');}
  return bytes;
}

async function seedKeys(db,input,candidate) {
  const sorted=values=>[...values].sort((a,b)=>Buffer.compare(Buffer.from(a),Buffer.from(b)));
  const map=values=>new Map(sorted(values).map((id,i)=>[id,i+1]));
  const keys={releases:map(input.manifest.releases.map(r=>r.id)),entities:map(input.entities.keys()),sources:map(input.sources)};
  const configurations=candidate ? [
    ['release_keys',['key','id'],[...keys.releases].map(([id,key])=>({id,key})),['integer','text']],
    ['entity_keys',['key','id','kind'],[...keys.entities].map(([id,key])=>({id,key,kind:input.entities.get(id)})),['integer','text','text']],
    ['source_keys',['key','id'],[...keys.sources].map(([id,key])=>({id,key})),['integer','text']]
  ] : [
    ['atlas_geographic_releases',['id'],[...keys.releases].map(([id])=>({id})),['text']],
    ['atlas_entities',['id','kind'],[...keys.entities].map(([id])=>({id,kind:input.entities.get(id)})),['text','text']],
    ['atlas_sources',['id'],[...keys.sources].map(([id])=>({id})),['text']]
  ];
  for(const [table,fields,rows,types] of configurations)for(let i=0;i<rows.length;i+=200)
    await insertJSON(db,table,fields,rows.slice(i,i+200),types);
  return keys;
}

async function verifyRelease(db,release,candidate) {
  let cursor='',rows=0,comma='';const hash=createHash('sha256').update('['),rawHash=createHash('sha256');
  const kindTable=candidate?'entity_keys':'atlas_entities';
  for(;;) {
    const page=(await db.query(`SELECT m.*,e.kind FROM atlas_geographic_memberships m JOIN ${kindTable} e ON e.id=m.entity_id
      WHERE m.release_id=$1 AND m.entity_id>$2 COLLATE "C" ORDER BY m.entity_id COLLATE "C" LIMIT 1000`,[release.id,cursor])).rows;
    if(!page.length)break;
    for(const row of page) {
      const fields={entity_id:row.entity_id,kind:row.kind,parent_id:row.parent_id,reference_name:row.reference_name,
        active:row.active,source_id:row.source_id,evidence:JSON.parse(row.evidence)};
      hash.update(comma+canonicalJSON(fields));comma=',';rows++;
      rawHash.update(canonicalJSON(Object.fromEntries(columns.map(key=>[key,row[key]])))+'\n');
    }
    cursor=page.at(-1).entity_id;
  }
  const actual=hash.update(']').digest('hex');need(actual===release.membership_sha256,'Original release membership hash failed: '+release.version);
  return {version:release.version,rows,membership_sha256:actual,raw_rows_sha256:rawHash.digest('hex')};
}

async function queries(db,releases) {
  const samples=[];
  for(const release of releases) {
    const first=(await db.query('SELECT entity_id,parent_id FROM atlas_geographic_memberships WHERE release_id=$1 AND active=1 AND parent_id IS NOT NULL ORDER BY entity_id COLLATE "C" LIMIT 1',[release.id])).rows[0];
    const midpoint=(await db.query('SELECT entity_id FROM atlas_geographic_memberships WHERE release_id=$1 AND active=1 ORDER BY entity_id COLLATE "C" OFFSET 20000 LIMIT 1',[release.id])).rows[0] ?? first;
    const largest=(await db.query('SELECT parent_id,count(*) AS n FROM atlas_geographic_memberships WHERE release_id=$1 AND active=1 AND parent_id IS NOT NULL GROUP BY parent_id ORDER BY count(*) DESC,parent_id COLLATE "C" LIMIT 1',[release.id])).rows[0];
    const cases=[['page','SELECT * FROM atlas_geographic_memberships WHERE release_id=$1 AND active=1 AND entity_id>$2 COLLATE "C" ORDER BY entity_id COLLATE "C" LIMIT 200',[release.id,'']],
      ['parent','SELECT * FROM atlas_geographic_memberships WHERE release_id=$1 AND active=1 AND parent_id=$2 ORDER BY entity_id COLLATE "C" LIMIT 200',[release.id,first.parent_id]],
      ['identity','SELECT * FROM atlas_geographic_memberships WHERE release_id=$1 AND entity_id=$2',[release.id,first.entity_id]],
      ['midpoint-page','SELECT * FROM atlas_geographic_memberships WHERE release_id=$1 AND active=1 AND entity_id>$2 COLLATE "C" ORDER BY entity_id COLLATE "C" LIMIT 200',[release.id,midpoint.entity_id]],
      ['largest-parent','SELECT * FROM atlas_geographic_memberships WHERE release_id=$1 AND active=1 AND parent_id=$2 ORDER BY entity_id COLLATE "C" LIMIT 200',[release.id,largest.parent_id]]];
    for(const [kind,sql,args] of cases) {
      const elapsed=[];let expected,count;
      for(let repeat=0;repeat<3;repeat++){const start=performance.now(),result=(await db.query(sql,args)).rows;
        elapsed.push(performance.now()-start);const hash=digest(canonicalJSON(result));need(expected===undefined||hash===expected,'Unstable lookup');expected=hash;count=result.length;}
      need(count>0,'Empty query probe cannot establish lookup parity');
      samples.push({version:release.version,kind,args,rows:count,elapsed_ms:elapsed,result_sha256:expected});
    }
  }
  return samples;
}

export async function runBenchmark({directory,output,workDirectory,diskBudgetBytes=8*1024**3,onProgress=()=>{}}) {
  need(path.isAbsolute(workDirectory),'Use an explicit absolute isolated work directory');
  need(!fs.existsSync(workDirectory),'Refuse an existing target; preserve previous results');
  const input=inspectInputs(directory),schema=fs.readFileSync(new URL('../postgres/schema.sql',import.meta.url),'utf8');
  fs.mkdirSync(workDirectory,{recursive:true});fs.mkdirSync(output,{recursive:true});
  fs.writeFileSync(path.join(output,'inputs.json'),JSON.stringify(input.inventory,null,2)+'\n');
  const ddl={original:originalDDL(schema),candidate:candidateDDL};
  const result={version:1,scope:'offline-prepared-membership-subsystem',observed_at:new Date().toISOString(),
    input_inventory_sha256:digest(fs.readFileSync(path.join(output,'inputs.json'))),schema_sha256:digest(schema),
    environment:{node:process.version,platform:process.platform,arch:process.arch,physical_memory_bytes:os.totalmem(),
      pglite_version:JSON.parse(fs.readFileSync(new URL('../node_modules/@electric-sql/pglite/package.json',import.meta.url))).version,
      disk_budget_bytes:diskBudgetBytes},targets:{},limits:input.inventory.limits.concat([
      'Independent local disk-backed PGlite/PostgreSQL targets, not production Neon or an authorized production backup.',
      'Original membership DDL, constraints and three indexes copied from the frozen schema; shared registries reduced to identity/kind columns. Full application data/triggers are outside this benchmark.',
      'All prototype tables and dictionary/index overhead counted. Relation bytes are actual; target allocated bytes include local WAL/temporary files and are sampled, not a guaranteed peak.',
      'Sampled allocated-byte peaks are for the aggregate work directory, including the closed original target during candidate execution. RSS is the shared sequential Node process, with possible retained WASM memory; neither measures independent candidate memory.',
      'Post-load ANALYZE is local only. Three repeated bounded query timings include local cache/JIT effects, not provider network/cold-start performance.',
      'This creates no production schema/adapter/migration. Measured local savings are not reclaimable production bytes; production export/parity, peak-space/rollback planning and publisher delivery remain required.'])};
  for(const candidate of [false,true]) {
    const name=candidate?'candidate':'original',db=new PGlite(path.join(workDirectory,name));
    const target={ddl_sha256:digest(ddl[name]),progress:[],peak_sampled_rss_bytes:process.memoryUsage().rss,peak_sampled_allocated_bytes:0};
    result.targets[name]=target;
    try {
      await db.waitReady;await db.exec(ddl[name]);
      await db.exec(immutableDDL(candidate ? ['release_keys','entity_keys','source_keys','evidence_values','membership_values'] : ['atlas_geographic_memberships']));
      target.settings=(await db.query(`SELECT version() AS version,current_setting('block_size') AS block_size,
        current_setting('server_encoding') AS encoding,(SELECT datcollate FROM pg_database WHERE datname=current_database()) AS collate,
        current_setting('default_toast_compression') AS toast_compression`)).rows[0];
      const keys=await seedKeys(db,input,candidate),evidence=new Map(),start=performance.now();let count=0,lastRelease;
      for(const batch of preparedBatches(directory,input.manifest)) {
        if(candidate)await insertCandidate(db,batch.rows,keys,evidence);
        else await db.transaction(tx=>insertOriginal(tx,batch.rows));
        count+=batch.rows.length;target.peak_sampled_rss_bytes=Math.max(target.peak_sampled_rss_bytes,process.memoryUsage().rss);
        if(lastRelease!==batch.value.release_id||count%10000<200||count===input.inventory.membership_rows) {
          lastRelease=batch.value.release_id;const allocated=allocatedBytes(workDirectory);
          target.peak_sampled_allocated_bytes=Math.max(target.peak_sampled_allocated_bytes,allocated);
          need(allocated<=diskBudgetBytes,'Isolated disk budget exceeded; preserve targets and partial receipt');
          target.progress.push({rows:count,allocated_bytes:allocated,rss_bytes:process.memoryUsage().rss});onProgress({target:name,rows:count});
          fs.writeFileSync(path.join(output,'partial.json'),JSON.stringify(result,null,2)+'\n');
        }
      }
      target.ingest_ms=performance.now()-start;target.rows=count;target.distinct_evidence=candidate?evidence.size:null;
      await db.exec('ANALYZE');target.storage=await measureRelations(db);
      if(candidate)need(await verifyEvidenceDictionary(db)===evidence.size,'Evidence dictionary row count differs');
      target.releases=[];for(const release of input.manifest.releases)target.releases.push(await verifyRelease(db,release,candidate));
      target.queries=await queries(db,input.manifest.releases);
      target.peak_sampled_rss_bytes=Math.max(target.peak_sampled_rss_bytes,process.memoryUsage().rss);
    } finally {await db.close();}
    target.closed_target_allocated_bytes=allocatedBytes(path.join(workDirectory,name));
    fs.writeFileSync(path.join(output,'partial.json'),JSON.stringify(result,null,2)+'\n');
  }
  need(canonicalJSON(result.targets.original.releases)===canonicalJSON(result.targets.candidate.releases),'Reconstructed original bytes/identities differ');
  for(let i=0;i<result.targets.original.queries.length;i++)
    need(result.targets.original.queries[i].result_sha256===result.targets.candidate.queries[i].result_sha256,'Page/parent/identity query parity failed');
  result.parity={complete:true,rows:input.inventory.membership_rows,releases:input.manifest.releases.length,query_cases:result.targets.original.queries.length};
  result.savings={original_relation_bytes:result.targets.original.storage.total_relation_bytes,
    candidate_relation_bytes:result.targets.candidate.storage.total_relation_bytes,
    measured_local_reduction_bytes:result.targets.original.storage.total_relation_bytes-result.targets.candidate.storage.total_relation_bytes};
  fs.writeFileSync(path.join(output,'result.json'),JSON.stringify(result,null,2)+'\n');return result;
}

if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  const [directory,output,workDirectory]=process.argv.slice(2);
  need(directory&&output&&workDirectory,'Usage: node scripts/benchmark-membership-storage.mjs prepared-directory output-directory absolute-new-isolated-directory');
  let last=0;const result=await runBenchmark({directory,output,workDirectory,onProgress:p=>{
    if(Date.now()-last>15000){console.log(JSON.stringify(p));last=Date.now();}}});console.log(JSON.stringify({parity:result.parity,savings:result.savings}));
}
