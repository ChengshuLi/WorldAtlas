// Job-scoped use of the existing ordered exact-byte fragment transport.
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import{createHash}from'node:crypto';import{gzipSync,gunzipSync}from'node:zlib';
const sha=b=>createHash('sha256').update(b).digest('hex'),CAP=32*1024*1024,PART=16*1024*1024;
const safe=p=>typeof p==='string'&&!path.isAbsolute(p)&&p.split('/').every(x=>x&&x!=='.'&&x!=='..')&&!p.includes('\\');
function bytes(root,p){assert(safe(p));const file=path.join(root,p),stat=fs.lstatSync(file);assert(stat.isFile()&&fs.realpathSync(file)===file&&stat.size<=CAP);return fs.readFileSync(file);}
function files(root,prefix=''){return fs.readdirSync(path.join(root,prefix),{withFileTypes:true}).flatMap(e=>{const p=prefix?prefix+'/'+e.name:e.name;assert(!e.isSymbolicLink());return e.isDirectory()?files(root,p):[p];}).sort();}
export function retainWholeImage(source,out,{roles={}}={}){
 assert(fs.realpathSync(source)===source&&path.isAbsolute(out)&&!fs.existsSync(out)&&fs.realpathSync(path.dirname(out))===path.dirname(out));fs.mkdirSync(out);
 let pending=Buffer.alloc(0),offset=0,partOffset=0;const index={version:1,issue:1295,kind:'ordered-exact-original-byte-fragments',files:[],parts:[]},whole=createHash('sha256');
 function flush(){if(!pending.length)return;const name=`part-${String(index.parts.length).padStart(3,'0')}.bin.gz`,raw=gzipSync(pending,{level:9});assert(raw.length<=CAP&&pending.length<=PART);fs.writeFileSync(path.join(out,name),raw,{flag:'wx'});index.parts.push({path:name,offset:partOffset,bytes:raw.length,sha256:sha(raw),decoded_bytes:pending.length,decoded_sha256:sha(pending)});partOffset+=pending.length;pending=Buffer.alloc(0);}
 for(const p of files(source)){const raw=bytes(source,p),mode=(fs.statSync(path.join(source,p)).mode&0o111)?'100755':'100644';whole.update(raw);index.files.push({path:p,offset,bytes:raw.length,sha256:sha(raw),mode,...roles[p]});offset+=raw.length;
  for(let first=0;first<raw.length;){const n=Math.min(PART-pending.length,raw.length-first);pending=Buffer.concat([pending,raw.subarray(first,first+n)]);first+=n;if(pending.length===PART)flush();}
 }flush();assert.equal(partOffset,offset);index.whole_bytes=offset;index.whole_sha256=whole.digest('hex');fs.writeFileSync(path.join(out,'index.json'),JSON.stringify(index)+'\n',{flag:'wx'});return index;
}
export function restoreWholeImage(source,out,{expectedIndexSha}={}){
 assert(fs.realpathSync(source)===source&&path.isAbsolute(out)&&!fs.existsSync(out)&&fs.realpathSync(path.dirname(out))===path.dirname(out));
 const indexRaw=bytes(source,'index.json');assert.equal(sha(indexRaw),expectedIndexSha,'Whole image index binding differs');const index=JSON.parse(indexRaw);
 assert.equal(index.version,1);assert.equal(index.issue,1295);assert.equal(index.kind,'ordered-exact-original-byte-fragments');
 const chunks=[];let offset=0;const names=new Set();for(const pin of index.parts){assert(safe(pin.path)&&!names.has(pin.path));names.add(pin.path);assert.equal(pin.offset,offset);assert(pin.decoded_bytes>0&&pin.decoded_bytes<=PART&&pin.bytes>0&&pin.bytes<=CAP);const encoded=bytes(source,pin.path);assert.equal(encoded.length,pin.bytes);assert.equal(sha(encoded),pin.sha256);const raw=gunzipSync(encoded,{maxOutputLength:PART});assert.equal(raw.length,pin.decoded_bytes);assert.equal(sha(raw),pin.decoded_sha256);chunks.push(raw);offset+=raw.length;}
 assert.equal(offset,index.whole_bytes);assert(offset<=512*1024*1024,'Bounded original fixed image required');const whole=Buffer.concat(chunks);assert.equal(sha(whole),index.whole_sha256);
 const memberNames=new Set();offset=0;for(const pin of index.files){assert(safe(pin.path)&&!memberNames.has(pin.path));memberNames.add(pin.path);assert.equal(pin.offset,offset);assert(pin.bytes>0&&pin.bytes<=CAP&&['100644','100755'].includes(pin.mode));const raw=whole.subarray(offset,offset+pin.bytes);assert.equal(raw.length,pin.bytes);assert.equal(sha(raw),pin.sha256);offset+=pin.bytes;}
 assert.equal(offset,whole.length,'Original image roster omits bytes');fs.mkdirSync(out);
 for(const pin of index.files){const name=path.join(out,pin.path);fs.mkdirSync(path.dirname(name),{recursive:true});assert(fs.realpathSync(path.dirname(name))===path.dirname(name));fs.writeFileSync(name,whole.subarray(pin.offset,pin.offset+pin.bytes),{flag:'wx',mode:pin.mode==='100755'?0o755:0o644});}
 return index;
}
