import fs from 'node:fs';
import path from 'node:path';
import {gzipSync,gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {shuffleOwnershipBytes,unshuffleOwnershipBytes,encodeOwnershipVarints,decodeOwnershipVarints} from '../src/ownership-codec.js';
const root='.cache/compact-ownership-benchmark',results=[];
for(const zoom of [7,9,10]){
 const directory=path.join(root,String(zoom)),manifest=JSON.parse(fs.readFileSync(path.join(directory,'manifest.json'))),rows=new Uint32Array(manifest.size*2);
 for(const p of manifest.parts.filter(p=>p.kind==='rows')){const bytes=gunzipSync(fs.readFileSync(path.join(directory,p.path)));rows.set(new Uint32Array(bytes.buffer,bytes.byteOffset,bytes.length/4),p.offset);}
 for(const encoding of ['byte-shuffle','row-varint']){
  const dest=path.join(directory,encoding);fs.mkdirSync(dest,{recursive:true});const started=performance.now(),parts=[];let gzip=0,encoded=0,decodedWords=0,maxPart=0;
  for(const p of manifest.parts){
   const bytes=gunzipSync(fs.readFileSync(path.join(directory,p.path))),words=new Uint32Array(bytes.buffer,bytes.byteOffset,bytes.length/4),codec=p.kind==='rows'?'byte-shuffle':encoding;
   const raw=codec==='byte-shuffle'?shuffleOwnershipBytes(words):encodeOwnershipVarints(words,{rows,offset:p.offset,coordinateBits:manifest.coordinateBits});
   const decoded=codec==='byte-shuffle'?unshuffleOwnershipBytes(raw,p.words):decodeOwnershipVarints(raw,{rows,offset:p.offset,words:p.words,coordinateBits:manifest.coordinateBits,size:manifest.size});
   for(let k=0;k<words.length;k++)if(words[k]!==decoded[k])throw Error('Transport changed canonical word');decodedWords+=words.length;
   const compressed=gzipSync(raw,{level:9});fs.writeFileSync(path.join(dest,p.path),compressed);gzip+=compressed.length;encoded+=raw.length;maxPart=Math.max(maxPart,compressed.length);parts.push({...p,encoding:codec,encoded_sha256:createHash('sha256').update(raw).digest('hex')});
  }
  const stats={...manifest.stats,transport:encoding,gzip_bytes:gzip,encoded_before_gzip_bytes:encoded,maximum_part_bytes:maxPart,transport_prepare_verify_ms:Math.round(performance.now()-started),decoded_words_exactly_verified:decodedWords};fs.writeFileSync(path.join(dest,'manifest.json'),JSON.stringify({...manifest,parts,stats}));results.push(stats);console.log(JSON.stringify(stats));
 }
}
fs.writeFileSync(path.join(root,'transport-results.json'),JSON.stringify({method:'Transports encode cached actual complete-world compact grids; every decoded Uint32 word compared exactly, including row crossings and arbitrary chunk crossings.',results},null,2));
