import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {admitNativeEnvelopeStore} from '../scripts/native-patch-store.mjs';
import {valueBytes,valueSha} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {nativeLiteral} from './helpers/native-literal.mjs';
const hash=b=>createHash('sha256').update(b).digest('hex');
const directory=t=>{const root=fs.mkdtempSync(path.join(os.tmpdir(),'native-envelope-test-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));return root;};
const open=(root,text,options={})=>{const body=Buffer.from(text);return admitNativeEnvelopeStore({directory:root,size:100,ownerCount:3,chunks:(function*(){for(let i=0;i<body.length;i+=17)yield body.subarray(i,i+17);})(),expected:{bytes:body.length,sha256:hash(body)},...options});};

test('nested native rows and root metadata vectors retain exact whole canonical values and lookup',async t=>{
 const value={current_rows:[{y:1,runs:[[0,2,1]]}],current_targets:[{id:'a',geometry:{coordinates:[[1,2],[3,4]]}}],
  acquisition:{predecessor_rows:[{y:2,runs:[[3,5,2]]}],native_inputs:[{path:'x',bytes:2}]},native:{rows:[{y:3,runs:[]}]},scope_ids:['a','b']};
 const store=await open(directory(t),JSON.stringify(value));
 assert.deepEqual(nativeLiteral(store.metadata),value);assert.equal(store.canonical_sha256,hash(valueBytes(value)));
 assert.equal(valueSha(store.metadata),hash(valueBytes(value)));
 assert.deepEqual(store.metadata.current_targets.at(0),value.current_targets[0]);
 assert.deepEqual([...store.metadata.scope_ids],value.scope_ids);
 const target=store.metadata.current_targets.at(0);assert.throws(()=>target.id='mutated',TypeError);
 store.close();assert.throws(()=>store.metadata.current_targets.at(0),/closed/);
});

test('nested duplicate fields keep last-key-wins, including overwritten invalid domains and metadata',async t=>{
 const text='{"current_rows":[{"y":-1,"runs":[]}],"current_rows":[{"y":2,"runs":[]}],"scope_ids":[1e400],"scope_ids":["final"],"acquisition":{"predecessor_rows":[{"y":-1,"runs":[]}]},"acquisition":{"predecessor_rows":[]}}';
 const store=await open(directory(t),text);assert.deepEqual(nativeLiteral(store.metadata),JSON.parse(text));
 assert.equal(store.canonical_sha256,hash(valueBytes(JSON.parse(text))));store.close();
});

test('late syntax, final row domains, metadata and whole identities refuse before exposing an envelope',async t=>{
 const root=directory(t);
 for(const text of ['{"current_rows":[{"y":-1,"runs":[]}]}','{"current_rows":[],"scope_ids":[1e400]}','{"current_rows":[]} trailing','{"current_rows":[,],"current_rows":[]}']){
  await assert.rejects(open(root,text));assert.deepEqual(fs.readdirSync(root),[]);
 }
 const text='{"current_rows":[]}';await assert.rejects(open(root,text,{expected:{bytes:text.length,sha256:'0'.repeat(64)}}),/identity/);
 assert.deepEqual(fs.readdirSync(root),[]);
});

test('growing root target metadata is spooled under a fixed heap with exact ordered canonical output',t=>{
 const root=directory(t),module=new URL('../scripts/native-patch-store.mjs',import.meta.url).href;
 const helper=new URL('../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs',import.meta.url).href;
 const grid=new URL('../src/native-grid.js',import.meta.url).href;
 const source=`import {admitNativeEnvelopeStore} from ${JSON.stringify(module)};import {valueSha} from ${JSON.stringify(helper)};import {nativeSequence} from ${JSON.stringify(grid)};import {createHash} from 'node:crypto';
 const count=10000,item=i=>({id:String(i),metadata:'x'.repeat(8192)});
 function* chunks(){yield Buffer.from('{"current_rows":[],"current_targets":[');for(let i=0;i<count;i++)yield Buffer.from((i?',':'')+JSON.stringify(item(i)));yield Buffer.from(']}');}
 let bytes=0,h=createHash('sha256');for(const body of chunks()){bytes+=body.length;h.update(body);}
 const store=await admitNativeEnvelopeStore({directory:${JSON.stringify(root)},size:100,ownerCount:3,chunks:chunks(),expected:{bytes,sha256:h.digest('hex')}});
 const expected=valueSha({current_rows:[],current_targets:nativeSequence(count,function*(){for(let i=0;i<count;i++)yield item(i);})});
 if(store.canonical_sha256!==expected||valueSha(store.metadata)!==expected)throw Error('whole canonical output changed');
 let n=0;for(const row of store.metadata.current_targets){if(row.id!==String(n++)||row.metadata!=='x'.repeat(8192))throw Error('ordered metadata changed');}
 if(n!==count)throw Error('omitted target');console.log(JSON.stringify({bytes,count,largest_metadata:8192,stored_bytes:store.storedBytes,rss:process.memoryUsage().rss}));store.close();`;
 const result=spawnSync(process.execPath,['--max-old-space-size=48','--input-type=module','-e',source],{encoding:'utf8',maxBuffer:1024*1024});
 assert.equal(result.status,0,result.stderr);const measured=JSON.parse(result.stdout);assert.equal(measured.count,10000);assert(measured.bytes>80*1024*1024-4*1024*1024);
 assert.deepEqual(fs.readdirSync(root),[]);
});
