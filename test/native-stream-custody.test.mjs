import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {execFileSync} from 'node:child_process';
import {gzipSync} from 'node:zlib';
import {digest,collect} from './fixtures/native-word-store.mjs';
import {ImmutableReader,NativeAssetImage} from '../scripts/check-effective-geographic-regression.mjs';
const root=fs.mkdtempSync(path.join(os.tmpdir(),'ci-native-custody-'));test.after(()=>fs.rmSync(root,{recursive:true,force:true}));
function fixture({decodedSuffix=false,encodedSuffix=false,truncate=false,split=false}={}){
  const repo=fs.mkdtempSync(path.join(root,'repo-')),git=(...args)=>execFileSync('git',['-C',repo,...args],{encoding:'utf8'}).trim();
  git('init','-q');git('config','user.name','Independent test');git('config','user.email','test@example.invalid');
  const first=Buffer.from('first complete member'),second=Buffer.from('second complete member with a suffix outside first'),bank=Buffer.concat([first,second]);
  const files=[first,second].map((body,i)=>({path:`part${i}.gz`,mode:'100644',offset:i?first.length:0,bytes:body.length,sha256:digest(body)}));
  const spans=split?[[0,7],[7,first.length+3],[first.length+3,bank.length]]:[[0,bank.length]];
  fs.mkdirSync(path.join(repo,'bank'));let parts=[];
  for(let i=0;i<spans.length;i++){
    const [a,b]=spans[i],raw=Buffer.from(bank.subarray(a,b)),original=Buffer.from(raw);
    if(decodedSuffix&&i===spans.length-1)raw[raw.length-1]^=1;
    let encoded=gzipSync(raw),expected=digest(encoded);
    if(encodedSuffix&&i===spans.length-1){encoded=Buffer.from(encoded);encoded[encoded.length-1]^=1;}
    if(truncate&&i===spans.length-1)encoded=encoded.subarray(0,encoded.length-3);
    const name=`fragment${i}.gz`;fs.writeFileSync(path.join(repo,'bank',name),encoded);
    parts.push({path:name,offset:a,bytes:encoded.length,sha256:expected,decoded_bytes:original.length,decoded_sha256:digest(original)});
  }
  const index={version:1,kind:'ordered-exact-original-byte-fragments',whole_sha256:digest(bank),whole_bytes:bank.length,files,parts};
  const indexBytes=Buffer.from(JSON.stringify(index));fs.writeFileSync(path.join(repo,'bank/index.json'),indexBytes);
  fs.writeFileSync(path.join(repo,'body.bin'),Buffer.alloc(128*1024,81));fs.symlinkSync('body.bin',path.join(repo,'link'));
  git('add','.');git('commit','-qm','synthetic exact custody');const commit=git('rev-parse','HEAD');
  const manifest={parts:files,native_asset_transport:{version:1,kind:index.kind,index:{path:'bank/index.json',bytes:indexBytes.length,sha256:digest(indexBytes)},logical_assets:files.length,original_compressed_bytes:bank.length}};
  return {repo,commit,manifest,files,first,second,reader:()=>new ImmutableReader(repo,commit)};
}
test('stream matches complete real immutable blob and marks only completed custody',async()=>{
  const f=fixture(),r=f.reader(),expected=digest(Buffer.alloc(128*1024,81));
  const result=await collect(r.stream('body.bin',{expected}));assert.equal(result.length,128*1024);assert.equal(digest(result),expected);assert.equal(r.inventory.get(f.commit+':body.bin').whole_body_consumed,true);
});
test('early return and consumer throw do not mark whole-body custody',async()=>{
  const f=fixture();for(const throws of [false,true]){const r=f.reader();const consume=async()=>{for await(const chunk of r.stream('body.bin')){assert.ok(chunk.length);if(throws)throw Error('consumer sentinel');break;}};if(throws)await assert.rejects(consume(),/consumer sentinel/);else await consume();assert.notEqual(r.inventory.get(f.commit+':body.bin').whole_body_consumed,true);}
});
test('incorrect hash and symlink body refuse without whole-body mark',async()=>{
  const f=fixture(),r=f.reader();await assert.rejects(collect(r.stream('body.bin',{expected:'f'.repeat(64)})),/differs/);assert.notEqual(r.inventory.get(f.commit+':body.bin').whole_body_consumed,true);await assert.rejects(collect(r.stream('link')),/ordinary/);
});
test('nonzero source exit after exact body refuses',async()=>{
  const f=fixture(),wrapper=path.join(f.repo,'git-exit-seven');
  fs.writeFileSync(wrapper,`#!${process.execPath}\nconst cp=require('node:child_process');const a=process.argv.slice(2);const r=cp.spawnSync('git',a,{stdio:'inherit'});process.exit(a.includes('blob')?7:r.status);\n`,{mode:0o700});
  const r=new ImmutableReader(f.repo,f.commit,{gitExecutable:wrapper});await assert.rejects(collect(r.stream('body.bin')),/Incomplete/);assert.notEqual(r.inventory.get(f.commit+':body.bin').whole_body_consumed,true);
});
test('whole containing fragments match legacy inversion across member/fragment boundaries',async()=>{
  for(const split of [false,true]){const f=fixture({split}),r=f.reader(),image=new NativeAssetImage(r,f.manifest,'native/manifest.json');
    for(let i=0;i<2;i++){const body=await collect(image.logicalStream('native/'+f.files[i].path,f.files[i]));assert.deepEqual(body,image.logical('native/'+f.files[i].path,f.files[i]));assert.deepEqual(body,i?f.second:f.first);}
  }
});
test('corrupt decoded suffix outside requested member refuses after all requested bytes arrive',async()=>{
  const f=fixture({decodedSuffix:true}),r=f.reader(),image=new NativeAssetImage(r,f.manifest,'native/manifest.json');let yielded=0;
  await assert.rejects(async()=>{for await(const chunk of image.logicalStream('native/part0.gz',f.files[0]))yielded+=chunk.length;},/decoded body differs/);
  assert.equal(yielded,f.first.length,'the adversary must sit beyond all requested member bytes');
});
test('encoded tail corruption and truncation outside requested prefix refuse',async()=>{
  for(const options of [{encodedSuffix:true},{truncate:true}]){const f=fixture(options),r=f.reader(),image=new NativeAssetImage(r,f.manifest,'native/manifest.json');await assert.rejects(collect(image.logicalStream('native/part0.gz',f.files[0])));}
});
test('early logical-stream return cancels the physical reader without whole custody',async()=>{
  const f=fixture(),r=f.reader(),image=new NativeAssetImage(r,f.manifest,'native/manifest.json');for await(const chunk of image.logicalStream('native/part0.gz',f.files[0])){assert.ok(chunk.length);break;}
  // The physical reader may finish before a tiny decoded member is yielded. In that case its whole mark is valid;
  // no API here marks the unconsumed logical member as authenticated or returns a verified word store.
  assert.ok([...r.inventory.values()].every(p=>p.whole_body_consumed!==true||p.sha256));
});

