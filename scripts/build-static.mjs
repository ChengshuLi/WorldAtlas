import fs from 'node:fs/promises';
import { build } from 'vite';
import {gzipSync,gunzipSync} from 'node:zlib';
import {createGridIndex} from '../src/pixel-grid.js';
import {compileOwnership,packOwnership} from '../src/pixel-ownership.js';
import {shuffleOwnershipBytes} from '../src/ownership-codec.js';
import {prepareEvidenceBundle} from './prepare-evidence-bundle.mjs';
import { createHash } from 'node:crypto';
const audit=JSON.parse(await fs.readFile('data/granularity-audit.json','utf8'));
if(audit.issues.length || !audit.input_sha256)throw new Error('Geography audit has not passed');
for(const [file,expected] of Object.entries(audit.input_sha256)){
 const actual=createHash('sha256').update(await fs.readFile(`data/${file}`)).digest('hex');
 if(actual!==expected)throw new Error(`Stale geography audit: ${file}; rerun scripts/audit-granularity.py`);
}
import {checkPrepared} from './check-prepared.mjs';
import {environmentClassifications} from '../src/environment-classifications.js';
import { openDatabase, seedDatabase, geography } from '../database.mjs';

// A read-only export of the current database, suitable for a private hosted preview.
const preparedEvidence=prepareEvidenceBundle();
const db = openDatabase();
try {
  seedDatabase(db);
  const reference = geography(db);
  const pixelAudit=JSON.parse(await fs.readFile('data/pixel-audit.json','utf8'));
  reference.pixelMissing=pixelAudit.missing.map(f=>f.id);
  checkPrepared(reference.features);
  const fixedGridPath='data/canonical-grid/manifest.json';
  const fixedGrid=await fs.access(fixedGridPath).then(async()=>JSON.parse(await fs.readFile(fixedGridPath)),()=>null);
  let gridIndex,ownership;
  if(fixedGrid){
    if(fixedGrid.footprints_sha256!==checkPrepared(reference.features)||fixedGrid.hierarchy_sha256!==createHash('sha256').update(await fs.readFile('data/hierarchy.json')).digest('hex'))throw Error('Precompiled canonical grid is stale');
    const bytes=await fs.readFile(`data/canonical-grid/${fixedGrid.bounds.path}`);
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
  // Keep every hosted asset below common static-host file limits.
  const parts=[];
  await fs.mkdir('dist/geography',{recursive:true});
  for(let i=0;i<reference.features.length;i+=1500){
    const part=`geography/part-${i/1500}.json.gz`;parts.push(part);
    await fs.writeFile(`dist/${part}`,gzipSync(JSON.stringify(reference.features.slice(i,i+1500).map(({id,geometry})=>({id,geometry}))),{level:9}));
  }
  await fs.mkdir('dist/ownership',{recursive:true});
  const pixelMap=fixedGrid?Object.fromEntries(['version','coordinateBits','size','runWords','parts'].map(key=>[key,fixedGrid[key]])):{version:ownership.version??1,coordinateBits:ownership.coordinateBits,size:ownership.size,runWords:ownership.runs.length,parts:[]};
  if(fixedGrid)for(const part of fixedGrid.parts){const bytes=await fs.readFile(`data/canonical-grid/${part.path}`);if(createHash('sha256').update(bytes).digest('hex')!==part.sha256)throw Error(`Precompiled ownership hash mismatch: ${part.path}`);await fs.writeFile(`dist/${part.path}`,bytes);}
  else for(const kind of ['rows','runs'])for(let offset=0;offset<ownership[kind].length;offset+=1048576){
    const words=ownership[kind].slice(offset,offset+1048576),path=`ownership/${kind}-${offset}.bin.gz`;
    await fs.writeFile(`dist/${path}`,gzipSync(shuffleOwnershipBytes(words),{level:9}));pixelMap.parts.push({kind,offset,words:words.length,path,encoding:'byte-shuffle'});
  }
  const catalog=gridIndex.map(({feature,index,bounds})=>({...feature,geometry:null,pixelIndex:index,gridBounds:bounds}));
  const catalogParts=[];
  for(let i=0;i<catalog.length;i+=1500){const path=`geography/catalog-${i/1500}.json.gz`;catalogParts.push(path);await fs.writeFile(`dist/${path}`,gzipSync(JSON.stringify(catalog.slice(i,i+1500)),{level:9}));}
  const entityParts=[];
  for(let i=0;i<reference.temporal.entities.length;i+=5000){const path=`geography/entities-${i/5000}.json.gz`;entityParts.push(path);await fs.writeFile(`dist/${path}`,gzipSync(JSON.stringify(reference.temporal.entities.slice(i,i+5000)),{level:9}));}
  const temporalHistoryParts=[];
  for(let i=0;i<reference.temporal.history.length;i+=5000){const path=`geography/history-${i/5000}.json.gz`;temporalHistoryParts.push(path);await fs.writeFile(`dist/${path}`,gzipSync(JSON.stringify(reference.temporal.history.slice(i,i+5000))));}
  const geographicRelease=JSON.parse(await fs.readFile('data/geographic-releases/index.json','utf8')).releases.at(-1);
  if(geographicRelease.hierarchy_sha256!==createHash('sha256').update(await fs.readFile('data/hierarchy.json')).digest('hex')||geographicRelease.footprints_sha256!==checkPrepared(reference.features))throw Error('Reference release does not match prepared map assets');
  await fs.writeFile('dist/atlas-geography.json', JSON.stringify({contentCapabilities:{mapSnapshots:1},type:reference.type,sourceQualityReviews:reference.sourceQualityReviews,reference_release:geographicRelease,preparedEvidence:{footprints_sha256:preparedEvidence.footprints_sha256,hierarchy_sha256:preparedEvidence.hierarchy_sha256,index_sha256:createHash('sha256').update(await fs.readFile('data/prepared-evidence/index.json')).digest('hex')},pixelMissing:reference.pixelMissing,units:reference.units,temporal:{history:[],links:reference.temporal.links},entityParts,temporalHistoryParts,parts:catalogParts,geometryParts:parts,pixelMap}));
  await fs.writeFile('dist/atlas-history.json.gz',gzipSync(JSON.stringify(history)));
  await fs.writeFile('dist/environment-classifications.json',JSON.stringify({version:1,unknown:null,attributes:environmentClassifications}));
  await fs.cp('data/ownership-history','dist/ownership-history',{recursive:true});
  await fs.cp('data/ownership-runtime','dist/ownership-runtime',{recursive:true});
  await fs.cp('data/reference-attributes','dist/reference-attributes',{recursive:true});
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
  for(const file of ['world-review.json','global-refinement-report.json','source-inventory.json','pixel-audit.json','regional-membership-report.json','border-parent-review.json','attribute-sources.json','reference-polity-report.json','settlement-source-report.json'])await fs.copyFile(`data/${file}`,`dist/${file}`);
  for(const file of ['administrative-sources.json','granularity-report.json','hierarchy-report.json','semantic-report.json','granularity-audit.json','location-policy.json','coverage-report.json'])await fs.copyFile(`data/${file}`,`dist/${file}`);
  await fs.mkdir('dist/source-policy-corrections',{recursive:true});
  await fs.copyFile('data/source-policy-corrections/summary.json','dist/source-policy-corrections/summary.json');
  const frameworkReport=JSON.parse(await fs.readFile('data/hierarchy-report.json','utf8'));
  const worldReview=JSON.parse(await fs.readFile('data/world-review.json','utf8'));
  for(const file of worldReview.location_parts||[])await fs.copyFile(`data/${file}`,`dist/${file}`);
  for(const file of frameworkReport.change_parts||[])await fs.copyFile(`data/${file}`,`dist/${file}`);
  await fs.copyFile('data/framework-sources/manifest.json','dist/framework-sources.json');
  for(const file of await fs.readdir('dist',{recursive:true})){const stat=await fs.stat(`dist/${file}`);if(stat.isFile()&&stat.size>25*1024*1024)throw new Error(`Static asset exceeds 25 MiB: ${file}`);}
  console.log(`Static atlas ready: ${reference.features.length} polygons and ${history.states.length} dated records.`);
} finally { db.close(); }
