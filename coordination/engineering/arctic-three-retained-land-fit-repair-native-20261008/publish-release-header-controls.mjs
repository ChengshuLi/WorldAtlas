import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {bindPublishedGeometryReceipt} from './publish-release-header.mjs';
const header=JSON.parse(fs.readFileSync(process.argv[2])),raw=fs.readFileSync(process.argv[3]);
const binding={commit:'9b212c585583dc218a961b4c7ee1056a64b54726',path:'coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/migration-receipt.json',
 mode:'100644',oid:'41a9f44a0846850fe07519a05615ea43c0a945d2',bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')};
const result=bindPublishedGeometryReceipt(header,raw,binding);
assert.equal(result.release.metadata.geometry_migration.commit,binding.commit);
assert.equal(result.release.id,header.release.id);assert.equal(result.release.membership_sha256,header.release.membership_sha256);
assert.equal(result.changes,header.changes);assert.equal(result.complete_member_inputs,header.complete_member_inputs);
assert.equal(result.source,header.source);
let negative=0;
for(const patch of [{commit:header.release.metadata.geometry_migration.commit},{path:'foreign.json'},{mode:'100755'},
 {oid:'foreign'},{sha256:'0'.repeat(64)},{bytes:raw.length-1}]){
 assert.throws(()=>bindPublishedGeometryReceipt(header,raw,{...binding,...patch}));negative++;
}
assert.throws(()=>bindPublishedGeometryReceipt({...header,migration_receipt_sha256:'0'.repeat(64)},raw,binding));negative++;
console.log(JSON.stringify({positive:1,negative,real_receipt_body:true,all_nonlocator_release_content_preserved:true,
 limit:'Caller must authenticate commit/path/OID/mode against immutable Git before publication.'}));
