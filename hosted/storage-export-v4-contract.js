import {storageExportV2Contract} from './storage-export-v2-contract.js';
import {storageExportV3Contract} from './storage-export-v3-contract.js';
import {membershipStoragePins} from './membership-storage-pins.js';
export const v4MarkerIdentity=marker=>({version:4,revision:marker.revision,counts:marker.counts,geographic_releases_sha256:marker.geographic_releases_sha256,footprint_versions_sha256:marker.footprint_versions_sha256,catalog_sha256:marker.catalog_sha256,contract:marker.contract});
/** No caller-defined contracts: only exact compact profiles over frozen V2/V3. */
export function checkedStorageV4Contract(contract){
 const version=contract?.base_contract?.version,base=version===2?storageExportV2Contract:version===3?storageExportV3Contract:null;
 const pins=membershipStoragePins[version]?.[contract?.profile];
 if(contract?.version!==4||contract.membership_storage!=='compact-membership-v1'||!pins||contract.public_sha256!==pins.public_sha256||contract.private_sha256!==pins.private_sha256||JSON.stringify(contract.base_contract)!==JSON.stringify(base)||Object.keys(contract).sort().join(',')!=='base_contract,membership_storage,private_sha256,profile,public_sha256,version')throw Error('Unknown compact export contract');
 return contract;
}
