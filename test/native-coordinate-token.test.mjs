import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {admitNativeMetadataStore} from '../scripts/native-patch-store.mjs';
import {valueSha} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {nativeLiteral} from './helpers/native-literal.mjs';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
async function inspect(text,chunkBytes,consume){
 const raw=Buffer.from(text),directory=fs.mkdtempSync(path.join(os.tmpdir(),'coordinate-token-'));let store;
 try{store=await admitNativeMetadataStore({directory,chunks:(function*(){for(let i=0;i<raw.length;i+=chunkBytes)yield raw.subarray(i,i+chunkBytes);})(),expected:{bytes:raw.length,sha256:sha(raw)}});consume(store.metadata);}
 finally{store?.close();assert.deepEqual(fs.readdirSync(directory),[]);fs.rmdirSync(directory);}
}
test('in-chunk coordinate tuples preserve JSON number semantics and every byte split',async()=>{
 const text='{"coordinates":[[ -0, 5e-324 ],[1.7976931348623157e308,-1e-4000],[1e400,-1e400],[2E+3,0.25], ["雪",1], [1,2,3], [], [[1,2]]] }';
 for(let chunk=1;chunk<=Buffer.byteLength(text)+1;chunk++)await inspect(text,chunk,value=>assert.deepEqual(nativeLiteral(value),JSON.parse(text)));
});
test('coordinate tuple framing preserves malformed JSON refusals and cleanup at every split',async()=>{
 for(const tuple of ['[1e,2]','[+1,2]','[01,2]','[1,]','[,2]','[1 2,3]','[1,2'] ){
  const text='{"coordinates":['+tuple+']}';for(let chunk=1;chunk<=text.length+1;chunk++)
   await assert.rejects(inspect(text,chunk,()=>assert.fail('Malformed input admitted')),SyntaxError);
 }
});
test('large valid scalar, duplicate keys and spilled pair arrays remain exact',async()=>{
 const tuple='[0.'+'0'.repeat(70000)+'1,-0]',pairs=Array.from({length:65},(_,i)=>`[${i},-${i}]`).join(',');
 for(const text of ['{"coordinates":['+tuple+']}','{"coordinates":[[1e400,2]],"coordinates":['+pairs+']}'])
  for(const chunk of [17,65536,Buffer.byteLength(text)+1])await inspect(text,chunk,value=>assert.deepEqual(nativeLiteral(value),JSON.parse(text)));
});

test('tuple framing keeps exact semantic canonical identity across spill and chunk boundaries',async()=>{
 const text='{"coordinates":['+Array(65).fill('[ -0, 1.25e+2 ]').join(',')+']}';
 for(const chunk of [1,17,31,64,65536])await inspect(text,chunk,value=>assert.equal(valueSha(value),valueSha(JSON.parse(text))));
});
