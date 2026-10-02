import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {createHash} from 'node:crypto';
import worker from '../hosted/worker.js';
import {importBatch} from '../hosted/records.js';

class Database {
 constructor(){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');for(const file of fs.readdirSync(new URL('../drizzle/',import.meta.url)).filter(name=>/^000[0-7]_.*\.sql$/.test(name)).sort())this.sqlite.exec(fs.readFileSync(new URL('../drizzle/'+file,import.meta.url),'utf8'));}
 prepare(sql){const statement=this.sqlite.prepare(sql);let values=[];return {bind(...input){values=input;return this;},async first(){return statement.get(...values)??null;},async all(){return {results:statement.all(...values)};},async run(){return {meta:{changes:Number(statement.run(...values).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN');try{const result=[];for(const statement of statements)result.push(await statement.run());this.sqlite.exec('COMMIT');return result;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
async function fixture(){
 const DB=new Database(),objects=new Map();let writes=0;
 await importBatch(DB,{sources:[{id:'media:test-source',name:'Instrument source',url:'https://example.org/instrument',license:'CC0',vintage:'2026',supported_from:2026,supported_to:2027,status:'reference'}]});
 const env={DB,BUCKET:{async head(key){return objects.has(key)?{}:null;},async put(key,bytes){writes++;objects.set(key,bytes);},async get(key){const bytes=objects.get(key);return bytes?{body:bytes,size:bytes.byteLength}:null;}}};
 const content=Buffer.from('public-domain instrument recording fixture'),sha=createHash('sha256').update(content).digest('hex');
 const parameters={id:`media:${sha}`,source_id:'media:test-source',name:'Instrument recording',license:'CC0',attribution:'Fixture source',metadata:JSON.stringify({source_sha256:sha,observation:'source reference only'})};
 const upload=(parameters,selected=env)=>worker.fetch(new Request('https://atlas.example/api/media/upload?'+new URLSearchParams(parameters),{method:'POST',headers:{Origin:'https://atlas.example','Content-Type':'audio/wav'},body:content}),selected,{});
 const metadata=(selected=env)=>worker.fetch(new Request('https://atlas.example/api/media/'+encodeURIComponent(parameters.id)+'?metadata=1'),selected,{});
 return {DB,env,content,parameters,upload,metadata,writes:()=>writes};
}
test('media bytes and sourced provenance survive upload, metadata-only reads and identical retries',async()=>{
 const f=await fixture();try{
  const response=await f.upload(f.parameters);assert.equal(response.status,200);const stored=await response.json();assert.deepEqual(stored.metadata,JSON.parse(f.parameters.metadata));assert.equal(stored.source_id,f.parameters.source_id);assert.equal(stored.bytes,f.content.byteLength);
  const metadata=await f.metadata({DB:f.DB});assert.equal(metadata.status,200);assert.equal(metadata.headers.get('X-Atlas-Media-Metadata-Version'),'1');assert.deepEqual(await metadata.json(),stored,'metadata recovery does not require reading the bucket');
  const bytes=await worker.fetch(new Request('https://atlas.example/api/media/'+encodeURIComponent(f.parameters.id)),f.env,{});assert.deepEqual(Buffer.from(await bytes.arrayBuffer()),f.content);
  assert.equal((await f.upload(f.parameters)).status,200);assert.equal(f.writes(),1);
  assert.equal((await f.upload({...f.parameters,metadata:JSON.stringify({observation:'contradictory provenance'})})).status,409);assert.equal(f.writes(),1);assert.deepEqual(await (await f.metadata()).json(),stored);
 }finally{f.DB.sqlite.close();}
});
test('invalid or oversized provenance and maintenance never write source objects',async()=>{
 const f=await fixture();try{
  for(const metadata of ['null','[]','invalid'])assert.equal((await f.upload({...f.parameters,metadata})).status,400);
  assert.equal((await f.upload({...f.parameters,metadata:JSON.stringify({text:'é'.repeat(2500)})})).status,413);
  assert.equal((await f.upload(f.parameters,{...f.env,ATLAS_READ_ONLY:'1'})).status,503);assert.equal(f.writes(),0);
  const missing=await f.metadata();assert.equal(missing.status,404);assert.equal(missing.headers.get('X-Atlas-Media-Metadata-Version'),'1');
 }finally{f.DB.sqlite.close();}
});