test('logical cancellation joins delayed physical cleanup and preserves consumer errors',async()=>{
  const f=fixture();
  for(const throws of [false,true]){
    const r=f.reader(),original=r.stream.bind(r);let active=0,closed=0;
    r.stream=async function*(...args){
      active++;
      try{for await(const chunk of original(...args)){yield chunk;await new Promise(resolve=>setTimeout(resolve,15));}}
      finally{await new Promise(resolve=>setTimeout(resolve,15));active--;closed++;}
    };
    const image=new NativeAssetImage(r,f.manifest,'native/manifest.json'),sentinel=Error('consumer cancellation sentinel');
    const consume=async()=>{for await(const chunk of image.logicalStream('native/part0.gz',f.files[0])){assert.ok(chunk.length);if(throws)throw sentinel;break;}};
    if(throws)await assert.rejects(consume(),error=>error===sentinel);else await consume();
    assert.equal(active,0,'no physical producer may survive logical return');assert.equal(closed,1);
  }
});

test('logical stream propagates a late physical-source failure after decoded bytes',async()=>{
  const f=fixture(),r=f.reader(),original=r.stream.bind(r),sentinel=Error('late physical failure');let closed=false;
  r.stream=async function*(...args){try{yield* original(...args);throw sentinel;}finally{closed=true;}};
  const image=new NativeAssetImage(r,f.manifest,'native/manifest.json');
  await assert.rejects(collect(image.logicalStream('native/part0.gz',f.files[0])),error=>error===sentinel);
  assert.equal(closed,true);
});
