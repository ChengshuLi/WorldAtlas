import path from 'node:path';
import fs from 'node:fs/promises';
import { build } from 'vite';
import {gzipSync,gunzipSync} from 'node:zlib';
import { createHash } from 'node:crypto';
import {assertPackageStage} from './package-build.mjs';
import {requireValidatedGeometryMigrations} from './prepare-geographic-release.mjs';
assertPackageStage();
import {restoreCanonicalProducts} from '../coordination/engineering/eastern-two-gap-repair-native-20261007/restore-canonical-products.mjs';
await fs.mkdir('.cache',{recursive:true});
const restoredCanonical=await restoreCanonicalProducts({root:process.cwd(),temporaryRoot:process.cwd()+'/.cache'});
const {resolveTypedSnapshot} = await import('../src/typed-snapshot.js');
const {createGridIndex} = await import('../src/pixel-grid.js');
const {compileOwnership,packOwnership} = await import('../src/pixel-ownership.js');
const {shuffleOwnershipBytes} = await import('../src/ownership-codec.js');
const {prepareEvidenceBundle} = await import('./prepare-evidence-bundle.mjs');
const {readPreparedEvidenceBundle} = await import('./read-prepared-evidence-bundle.mjs');
const {validatePreparedEvidenceIndex} = await import('../src/prepared-evidence.js');
const {packageOwnershipHistory} = await import('./package-ownership-history.mjs');
const {packageReferenceBundle} = await import('./package-reference-bundle.mjs');
const {loadCoverageClassification} = await import('../src/coverage-classification.js');
const {packageStartupOwnership} = await import('./package-startup-ownership.mjs');
const {packageVersionedStartupOwnership} = await import('../coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/startup-vintage.mjs');
const {selectBuildOwnership,readBuildOwnershipSelection} = await import('./select-build-ownership.mjs');
const {validateBuildContextVintage: validateOriginalBuildContext} = await import('../coordination/engineering/subject-descriptor-decode-20261007/context-vintage-dispatch.mjs');
const {validateBuildContextStage: validateCurrentBuildContext,BUILD_CONTEXT_STAGE_PATH} = await import('./native-ownership/validate-build-context-stage.mjs');
const {packageNativeLatitudes} = await import('./package-native-latitudes.mjs');
const {rebindCoverageManifest} = await import('./rebind-coverage-manifest.mjs');
const {foldCoverageContinuation,selectBuildContextValidator} = await import('../coordination/engineering/eastern-two-gap-repair-native-20261007/chained-context.mjs');
const {readPackageCurrentExecution} = await import('../coordination/engineering/eastern-two-gap-repair-native-20261007/current-execution.mjs');
function releaseBuildContextBaselines(context) {
  const third=context.coverageContinuation.predecessorGeometryValidation;
  const results=third?[context.geometryValidation,third,context.coverageContinuation.originalGeometryValidation]:[context.geometryValidation,context.coverageContinuation.originalGeometryValidation];
  const expected=context.receipt.migration.locations;
  if(!Number.isSafeInteger(expected)||expected<=0||new Set(results).size!==results.length)throw Error('Complete distinct context validation results required');
  for(const result of results){
    requireValidatedGeometryMigrations(result);
    if(!Array.isArray(result.baselineFeatures)||result.baselineFeatures.length!==expected)throw Error('Complete validated baseline work arrays required');
  }
  // These full rows have already passed both complete validations. This builder
  // consumes only the live branded proofs and disposition sets in coverage folds.
  // General validators and their other callers keep their own baselineFeatures.
  for(const result of results)result.baselineFeatures=null;
  for(const result of results)requireValidatedGeometryMigrations(result);
  return {results:results.length,released_baseline_feature_references:expected*results.length,proofs_and_dispositions_retained:true};
}
const originalContextStage=await fs.readFile(BUILD_CONTEXT_STAGE_PATH,'utf8').then(JSON.parse,error=>{if(error.code==='ENOENT')return null;throw error;});
let contextStage=originalContextStage;
const validateBuildContextStage=selectBuildContextValidator(originalContextStage,{legacy:validateOriginalBuildContext,current:validateCurrentBuildContext});
const {readGeographicReleaseManifest,decodeGeographicReleaseBatch} = await import('./read-geographic-release-manifest.mjs');
const {checkPrepared} = await import('./check-prepared.mjs');
const {environmentClassifications} = await import('../src/environment-classifications.js');
const { openDatabase, seedDatabase, geography } = await import('../database.mjs');
// The outer package retains literal oldV2 so it issues genuine current code
// authority. A separately owned sidecar opts into the third continuation.
const sidecarPath='coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/context-stage-v9.json';
const sidecarRaw=await fs.readFile(sidecarPath).catch(error=>{if(error.code==='ENOENT')return null;throw error;});
let continuedContext=null;
if(sidecarRaw){
  contextStage=JSON.parse(sidecarRaw);if(originalContextStage?.version!==2)throw Error('Successor requires genuine originalV2 package execution');
  const {preflightArcticPackage}=await import('../coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/arctic-package-preflight.mjs');
  const {validateArcticBuildContext}=await import('../coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/arctic-context.mjs');
  const {installV9Stage}=await import('../coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/install-v9-stage.mjs');
  if(contextStage.version===4){
    const {preflightArtifactPackage}=await import('../coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/arctic-package-preflight.mjs');
    preflightArtifactPackage({source:process.env.WORLDATLAS_PACKAGE_SOURCE_ROOT,stage:process.cwd(),sidecar:contextStage});
    const currentExecution=readPackageCurrentExecution(process.cwd());
    const {consumeQualifiedArcticArtifacts}=await import('../coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/qualified-artifact-consumer.mjs');
    continuedContext=await consumeQualifiedArcticArtifacts({root:process.cwd(),stage:contextStage,selection:JSON.parse(await fs.readFile('data/ownership-selection.json')),restoredReceipt:restoredCanonical,currentExecution});
  }else{
    const admission=preflightArcticPackage({root:process.cwd(),stageRaw:sidecarRaw,stage:contextStage,priorImage:restoredCanonical.priorImage});
    const execution=readPackageCurrentExecution(process.cwd());
    const priorRegistry=JSON.parse(gunzipSync(await fs.readFile(contextStage.priorRegistry.path)));
    continuedContext=await validateArcticBuildContext({root:process.cwd(),stageRaw:sidecarRaw,stage:contextStage,currentExecution:execution,reservation:admission.reservation,predecessorReference:priorRegistry.releases.at(-1)});
    releaseBuildContextBaselines(continuedContext);
  }
  continuedContext.installation=await installV9Stage({root:process.cwd(),stage:contextStage,context:continuedContext});
}
const ownershipSelection=await readBuildOwnershipSelection();
const audit=JSON.parse(await fs.readFile('data/granularity-audit.json','utf8'));
if(audit.issues.length || !audit.input_sha256)throw new Error('Geography audit has not passed');
for(const [file,expected] of Object.entries(audit.input_sha256)){
 const actual=createHash('sha256').update(await fs.readFile(`data/${file}`)).digest('hex');
 if(actual!==expected)throw new Error(`Stale geography audit: ${file}; rerun scripts/audit-granularity.py`);
}

