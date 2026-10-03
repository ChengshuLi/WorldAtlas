import test from 'node:test';
import assert from 'node:assert/strict';
import {validatePendingMacroCertificate} from '../scripts/prepare-reference-macro-binding.mjs';
test('candidate certificate cannot inherit successful readback or publication from its predecessor',()=>{
 const prior={publication_verified:true,local_installation_verified:true,database_release_readback_verified:true};
 const candidate={...prior,status:'reference-compatible-pending-publication',publication_verified:false,local_installation_verified:false,publication_receipt_path:null,new_approval_created:false,regional_interiors_approved:false};
 assert.throws(()=>validatePendingMacroCertificate(candidate),/unperformed/);
 candidate.database_release_readback_verified=false;assert.doesNotThrow(()=>validatePendingMacroCertificate(candidate));
 for(const key of ['publication_verified','local_installation_verified','database_release_readback_verified','new_approval_created','regional_interiors_approved'])assert.throws(()=>validatePendingMacroCertificate({...candidate,[key]:true}),/unperformed/);
 assert.throws(()=>validatePendingMacroCertificate({...candidate,publication_receipt_path:'old-published-release.json'}),/unperformed/);
});
