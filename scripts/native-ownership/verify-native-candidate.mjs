// Exhaustive transport-to-native-rule comparison, separate from preparation.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {loadNativeSourceInputs} from './native-only-inputs.mjs';
import {committedPreparationFiles,requirePlainExecution} from './native-preparation-guards.mjs';
import {nativeCandidateManifest,NATIVE_CANONICAL_LATITUDE_SHA256} from './native-candidate-manifest.mjs';
import {nativePolygonIntervals,NATIVE_GRID_METHOD} from '../../src/native-grid.js';
import {coverageRow} from '../audit-grid-intervals.mjs';
import {loadOwnershipAssets} from '../../src/ownership-assets.js';
import {ownershipRun} from '../../src/pixel-ownership.js';

const digest = bytes => createHash('sha256').update(bytes).digest('hex');
requirePlainExecution();
const options = {};
for (let n=2;n<process.argv.length;n+=2) {
  const key=process.argv[n];
  if (!['--repo','--one','--two'].includes(key) || !process.argv[n+1] || options[key])
    throw Error('Require repository and two complete fresh candidate vintages');
  options[key]=process.argv[n+1];
}
const repo=fs.realpathSync(options['--repo']);
const head=execFileSync('git',['-C',repo,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
const code=['package.json', ...[import.meta.url,...[
  'native-only-inputs.mjs','native-preparation-guards.mjs','native-candidate-manifest.mjs'
].map(name=>new URL(name,import.meta.url)), ...[
  'src/native-grid.js','scripts/audit-grid-intervals.mjs','src/ownership-assets.js',
  'src/ownership-codec.js','src/pixel-ownership.js','src/pixel-grid.js'
].map(name=>new URL('../../'+name,import.meta.url))].map(url=>path.relative(repo,fileURLToPath(url)))];
const executed=committedPreparationFiles(repo,head,code);
const directory = vintage => {
  if (!/^[a-zA-Z0-9_-]+$/.test(vintage??'')) throw Error('Unsafe candidate vintage');
  const dir=path.join(repo,'.cache/native-grid-candidates',vintage);
  if (fs.realpathSync(dir)!==dir) throw Error('Candidate directory must be ordinary');
  return dir;
};
const one=directory(options['--one']),two=directory(options['--two']);
if(one===two)throw Error('Two distinct complete runs required');
const products = dir => fs.readdirSync(dir,{withFileTypes:true}).flatMap(item=>{
  const file=path.join(dir,item.name);
  if(item.isDirectory())return products(file).map(row=>({...row,path:item.name+'/'+row.path}));
  if(!item.isFile())throw Error('Candidate product must be ordinary');
  if(item.name==='progress.json')return [];
  const bytes=fs.readFileSync(file);
  return [{path:item.name,bytes:bytes.length,sha256:digest(bytes)}];
}).sort((a,b)=>a.path.localeCompare(b.path));
const inventory=products(one),second=products(two);
if(JSON.stringify(inventory)!==JSON.stringify(second))throw Error('Two-run complete product bytes differ');
for(const dir of [one,two]) {
  if(JSON.parse(fs.readFileSync(path.join(dir,'progress.json'))).phase!=='complete')
    throw Error('Both candidate runs must be complete');
}
const manifest=JSON.parse(fs.readFileSync(path.join(one,'manifest.json')));
if(manifest.method!==NATIVE_GRID_METHOD || manifest.size!==262166 || manifest.version!==2)
  throw Error('Unknown candidate convention');
const inputs=await loadNativeSourceInputs(repo,manifest.provenance.baseline_commit);
const report=JSON.parse(gunzipSync(fs.readFileSync(path.join(one,'report.json.gz'))));
const expected=nativeCandidateManifest({original:inputs.manifest,originalSha256:digest(inputs.manifestRaw),
  baselineCommit:inputs.baselineCommit,evaluationCommit:manifest.provenance.evaluation_commit,
  releaseId:inputs.release.id,rosterSha256:digest(Buffer.from(JSON.stringify(inputs.roster)+'\n')),
  ownerCount:inputs.roster.length,latitude:manifest.native_latitudes,compiled:report});
if(JSON.stringify(expected)!==JSON.stringify(manifest))throw Error('Candidate release/identity/method contract differs');
if(digest(inputs.manifestRaw)!==manifest.provenance.original_canonical_sha256 ||
   digest(Buffer.from(JSON.stringify(inputs.roster)+'\n'))!==manifest.provenance.owner_roster_sha256)
  throw Error('Original manifest/complete stable roster differs');
const reference=manifest.native_latitudes;
if(reference.root!=='repository' || reference.role!=='immutable-normative-rule-input' ||
   reference.path!=='coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz' ||
   reference.commit!==manifest.provenance.evaluation_commit)
  throw Error('Unknown normative table reference');
const encoded=execFileSync('git',['-C',repo,'show',reference.commit+':'+reference.path],{maxBuffer:32*1024*1024});
const raw=gunzipSync(encoded,{maxOutputLength:inputs.manifest.size*8});
if(encoded.length!==reference.bytes || digest(encoded)!==reference.sha256 ||
   raw.length!==inputs.manifest.size*8 || digest(raw)!==NATIVE_CANONICAL_LATITUDE_SHA256)
  throw Error('Normative latitude bytes differ');
const latitudes=Float64Array.from({length:manifest.size},(_,y)=>raw.readDoubleLE(y*8));
const grid=await loadOwnershipAssets(manifest,async url=>{
  if(!/^\.\/native-v1\/ownership\/(rows|runs)-[0-9]+\.bin\.gz$/.test(url))throw Error('Unexpected candidate asset');
  const file=path.join(one,url.slice(2));
  if(fs.realpathSync(file)!==file)throw Error('Candidate asset must be ordinary');
  return new Response(fs.readFileSync(file));
});
let checkedRows=0,checkedRuns=0,ownedCells=0;
const counts=new Map(inputs.roster.map(owner=>[owner.index,0])),started=performance.now();
for(let first=0;first<grid.size;first+=4096) {
  const end=Math.min(grid.size,first+4096);
  const native=nativePolygonIntervals(inputs.index.filter(item=>
    item.minLat<=latitudes[first]&&item.maxLat>=latitudes[end-1]),
    {size:grid.size,rowStart:first,rowEnd:end,latitudes});
  for(let y=first;y<end;y++) {
    let actual=grid.rows[y*2],stop=actual+grid.rows[y*2+1],pending=null;
    const compare = segment => {
      if(actual>=stop)throw Error('Missing decoded native run at row '+y);
      const found=ownershipRun(grid,actual++);
      if(found.start!==segment.start || found.end!==segment.end || found.id!==segment.id)
        throw Error('Decoded ownership differs from native source rule at row '+y);
      const cells=segment.end-segment.start;
      ownedCells+=cells;counts.set(segment.id,counts.get(segment.id)+cells);checkedRuns++;
    };
    for(const segment of coverageRow(native.rows.get(y)??[],grid.size)) {
      const id=segment.owners[0]??0;
      if(pending && id===pending.id && pending.end===segment.start)pending.end=segment.end;
      else {if(pending)compare(pending);pending=id?{start:segment.start,end:segment.end,id}:null;}
    }
    if(pending)compare(pending);
    if(actual!==stop)throw Error('Extra decoded run at row '+y);
    checkedRows++;
  }
  console.error(JSON.stringify({completed_rows:checkedRows,checked_runs:checkedRuns}));
}
if(checkedRows!==grid.size || checkedRuns*2!==grid.runs.length || ownedCells!==report.owned_cells ||
   JSON.stringify([...counts])!==JSON.stringify(report.per_owner_cells))
  throw Error('Complete domain/per-owner accounting differs');
console.log(JSON.stringify({version:1,baseline_commit:manifest.provenance.baseline_commit,
  preparation_commit:manifest.provenance.evaluation_commit,verification_commit:head,executed_sources:executed,
  method:NATIVE_GRID_METHOD,checked_rows:checkedRows,checked_cells:grid.size**2,unchecked_cells:0,
  checked_runs:checkedRuns,owned_cells:ownedCells,owners:counts.size,two_run_products:inventory.length,
  products:inventory,run_one_sha256:digest(Buffer.from(JSON.stringify(inventory))),
  run_two_sha256:digest(Buffer.from(JSON.stringify(second))),elapsed_ms:performance.now()-started,
  maxRSS_raw:process.resourceUsage().maxRSS,installation_ready:false,
  limits:['Full-domain equality to the declared native numerical rule through actual asset decoding.',
    'Native interval mathematics is shared with preparation; independent integer oracles are separate controls.',
    'Does not establish factual source completeness, water class, political affiliation or production delivery.']}));
