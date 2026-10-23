import {createHash} from 'node:crypto';
import {Readable} from 'node:stream';
import {createGzip} from 'node:zlib';
export const digest=body=>createHash('sha256').update(body).digest('hex');
// Independent numerical source. All four bytes vary; no production codec used.
export function wordAt(i){return (Math.imul(i+1,0x9e3779b1)^(Math.floor(i/65536)*0x85ebca6b)^0xa5c37e19)>>>0;}
export function* shuffledChunks(words,{chunkBytes=65536,value=wordAt}={}){
  for(let plane=0;plane<4;plane++)for(let at=0;at<words;at+=chunkBytes){
    const out=Buffer.allocUnsafe(Math.min(chunkBytes,words-at));
    for(let j=0;j<out.length;j++)out[j]=(value(at+j)>>>8*plane)&255;
    yield out;
  }
}
export function canonicalHash(words,value=wordAt){
  const hash=createHash('sha256');
  for(let at=0;at<words;at+=16384){
    const out=Buffer.allocUnsafe(Math.min(16384,words-at)*4);
    for(let j=0;j<out.length/4;j++)out.writeUInt32LE(value(at+j),j*4);
    hash.update(out);
  }
  return hash.digest('hex');
}
export function gzipChunks(words,options={}){return Readable.from(shuffledChunks(words,options)).pipe(createGzip());}
export async function wordPin(words,options={}){
  const hash=createHash('sha256');let bytes=0;
  for await(const chunk of gzipChunks(words,options)){hash.update(chunk);bytes+=chunk.length;}
  return {words,decoded_bytes:words*4,bytes,sha256:hash.digest('hex'),decoded_sha256:canonicalHash(words,options.value)};
}
export async function collect(iterable){const chunks=[];for await(const chunk of iterable)chunks.push(chunk);return Buffer.concat(chunks);}
