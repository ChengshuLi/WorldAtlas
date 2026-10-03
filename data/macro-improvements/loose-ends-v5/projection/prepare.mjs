// Offline overlay supplies the exact v4 predecessor without editing live v5 data.
import fs from 'node:fs';import path from 'node:path';import os from 'node:os';import {createHash} from 'node:crypto';import {gunzipSync} from 'node:zlib';
import {prepareMacroReviewProjection,validateMacroReviewProjection} from '../../../../scripts/prepare-macro-review-projection.mjs';
import {footprintHash} from '../../../../scripts/check-prepared.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex'),read=p=>JSON.parse(p.endsWith('.gz')?gunzipSync(fs.readFileSync(p)):fs.readFileSync(p));
const get=k=>{const i=process.argv.indexOf('--'+k);if(i<0||!process.argv[i+1])throw Error('Required --'+k);return path.resolve(process.argv[i+1]);};
const root=get('root'),beforeData=get('before'),afterData=get('after'),proofs=get('geometry-proofs'),receipt=get('source-receipt'),output=get('output');
if(fs.existsSync(output)||[root,beforeData,afterData].some(p=>output===p||output.startsWith(p+path.sep)))throw Error('Fresh independent output required');
const context=fs.mkdtempSync(path.join(os.tmpdir(),'worldatlas-v5-projection-context-')),contextData=path.join(context,'data');fs.mkdirSync(contextData);
try{
 for(const entry of fs.readdirSync(root)){if(entry==='data'||entry==='.git'||entry==='.cache')continue;fs.symlinkSync(path.join(root,entry),path.join(context,entry));}
 for(const name of fs.readdirSync(afterData)){const old=path.join(beforeData,name);fs.symlinkSync(fs.existsSync(old)?old:path.join(afterData,name),path.join(contextData,name));}
 const snapshot=data=>{const hierarchy=path.join(data,'hierarchy.json'),index=path.join(data,'world-index.json'),units=read(hierarchy),features=read(index).parts.flatMap(part=>read(path.join(data,part)).features);return {units,features,proof:{hierarchy_sha256:sha(fs.readFileSync(hierarchy)),location_index_sha256:sha(fs.readFileSync(index)),footprints_sha256:footprintHash(features)}};};
 const before=snapshot(contextData),after=snapshot(afterData);
 if(before.features.length!==49623||after.features.length!==49625)throw Error('Wrong predecessor/current counts');
 const predecessorFile=path.join(contextData,'macro-foundation/current-membership-projection.json.gz');let predecessorBytes=fs.readFileSync(predecessorFile),predecessor=read(predecessorFile);
 while(['hierarchy_sha256','location_index_sha256','footprints_sha256'].some(key=>predecessor.current_pins?.[key]!==before.proof[key])){
  const entry=predecessor.predecessor_files?.['data/macro-foundation/current-membership-projection.json.gz'];if(!entry)throw Error('Exact prior projection is unavailable');
  const archivePath=path.resolve(root,entry.archive_path);if(!archivePath.startsWith(root+path.sep))throw Error('Unsafe prior projection archive');
  const archive=fs.readFileSync(archivePath);if(sha(archive)!==entry.archive_sha256)throw Error('Prior projection archive changed');predecessorBytes=gunzipSync(archive);if(sha(predecessorBytes)!==entry.original_sha256)throw Error('Prior projection bytes changed');predecessor=JSON.parse(gunzipSync(predecessorBytes));
 }
 if(sha(predecessorBytes)!==sha(fs.readFileSync(predecessorFile))){
  const macro=path.join(contextData,'macro-foundation');fs.unlinkSync(macro);fs.mkdirSync(macro);
  for(const name of fs.readdirSync(path.join(afterData,'macro-foundation')))if(name!=='current-membership-projection.json.gz')fs.symlinkSync(path.join(afterData,'macro-foundation',name),path.join(macro,name));
  fs.writeFileSync(predecessorFile,predecessorBytes);
 }
 const previous=read(path.join(contextData,'macro-foundation/current-membership-projection.json.gz'));
 const files=await prepareMacroReviewProjection({data:contextData,before,after,geometryProofs:proofs,sourceReceipt:receipt});
 const projection=JSON.parse(gunzipSync(files.get('macro-foundation/current-membership-projection.json.gz'))),locations=after.features.map(f=>({id:f.id,name:f.properties.name,parent_id:f.properties.parent_id,owner:f.properties.reference_owner}));
 const result=validateMacroReviewProjection({projection,hierarchy:after.units,locations,currentPins:after.proof,baselineLocations:previous.locations});
 if(projection.geometry_proof.changed_ids.length!==3||projection.geometry_proof.added_ids.length!==2||projection.geometry_proof.removed_ids.length||projection.semantic_complete!==false||JSON.stringify(projection.source_inspections)!==JSON.stringify(previous.source_inspections))throw Error('Source scope/inspection preservation failed');
 const total=[...files.values()].reduce((n,b)=>n+b.byteLength,0),disk=fs.statfsSync(path.dirname(output));if(total+16*1024*1024>disk.bavail*disk.bsize)throw Error('Insufficient disk space for exact projection assets');
 const hashes={};fs.mkdirSync(output,{recursive:true});
 for(const [name,bytes]of files){const file=path.resolve(output,name);if(!file.startsWith(output+path.sep))throw Error('Unsafe projection output');fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,bytes);hashes[name]=sha(bytes);}
 const report={version:1,verified:true,...result,before_locations:before.features.length,after_locations:after.features.length,changed_locations:3,added_locations:2,removed_locations:0,current_pins:after.proof,source_inspections_preserved:true,prior_projection_sha256:sha(fs.readFileSync(path.join(contextData,'macro-foundation/current-membership-projection.json.gz'))),output_bytes:total,output_sha256:hashes,installed:false,published:false};
 fs.writeFileSync(path.join(output,'preparation-receipt.json'),JSON.stringify(report)+'\n');console.log(JSON.stringify({...report,output_sha256:{files:Object.keys(hashes).length}}));
}finally{fs.rmSync(context,{recursive:true,force:true});}
