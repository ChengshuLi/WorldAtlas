import fs from 'node:fs';import path from 'node:path';import {createHash}from'node:crypto';
import {restoreCanonicalProducts,getRestoredCanonicalProducts}from'../coordination/engineering/eastern-two-gap-repair-native-20261007/restore-canonical-products.mjs';
const repo=process.cwd(),root=path.join(repo,'.cache/1295-byte-inverse-entry-current'),ns='coordination/engineering/eastern-two-gap-repair-native-20261007';
if(fs.existsSync(root))throw Error('Fresh inverse destination required');
const started=new Date().toISOString();fs.mkdirSync(root);const temporary=path.join(root,'.cache');fs.mkdirSync(temporary);
const sha=x=>createHash('sha256').update(x).digest('hex'),source=[];
for(const group of ['canonical-products','prior-v1']){
 const dir=path.join(repo,ns,group),dest=path.join(root,ns,group);fs.mkdirSync(dest,{recursive:true});
 for(const name of fs.readdirSync(dir).sort()){
 const p=path.join(dir,name),q=path.join(dest,name),st=fs.lstatSync(p);if(!st.isFile()||st.isSymbolicLink())throw Error('Ordinary source required');
 fs.copyFileSync(p,q,fs.constants.COPYFILE_FICLONE);const raw=fs.readFileSync(q);source.push({path:ns+'/'+group+'/'+name,bytes:raw.length,sha256:sha(raw),mode:st.mode&0o111?'100755':'100644'});
 }
}
process.env.WORLDATLAS_PACKAGE_STAGE=root;
const receipt=restoreCanonicalProducts({root,temporaryRoot:temporary});getRestoredCanonicalProducts(root);
const result={status:'PASS',started_at:started,finished_at:new Date().toISOString(),command:process.argv,source_files:source,receipt,scope:'actual complete production restoration entry on a private explicitly enumerated transport image; not normal package materialization/build',source_and_geometry_producers_invoked:false};
fs.writeFileSync(path.join(repo,'.cache/1295-complete-byte-inverse-entry-receipt.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({status:'PASS',canonical_paths:receipt.canonical_paths,prior_paths:receipt.prior_paths,finished_at:result.finished_at}));
