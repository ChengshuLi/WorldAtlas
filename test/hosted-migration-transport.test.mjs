import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {Miniflare,convertV4MiniflareOptions} from 'miniflare';
import {compileHostedMigrations,compileGeographicReleaseSql} from '../scripts/compile-hosted-migrations.mjs';
const root=path.resolve(import.meta.dirname,'..'),input=path.join(root,'drizzle'),raw=file=>fs.readFileSync(path.join(input,file),'utf8'),sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const split=sql=>sql.split('--> statement-breakpoint').map(v=>v.trim()).filter(Boolean);
// Deliberately reproduces the deployment transport failure hypothesis, not an
// endorsed SQL parser. Quoted END and comments are skipped; CASE END is not.
function naiveBlockSplit(sql){const re=/'(?:''|[^'])*'|"(?:""|[^"])*"|`[^`]*`|--[^\n]*|\/\*[\s\S]*?\*\/|\bBEGIN\b|\bEND\b|;/gi;let depth=0,start=0;const parts=[];for(const match of sql.matchAll(re)){const token=match[0].toUpperCase();if(token==='BEGIN')depth++;if(token==='END')depth=Math.max(0,depth-1);if(token===';'&&depth===0){parts.push(sql.slice(start,match.index+1));start=match.index+1;}}if(sql.slice(start).trim())parts.push(sql.slice(start));return parts.filter(v=>v.replace(/--[^\n]*/g,'').trim());}
const fixture=`INSERT INTO atlas_entity_types(id,name,geographic_level) VALUES('continent','continent',5),('subcontinent','subcontinent',4),('region','region',3),('area','area',2),('province','province',1),('location','location',0);
INSERT INTO atlas_sources(id,name,license,vintage,supported_from,supported_to,status) VALUES('history','QA history','CC0 test-only','1000',1000,1100,'historical'),('review','QA review','CC0 test-only','2026',2026,2027,'reference');
INSERT INTO atlas_entities(id,kind,name,parent_id) VALUES('c','continent','c',null),('s','subcontinent','s','c'),('r','region','r','s'),('a','area','a','r'),('p','province','p','a'),('l','location','l','p');
INSERT INTO atlas_attribute_records(id,location_id,attribute,value,valid_from,valid_to,method,status,source_id) VALUES('old-pop','l','population','42',1000,1100,'direct','sourced','history'),('old-rank','l','rank','"city"',1000,1100,'direct','sourced','history');
INSERT INTO atlas_evidence_retirements(id,collection,target_id,source_id,reason) VALUES('retire-rank','records','old-rank','review','QA correction');`;

test('transport compiler changes exactly the pinned 21 guards and preserves all other raw SQL and metadata',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-sql-transport-'));try{const before=new Map(fs.readdirSync(input).filter(v=>v.endsWith('.sql')).map(v=>[v,sha(fs.readFileSync(path.join(input,v)))])),receipt=compileHostedMigrations({input,output:dir});assert.equal(receipt.transformed_guards,21);assert.equal(receipt.source_sql_rewritten,false);assert.equal(receipt.claims_rewritten,false);
 for(const row of receipt.migrations){assert.equal(row.source_sha256,before.get(row.file));assert.equal(sha(fs.readFileSync(path.join(input,row.file))),before.get(row.file));assert.equal(row.transport_sha256,sha(fs.readFileSync(path.join(dir,row.file))));if(row.file!=='0002_geographic_reference_releases.sql')assert.deepEqual(fs.readFileSync(path.join(dir,row.file)),fs.readFileSync(path.join(input,row.file)));else{assert.equal(row.transformed_guards,21);assert.equal(row.transport_sha256,'77459729e200a45e3c003333acbd2a30446acba1670138a4861f7315a4241e77');}}
 for(const m of receipt.meta)assert.deepEqual(fs.readFileSync(path.join(dir,m.file)),fs.readFileSync(path.join(input,m.file)));const again=compileHostedMigrations({input,output:dir});assert.deepEqual(again,receipt);assert.throws(()=>compileGeographicReleaseSql(raw('0002_geographic_reference_releases.sql')+'\n'),/source hash changed/);assert.throws(()=>compileHostedMigrations({input,output:input}),/separate derivative/);
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});

