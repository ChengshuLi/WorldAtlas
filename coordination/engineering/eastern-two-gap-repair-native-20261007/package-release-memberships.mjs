// Preserve only this job's complete generated v8 membership tail as exact bytes.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
import {retainWholeImage,restoreWholeImage} from './whole-image.mjs';

export const SOURCE_COMMIT='bad783529fa35d0bd45cd65ed899c02ea96c93b6';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const blob=raw=>createHash('sha1').update(Buffer.from(`blob ${raw.length}\0`)).update(raw).digest('hex');
const cap=32*1024*1024;
export function packageReleaseMemberships({repo,output,temporaryRoot}) {
 assert(path.isAbsolute(repo)&&fs.realpathSync(repo)===repo);
 assert(path.isAbsolute(temporaryRoot)&&fs.realpathSync(temporaryRoot)===temporaryRoot);
 assert(path.isAbsolute(output)&&!fs.existsSync(output)&&fs.realpathSync(path.dirname(output))===path.dirname(output));
 assert.equal(process.execArgv.length,0);assert(!process.env.NODE_OPTIONS&&!process.env.NODE_PATH);
 const tree=new Map();
 for(const row of execFileSync('git',['-C',repo,'ls-tree','-r','-l','-z',SOURCE_COMMIT,'--','data/geographic-releases'],{maxBuffer:cap}).toString().split('\0').filter(Boolean)) {
  const [meta,name]=row.split('\t'),[mode,type,oid,size]=meta.trim().split(/\s+/);tree.set(name,{mode,type,oid,bytes:Number(size)});
 }
 const expected=Array.from({length:340},(_,i)=>`data/geographic-releases/8-memberships-${i*250}.json.gz`);
 assert.deepEqual([...tree.keys()].filter(p=>/^data\/geographic-releases\/8-memberships-/.test(p)).sort(),[...expected].sort());
 const source=fs.mkdtempSync(path.join(temporaryRoot,'1295-release-memberships-source-')),roles={},ids=new Set();let rows=0,encodedBytes=0;
 for(const name of expected) {
  const pin=tree.get(name);assert(pin&&pin.mode==='100644'&&pin.type==='blob'&&pin.bytes>0&&pin.bytes<=cap);
  const raw=execFileSync('git',['-C',repo,'show',`${SOURCE_COMMIT}:${name}`],{maxBuffer:cap});
  assert.equal(raw.length,pin.bytes);assert.equal(blob(raw),pin.oid);
  const decoded=gunzipSync(raw,{maxOutputLength:1024*1024}),payload=JSON.parse(decoded);
  assert(Array.isArray(payload.memberships)&&payload.memberships.length>0&&payload.memberships.length<=250);
  assert.equal(payload.release_id,'geography:review:896bf79dd6e5661dfbbffba60da96fa987b9971af2b884cf52347189861ebe9e');
  for(const member of payload.memberships){assert(typeof member.entity_id==='string'&&!ids.has(member.entity_id));ids.add(member.entity_id);}
  rows+=payload.memberships.length;encodedBytes+=raw.length;
  const target=path.join(source,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,raw,{flag:'wx',mode:0o644});
  roles[name]={kind:'unaccepted-generated-v8-membership-output',commit:SOURCE_COMMIT,path:name,mode:pin.mode,blob:pin.oid,bytes:raw.length,sha256:sha(raw),decoded_bytes:decoded.length,decoded_sha256:sha(decoded),memberships:payload.memberships.length,scientific_records_recomputed:false};
 }
 assert.equal(rows,84833);assert.equal(ids.size,84833);
 const index=retainWholeImage(source,output,{roles}),indexRaw=fs.readFileSync(path.join(output,'index.json'));
 const inverse=path.join(temporaryRoot,`1295-release-memberships-inverse-${path.basename(source)}`);
 const restored=restoreWholeImage(output,inverse,{expectedIndexSha:sha(indexRaw)});assert.deepEqual(restored,index);
 for(const pin of index.files){const raw=fs.readFileSync(path.join(inverse,pin.path));assert.equal(blob(raw),pin.original_binding.blob);assert.equal(sha(raw),pin.original_binding.sha256);assert.equal((fs.statSync(path.join(inverse,pin.path)).mode&0o111)?'100755':'100644',pin.original_binding.mode);}
 return {version:1,issue:1295,kind:'whole-encoded-membership-tail-custody',source_commit:SOURCE_COMMIT,files:index.files.length,memberships:rows,encoded_original_bytes:encodedBytes,index_sha256:sha(indexRaw),transport_bytes:indexRaw.length+index.parts.reduce((n,p)=>n+p.bytes,0),source,inverse,scientific_records_recomputed:false,all_original_paths_modes_and_encoded_decoded_bodies_preserved:true,node:process.version,execArgv:process.execArgv};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
 const [repo,output,temporaryRoot]=process.argv.slice(2);console.log(JSON.stringify(packageReleaseMemberships({repo,output,temporaryRoot})));
}
