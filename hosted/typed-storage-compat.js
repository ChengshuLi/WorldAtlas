/** Typed APIs use either the exact original V3 contract or exact compact V4
 * over all 26 collections. No arbitrary view or filtered catalog is accepted. */
import {storageCatalogV3,exportStorageMarkerV3} from './storage-export-v3.js';
import {membershipStorageKind} from './membership-storage-profile.js';
import {storageCatalogV4,exportStorageMarkerV4} from './storage-export-v4.js';
import {RecordError} from './records.js';
export async function typedStorageCatalog(db){
 if(await membershipStorageKind(db)==='original')return storageCatalogV3(db);
 const catalog=await storageCatalogV4(db);
 if(catalog.base_version!==3)throw new RecordError('Typed schema is uninstalled',503);
 return catalog;
}
export async function typedStorageMarker(db){
 if(await membershipStorageKind(db)==='original')return exportStorageMarkerV3(db);
 await typedStorageCatalog(db);return exportStorageMarkerV4(db);
}
