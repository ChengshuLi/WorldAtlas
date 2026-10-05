import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {createHash} from 'node:crypto';
import {packageOwnershipHistory,verifyOwnershipDelivery} from '../scripts/package-ownership-history.mjs';
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
async function fixture(t){
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'atlas-ownership-delivery-'));t.after(()=>fs.rm(root,{recursive:true,force:true}));
 const source=path.join(root,'source'),destination=path.join(root,'destination'),archive='prior-archives/old';
 await fs.mkdir(path.join(source,archive),{recursive:true});await fs.mkdir(path.join(source,'algorithms'));
 const originals=new Map([['index.json','{"parts":["reuse-0.json.gz"]}'],['reuse-0.json.gz',Buffer.from([31,139,0,255])],['evidence-0.json.gz',Buffer.from([31,139,1,254])],['archive-index.json','{"parts":[]}'],['algorithms/majority.py','exact historical algorithm\n'],[`${archive}/archive-0.json.gz`,Buffer.from([31,139,20,250])],[`${archive}/migration-receipt.json`,'{"historical_claims_transferred":false}'],[`${archive}/.retained-note`,'hidden retained evidence']]);
 const priorIndex=JSON.stringify({parts:[{path:'archive-0.json.gz',sha256:sha(originals.get(`${archive}/archive-0.json.gz`))}]});originals.set(`${archive}/archive-index.json`,priorIndex);
 for(const [file,bytes]of originals)await fs.writeFile(path.join(source,file),bytes);
 return {source,destination,originals};
}
test('hosted omission accounts for all prior bytes and preserves every current/source file exactly',async t=>{
 const {source,destination,originals}=await fixture(t),manifest=await packageOwnershipHistory({source,destination,hosted:true});
 assert.equal(manifest.delivery_status,'repository-retained');assert.match(manifest.note,/does not assert an object-storage upload/);
 assert.equal(manifest.archives.length,4);assert.ok(manifest.archives.some(file=>file.path.endsWith('/.retained-note')));
 assert.equal(manifest.archived_bytes,manifest.archives.reduce((n,file)=>n+file.bytes,0));
 for(const [file,bytes]of originals){assert.deepEqual(await fs.readFile(path.join(source,file)),Buffer.from(bytes));if(!file.startsWith('prior-archives/'))assert.deepEqual(await fs.readFile(path.join(destination,file)),Buffer.from(bytes));}
 await assert.rejects(fs.access(path.join(destination,'prior-archives')));
 for(const file of manifest.archives){assert.equal(file.sha256,sha(originals.get(file.path)));assert.equal(file.repository_path,`data/ownership-history/${file.path}`);assert.equal(file.content_addressed_path,`ownership-history/sha256/${file.sha256}`);}
 await verifyOwnershipDelivery({source,destination,manifest});
});
test('portable static export retains the full tree without a delivery manifest',async t=>{
 const {source,destination,originals}=await fixture(t);assert.equal(await packageOwnershipHistory({source,destination}),null);
 for(const [file,bytes]of originals)assert.deepEqual(await fs.readFile(path.join(destination,file)),Buffer.from(bytes));
 await assert.rejects(fs.access(path.join(destination,'archive-delivery.json')));
});
test('existing pinned archive tampering fails before packaging',async t=>{
 const {source,destination}=await fixture(t);await fs.writeFile(path.join(source,'prior-archives/old/archive-0.json.gz'),'changed');
 await assert.rejects(packageOwnershipHistory({source,destination,hosted:true}),/Prior archive hash mismatch/);await assert.rejects(fs.access(destination));
});
test('verification rejects unlisted excluded files, altered retained bytes and deployed tampering',async t=>{
 const {source,destination}=await fixture(t),manifest=await packageOwnershipHistory({source,destination,hosted:true});
 await fs.writeFile(path.join(source,'prior-archives/old/.new-hidden-file'),'unlisted');await assert.rejects(verifyOwnershipDelivery({source,destination,manifest}),/source inventory or hash changed/);await fs.unlink(path.join(source,'prior-archives/old/.new-hidden-file'));
 const archived=path.join(source,'prior-archives/old/migration-receipt.json'),before=await fs.readFile(archived);await fs.writeFile(archived,'changed');await assert.rejects(verifyOwnershipDelivery({source,destination,manifest}),/source inventory or hash changed/);await fs.writeFile(archived,before);
 await fs.writeFile(path.join(destination,'reuse-0.json.gz'),'changed');await assert.rejects(verifyOwnershipDelivery({source,destination,manifest}),/deployed inventory or hash changed/);
});
test('symbolic links cannot silently omit archive content',async t=>{
 const {source,destination}=await fixture(t);await fs.symlink('../migration-receipt.json',path.join(source,'prior-archives/old/link'));
 await assert.rejects(packageOwnershipHistory({source,destination,hosted:true}),/symbolic link/);
});

test('hosted receipt compression preserves exact original bytes with explicit transport proof',async t=>{
 const {source,destination}=await fixture(t),original=Buffer.from(JSON.stringify({evidence:'retained',rows:Array(100).fill('original record')}));
 await fs.writeFile(path.join(source,'candidate-recovery.json'),original);
 const manifest=await packageOwnershipHistory({source,destination,hosted:true,compactReceipts:true});
 assert.equal(manifest.version,2);assert.equal(manifest.transports.length,1);
 const row=manifest.transports[0];assert.equal(row.source.sha256,sha(original));assert.equal(row.deployment.path,'candidate-recovery.json.gz');
 assert.deepEqual(await fs.readFile(path.join(source,'candidate-recovery.json')),original);
 const {gunzipSync}=await import('node:zlib');assert.deepEqual(gunzipSync(await fs.readFile(path.join(destination,row.deployment.path))),original);
 await verifyOwnershipDelivery({source,destination,manifest});
 await fs.writeFile(path.join(destination,row.deployment.path),'corrupt');
 await assert.rejects(verifyOwnershipDelivery({source,destination,manifest}),/deployed inventory or hash changed/);
});
