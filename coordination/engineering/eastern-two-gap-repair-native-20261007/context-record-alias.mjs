// Whole original JSON-record aliases for this fixed three-context continuation.
// No numerical method, gzip encoder, or geometry normalization participates.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
const CAP=32*1024*1024,TOTAL=256*1024*1024;
const sha=b=>createHash('sha256').update(b).digest('hex');
const retained=new WeakMap();
export function splitOriginalContextRecords(raw){
 const whitespace=c=>[9,10,13,32].includes(c);let i=0;
 while(whitespace(raw[i]))i++;assert.equal(raw[i++],91);
 const prefix=raw.subarray(0,i),rows=[],separators=[];let end=i;
 for(;;){
  while(whitespace(raw[i])||raw[i]===44)i++;
  if(raw[i]===93)break;
  separators.push(raw.subarray(end,i));const start=i;assert.equal(raw[i],123);
  let depth=0,quoted=false,escaped=false;
  for(;i<raw.length;i++){
   const c=raw[i];if(quoted){if(escaped)escaped=false;else if(c===92)escaped=true;else if(c===34)quoted=false;continue;}
   if(c===34){quoted=true;continue;}if(c===123||c===91)depth++;if(c===125||c===93)depth--;
   if(depth===0){i++;break;}
  }
  assert(!quoted&&depth===0&&i<=raw.length);const bytes=raw.subarray(start,i),value=JSON.parse(bytes);
  assert(typeof value.id==='string'&&Number.isSafeInteger(value.pixelIndex));rows.push({raw:bytes,value});end=i;
 }
 const suffix=raw.subarray(end);assert(/^[\t\r\n ]*\[$/.test(prefix.toString()));assert(/^[\t\r\n ]*\][\t\r\n ]*$/.test(suffix.toString()));
 for(let j=0;j<separators.length;j++)assert((j?/^[\t\r\n ]*,[\t\r\n ]*$/:/^[\t\r\n ]*$/).test(separators[j].toString()));
 assert.equal(new Set(rows.map(r=>r.value.id)).size,rows.length);
 return {prefix,rows,separators,suffix};
}
function ordinary(file,pin){
 const stat=fs.lstatSync(file);assert(stat.isFile()&&fs.realpathSync(file)===file&&stat.size===pin.bytes&&stat.size<=CAP);
 assert.equal((stat.mode&0o111)?'100755':'100644',pin.mode??'100644');
 const fd=fs.openSync(file,'r');let raw;
 try{assert.equal(fs.fstatSync(fd).size,stat.size);raw=Buffer.alloc(stat.size+1);let offset=0;
  while(offset<raw.length){const n=fs.readSync(fd,raw,offset,raw.length-offset,null);if(!n)break;offset+=n;}
  assert.equal(offset,stat.size);assert.equal(fs.readSync(fd,Buffer.alloc(1),0,1,null),0);raw=raw.subarray(0,offset);
 }finally{fs.closeSync(fd);}assert.equal(sha(raw),pin.sha256);return raw;
}
export const readContextBody=ordinary;
export function acquireOriginalContextPair({beforeFile,afterFile,beforePin,afterPin,afterRaw,runtimeBytes,codeBytes,reserveBytes=131072}){
 const decoded=pin=>pin.decoded_bytes??pin.uncompressed_bytes;
 const retainedOutputReserve=decoded(beforePin)+decoded(afterPin)+reserveBytes;
 let total=runtimeBytes+codeBytes+retainedOutputReserve;assert(Number.isSafeInteger(total)&&total>=0);
 for(const pin of [beforePin,afterPin])for(const n of [pin.bytes,decoded(pin)]){assert(Number.isSafeInteger(n)&&n>0&&n<=CAP);total+=n;}
 assert(total<=TOTAL,'Complete context acquisition exceeds budget before body opens');
 if(afterRaw){assert(Buffer.isBuffer(afterRaw));assert.equal(afterRaw.length,afterPin.bytes);assert.equal(sha(afterRaw),afterPin.sha256);}
 const bodies=[ordinary(beforeFile,beforePin),afterRaw??ordinary(afterFile,afterPin)],pins=[beforePin,afterPin];
 const chunks=bodies.map((raw,i)=>{const result=gunzipSync(raw,{maxOutputLength:CAP});assert.equal(result.length,decoded(pins[i]));assert.equal(sha(result),pins[i].decoded_sha256??pins[i].uncompressed_sha256);return splitOriginalContextRecords(result);});
 const [before,after]=chunks;assert.deepEqual(before.rows.map(r=>[r.value.id,r.value.pixelIndex]),after.rows.map(r=>[r.value.id,r.value.pixelIndex]));
 const changes=[];
 for(let i=0;i<before.rows.length;i++)if(!before.rows[i].raw.equals(after.rows[i].raw))changes.push({ordinal:i,id:before.rows[i].value.id,before_sha256:sha(before.rows[i].raw),after_sha256:sha(after.rows[i].raw),before:Buffer.from(before.rows[i].raw),after:Buffer.from(after.rows[i].raw)});
 const result={beforePin:structuredClone(beforePin),afterPin:structuredClone(afterPin),row_count:before.rows.length,changes,
  layouts:[before,after].map(c=>({prefix:Buffer.from(c.prefix),separators:c.separators.map(b=>Buffer.from(b)),suffix:Buffer.from(c.suffix)})),
  budget:{complete_phase_bytes:total,installed_runtime_bytes:runtimeBytes,actual_code_bytes:codeBytes,reserved_output_review_bytes:retainedOutputReserve,small_metadata_reserve_bytes:reserveBytes},
  original_encoded_sha256:bodies.map(sha),original_decoded_sha256:pins.map(p=>p.decoded_sha256??p.uncompressed_sha256)};
 retained.set(result,sha(Buffer.from(JSON.stringify(result))));return result;
}
export function constructAliasedContextChunk(baseRaw,pair,{baseSide=0}={}){
 assert.equal(retained.get(pair),sha(Buffer.from(JSON.stringify(pair))),'Only live authenticated whole-original acquisition may issue record aliases');
 assert(baseSide===0||baseSide===1);const pin=baseSide?pair.afterPin:pair.beforePin;
 assert.equal(baseRaw.length,pin.decoded_bytes??pin.uncompressed_bytes);assert.equal(sha(baseRaw),pin.decoded_sha256??pin.uncompressed_sha256);
 const base=splitOriginalContextRecords(baseRaw);assert.equal(base.rows.length,pair.row_count);const other=1-baseSide;
 const rows=base.rows.map(r=>r.value),rawRows=base.rows.map(r=>r.raw);
 for(const change of pair.changes){assert.equal(rows[change.ordinal].id,change.id);assert.equal(sha(rawRows[change.ordinal]),baseSide?change.after_sha256:change.before_sha256);
  const raw=other?change.after:change.before;rawRows[change.ordinal]=raw;rows[change.ordinal]=JSON.parse(raw);
 }
 const layout=pair.layouts[other],hash=createHash('sha256');hash.update(layout.prefix);
 for(let i=0;i<rawRows.length;i++){hash.update(layout.separators[i]);hash.update(rawRows[i]);}hash.update(layout.suffix);
 assert.equal(hash.digest('hex'),pair.original_decoded_sha256[other],'Complete original reconstructed context bytes changed');
 return {rows,original_rows:base.rows.map(r=>r.value),whole_original_decoded_sha256:pair.original_decoded_sha256[other],changed_records:pair.changes.length};
}
