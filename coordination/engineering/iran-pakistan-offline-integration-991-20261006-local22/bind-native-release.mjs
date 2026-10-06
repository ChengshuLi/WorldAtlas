// Bind the exhaustively checked materialization to the actual offline release.
// This composes retained comparisons; it never claims geographic approval.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {committedPreparationFiles,requirePlainExecution,candidateBudget} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
requirePlainExecution();
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..'),prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const [oneName,twoName,receiptName]=process.argv.slice(2);
const owned=name=>{const p=path.resolve(root,name??'');if(!p.startsWith(path.join(root,prefix)+path.sep)||fs.existsSync(p))throw Error('Exclusive owned output required');return p;};
const one=owned(oneName),two=owned(twoName),receiptPath=owned(receiptName);
if(new Set([one,two,receiptPath]).size!==3)throw Error('Distinct output vintages required');
const head=execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim(),digest=raw=>createHash('sha256').update(raw).digest('hex');
const producer=committedPreparationFiles(root,head,['package.json',prefix+'/bind-native-release.mjs','scripts/native-ownership/native-preparation-guards.mjs']);
const inputs=[];
const read=name=>{
  const raw=execFileSync('git',['-C',root,'show',head+':'+prefix+'/'+name],{maxBuffer:32*1024*1024});
  if(!raw.equals(fs.readFileSync(path.join(root,prefix,name))))throw Error('Uncommitted source product');
  inputs.push({commit:head,path:prefix+'/'+name,bytes:raw.length,sha256:digest(raw)});return raw;
};
const auditRaw=read('native-patch-verification.json'),audit=JSON.parse(auditRaw);
const sourceRaw=read('native-patch-v2/pending-manifest.json'),source=JSON.parse(sourceRaw);
const releaseRaw=read('successor-release-v1/releases-v7-gzip.json.gz'),release=JSON.parse(gunzipSync(releaseRaw)).releases.at(-1);
const successorRaw=read('successor-verification-v1.json'),successor=JSON.parse(successorRaw);
const migrationRaw=read('release-proof-v3/migration-receipt.json'),migration=JSON.parse(migrationRaw);
const validationRaw=read('release-proof-v3/validation.json'),validation=JSON.parse(validationRaw);
if(source.geographic_release!==null||source.release_pending!==true||source.installation_ready!==false||
  digest(sourceRaw)!==audit.pending_manifest_sha256||audit.changed_cells!==954||audit.changed_rows!==65||
  audit.lost_owned_cells!==0||audit.unsupported_changes!==0||audit.checked_rows!==source.size||audit.unchecked_cells!==0||
  audit.checked_cells!==source.size**2||audit.checked_candidate_runs*2!==source.runWords||audit.owned_cells!==source.accounting.owned_cells||
  release.id!==successor.successor_release||successor.historical_claims_transferred!==false||successor.complete_memberships!==84833||
  release.footprints_sha256!==source.footprints_sha256||release.footprints_sha256!==migration.after_footprints_sha256||
  release.hierarchy_sha256!==source.hierarchy_sha256||!validation.exact_staged_original_archive_checked||
  migration.historical_claims_transferred!==false||migration.changed_ids.length!==2||migration.added_ids.length||migration.removed_ids.length||successor.retained_target_identities!==2)throw Error('Complete grid/migration/release proof linkage differs');
const raws=new Map();
for(const product of audit.products){
  const a=read('native-patch-v2/'+product.path),b=read('native-patch-v3/'+product.path);
  if(a.length!==product.bytes||digest(a)!==product.sha256||!a.equals(b))throw Error('Original complete native two-run products differ');
  raws.set(product.path,a);
}
const oldInventoryHash=digest(Buffer.from(JSON.stringify(audit.products)));
if(audit.two_run_products!==audit.products.length||audit.run_one_sha256!==oldInventoryHash||audit.run_two_sha256!==oldInventoryHash)throw Error('Original complete two-run inventory differs');
const manifest={...source,geographic_release:release.id,release_pending:false,
  provenance:{...source.provenance,source_migration:{commit:head,path:prefix+'/release-proof-v3/validation.json',sha256:digest(validationRaw)},
    release_binding:{commit:head,successor_manifest:{path:prefix+'/successor-release-v1/releases-v7-gzip.json.gz',sha256:digest(releaseRaw)},
      decoded_comparison:{path:prefix+'/native-patch-verification.json',sha256:digest(auditRaw)},
      successor_readback:{path:prefix+'/successor-verification-v1.json',sha256:digest(successorRaw)},
      scope:'Mathematical composition of original exhaustive native rule proof, exact component native delta and complete decoded-grid comparison; no source/geographic/installation approval.'}}};
const budget=candidateBudget([...inputs,...producer]);
const manifestRaw=Buffer.from(JSON.stringify(manifest)+'\n'),products=[];
for(const destination of [one,two]){
  fs.mkdirSync(destination);
  for(const part of manifest.parts){
    const raw=raws.get(part.path);if(!raw||digest(raw)!==part.sha256||raw.length!==part.bytes)throw Error('Final part differs from checked grid');
    budget.add({bytes:raw.length});fs.mkdirSync(path.dirname(path.join(destination,part.path)),{recursive:true});fs.writeFileSync(path.join(destination,part.path),raw,{flag:'wx'});
  }
  budget.add({bytes:manifestRaw.length});fs.writeFileSync(path.join(destination,'manifest.json'),manifestRaw,{flag:'wx'});
}
for(const part of manifest.parts)products.push({path:part.path,bytes:part.bytes,sha256:part.sha256});
products.push({path:'manifest.json',bytes:manifestRaw.length,sha256:digest(manifestRaw)});products.sort((a,b)=>a.path.localeCompare(b.path));
for(const product of products)if(!fs.readFileSync(path.join(one,product.path)).equals(fs.readFileSync(path.join(two,product.path))))throw Error('Final full two-run binding differs');
const inventoryHash=digest(Buffer.from(JSON.stringify(products)));
const receipt={version:1,evaluation_commit:head,executed_sources:producer,inputs,method:manifest.method,
  baseline_commit:manifest.provenance.baseline_commit,preparation_commit:manifest.provenance.evaluation_commit,binding_commit:head,
  checked_rows:audit.checked_rows,checked_cells:audit.checked_cells,unchecked_cells:0,checked_runs:audit.checked_candidate_runs,
  owned_cells:audit.owned_cells,owners:manifest.accounting.owners,products,two_run_products:products.length,run_one_sha256:inventoryHash,run_two_sha256:inventoryHash,
  predecessor_exhaustive_native_proof:source.provenance.native_baseline_manifest,decoded_patch_proof:{commit:head,path:prefix+'/native-patch-verification.json',sha256:digest(auditRaw)},
  source_migration:manifest.provenance.source_migration,successor_release:release.id,budget:budget.snapshot(),
  scientific_approval:false,installation_ready:false,installed:false,published:false,
  limits:['Full-domain normative proof by retained original-grid comparison plus exact native source delta and exhaustive decoded comparison; no independent physical water/legal/date assertion or installation approval.']};
fs.writeFileSync(receiptPath,JSON.stringify(receipt)+'\n',{flag:'wx'});
console.log(JSON.stringify({manifest_sha256:digest(manifestRaw),receipt_sha256:digest(fs.readFileSync(receiptPath)),products:products.length,release:release.id,installed:false}));
