import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {retainWholeImage,restoreWholeImage as originalRestore} from '../coordination/engineering/eastern-two-gap-repair-native-20261007/whole-image.mjs';
import {restoreWholeImage} from '../scripts/evidence/restore-whole-image.mjs';
const sha = raw => createHash('sha256').update(raw).digest('hex');
function fixture(t, big = false) {
 const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'worldatlas-image-control-')));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const source=path.join(root,'source'),wire=path.join(root,'wire');fs.mkdirSync(source);
 fs.writeFileSync(path.join(source,'a'),Buffer.alloc(big?9*1024*1024:37,65));
 fs.mkdirSync(path.join(source,'nested'));
 fs.writeFileSync(path.join(source,'nested','b'),Buffer.alloc(big?9*1024*1024:23,66),{mode:0o755});
 const index=retainWholeImage(source,wire,{roles:{a:{kind:'preserved-test-role'}}});
 const out=path.join(root,'output');
 const pin=()=>sha(fs.readFileSync(path.join(wire,'index.json')));
 const change=mutate=>{mutate(index);fs.writeFileSync(path.join(wire,'index.json'),JSON.stringify(index)+'\n');};
 return {root,source,wire,out,index,pin,change};
}
test('real original transport restores cross-part members, bytes, modes and roles',t=>{
 const f=fixture(t,true),original=path.join(f.root,'original');assert.equal(f.index.parts.length,2);
 const old=originalRestore(f.wire,original,{expectedIndexSha:f.pin()});
 const current=restoreWholeImage(f.wire,f.out,{expectedIndexSha:f.pin()});assert.deepEqual(current,old);
 for(const pin of current.files){assert(fs.readFileSync(path.join(original,pin.path)).equals(fs.readFileSync(path.join(f.out,pin.path))));assert.equal(fs.statSync(path.join(f.out,pin.path)).mode&0o777,fs.statSync(path.join(original,pin.path)).mode&0o777);}
});
test('changed encoded bytes and wrong decoded or whole bindings cannot create output',t=>{
 const f=fixture(t);const part=f.index.parts[0];const file=path.join(f.wire,part.path),raw=fs.readFileSync(file);raw[raw.length-1]^=1;fs.writeFileSync(file,raw);
 assert.throws(()=>restoreWholeImage(f.wire,f.out,{expectedIndexSha:f.pin()}));assert(!fs.existsSync(f.out));
});
for(const [name,mutate] of [
 ['missing member',j=>j.files.pop()],
 ['duplicate member',j=>j.files[1].path=j.files[0].path],
 ['noncontiguous part',j=>j.parts[0].offset=1],
 ['whole cap',j=>j.whole_bytes=257*1024*1024],
 ['invalid decoded hash',j=>j.parts[0].decoded_sha256='0'.repeat(64)],
 ['invalid member hash',j=>j.files[0].sha256='0'.repeat(64)],
 ['invalid whole hash',j=>j.whole_sha256='0'.repeat(64)],
 ['fractional aggregate',j=>j.whole_bytes+=0.5],
 ['directory collision',j=>j.files[1].path='a/b'],
 ['traversal',j=>j.files[0].path='../escaped']
])test(`rebound ${name} index fails before destination creation`,t=>{
 const f=fixture(t);f.change(mutate);
 assert.throws(()=>restoreWholeImage(f.wire,f.out,{expectedIndexSha:f.pin()}));assert(!fs.existsSync(f.out));
});
test('complete aggregate admission precedes opening any part',t=>{
 const f=fixture(t);f.change(j=>j.whole_bytes=257*1024*1024);fs.unlinkSync(path.join(f.wire,f.index.parts[0].path));
 assert.throws(()=>restoreWholeImage(f.wire,f.out,{expectedIndexSha:f.pin()}),/Bounded original fixed image/);assert(!fs.existsSync(f.out));
});
test('empty original image stays valid',t=>{
 const root=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'worldatlas-image-empty-')));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const source=path.join(root,'source'),wire=path.join(root,'wire'),out=path.join(root,'out');fs.mkdirSync(source);const index=retainWholeImage(source,wire);
 assert.deepEqual(restoreWholeImage(wire,out,{expectedIndexSha:sha(fs.readFileSync(path.join(wire,'index.json')))}),index);assert.deepEqual(fs.readdirSync(out),[]);
});
test('existing destination and linked parts preserve original sentinels',t=>{
 const f=fixture(t);fs.mkdirSync(f.out);const sentinel=path.join(f.out,'sentinel');fs.writeFileSync(sentinel,'untouched');
 assert.throws(()=>restoreWholeImage(f.wire,f.out,{expectedIndexSha:f.pin()}));assert.equal(fs.readFileSync(sentinel,'utf8'),'untouched');
 fs.rmSync(f.out,{recursive:true});const part=path.join(f.wire,f.index.parts[0].path),backup=path.join(f.root,'backup');fs.renameSync(part,backup);fs.symlinkSync(backup,part);
 assert.throws(()=>restoreWholeImage(f.wire,f.out,{expectedIndexSha:f.pin()}));assert(!fs.existsSync(f.out));
});
