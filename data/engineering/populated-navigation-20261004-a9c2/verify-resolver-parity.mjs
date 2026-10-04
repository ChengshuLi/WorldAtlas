import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {performance} from 'node:perf_hooks';
import {isDeepStrictEqual} from 'node:util';
import {resolveAttributes} from '../../../src/attributes.js';
import {referenceContextByLocation} from '../../../src/reference-context.js';
import {decodeReferences,decodeReferenceContext} from '../../../src/reference-records.js';
import {decodeDerived} from '../../../src/derived-records.js';
import {runtimeOwnershipBucket,runtimeOwnershipData} from '../../../src/runtime-ownership.js';
import {hydrateMapSnapshotPage} from '../../../src/map-snapshot-format.js';
const baselineDirectory=process.argv[2],output=process.argv[3];
if(!baselineDirectory||!output)throw Error('Supply git-archived baseline source directory and output path');
const {resolveAttributes:before}=await import(pathToFileURL(path.resolve(baselineDirectory,'src/attributes.js')));
const inputs=new Map(),sha=bytes=>createHash('sha256').update(bytes).digest('hex');
function read(file){const bytes=fs.readFileSync(file);inputs.set(file,{path:file,bytes:bytes.length,sha256:sha(bytes)});return JSON.parse(bytes[0]===31&&bytes[1]===139?gunzipSync(bytes):bytes);}
const referenceIndex=read('data/reference-attributes/index.json'),parts=referenceIndex.parts.map(file=>read('data/reference-attributes/'+file));
const baselines=decodeReferenceContext(parts,referenceIndex),referenceContexts=referenceContextByLocation(baselines);
const features=[];for(const file of read('data/world-index.json').parts)for(const feature of read('data/'+file).features)features.push({id:feature.id,properties:feature.properties});
const runtime=read('data/ownership-runtime/index.json'),results=[];
for(const year of [2020,2021,1900,2026,-1,1]){
 const rawFile=`data/engineering/populated-navigation-20261004-a9c2/snapshot-before-20261004/snapshot-${year}.json`;
 const page=fs.existsSync(rawFile)?hydrateMapSnapshotPage(read(rawFile)):null;
 const selected=runtimeOwnershipBucket(runtime,year),ownership=selected?runtimeOwnershipData(runtime,read('data/ownership-runtime/'+selected.path),year):null;
 const records=[...decodeReferences(parts,referenceIndex,year),...(ownership?decodeDerived(ownership.parts,ownership.index,year):[]),...(page?.records??[])];
 const options={records,referenceBaselines:baselines};
 const started=performance.now(),original=before(features,year,options),beforeMs=performance.now()-started;
 const candidateStart=performance.now(),candidate=resolveAttributes(features,year,{...options,referenceContexts}),candidateMs=performance.now()-candidateStart;
 const originalHash=createHash('sha256'),candidateHash=createHash('sha256');let matched=0;
 for(const [id,row] of original){const next=candidate.get(id);if(!isDeepStrictEqual(row,next))throw Error('Resolver output differs at '+id+' year '+year);originalHash.update(JSON.stringify([id,row])+'\n');candidateHash.update(JSON.stringify([id,next])+'\n');matched++;}
 if(original.size!==candidate.size)throw Error('Resolver location inventory differs');
 const before_sha256=originalHash.digest('hex'),candidate_sha256=candidateHash.digest('hex');
 if(before_sha256!==candidate_sha256)throw Error('Complete output hashes differ');
 results.push({year,locations:matched,before_ms:beforeMs,candidate_ms:candidateMs,before_sha256,candidate_sha256,outcome:'passed',scalar_snapshot_revision:page?.revision??null});
 console.log(JSON.stringify(results.at(-1)));
}
const beforeBytes=fs.readFileSync(path.resolve(baselineDirectory,'src/attributes.js'));
const result={version:1,scope:'complete scalar resolver output parity on committed atlas IDs/reference/ownership inputs, plus retained actual scalar snapshot claims; not geographical approval or production timing',baseline_commit:'f3263796efccac63dd20296130aeb176323d38ea',baseline_attributes_sha256:sha(beforeBytes),candidate_attributes_sha256:sha(fs.readFileSync('src/attributes.js')),source_inputs:[...inputs.values()],results,outcome:'passed',publication_verified:false};
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');
