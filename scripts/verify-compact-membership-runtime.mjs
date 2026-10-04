import {verifyForwardRuntimeRole} from './neon-forward-migrations.mjs';
import {compactMembershipCatalog} from '../hosted/membership-storage-profile.js';
/** Owner-side inspection of the exact new profile plus unchanged effective
 * runtime restrictions. Never provisions roles or alters frozen contracts. */
export async function verifyCompactMembershipRuntime(driver,definitions){
 const db={dialect:'postgres',prepare:sql=>({all:async()=>({results:(await driver.query(sql)).rows})})};
 const profile=await compactMembershipCatalog(db);
 if(profile.base_version!==definitions.length||![2,3].includes(definitions.length))throw Error('Known compact forward inventory required');
 const runtime=await verifyForwardRuntimeRole(driver,definitions);
 return {version:1,status:'verified',storage_format:'compact-membership-v1',profile:profile.profile,base_version:profile.base_version,public_sha256:profile.public_sha256,private_sha256:profile.private_sha256,runtime};
}
