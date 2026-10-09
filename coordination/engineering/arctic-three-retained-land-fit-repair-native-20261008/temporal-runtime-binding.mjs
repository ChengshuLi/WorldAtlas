// Exact header-only transport continuation. Every factual/evidence/interval
// payload byte is preserved; all original gzip paths remain available.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
const sha=b=>createHash('sha256').update(b).digest('hex');
export function continueTemporalBucket(encoded,pin,{originalSourceSha,currentSourceSha}){
 assert(/^[a-f0-9]{64}$/.test(originalSourceSha)&&/^[a-f0-9]{64}$/.test(currentSourceSha));
 assert.equal(encoded.length,pin.compressed_bytes);assert.equal(sha(encoded),pin.sha256);
 assert(Number.isSafeInteger(pin.uncompressed_bytes)&&pin.uncompressed_bytes>0&&pin.uncompressed_bytes<=32*1024*1024);
 const original=gunzipSync(encoded,{maxOutputLength:pin.uncompressed_bytes});assert.equal(original.length,pin.uncompressed_bytes);
 const boundary=original.indexOf(Buffer.from('"parts":'));assert(boundary>0&&boundary<4096,'Original typed bucket header required');
 const prefix=original.subarray(0,boundary).toString('utf8');
 const pattern=/"source_index_sha256"\s*:\s*"([a-f0-9]{64})"/g;const matches=[...prefix.matchAll(pattern)];assert.equal(matches.length,1);assert.equal(matches[0][1],originalSourceSha);
 const characterOffset=matches[0].index+matches[0][0].lastIndexOf(originalSourceSha);
 const start=Buffer.byteLength(prefix.slice(0,characterOffset),'utf8');
 const changed=Buffer.from(original);changed.write(currentSourceSha,start,64,'ascii');
 assert(changed.subarray(0,start).equals(original.subarray(0,start)));assert(changed.subarray(start+64).equals(original.subarray(start+64)));
 const inverse=Buffer.from(changed);inverse.write(originalSourceSha,start,64,'ascii');assert(inverse.equals(original));
 const current=gzipSync(changed,{level:9});assert(current.length<=8*1024*1024);assert(gunzipSync(current,{maxOutputLength:pin.uncompressed_bytes}).equals(changed));
 return {bytes:current,pin:{...pin,sha256:sha(current),compressed_bytes:current.length},proof:{original_encoded_sha256:pin.sha256,original_decoded_sha256:sha(original),successor_decoded_sha256:sha(changed),source_index_offset:start,unchanged_payload_bytes:original.length-64,original_decoded_inverse_sha256:sha(inverse),original_encoded_bytes_retained:true,temporal_records_recomputed:false}};
}
