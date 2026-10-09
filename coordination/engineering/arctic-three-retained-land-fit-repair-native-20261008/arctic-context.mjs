// Complete current continuation; original numerical validators retain their own brands.
import assert from 'node:assert/strict';
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {isDeepStrictEqual} from 'node:util';
import {validateChainedBuildContext,getSuccessfulChainedContext,foldCoverageContinuation} from '../eastern-two-gap-repair-native-20261007/chained-context.mjs';
import {validateContextMigration} from '../../../scripts/native-ownership/validate-context-migration.mjs';
import {requireValidatedGeometryMigrations} from '../../../scripts/prepare-geographic-release.mjs';
import {validateNativeSelectionReceipt} from '../../../scripts/native-ownership/require-verified-selection.mjs';
import {rebindCoverageManifest} from '../../../scripts/rebind-coverage-manifest.mjs';
import {candidateBudget} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
const hash=raw=>createHash('sha256').update(raw).digest('hex');
const IDS=['atlas:physical:CAN-15:NWT','atlas:physical:CAN-25:NUN'];
const BEFORE='b9a3c8bf375217dba3a50d1a022ec7e4ac6c6f1cdedff22845da953c805b7433';
const AFTER='2deeff1457ff9238cb3dbe599e9a858dcce29d8ba88e2a66abe2785ddec0aed9';
const PRIOR_STAGE='78347715e701c7e7d9775d17f3934dd3c1b61dbc46533d6179c979ae629d69d7';
const RECEIPT='fbcdc93980b55dd679cf7343da7c22e5ef8b7f37278f340f932a70b3770014b6';
const N2='coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008';
const validatedContinuations=new WeakMap();
export function requireArcticContinuation(result){
 const saved=validatedContinuations.get(result);assert(saved,'Actual successful three-step continuation identity required');
 assert.equal(hash(JSON.stringify(result.receipt)),saved.receipt_sha256);
 for(const proof of [result.coverageContinuation.originalGeometryValidation,result.coverageContinuation.predecessorGeometryValidation,result.geometryValidation])requireValidatedGeometryMigrations(proof);
 return saved;
}
const NAMED=['priorStage','registry','priorRegistry','changedRows','contextIndex','nativeManifest','priorNativeManifest','nativeComparison','geometryManifest','migrationReceipt'];
function ordinary(root,pin){
 assert(pin&&typeof pin.path==='string'&&!path.isAbsolute(pin.path)&&!pin.path.split('/').includes('..'));
 const file=path.join(root,pin.path);for(let p=file;;p=path.dirname(p)){assert(!fs.lstatSync(p).isSymbolicLink());if(p===path.dirname(p))break}
 const stat=fs.lstatSync(file);assert(stat.isFile()&&(stat.mode&511)===420);assert.equal(stat.size,pin.bytes);return {file,stat};
}
// Called BEFORE actual runtime authentication/body reads. Metadata stage is separately pinned.
export function reserveArcticContinuation({root,stageRaw,stage,declaredOriginalInputs}){
 assert.equal(stage.version,3);assert.equal(stage.issue,1520);assert.equal(stage.kind,'arctic-retained-land-context-continuation-v3');
 assert.deepEqual(stage.subjects,IDS);assert.equal(stage.before_footprints_sha256,BEFORE);assert.equal(stage.after_footprints_sha256,AFTER);
 const budget=candidateBudget([],{reserveBytes:262144,reserveDescriptors:16});
 budget.add({bytes:stageRaw.length});const pins=new Map();
 for(const name of NAMED){const pin=stage[name];
  if(declaredOriginalInputs&&['priorStage','priorRegistry','priorNativeManifest'].includes(name)){
   const original=declaredOriginalInputs.find(p=>p.space==='root'&&p.path===pin.path);assert(original,'Complete authenticated catalogue original member required');
   for(const key of ['bytes','sha256','decoded_bytes','decoded_sha256'])assert.equal(original[key],pin[key],'Original catalogue/pin mismatch');
  }else ordinary(root,pin);assert.equal(typeof pin.sha256,'string');assert(/^[a-f0-9]{64}$/.test(pin.sha256));
  const prior=pins.get(pin.path);if(prior)assert.deepEqual(prior,pin);else{pins.set(pin.path,pin);budget.add({bytes:pin.bytes});if(pin.decoded_bytes!==undefined)budget.add({bytes:pin.decoded_bytes});}}
 const snapshot=budget.snapshot();return {pins,reservedBytes:snapshot.accounted_bytes+262144,reservedDescriptors:pins.size+16};
}
function reader(root,reserved){
 return pin=>{assert.deepEqual(reserved.pins.get(pin.path),pin);const {file,stat}=ordinary(root,pin);const fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);let raw;
  try{raw=fs.readFileSync(fd);const held=fs.fstatSync(fd),after=fs.lstatSync(file);for(const k of ['dev','ino','size','mode','mtimeMs','ctimeMs'])assert.equal(stat[k],held[k]),assert.equal(stat[k],after[k]);}finally{fs.closeSync(fd)}
  assert.equal(raw.length,pin.bytes);assert.equal(hash(raw),pin.sha256);return raw;};
}
function registry(read,pin){const raw=read(pin);assert.equal(raw.readUInt32LE(raw.length-4),pin.decoded_bytes);const decoded=gunzipSync(raw,{maxOutputLength:pin.decoded_bytes});assert.equal(decoded.length,pin.decoded_bytes);assert.equal(hash(decoded),pin.decoded_sha256);return JSON.parse(decoded);}
export async function validateArcticBuildContext({root,stageRaw,stage,currentExecution,reservation,predecessorReference}){
 const reserved=reserveArcticContinuation({root,stageRaw,stage});assert.equal(reserved.reservedBytes,reservation.reservedBytes);assert.equal(reserved.reservedDescriptors,reservation.reservedDescriptors);
 const read=reader(root,reserved);const priorRaw=read(stage.priorStage);assert.equal(hash(priorRaw),PRIOR_STAGE);const priorStage=JSON.parse(priorRaw);
 // predecessorReference is the complete independently read old normal release;
 // the original validator compares it to its authenticated registry, no author boolean.
 assert.equal(predecessorReference.version,8);assert.equal(predecessorReference.footprints_sha256,BEFORE);
 // This performs the ORIGINAL actual 17-module child and both original full migrations.
 const prior=await validateChainedBuildContext({root,expectedReference:predecessorReference,stagePath:stage.priorStage.path,stageRaw:priorRaw,stage:priorStage,currentExecution,retainContextForContinuation:true,registryContinuation:stage.registryContinuation,continuationReservedBytes:reserved.reservedBytes,continuationReservedDescriptors:reserved.reservedDescriptors});
 const originalRegistry=registry(read,stage.priorRegistry),nextRegistry=registry(read,stage.registry);
 assert.deepEqual(nextRegistry.releases.slice(0,-1),originalRegistry.releases);assert.deepEqual(nextRegistry.batches.slice(0,originalRegistry.batches.length),originalRegistry.batches);
 for(const key of ['memberships_batches','sources_batches'])assert.deepEqual(nextRegistry[key].slice(0,originalRegistry[key].length),originalRegistry[key]);
 const predecessor=originalRegistry.releases.at(-1),release=nextRegistry.releases.at(-1);assert.deepEqual(predecessor,predecessorReference);assert.equal(release.version,9);assert.equal(release.footprints_sha256,AFTER);assert.equal(release.id,stage.release_id);
 const saved=getSuccessfulChainedContext(prior);const changed=JSON.parse(read(stage.changedRows));assert.equal(changed.length,2);assert.deepEqual(changed.map(r=>r.id).sort(),IDS);
 const replacements=new Map(changed.map(r=>[r.id,r]));const after=saved.rows.map(row=>{const update=replacements.get(row.id);if(!update)return row;assert.equal(update.pixelIndex,row.pixelIndex);assert.equal(update.properties.parent_id,row.properties.parent_id);return {...row,geometry:update.geometry};});
 assert.equal(after.length,49625);assert.equal(new Set(after.map(r=>r.id)).size,49625);assert.equal(after.filter((row,i)=>row===saved.rows[i]).length,49623);
 const index=JSON.parse(read(stage.contextIndex));assert.equal(index.locations,49625);assert.equal(index.footprints_sha256,AFTER);assert.equal(index.owner_sha256,saved.index.owner_sha256);assert.equal(index.parts.length,34);
 const differing=index.parts.map((part,i)=>isDeepStrictEqual(part,saved.index.parts[i])?-1:i).filter(i=>i!==-1);assert.deepEqual(differing,[4]);assert.equal(index.parts[4].sha256,'f9862325bcb56299f0eb843c8aa7ceac3a08c321ee475d4ad6ea1611a4f070ac');assert.equal(index.parts[4].decoded_sha256,'385deb287f9d79d82e17d034fe15cda937548b705851809af08308267f7759ea');
 const nativeRaw=read(stage.nativeManifest),native=JSON.parse(nativeRaw),priorNativeRaw=read(stage.priorNativeManifest),priorNative=JSON.parse(priorNativeRaw);
 validateNativeSelectionReceipt(native,hash(nativeRaw),JSON.parse(read(stage.nativeComparison)));assert.equal(native.geographic_release,release.id);assert.equal(native.footprints_sha256,AFTER);assert.equal(hash(priorNativeRaw),'a71edb65cbd7986e245f626e8a34b70e12c12d081ca24fc936bdd84e1bb07885');
 const receiptRaw=read(stage.migrationReceipt);assert.equal(hash(receiptRaw),RECEIPT);const receipt=JSON.parse(receiptRaw);assert.deepEqual(receipt.changed_ids,IDS);assert.equal(receipt.reused_ids.length,49623);assert.equal(receipt.history_transfer,'none');
 assert.deepEqual(release.metadata.geometry_migration,{commit:'9b212c585583dc218a961b4c7ee1056a64b54726',path:N2+'/migration-receipt.json',sha256:RECEIPT,before_footprints_sha256:BEFORE,after_footprints_sha256:AFTER,history_transfer:'none'});
 const manifest=JSON.parse(read(stage.geometryManifest));assert.deepEqual(Object.keys(manifest.files),['migration-receipt.json']);assert.equal(manifest.files['migration-receipt.json'].archive_path,undefined);assert.equal(manifest.files['migration-receipt.json'].uncompressed_bytes,undefined);assert.equal(manifest.files['migration-receipt.json'].bytes,receiptRaw.length);assert.equal(manifest.files['migration-receipt.json'].sha256,RECEIPT);
 // The original general validator issues the third LIVE brand; no compact receipt substitute.
 const migration=validateContextMigration({original:saved.rows,migrated:after,candidates:Object.fromEntries(changed.map(row=>[row.id,row.geometry])),predecessorRelease:predecessor,release,migrationManifestFile:path.join(root,stage.geometryManifest.path)});
 const results=[prior.coverageContinuation.originalGeometryValidation,prior.geometryValidation,migration.geometryValidation];assert.equal(new Set(results).size,3);for(const result of results)requireValidatedGeometryMigrations(result);
 const {geometryValidation,...compact}=migration;const result={receipt:{status:'verified',stage_sha256:hash(stageRaw),stage_path:stage.path,migration:compact,prior_context:prior.receipt,physical_association_chain:{versions:[6,7,8,9],physical_assets_recalculated:false},continuation_reservation:reserved.reservedBytes,scientific_approval:false},geometryValidation,predecessorRelease:predecessor,coverageContinuation:{...prior.coverageContinuation,predecessorGeometryValidation:prior.geometryValidation,predecessorGrid:priorNative,predecessorGridSha256:hash(priorNativeRaw),predecessorRelease:predecessor},sourceAssociations:[{release:predecessor,changed_ids:prior.receipt.migration.changed_ids},{release,changed_ids:compact.changed_ids}]};
 validatedContinuations.set(result,Object.freeze({receipt_sha256:hash(JSON.stringify(result.receipt)),manifest_sha256:hash(nativeRaw),release_id:release.id,stage_sha256:hash(stageRaw)}));
 return result;
}
export function foldArcticCoverage(manifest,{context,originalGrid,originalGridSha256,selectedGrid,selectedGridSha256,release}){
 const c=context.coverageContinuation;
 for(const proof of [c.originalGeometryValidation,c.predecessorGeometryValidation,context.geometryValidation])requireValidatedGeometryMigrations(proof);
 const v8=foldCoverageContinuation(manifest,{originalGrid,originalGridSha256,selectedGrid:c.predecessorGrid,selectedGridSha256:c.predecessorGridSha256,release:c.predecessorRelease,steps:[{originalGrid,originalGridSha256,selectedGrid:c.middleGrid,selectedGridSha256:c.middleGridSha256,release:c.middleRelease,predecessorRelease:c.originalRelease,geometryValidation:c.originalGeometryValidation},{originalGrid:c.middleGrid,originalGridSha256:c.middleGridSha256,selectedGrid:c.predecessorGrid,selectedGridSha256:c.predecessorGridSha256,release:c.predecessorRelease,predecessorRelease:c.middleRelease,geometryValidation:c.predecessorGeometryValidation}]});
 const result=rebindCoverageManifest(v8,{originalGrid:c.predecessorGrid,originalGridSha256:c.predecessorGridSha256,selectedGrid,selectedGridSha256,release,predecessorRelease:c.predecessorRelease,geometryValidation:context.geometryValidation});
 const last=structuredClone(v8.ownership_binding);const earlier=last.previous_associations??[];delete last.previous_associations;
 assert.equal(earlier.length,1);result.ownership_binding.previous_associations=[...earlier,last];
 assert.deepEqual([...result.ownership_binding.previous_associations,result.ownership_binding].map(binding=>[binding.geometry_migration.predecessor_release_id,binding.geometry_migration.successor_release_id]),[[c.originalRelease.id,c.middleRelease.id],[c.middleRelease.id,c.predecessorRelease.id],[c.predecessorRelease.id,release.id]]);
 const fields=structuredClone(result);delete fields.ownership_binding;for(const key of ['release_id','footprints_sha256','canonical_grid_sha256'])fields[key]=manifest[key];assert.deepEqual(fields,manifest,'All original class/source/blocked/pixel asset metadata retained');return result;
}