// A read-only export of the current database, suitable for a private hosted preview.
const preparedEvidence=ownershipSelection.requireNative?await readPreparedEvidenceBundle():prepareEvidenceBundle();
// Validate the complete retained context chain before allocating application geography.
const releaseManifest=readGeographicReleaseManifest('data/geographic-releases');
const geographicRelease=releaseManifest.releases.at(-1);
if(ownershipSelection.releaseId&&ownershipSelection.releaseId!==geographicRelease.id)throw Error('Committed ownership selection belongs to another release');
const fixedGridPath=ownershipSelection.manifestPath;
const selectedGrid=await fs.access(fixedGridPath).then(()=>selectBuildOwnership({...ownershipSelection,expectedReference:geographicRelease}),()=>{if(ownershipSelection.requireNative)throw Error('Selected native grid is missing');return null;});
const fixedGrid=selectedGrid?.manifest;
const currentExecution=!continuedContext&&contextStage?.version===2?readPackageCurrentExecution(process.cwd()):undefined;
const nativeBuildContext=continuedContext??(fixedGrid?.method?await validateBuildContextStage({expectedReference:geographicRelease,currentExecution}):null);
if(continuedContext&&(fixedGridPath!==contextStage.nativeManifest.path||selectedGrid.sha256!==contextStage.nativeManifest.sha256||geographicRelease.id!==contextStage.release_id))throw Error('Normal selected bank differs from actual three-step validation');
const nativeContextInputStage=nativeBuildContext?.receipt??null;
if(!continuedContext&&nativeBuildContext?.coverageContinuation)releaseBuildContextBaselines(nativeBuildContext);
const db = openDatabase();
try {
  seedDatabase(db);
  const reference = geography(db);
  const pixelAudit=JSON.parse(await fs.readFile('data/pixel-audit.json','utf8'));
  reference.pixelMissing=pixelAudit.missing.map(f=>f.id);
  checkPrepared(reference.features);
  if(geographicRelease.hierarchy_sha256!==createHash('sha256').update(await fs.readFile('data/hierarchy.json')).digest('hex')||geographicRelease.footprints_sha256!==checkPrepared(reference.features))throw Error('Reference release does not match prepared map assets');
  validatePreparedEvidenceIndex(preparedEvidence,geographicRelease);
  const boundarySourceReviews={};
  if(nativeContextInputStage?.migration){
    const sources=[];
    for(const name of releaseManifest.sources_batches){
      const part=releaseManifest.batches.find(part=>part.path===name);
      const payload=decodeGeographicReleaseBatch(await fs.readFile('data/geographic-releases/'+name),part);
      sources.push(...JSON.parse(payload).sources);
    }
    const associations=nativeBuildContext.sourceAssociations??[{release:geographicRelease,changed_ids:nativeContextInputStage.migration.changed_ids}];
    for(const association of associations){
      const associated=association.release;
      const source=sources.find(source=>source.id===associated.source_id);
      if(!source?.metadata?.source_policy)throw Error('Migrated reference lacks its source policy');
      if(source.metadata.geometry_migration?.sha256!==associated.metadata.geometry_migration.sha256)throw Error('Migrated boundary attribution belongs to another geometry proof');
      for(const id of association.changed_ids)boundarySourceReviews[id]={
        source:source.name,url:source.url,license:source.license,vintage:source.vintage,
        policy:source.metadata.source_policy,source_offer:source.metadata.source_offer,
        derivative_url:'https://github.com/ChengshuLi/WorldAtlas/tree/'+associated.metadata.geometry_migration.commit,
        original_sources:source.metadata.source_evidence
      };
    }
  }
  let gridIndex,ownership;
  if(fixedGrid){
    if(fixedGrid.footprints_sha256!==checkPrepared(reference.features)||fixedGrid.hierarchy_sha256!==createHash('sha256').update(await fs.readFile('data/hierarchy.json')).digest('hex'))throw Error('Precompiled canonical grid is stale');
    const bytes=selectedGrid.bounds;
    if(createHash('sha256').update(bytes).digest('hex')!==fixedGrid.bounds.sha256)throw Error('Precompiled location bounds hash mismatch');
    const bounds=JSON.parse(gunzipSync(bytes)),byId=new Map(bounds.map(row=>[row.id,row]));
    if(byId.size!==reference.features.length||bounds.some((row,i)=>row.index!==i+1)||reference.features.some(f=>!byId.has(f.id)))throw Error('Precompiled grid identity inventory mismatch');
    gridIndex=createGridIndex(reference.features.map(feature=>({...feature,geometry:null,gridBounds:byId.get(feature.id).bounds,pixelIndex:byId.get(feature.id).index})));
  }else{gridIndex=createGridIndex(reference.features);ownership=packOwnership(compileOwnership(gridIndex));}
  const history = {
    attributes:db.prepare('SELECT * FROM attribute_records WHERE location_id IN (SELECT id FROM locations WHERE active=1)').all().map(r=>({...r,value:JSON.parse(r.value),metadata:JSON.parse(r.metadata)})),
    states: db.prepare('SELECT * FROM states WHERE location_id IN (SELECT id FROM locations WHERE active=1)').all(),
    boundaries: db.prepare('SELECT * FROM boundaries WHERE location_id IN (SELECT id FROM locations WHERE active=1)').all().map(record => ({ ...record, geometry: JSON.parse(record.geometry) }))
  };
  await build({ base: './', define: { 'import.meta.env.VITE_STATIC_ATLAS': JSON.stringify('true'),'import.meta.env.VITE_HOSTED_DATABASE': JSON.stringify(process.env.ATLAS_HOSTED_BUILD==='1'?'true':'false') } });
  const typedBytes=await fs.readFile('data/typed-prepared-v1.json');
  await resolveTypedSnapshot(JSON.parse(typedBytes),2026,{examples:true});
  await fs.writeFile('dist/typed-evidence.json',typedBytes);
  await fs.writeFile('dist/typed-evidence-manifest.json',JSON.stringify({version:1,path:'typed-evidence.json',sha256:createHash('sha256').update(typedBytes).digest('hex'),bytes:typedBytes.length,scope:'prepared typed evidence; no hosted schema capability assertion'}));
  // Keep every hosted asset below common static-host file limits.
  const parts=[];
  await fs.mkdir('dist/geography',{recursive:true});
  for(let i=0;i<reference.features.length;i+=1500){
    const part=`geography/part-${i/1500}.json.gz`;parts.push(part);
    await fs.writeFile(`dist/${part}`,gzipSync(JSON.stringify(reference.features.slice(i,i+1500).map(({id,geometry})=>({id,geometry}))),{level:9}));
  }
  await fs.mkdir('dist/ownership',{recursive:true});
  const pixelMap=fixedGrid?{...selectedGrid.metadata,parts:fixedGrid.parts}:{version:ownership.version??1,coordinateBits:ownership.coordinateBits,size:ownership.size,runWords:ownership.runs.length,parts:[]};
  // Original canonical files remain in data and prior published vintages. The
  // deployment includes only the transport referenced by its new manifest;
  // this build must never prune retained objects from the publisher's storage.
  if(fixedGrid)for(const part of fixedGrid.parts){const bytes=await fs.readFile(path.join(selectedGrid.source,part.path));if(createHash('sha256').update(bytes).digest('hex')!==part.sha256)throw Error(`Precompiled ownership hash mismatch: ${part.path}`);if(fixedGrid.version!==2||part.kind==='rows'){await fs.mkdir(path.dirname(`dist/${part.path}`),{recursive:true});await fs.writeFile(`dist/${part.path}`,bytes);}}
  else for(const kind of ['rows','runs'])for(let offset=0;offset<ownership[kind].length;offset+=1048576){
    const words=ownership[kind].slice(offset,offset+1048576),path=`ownership/${kind}-${offset}.bin.gz`;
    await fs.writeFile(`dist/${path}`,gzipSync(shuffleOwnershipBytes(words),{level:9}));pixelMap.parts.push({kind,offset,words:words.length,path,encoding:'byte-shuffle'});
  }
  if(fixedGrid?.version===2){
    const liveVersioned=contextStage?.version===3&&contextStage.issue===1520&&contextStage.kind==='arctic-retained-land-context-continuation-v3';
    const artifactVersioned=contextStage?.version===4&&contextStage.issue===1520&&nativeBuildContext?.kind==='authenticated-qualified-artifact-consumption-v1';
    if(artifactVersioned){const {requireConsumedArcticArtifacts}=await import('../coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/qualified-artifact-consumer.mjs');requireConsumedArcticArtifacts(nativeBuildContext);}
    const versioned=liveVersioned||artifactVersioned;
    if(versioned){
      // A clean output must retain the actual predecessor URLs for cached v8 clients.
      const priorPath='data/canonical-grid/eastern-v8/manifest.json';
      const priorRaw=await fs.readFile(priorPath);
      if(createHash('sha256').update(priorRaw).digest('hex')!=='a71edb65cbd7986e245f626e8a34b70e12c12d081ca24fc936bdd84e1bb07885')throw Error('Prior native manifest changed');
      const prior=JSON.parse(priorRaw),priorRows=prior.parts.filter(part=>part.kind==='rows');
      if(JSON.stringify(priorRows)!==JSON.stringify(fixedGrid.parts.filter(part=>part.kind==='rows')))throw Error('Successor row asset differs');
      await packageStartupOwnership({manifest:prior,source:path.dirname(priorPath),destination:'dist'});
    }
    const transport=versioned?await packageVersionedStartupOwnership({manifest:fixedGrid,manifestSha:selectedGrid.sha256,manifestPath:selectedGrid.manifestPath,source:selectedGrid.source,destination:'dist'}):await packageStartupOwnership({manifest:fixedGrid,source:selectedGrid.source,destination:'dist'});
    Object.assign(pixelMap,transport.pixelMap);
  }
  if(fixedGrid?.method){const latitude=await packageNativeLatitudes({manifest:fixedGrid,expectedReference:geographicRelease,destination:'dist'});pixelMap.native_latitudes=latitude.native_latitudes;}
  if(fixedGrid?.method)pixelMap.reference_owner_sha256=createHash('sha256').update(JSON.stringify(gridIndex.map(item=>[item.index,item.feature.id]))).digest('hex');
  const catalog=gridIndex.map(({feature,index,bounds})=>({...feature,geometry:null,pixelIndex:index,gridBounds:bounds}));
  const catalogParts=[];
  for(let i=0;i<catalog.length;i+=1500){const path=`geography/catalog-${i/1500}.json.gz`;catalogParts.push(path);await fs.writeFile(`dist/${path}`,gzipSync(JSON.stringify(catalog.slice(i,i+1500)),{level:9}));}
  const entityParts=[];
  for(let i=0;i<reference.temporal.entities.length;i+=5000){const path=`geography/entities-${i/5000}.json.gz`;entityParts.push(path);await fs.writeFile(`dist/${path}`,gzipSync(JSON.stringify(reference.temporal.entities.slice(i,i+5000)),{level:9}));}
  const temporalHistoryParts=[];
  for(let i=0;i<reference.temporal.history.length;i+=5000){const path=`geography/history-${i/5000}.json.gz`;temporalHistoryParts.push(path);await fs.writeFile(`dist/${path}`,gzipSync(JSON.stringify(reference.temporal.history.slice(i,i+5000))));}
  let coverageClassification=null;
  const coveragePath='data/coverage-classification/manifest.json';
  if(await fs.access(coveragePath).then(()=>true,()=>false)){
    if(!fixedGrid)throw Error('Physical classification requires canonical grid');
    coverageClassification=JSON.parse(await fs.readFile(coveragePath));
    const canonicalHash=selectedGrid.sha256;
    if(fixedGrid.method){
      const originalBytes=await fs.readFile('data/canonical-grid/manifest.json'),originalGrid=JSON.parse(originalBytes),originalGridSha256=createHash('sha256').update(originalBytes).digest('hex');
      const continuation=nativeBuildContext?.coverageContinuation;
      if(nativeBuildContext?.kind==='authenticated-qualified-artifact-consumption-v1'){
        const {associateQualifiedCoverage}=await import('../coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/qualified-artifact-association.mjs');
        coverageClassification=associateQualifiedCoverage(coverageClassification,{consumption:nativeBuildContext,originalGrid,originalGridSha256,selectedGrid:fixedGrid,selectedGridSha256:canonicalHash,release:geographicRelease});
      }else if(continuation?.predecessorGeometryValidation){
        const {foldArcticCoverage}=await import('../coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/arctic-context.mjs');
        coverageClassification=foldArcticCoverage(coverageClassification,{context:nativeBuildContext,originalGrid,originalGridSha256,selectedGrid:fixedGrid,selectedGridSha256:canonicalHash,release:geographicRelease});
      }else if(continuation){
        const middle={selectedGrid:continuation.middleGrid,selectedGridSha256:continuation.middleGridSha256,release:continuation.middleRelease};
        coverageClassification=foldCoverageContinuation(coverageClassification,{originalGrid,originalGridSha256,selectedGrid:fixedGrid,selectedGridSha256:canonicalHash,release:geographicRelease,steps:[
          {originalGrid,originalGridSha256,...middle,predecessorRelease:continuation.originalRelease,geometryValidation:continuation.originalGeometryValidation},
          {originalGrid:middle.selectedGrid,originalGridSha256:middle.selectedGridSha256,selectedGrid:fixedGrid,selectedGridSha256:canonicalHash,release:geographicRelease,predecessorRelease:middle.release,geometryValidation:nativeBuildContext.geometryValidation}
        ]});
      }else coverageClassification=rebindCoverageManifest(coverageClassification,{originalGrid,originalGridSha256,selectedGrid:fixedGrid,selectedGridSha256:canonicalHash,release:geographicRelease,predecessorRelease:nativeBuildContext?.predecessorRelease,geometryValidation:nativeBuildContext?.geometryValidation});
    }
    await loadCoverageClassification(coverageClassification,{...fixedGrid,release_id:geographicRelease.id,canonical_grid_sha256:canonicalHash},async url=>new Response(await fs.readFile('data/'+url.replace(/^\.\//,''))));
    pixelMap.canonical_grid_sha256=canonicalHash;
    await fs.mkdir('dist/coverage-classification',{recursive:true});
    for(const part of coverageClassification.parts)await fs.copyFile('data/'+part.path,'dist/'+part.path);
  }
  const referenceBundle=await packageReferenceBundle({source:'data/reference-attributes',destination:'dist/reference-attributes',expectedFootprints:geographicRelease.footprints_sha256});
  await fs.writeFile('dist/atlas-geography.json', JSON.stringify({gridVerification:selectedGrid?.verification??null,nativeContextInputStage,coverageClassification,referenceAttributes:referenceBundle.descriptor,contentCapabilities:{mapSnapshots:1,datedGeography:1,datedFootprints:0,storageExport:2},type:reference.type,sourceQualityReviews:reference.sourceQualityReviews,boundarySourceReviews,reference_release:geographicRelease,preparedEvidence:{footprints_sha256:preparedEvidence.footprints_sha256,hierarchy_sha256:preparedEvidence.hierarchy_sha256,index_sha256:createHash('sha256').update(await fs.readFile('data/prepared-evidence/index.json')).digest('hex')},pixelMissing:reference.pixelMissing,units:reference.units,temporal:{history:[],links:reference.temporal.links},entityParts,temporalHistoryParts,parts:catalogParts,geometryParts:parts,pixelMap}));
  await fs.writeFile('dist/atlas-history.json.gz',gzipSync(JSON.stringify(history)));
  await fs.writeFile('dist/environment-classifications.json',JSON.stringify({version:1,unknown:null,attributes:environmentClassifications}));
  await packageOwnershipHistory({source:'data/ownership-history',destination:'dist/ownership-history',hosted:process.env.ATLAS_HOSTED_BUILD==='1',compactReceipts:true});
  await fs.cp('data/ownership-runtime','dist/ownership-runtime',{recursive:true});
  // Complete original reference rows/index are pinned inside the new bundle.
  // Originals remain in data and prior published vintages; never prune them.
  await fs.mkdir('dist/prepared-evidence',{recursive:true});
  await fs.copyFile('data/prepared-evidence/index.json','dist/prepared-evidence/index.json');
  for(const part of preparedEvidence.parts)await fs.copyFile(`data/prepared-evidence/${part.path}`,`dist/prepared-evidence/${part.path}`);
  await fs.copyFile('data/macro-review-evidence.json','dist/macro-review-evidence.json');
  await fs.copyFile('data/macro-corrections.json','dist/macro-corrections.json');
  await fs.writeFile('dist/granularity-review-evidence.json.gz',gzipSync(await fs.readFile('data/granularity-review-evidence.json'),{level:9}));
  await fs.writeFile('dist/region-semantic-review.json.gz',gzipSync(await fs.readFile('data/region-semantic-review.json'),{level:9}));
  if(await fs.access('data/geographic-decisions').then(()=>true,()=>false)){
    await fs.mkdir('dist/geographic-decisions',{recursive:true});
    for(const file of await fs.readdir('data/geographic-decisions'))if(file.endsWith('.json'))await fs.writeFile(`dist/geographic-decisions/${file}.gz`,gzipSync(await fs.readFile(`data/geographic-decisions/${file}`),{level:9}));
    await fs.copyFile('data/geographic-decision-migration.json.gz','dist/geographic-decision-migration.json.gz');
  }
  await fs.copyFile('data/geographic-migration-archive.json.gz','dist/geographic-migration-archive.json.gz');
  for(const name of ['global-semantic-closure.json.gz','macro-boundary-migration.json.gz','final-grid-resolution-review.json.gz'])if(await fs.access(`data/${name}`).then(()=>true,()=>false))await fs.copyFile(`data/${name}`,`dist/${name}`);
  for(const file of new Map(Object.values(reference.sourceQualityReviews).flatMap(review=>review.public_evidence_files??[]).map(file=>[file.path,file])).values()){
    if(!/^[\w./-]+$/.test(file.path)||file.path.split('/').includes('..'))throw Error('Invalid public review evidence path');
    const bytes=await fs.readFile(`data/${file.path}`);if(createHash('sha256').update(bytes).digest('hex')!==file.sha256)throw Error('Public review evidence hash mismatch');
    await fs.mkdir('dist/'+file.path.split('/').slice(0,-1).join('/'),{recursive:true});await fs.writeFile(`dist/${file.path}`,bytes);
  }
  await fs.writeFile('dist/geographic-migration-review.json.gz',gzipSync(await fs.readFile('data/geographic-migration-review.json'),{level:9}));
  const pixelAuditBytes=await fs.readFile('data/pixel-audit.json'),pixelAuditTransport=gzipSync(pixelAuditBytes,{level:9});
  if(!gunzipSync(pixelAuditTransport).equals(pixelAuditBytes))throw Error('Pixel audit transport must preserve every original byte');
  await fs.writeFile('dist/pixel-audit.json.gz',pixelAuditTransport);
  for(const file of ['world-review.json','global-refinement-report.json','source-inventory.json','regional-membership-report.json','border-parent-review.json','attribute-sources.json','reference-polity-report.json','settlement-source-report.json'])await fs.copyFile(`data/${file}`,`dist/${file}`);
  const projectedReviewFile='data/macro-foundation/world-review-projection.json',hasProjectedReview=await fs.access(projectedReviewFile).then(()=>true,()=>false);
  if(hasProjectedReview){await fs.writeFile('dist/world-review-source-inspection.json.gz',gzipSync(await fs.readFile('data/world-review.json'),{level:9}));await fs.copyFile(projectedReviewFile,'dist/world-review.json');}
  for(const file of ['administrative-sources.json','granularity-report.json','hierarchy-report.json','semantic-report.json','granularity-audit.json','location-policy.json','coverage-report.json'])await fs.copyFile(`data/${file}`,`dist/${file}`);
  await fs.mkdir('dist/source-policy-corrections',{recursive:true});
  await fs.copyFile('data/source-policy-corrections/summary.json','dist/source-policy-corrections/summary.json');
  const frameworkReport=JSON.parse(await fs.readFile('data/hierarchy-report.json','utf8'));
  const worldReview=JSON.parse(await fs.readFile(hasProjectedReview?projectedReviewFile:'data/world-review.json','utf8'));
  for(const file of worldReview.location_parts||[]){await fs.mkdir(path.dirname(`dist/${file}`),{recursive:true});await fs.copyFile(`data/${file}`,`dist/${file}`);}
  for(const file of frameworkReport.change_parts||[])await fs.copyFile(`data/${file}`,`dist/${file}`);
  await fs.copyFile('data/framework-sources/manifest.json','dist/framework-sources.json');
  // Hosted packaging reports every violation with full file/category totals
  // after the Worker and migration transport join the final upload layout.
  if(process.env.ATLAS_HOSTED_BUILD!=='1')for(const file of await fs.readdir('dist',{recursive:true})){const stat=await fs.stat(`dist/${file}`);if(stat.isFile()&&stat.size>25*1024*1024)throw new Error(`Static asset exceeds 25 MiB: ${file}`);}
  console.log(`Static atlas ready: ${reference.features.length} polygons and ${history.states.length} dated records.`);
} finally { db.close(); }
