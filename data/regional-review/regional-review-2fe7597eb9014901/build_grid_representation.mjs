import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {unshuffleOwnershipBytes} from '../../../src/ownership-codec.js';

const OUT=path.dirname(new URL(import.meta.url).pathname);
const ROOT=path.resolve(OUT,'../../../');
const grid=path.join(ROOT,'data/canonical-grid');
const hash=b=>createHash('sha256').update(b).digest('hex');
const manifest=JSON.parse(fs.readFileSync(path.join(grid,'manifest.json')));
const ids=['atlas:coverage:ATF-5916','atlas:coverage:ATF-5917','atlas:coverage:ATF-5918','atlas:coverage:HMD+00?'];
const bounds=JSON.parse(gunzipSync(fs.readFileSync(path.join(grid,'bounds.json.gz'))));
const indexById=Object.fromEntries(ids.map(id=>[id,bounds.find(x=>x.id===id)?.index]));
if(Object.values(indexById).some(x=>!Number.isInteger(x)))throw Error('A scoped subject is missing from canonical grid bounds');
const counts=Object.fromEntries(ids.map(id=>[id,0]));let chunks=0,words=0;
const mask=2**manifest.coordinateBits-1,base=2**(32-manifest.coordinateBits);
for(const part of manifest.parts.filter(p=>p.kind==='runs')){
 const compressed=fs.readFileSync(path.join(grid,part.path));
 if(compressed.length!==part.compressed_bytes||hash(compressed)!==part.sha256)throw Error(`Compressed hash mismatch: ${part.path}`);
 const raw=gunzipSync(compressed),decoded=unshuffleOwnershipBytes(raw,part.words);
 if(hash(Buffer.from(decoded.buffer))!==part.decoded_sha256)throw Error(`Decoded hash mismatch: ${part.path}`);
 for(let i=0;i<decoded.length;i+=2){
  const a=decoded[i],b=decoded[i+1],owner=(a>>>manifest.coordinateBits)+(b>>>manifest.coordinateBits)*base;
  const id=ids.find(candidate=>indexById[candidate]===owner);
  if(id)counts[id]+=(b&mask)+1-(a&mask);
 }
 chunks++;words+=part.words;
}
const result={method:'Read-only full scan of all canonical ownership run chunks. Verify compressed and unshuffled decoded bytes against manifest SHA-256, decode v2 (19-bit coordinate packing), and sum interval cell counts for exact 1-based feature indexes in bounds.json.gz. No canonical grid files edited. Counts are discrete canonical cell assignment counts, not area estimates or evidence of source completeness.',baseline_commit:JSON.parse(fs.readFileSync(path.join(OUT,'baseline-extract.json'))).baseline_commit,manifest_path:'data/canonical-grid/manifest.json',manifest_version:manifest.version,coordinate_bits:manifest.coordinateBits,size:manifest.size,run_words:manifest.runWords,footprints_sha256:manifest.footprints_sha256,hierarchy_sha256:manifest.hierarchy_sha256,bounds_sha256:hash(fs.readFileSync(path.join(grid,'bounds.json.gz'))),run_chunks_verified:chunks,words_verified:words,location_feature_indexes:indexById,assigned_cells:counts};
const target=path.join(OUT,'grid-representation.json'),payload=JSON.stringify(result,null,2)+'\n';
if(process.argv.includes('--check')){if(fs.readFileSync(target,'utf8')!==payload)throw Error('Grid representation differs; review before regeneration');}
else fs.writeFileSync(target,payload);
console.log(JSON.stringify({result:process.argv.includes('--check')?'passed':'written',chunks,words,counts},null,2));
