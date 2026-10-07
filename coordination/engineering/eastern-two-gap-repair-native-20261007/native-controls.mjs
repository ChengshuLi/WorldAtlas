import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {gzipSync,gunzipSync} from 'node:zlib';import {createHash} from 'node:crypto';import {immutableReader} from './native-producer.mjs';
const hash=b=>createHash('sha256').update(b).digest('hex'),root=process.cwd(),baseline='913db0624b8aa79b188ff17a7f5c4ae0c0f63965';
const index=JSON.parse(fs.readFileSync('coordination/engineering/eastern-two-gap-repair-native-20261007/original-inputs/index.json'));
const row=index.files.find(x=>x.original.path==='data/world-index.json');assert(row);
const fixture=path.join(root,'.cache/native-controls-'+process.pid);fs.mkdirSync(fixture,{recursive:true});let checked=0;
const caseRun=(name,f)=>{f();checked++;console.log('PASS '+name);};
const withRow=r=>new Map([[baseline+':'+row.original.path,r]]);
const read=r=>immutableReader(root,baseline,withRow(r)).read(row.original.path);
try{
 caseRun('complete original whole-source positive',()=>assert.equal(hash(read(row)),row.original.sha256));
 caseRun('Git option rejected before write',()=>{const target=path.join(fixture,'no-write');assert.throws(()=>immutableReader(root,'--output='+target),/immutable source commit/);assert(!fs.existsSync(target));});
 caseRun('absent declared input rejected',()=>assert.throws(()=>immutableReader(root,baseline,new Map()).read(row.original.path),/Undeclared/));
 caseRun('original whole blob identity mutation rejected',()=>assert.throws(()=>read({...row,original:{...row.original,blob:'0'.repeat(40)}}),/OID changed/));
 caseRun('source mode mutation rejected',()=>assert.throws(()=>read({...row,original:{...row.original,mode:'100755'}})));
 caseRun('original size mutation rejected',()=>assert.throws(()=>read({...row,original:{...row.original,bytes:row.original.bytes+1}})));
 const original=gunzipSync(fs.readFileSync(row.alias.path));
 const altered=Buffer.concat([original,Buffer.from(' ')]),encoded=gzipSync(altered,{level:9}),relative=path.relative(root,path.join(fixture,'altered.gz'));fs.writeFileSync(relative,encoded);
 const rebound={...row,alias:{path:relative,bytes:encoded.length,sha256:hash(encoded),decoded_bytes:altered.length,decoded_sha256:hash(altered)}};
 caseRun('coherently rebound transport cannot alter original whole body',()=>assert.throws(()=>read(rebound),/Whole original input changed/));
 caseRun('encoded alias digest mutation rejected',()=>assert.throws(()=>read({...row,alias:{...row.alias,sha256:'0'.repeat(64)}})));
 caseRun('decoded alias digest mutation rejected',()=>assert.throws(()=>read({...row,alias:{...row.alias,decoded_sha256:'0'.repeat(64)}})));
 caseRun('absolute storage path rejected',()=>assert.throws(()=>read({...row,alias:{...row.alias,path:path.resolve(row.alias.path)}})));
 caseRun('parent traversal storage path rejected',()=>assert.throws(()=>read({...row,alias:{...row.alias,path:'../outside'}})));
 const linked=path.join(fixture,'linked');fs.symlinkSync(path.dirname(path.resolve(row.alias.path)),linked);const linkPath=path.relative(root,path.join(linked,path.basename(row.alias.path)));
 caseRun('symlink ancestor storage path rejected',()=>assert.throws(()=>read({...row,alias:{...row.alias,path:linkPath}}),/Ordinary retained alias/));
 console.log(JSON.stringify({checked,status:'PASS',scope:'Directed whole-source custody branches, no global native generation'}));
}finally{fs.rmSync(fixture,{recursive:true});}
