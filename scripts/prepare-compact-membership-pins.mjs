/** Offline reproduction; never writes deployed pins or original evidence. */
import fs from 'node:fs';
import {createLocalPostgres} from './verify-postgres-schema.mjs';
import {rehearseCompactMembershipStorage} from './compact-membership-storage.mjs';
import {compactMembershipCatalog} from '../hosted/membership-storage-profile.js';
const result={},output=process.argv[2];
if(!output||fs.existsSync(output))throw Error('New explicit profile evidence directory required');
fs.mkdirSync(output,{recursive:true});
for(const version of [2,3]){
 const f=await createLocalPostgres();try{
  for(const name of ['0001_temporal_geography','0002_footprint_versions',...(version===3?['0003_typed_observations']:[])])await f.engine.exec(fs.readFileSync('postgres/migrations/'+name+'.sql','utf8'));
  await f.engine.exec('CREATE ROLE worldatlas_app LOGIN NOINHERIT; GRANT USAGE ON SCHEMA public TO worldatlas_app');
  await rehearseCompactMembershipStorage(f.engine);
  result[version]={};
  for(const profile of ['retained-original','compact-only']){
   if(profile==='compact-only')await f.engine.exec('DROP TABLE worldatlas_memberships_original_v1');
   const proof=await compactMembershipCatalog(f.db,{verifyPins:false});
   result[version][profile]={public_sha256:proof.public_sha256,private_sha256:proof.private_sha256};
   fs.writeFileSync(output+'/catalog-v'+version+'-'+profile+'.json',JSON.stringify(proof,null,2)+'\n');
  }
 }finally{await f.close();}
}
fs.writeFileSync(output+'/membership-storage-pins.js','/** Exact isolated forward profiles; original schema and migrations remain frozen. */\nexport const membershipStoragePins=Object.freeze('+JSON.stringify(result,null,2)+');\n');console.log(JSON.stringify(result));
