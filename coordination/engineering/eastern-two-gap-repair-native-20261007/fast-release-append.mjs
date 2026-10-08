// Same actual versioned preparation codec, with one process for the full roster.
import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';
import {spawn} from 'node:child_process';import {once} from 'node:events';import {fileURLToPath} from 'node:url';
export async function appendCompleteSuccessor(registry,result,out){
 assert(path.isAbsolute(out)&&!fs.existsSync(out)&&fs.realpathSync(path.dirname(out))===path.dirname(out));
 const rows=[];
 const add=(name,payload,route)=>{assert(Buffer.byteLength(JSON.stringify(payload))<1048576);assert((payload.memberships?.length??0)+(payload.changes?.length??0)+Number(Boolean(payload.release))<=250);rows.push({path:name,payload,route});};
 add('sources-8.json.gz',{sources:[result.source],ingestion_id:result.release.id+':sources'},'/api/records/import');
 add('release-8.json.gz',{release:result.release,ingestion_id:result.release.id+':header'},'/api/geography/stage');
 for(const [kind,members] of [['memberships',result.memberships],['changes',result.changes]])for(let first=0;first<members.length;first+=250)
  add(`8-${kind}-${first}.json.gz`,{release_id:result.release.id,[kind]:members.slice(first,first+250),ingestion_id:`${result.release.id}:${kind}:${first}`},'/api/geography/stage');
 assert.equal(rows.length,343);const child=spawn(process.env.ATLAS_PYTHON??'python3',[fileURLToPath(new URL('./serialize-release.py',import.meta.url)),out],{stdio:['pipe','pipe','pipe']});
 const terminal=once(child,'close');let encoded='',error='';child.stdout.setEncoding('utf8');child.stderr.setEncoding('utf8');child.stdout.on('data',b=>{encoded+=b;assert(encoded.length<1048576);});child.stderr.on('data',b=>error+=b);
 for(const row of rows){if(!child.stdin.write(JSON.stringify({path:row.path,payload:row.payload})+'\n'))await once(child.stdin,'drain');}child.stdin.end();
 const [exit]=await terminal;assert.equal(exit,0,error);const pins=encoded.trim().split('\n').map(line=>JSON.parse(line));assert.equal(pins.length,rows.length);
 const batches=pins.map((p,i)=>{assert.equal(p.path,rows[i].path);assert(p.bytes<=32*1024*1024&&p.decoded_bytes<=1048576);assert(!registry.batches.some(b=>b.path===p.path));return {path:p.path,route:rows[i].route,sha256:p.sha256,encoding:'gzip',payload_sha256:p.payload_sha256};});
 const index={...registry,releases:[...registry.releases,result.release],batches:[...registry.batches,...batches],new_entities:registry.new_entities,
  total_memberships:registry.total_memberships+result.memberships.length,changes:registry.changes+result.changes.length,
  sources_batches:[...registry.sources_batches,'sources-8.json.gz']};
 // appendRelease sets this absent field from the candidate; omission is identical.
 delete index.validated_geometry;
 assert.deepEqual(index.releases.slice(0,7),registry.releases);assert.deepEqual(index.batches.slice(0,registry.batches.length),registry.batches);
 assert.deepEqual(index.sources_batches.slice(0,registry.sources_batches.length),registry.sources_batches);
 return {index,pins,output:out,codec:'Unchanged evidence.immutable canonical_json + deterministic_gzip',complete_members:result.memberships.length};
}
