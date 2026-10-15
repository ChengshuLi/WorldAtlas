import path from 'node:path';
import fs from 'node:fs/promises';
import { build } from 'vite';
import {gzipSync,gunzipSync} from 'node:zlib';
import { createHash } from 'node:crypto';
import {assertPackageStage} from './package-build.mjs';
assertPackageStage();
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
const {packageStartupOwnership,packagePreparedStartupOwnership} = await import('./package-startup-ownership.mjs');
const {selectBuildOwnership,readBuildOwnershipSelection} = await import('./select-build-ownership.mjs');
const {readGeographicReleaseManifest} = await import('./read-geographic-release-manifest.mjs');
const {checkPrepared} = await import('./check-prepared.mjs');
const {environmentClassifications} = await import('../src/environment-classifications.js');
const {openDatabase,seedDatabase,geography} = await import('../database.mjs');
const {prepareCurrentSelectedAdditive} = await import('./package-current-additive.mjs');

// Preparation and scientific qualification publish current products once. Builds
// consume those products; historical reconstruction remains explicit reproduction.
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
const currentContext=ownershipSelection.requireNative?JSON.parse(await fs.readFile('data/current-build-context.json')):null;
if(currentContext&&(currentContext.native_manifest_sha256!==selectedGrid.sha256||currentContext.release_id!==geographicRelease.id||currentContext.footprints_sha256!==geographicRelease.footprints_sha256||currentContext.hierarchy_sha256!==geographicRelease.hierarchy_sha256))throw Error('Prepared current context differs from selected native reference; prepare and review matching products');
const nativeContextInputStage=currentContext?{status:'accepted-prepared-assets',native_manifest_sha256:selectedGrid.sha256,preparation:currentContext.nativeContextInputStage}:null;
const db = openDatabase();
try {
  seedDatabase(db);
  const reference = geography(db);
  const pixelAudit=JSON.parse(await fs.readFile('data/pixel-audit.json','utf8'));
  reference.pixelMissing=pixelAudit.missing.map(f=>f.id);
  checkPrepared(reference.features);
  if(geographicRelease.hierarchy_sha256!==createHash('sha256').update(await fs.readFile('data/hierarchy.json')).digest('hex')||geographicRelease.footprints_sha256!==checkPrepared(reference.features))throw Error('Reference release does not match prepared map assets');
  validatePreparedEvidenceIndex(preparedEvidence,geographicRelease);
  const boundarySourceReviews=currentContext?.boundarySourceReviews??{};
  let gridIndex,ownership;
  if(fixedGrid){
    if(fixedGrid.footprints_sha256!==checkPrepared(reference.features)||fixedGrid.hierarchy_sha256!==createHash('sha256').update(await fs.readFile('data/hierarchy.json')).digest('hex'))throw Error('Precompiled canonical grid is stale');
    const bytes=selectedGrid.bounds;
    if(createHash('sha256').update(bytes).digest('hex')!==fixedGrid.bounds.sha256)throw Error('Precompiled location bounds hash mismatch');
    const bounds=JSON.parse(gunzipSync(bytes)),byId=new Map(bounds.map(row=>[row.id,row]));
    if(byId.size!==reference.features.length||bounds.some((row,i)=>row.index!==i+1)||reference.features.some(f=>!byId.has(f.id)))throw Error('Precompiled grid identity inventory mismatch');
    gridIndex=createGridIndex(reference.features.map(feature=>({...feature,geometry:null,gridBounds:byId.get(feature.id).bounds,pixelIndex:byId.get(feature.id).index})));
  }else{gridIndex=createGridIndex(reference.features);ownership=packOwnership(compileOwnership(gridIndex));}
  const pixelIndices=new Map(gridIndex.map(({feature,index})=>[feature.id,index]));
  const packageAdditive=ownershipSelection.requireNative?await prepareCurrentSelectedAdditive({root:process.cwd(),selectedGrid,geographicRelease,features:reference.features.map(feature=>({...feature,pixelIndex:pixelIndices.get(feature.id)}))}):null;
  const history = {
    attributes:db.prepare('SELECT * FROM attribute_records WHERE location_id IN (SELECT id FROM locations WHERE active=1)').all().map(r=>({...r,value:JSON.parse(r.value),metadata:JSON.parse(r.metadata)})),
    states: db.prepare('SELECT * FROM states WHERE location_id IN (SELECT id FROM locations WHERE active=1)').all(),
    boundaries: db.prepare('SELECT * FROM boundaries WHERE location_id IN (SELECT id FROM locations WHERE active=1)').all().map(record => ({ ...record, geometry: JSON.parse(record.geometry) }))
  };
  await build({ base: './', define: { 'import.meta.env.VITE_STATIC_ATLAS': JSON.stringify('true'),'import.meta.env.VITE_HOSTED_DATABASE': JSON.stringify(process.env.ATLAS_HOSTED_BUILD==='1'?'true':'false') } });
  await packageAdditive?.publish('dist');
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
  if(fixedGrid?.method){
    const prepared=await packagePreparedStartupOwnership({manifest:fixedGrid,manifestSha:selectedGrid.sha256,source:'data/canonical-grid/current-startup',destination:'dist'});
    Object.assign(pixelMap,prepared.pixelMap);
  }else if(fixedGrid){
    for(const part of fixedGrid.parts){
      const bytes=await fs.readFile(path.join(selectedGrid.source,part.path));
      if(createHash('sha256').update(bytes).digest('hex')!==part.sha256)throw Error(`Precompiled ownership hash mismatch: ${part.path}`);
      if(fixedGrid.version!==2||part.kind==='rows'){await fs.mkdir(path.dirname(`dist/${part.path}`),{recursive:true});await fs.writeFile(`dist/${part.path}`,bytes);}
    }
    if(fixedGrid.version===2)Object.assign(pixelMap,(await packageStartupOwnership({manifest:fixedGrid,source:selectedGrid.source,destination:'dist'})).pixelMap);
  }else for(const kind of ['rows','runs'])for(let offset=0;offset<ownership[kind].length;offset+=1048576){
    const words=ownership[kind].slice(offset,offset+1048576),asset=`ownership/${kind}-${offset}.bin.gz`;
    await fs.writeFile(`dist/${asset}`,gzipSync(shuffleOwnershipBytes(words),{level:9}));pixelMap.parts.push({kind,offset,words:words.length,path:asset,encoding:'byte-shuffle'});
  }
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
    coverageClassification=currentContext?.coverageClassification??JSON.parse(await fs.readFile(coveragePath));
    const canonicalHash=selectedGrid.sha256;
    await loadCoverageClassification(coverageClassification,{...fixedGrid,release_id:geographicRelease.id,canonical_grid_sha256:canonicalHash},async url=>new Response(await fs.readFile('data/'+url.replace(/^\.\//,''))));
    pixelMap.canonical_grid_sha256=canonicalHash;
    await fs.mkdir('dist/coverage-classification',{recursive:true});
    for(const part of coverageClassification.parts)await fs.copyFile('data/'+part.path,'dist/'+part.path);
  }
  const referenceBundle=await packageReferenceBundle({source:'data/reference-attributes',destination:'dist/reference-attributes',expectedFootprints:geographicRelease.footprints_sha256});
  await fs.writeFile('dist/atlas-geography.json', JSON.stringify({gridVerification:selectedGrid?.verification??null,nativeContextInputStage,coverageClassification,referenceAttributes:referenceBundle.descriptor,contentCapabilities:{mapSnapshots:1,datedGeography:1,datedFootprints:0,storageExport:2},type:reference.type,sourceQualityReviews:reference.sourceQualityReviews,boundarySourceReviews,reference_release:packageAdditive?.reference_release??geographicRelease,...(packageAdditive?{additiveRelease:packageAdditive.additiveRelease}:{}),preparedEvidence:{footprints_sha256:preparedEvidence.footprints_sha256,hierarchy_sha256:preparedEvidence.hierarchy_sha256,index_sha256:createHash('sha256').update(await fs.readFile('data/prepared-evidence/index.json')).digest('hex')},pixelMissing:reference.pixelMissing,units:reference.units,temporal:{history:[],links:reference.temporal.links},entityParts,temporalHistoryParts,parts:catalogParts,geometryParts:parts,pixelMap}));
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
