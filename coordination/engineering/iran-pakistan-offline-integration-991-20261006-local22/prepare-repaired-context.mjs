// Lossless context derivative: replace only the two reviewed native shapes.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import {isDeepStrictEqual} from 'node:util';
import {compactContextInputs} from '../../../scripts/native-ownership/compact-context-inputs.mjs';
import {committedPreparationFiles,requirePlainExecution,candidateBudget} from '../../../scripts/native-ownership/native-preparation-guards.mjs';

requirePlainExecution();
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const out=path.resolve(root,process.argv[2]??'');
if(!out.startsWith(path.join(root,prefix)+path.sep)||fs.existsSync(out))throw Error('Fresh owned output required');
const head=execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim(),digest=raw=>createHash('sha256').update(raw).digest('hex');
const producer=committedPreparationFiles(root,head,['package.json',prefix+'/prepare-repaired-context.mjs',
  'scripts/native-ownership/compact-context-inputs.mjs','scripts/native-ownership/native-preparation-guards.mjs',
  'src/native-runtime.js','src/native-grid.js']);
const inputs=[],baseline='d0cc67eac85038159f88a673acbc39b77ab7461d';
function read(commit,name,expected){
  const raw=execFileSync('git',['-C',root,'show',commit+':'+name],{maxBuffer:32*1024*1024});
  if(expected&&(raw.length!==expected.bytes||digest(raw)!==expected.sha256))throw Error('Context immutable input differs: '+name);
  inputs.push({commit,path:name,bytes:raw.length,sha256:digest(raw)});return raw;
}
const dir='coordination/engineering/native-grid-integration-1010-20261005-local17/context-inputs-v1';
const old=JSON.parse(read(baseline,dir+'/inputs.json')),features=[];
for(const part of old.parts){
  const raw=read(baseline,dir+'/'+part.path,part),decoded=gunzipSync(raw,{maxOutputLength:32*1024*1024});
  if(decoded.length!==part.uncompressed_bytes||digest(decoded)!==part.uncompressed_sha256)throw Error('Original compact context decode differs');
  const rows=JSON.parse(decoded);if(rows.length!==part.owners||part.first_owner!==features.length+1)throw Error('Original compact roster differs');
  features.push(...rows);
}
const bounds=JSON.parse(gunzipSync(read(baseline,'data/canonical-grid/bounds.json.gz')));
const original=compactContextInputs(features,bounds,old.footprints_sha256);
if(original.features.length!==49625||original.owner_sha256!==old.owner_sha256||old.original_release!=='geography:review:831aada26a8c7fe8c75553caf4432a22dc9c2cf458b14221a1135addb475f186')throw Error('Original complete context binding differs');
const geometry=JSON.parse(read(baseline,'coordination/engineering/iran-pakistan-native-joint-991-20261006-local21/results-v3/candidates.json'));
const migration=JSON.parse(read(head,prefix+'/release-proof-v3/migration-receipt.json'));
const validation=JSON.parse(read(head,prefix+'/release-proof-v3/validation.json'));
const releaseRaw=read(head,prefix+'/successor-release-v1/releases-v7-gzip.json.gz'),release=JSON.parse(gunzipSync(releaseRaw)).releases.at(-1);
if(!isDeepStrictEqual(Object.keys(geometry).sort(),[...migration.changed_ids].sort())||!validation.exact_staged_original_archive_checked||
  release.footprints_sha256!==migration.after_footprints_sha256||release.metadata.predecessor_release_id!==old.original_release)throw Error('Reviewed shape/release linkage differs');
const changed=features.map(f=>geometry[f.id]?{...f,geometry:geometry[f.id]}:f);
const compact=compactContextInputs(changed,bounds,release.footprints_sha256);
if(compact.owner_sha256!==old.owner_sha256||changed.filter((f,i)=>!isDeepStrictEqual(f,features[i])).length!==2)throw Error('Context identity or non-target geometry changed');
const budget=candidateBudget([...inputs,...producer]);fs.mkdirSync(out);const parts=[];
for(let first=0;first<compact.features.length;first+=1500){
  const rows=compact.features.slice(first,first+1500),raw=Buffer.from(JSON.stringify(rows)+'\n'),encoded=gzipSync(raw,{level:9});
  if(raw.length>32*1024*1024)throw Error('Decoded derivative exceeds file budget');budget.add({bytes:encoded.length});
  const name='part-'+first+'.json.gz';fs.writeFileSync(path.join(out,name),encoded,{flag:'wx'});
  parts.push({path:name,bytes:encoded.length,sha256:digest(encoded),uncompressed_bytes:raw.length,uncompressed_sha256:digest(raw),first_owner:first+1,owners:rows.length});
}
const report={version:1,execution_commit:head,producer,inputs,parts,locations:compact.features.length,
  predecessor_release:old.original_release,successor_release:release.id,footprints_sha256:compact.footprints_sha256,
  owner_sha256:compact.owner_sha256,changed_ids:migration.changed_ids,unchanged_locations:49623,
  source_shape_policy:'Two exact reviewed native geometry values; every other complete compact feature, stable owner index and parent preserved.',
  budget:budget.snapshot(),installed:false,published:false,installation_ready:false};
fs.writeFileSync(path.join(out,'inputs.json'),JSON.stringify(report)+'\n',{flag:'wx'});
console.log(JSON.stringify({locations:report.locations,changed:2,parts:parts.length,owner_mapping_preserved:true,release:release.id}));
