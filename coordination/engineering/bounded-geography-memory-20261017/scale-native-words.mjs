import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {wordAt,wordPin,gzipChunks,collect} from '../../../test/fixtures/native-word-store.mjs';
const dispersedWord=i=>{let x=(i+1)>>>0;x=Math.imul((x>>>16)^x,0x45d9f3b);x=Math.imul((x>>>16)^x,0x45d9f3b);return ((x>>>16)^x)>>>0;};
const [mode,wordsText]=process.argv.slice(2),words=Number(wordsText);
const checkout=fileURLToPath(new URL('../../../',import.meta.url));
const modulePath=path.join(checkout,mode==='window'?'scripts/native-word-store.mjs':'src/ownership-codec.js');
if(!['window','whole-buffer-kernel'].includes(mode)||!Number.isSafeInteger(words)||words<1)throw Error('mode and positive word count required');
const root=fs.mkdtempSync(path.join(process.env.SCALE_SCRATCH_PARENT??process.cwd(),'ci-native-scale-'));
const value=process.env.SCALE_PATTERN==='dispersed'?dispersedWord:wordAt;
let store;const snapshots=[],record=name=>snapshots.push({name,...process.memoryUsage(),maxRSS_KiB:process.resourceUsage().maxRSS});
try{
  const pin=await wordPin(words,{value});global.gc?.();record('before_open');
  const before=performance.now();let reads=0,maxRead=0,readBytes=0;
  const originalRead=fs.readSync;fs.readSync=(...args)=>{reads++;maxRead=Math.max(maxRead,args[3]);const n=originalRead(...args);readBytes+=n;return n;};
  let buffers;
  if(mode==='window'){
    const {openNativeWordStore}=await import(pathToFileURL(modulePath));
    store=await openNativeWordStore(gzipChunks(words,{value}),pin,{directory:root});
  }else{
    // Literal previous nativeAsset allocation sequence; codec is accepted production.
    const {unshuffleOwnershipBytes}=await import(pathToFileURL(modulePath));
    const encoded=await collect(gzipChunks(words,{value})),raw=gunzipSync(encoded,{maxOutputLength:pin.decoded_bytes});
    const decoded=unshuffleOwnershipBytes(raw,pin.words),canonical=Buffer.alloc(decoded.byteLength);
    for(let i=0;i<decoded.length;i++)canonical.writeUInt32LE(decoded[i],i*4);
    if(createHash('sha256').update(canonical).digest('hex')!==pin.decoded_sha256)throw Error('old canonical mismatch');
    buffers={encoded,raw,decoded,canonical};store={length:words,get:i=>decoded[i],close(){buffers=undefined;}};
  }
  record('after_open');const openMilliseconds=performance.now()-before;
  const hash=createHash('sha256'),window=Buffer.allocUnsafe(65536);
  for(let at=0;at<words;at+=16384){const count=Math.min(16384,words-at);for(let j=0;j<count;j++){const actual=store.get(at+j);if(actual!==value(at+j))throw Error('word mismatch '+(at+j));window.writeUInt32LE(actual,j*4);}hash.update(window.subarray(0,count*4));}
  if(hash.digest('hex')!==pin.decoded_sha256)throw Error('complete stream mismatch');
  record('after_complete_scan');
  const spoolBytes=fs.readdirSync(root).reduce((sum,name)=>sum+fs.readdirSync(path.join(root,name)).reduce((n,member)=>n+fs.statSync(path.join(root,name,member)).size,0),0);
  store.close();store=undefined;global.gc?.();record('after_close');
  console.log(JSON.stringify({pattern:process.env.SCALE_PATTERN??'multiplicative',scratchParent:process.env.SCALE_SCRATCH_PARENT??process.cwd(),mode,words,decodedBytes:words*4,encodedBytes:pin.bytes,canonical_sha256:pin.decoded_sha256,openMilliseconds,totalMilliseconds:performance.now()-before,reads,maxRead,readBytes,spoolBytes,cleanupEntries:fs.readdirSync(root).length,snapshots},null,2));
}finally{store?.close();fs.rmSync(root,{recursive:true,force:true});}
