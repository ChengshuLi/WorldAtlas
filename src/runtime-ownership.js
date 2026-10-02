import {validYear} from './model.js';

// Century buckets are transport/cache partitions, never replacement dates.
export function runtimeOwnershipBucket(runtime,year){
 if(!validYear(year))throw Error('Invalid ownership year: year zero is excluded');
 if(runtime.version!==1||runtime.encoding!=='ownership-v2-century'||runtime.shared?.version!==2)throw Error('Unsupported ownership runtime encoding');
 const buckets=runtime.buckets;let lo=0,hi=buckets.length;
 while(lo<hi){const mid=(lo+hi)>>>1;if(buckets[mid].valid_from<=year)lo=mid+1;else hi=mid;}
 const bucket=buckets[lo-1];return bucket&&year<bucket.valid_to?bucket:null;
}

export function runtimeOwnershipData(runtime,bucket,year){
 const selected=runtimeOwnershipBucket(runtime,year);
 if(!selected)throw Error('No ownership source coverage for selected year');
 if(bucket.version!==1||bucket.source_index_sha256!==runtime.source_index_sha256||bucket.valid_from!==selected.valid_from||bucket.valid_to!==selected.valid_to||!Array.isArray(bucket.parts)||!Array.isArray(bucket.evidence))throw Error('Ownership bucket does not match its runtime manifest');
 return {parts:bucket.parts,index:{...runtime.shared,evidence:bucket.evidence}};
}