test('raw and derivative guards have identical original schemas and preserve all 21 conditions and error messages',()=>{
 const original=raw('0002_geographic_reference_releases.sql'),compiled=compileGeographicReleaseSql(original).sql,guards=original.match(/^[ \t]*SELECT CASE WHEN (.+) THEN (RAISE\(ABORT,'(?:''|[^'])*'\)) END;$/gm);assert.equal(guards.length,21);
 for(const guard of guards){const [,condition,raise]=guard.match(/SELECT CASE WHEN (.+) THEN (RAISE\(ABORT,'(?:''|[^'])*'\)) END;/);assert.ok(compiled.includes(`SELECT ${raise} WHERE ${condition};`));}
 const create=sql=>{const db=new DatabaseSync(':memory:');db.exec(raw('0000_bizarre_sentry.sql'));db.exec(raw('0001_evidence_retirements.sql'));db.exec(fixture);db.exec(sql);return db;},a=create(original),b=create(compiled);try{const objects=db=>db.prepare("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").all();assert.deepEqual(objects(a).map(r=>({...r,sql:compileEquivalent(r.sql)})),objects(b).map(r=>({...r,sql:compileEquivalent(r.sql)})));for(const table of ['atlas_attribute_records','atlas_evidence_retirements'])assert.deepEqual(a.prepare(`SELECT * FROM ${table} ORDER BY id`).all(),b.prepare(`SELECT * FROM ${table} ORDER BY id`).all());}finally{a.close();b.close();}
});
function compileEquivalent(sql){return sql?.replace(/SELECT CASE WHEN (.+) THEN (RAISE\(ABORT,'(?:''|[^'])*'\)) END;/g,(_,c,r)=>`SELECT ${r} WHERE ${c};`);}

test('native workerd D1 reproduces CASE-block truncation and applies the derivative over populated retained claims',async()=>{
 const mf=new Miniflare(convertV4MiniflareOptions({name:'migration-transport-test',modules:true,script:'export default {fetch(){return new Response("QA")}}',compatibilityDate:'2026-10-01',d1Databases:{RAW:'00000000-0000-0000-0000-000000000011',TRUNCATED:'00000000-0000-0000-0000-000000000012',COMPILED:'00000000-0000-0000-0000-000000000013',EXEC:'00000000-0000-0000-0000-000000000014'}}));
 try{
  const setup=async name=>{const db=await mf.getD1Database(name);for(const sql of [raw('0000_bizarre_sentry.sql'),raw('0001_evidence_retirements.sql')])await db.batch(split(sql).map(p=>db.prepare(p)));await db.batch(fixture.split(';').map(v=>v.trim()).filter(Boolean).map(p=>db.prepare(p)));return db;};
  const original=raw('0002_geographic_reference_releases.sql');
  const good=await setup('RAW');await good.batch(split(original).map(p=>good.prepare(p)));
  const truncated=await setup('TRUNCATED'),fragment=naiveBlockSplit(original).find(p=>p.includes('CREATE TRIGGER geographic_release_insert'));assert.match(fragment,/END;$/);assert.equal((fragment.match(/SELECT CASE/g)??[]).length,1);await assert.rejects(truncated.batch(naiveBlockSplit(original).map(p=>truncated.prepare(p))),/incomplete input/);
  const badExec=await setup('EXEC');await assert.rejects(badExec.exec(original),/incomplete input/);
  const db=await setup('COMPILED'),snapshot=async table=>(await db.prepare(`SELECT * FROM ${table} ORDER BY id`).all()).results,claims=await snapshot('atlas_attribute_records'),retirements=await snapshot('atlas_evidence_retirements'),objects=(await db.prepare("SELECT type,name,sql FROM sqlite_master WHERE type IN ('index','trigger') ORDER BY type,name").all()).results;
  await db.batch(naiveBlockSplit(compileGeographicReleaseSql(original).sql).map(p=>db.prepare(p)));assert.deepEqual(await snapshot('atlas_attribute_records'),claims);assert.deepEqual(await snapshot('atlas_evidence_retirements'),retirements);const after=(await db.prepare("SELECT type,name,sql FROM sqlite_master WHERE type IN ('index','trigger') ORDER BY type,name").all()).results;for(const object of objects)assert.deepEqual(after.find(v=>v.name===object.name),object);assert.deepEqual((await db.prepare('PRAGMA foreign_key_check').all()).results,[]);assert.equal((await db.prepare("SELECT count(*) n FROM sqlite_master WHERE type='table' AND name LIKE 'atlas_geographic_%'").first()).n,3);
 }finally{await mf.dispose();}
});
