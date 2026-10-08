// Directed actual acquisition/inverse controls; no geographic calculation.
import fs from 'node:fs';import assert from 'node:assert/strict';import path from 'node:path';
import {gunzipSync,gzipSync}from'node:zlib';import{createHash}from'node:crypto';
import{acquireOriginalContextPair,constructAliasedContextChunk}from'./context-record-alias.mjs';
const [fixture,destination]=process.argv.slice(2),pins=JSON.parse(fs.readFileSync(fixture)),sha=b=>createHash('sha256').update(b).digest('hex');
assert(!fs.existsSync(destination));fs.mkdirSync(destination);const root=fs.realpathSync(destination);
const pin=p=>({bytes:p.encoded_bytes,sha256:p.encoded_sha256,decoded_bytes:p.decoded_bytes,decoded_sha256:p.decoded_sha256,mode:'100644'});
const [a,b]=pins,args={beforeFile:a.physical_path,afterFile:b.physical_path,beforePin:pin(a),afterPin:pin(b),runtimeBytes:fs.statSync(process.execPath).size,codeBytes:1048576};
const pair=acquireOriginalContextPair(args),base=gunzipSync(fs.readFileSync(a.physical_path)),current=gunzipSync(fs.readFileSync(b.physical_path));
assert.deepEqual(constructAliasedContextChunk(base,pair).rows,JSON.parse(current));assert.deepEqual(constructAliasedContextChunk(current,pair,{baseSide:1}).rows,JSON.parse(base));
assert.throws(()=>constructAliasedContextChunk(base,structuredClone(pair)),/live authenticated/);
const altered=Buffer.from(base);altered[100]^=1;assert.throws(()=>constructAliasedContextChunk(altered,pair));
let opens=0;const open=fs.openSync;fs.openSync=function(...args){opens++;return open.apply(this,args);};
try{assert.throws(()=>acquireOriginalContextPair({...args,codeBytes:256*1024*1024}),/before body opens/);assert.equal(opens,0);}finally{fs.openSync=open;}
function adverse(name,transform){const rows=JSON.parse(current);transform(rows);const decoded=Buffer.from(JSON.stringify(rows)),raw=gzipSync(decoded),file=path.join(root,name+'.gz');fs.writeFileSync(file,raw);
 assert.throws(()=>acquireOriginalContextPair({...args,afterFile:file,afterPin:{bytes:raw.length,sha256:sha(raw),decoded_bytes:decoded.length,decoded_sha256:sha(decoded),mode:'100644'}}));}
adverse('omitted',rows=>rows.pop());adverse('reordered',rows=>rows.reverse());adverse('foreign',rows=>rows[0].id='foreign');adverse('duplicate',rows=>rows[1].id=rows[0].id);
const link=path.join(root,'link.gz');fs.symlinkSync(b.physical_path,link);assert.throws(()=>acquireOriginalContextPair({...args,afterFile:link}));
pair.changes[0].after[0]^=1;assert.throws(()=>constructAliasedContextChunk(base,pair),/live authenticated/);
console.log(JSON.stringify({status:'PASS',full_rows:JSON.parse(base).length,whole_inverse_both_directions:true,negative_controls:9,oversized_body_opens:opens,scientific_operators_invoked:false}));
