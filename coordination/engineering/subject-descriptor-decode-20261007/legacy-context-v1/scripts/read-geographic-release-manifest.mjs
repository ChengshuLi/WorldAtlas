import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {isDeepStrictEqual} from 'node:util';
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const digest=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
const filename=value=>typeof value==='string'&&/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/.test(value);
function readFile(file,limit){const stat=fs.lstatSync(file);if(!stat.isFile()||stat.size>limit)throw Error('Invalid geographic manifest file');return fs.readFileSync(file);}
/** Resolve an immutable extension while preserving the exact legacy index. */
export function decodeGeographicReleaseBatch(bytes,part){
 if(sha(bytes)!==part.sha256)throw Error('Prepared release hash mismatch: '+part.path);
 if(part.encoding===undefined)return bytes;
 if(part.encoding!=='gzip'||!digest(part.payload_sha256))throw Error('Invalid prepared release encoding');
 const payload=gunzipSync(bytes,{maxOutputLength:1024*1024});
 if(sha(payload)!==part.payload_sha256)throw Error('Prepared release payload hash mismatch: '+part.path);
 return payload;
}
export function readGeographicReleaseManifest(directory='data/geographic-releases'){
 const original=readFile(path.join(directory,'index.json'),64*1024*1024),base=JSON.parse(original),pointerFile=path.join(directory,'current-manifest.json');
 if(!fs.existsSync(pointerFile))return base;
 const pointer=JSON.parse(readFile(pointerFile,4096));
 if(!filename(pointer.path)||!pointer.path.endsWith('.json.gz')||!digest(pointer.sha256)||!digest(pointer.predecessor_index_sha256))throw Error('Invalid geographic manifest pointer');
 if(sha(original)!==pointer.predecessor_index_sha256)throw Error('Geographic manifest predecessor index changed');
 const compressed=readFile(path.join(directory,pointer.path),16*1024*1024);
 if(sha(compressed)!==pointer.sha256)throw Error('Geographic manifest extension hash mismatch');
 const next=JSON.parse(gunzipSync(compressed,{maxOutputLength:64*1024*1024}));
 if(next.version!==base.version||next.original_catalog_sha256!==base.original_catalog_sha256)throw Error('Geographic manifest baseline identity changed');
 if(!Array.isArray(base.releases)||!Array.isArray(next.releases)||next.releases.length<=base.releases.length||!isDeepStrictEqual(next.releases.slice(0,base.releases.length),base.releases))throw Error('Geographic manifest predecessor releases changed');
 const ids=new Set();let version=0;
 for(const release of next.releases){if(typeof release.id!=='string'||ids.has(release.id)||!Number.isSafeInteger(release.version)||release.version<=version)throw Error('Geographic manifest releases must have unique ordered versions and IDs');ids.add(release.id);version=release.version;}
 if(!Array.isArray(base.batches)||!Array.isArray(next.batches)||next.batches.length<=base.batches.length||!isDeepStrictEqual(next.batches.slice(0,base.batches.length),base.batches))throw Error('Geographic manifest predecessor batches changed');
 const names=new Set();
 for(const batch of next.batches){if(!filename(batch.path)||names.has(batch.path)||!digest(batch.sha256)||typeof batch.route!=='string')throw Error('Invalid geographic manifest batch');if(batch.encoding!==undefined&&(batch.encoding!=='gzip'||!batch.path.endsWith('.json.gz')||!digest(batch.payload_sha256)))throw Error('Invalid geographic manifest batch encoding');names.add(batch.path);}
 for(const key of ['new_entities','total_memberships','changes'])if(!Number.isSafeInteger(next[key])||next[key]<base[key])throw Error('Geographic manifest cumulative counts decreased');
 const sources=base.sources_batches??['sources.json'];if(!Array.isArray(next.sources_batches)||!isDeepStrictEqual(next.sources_batches.slice(0,sources.length),sources)||new Set(next.sources_batches).size!==next.sources_batches.length||next.sources_batches.some(name=>!names.has(name)))throw Error('Geographic manifest source batches changed');
 return next;
}
