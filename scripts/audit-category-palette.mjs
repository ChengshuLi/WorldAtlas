import fs from 'node:fs';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {legacyCategoryColor} from '../src/model.js';
import {displayCategoryKey} from '../src/color-perception.js';
import {resolveAttributes} from '../src/attributes.js';
import {assignCategoryColors,auditCategoryColors,contrastBudget} from './build-category-palette.mjs';

const directory=process.argv[2], tag=process.argv[3]??'sample';
if(!['sample','all-times','all-times-modern'].includes(tag))throw Error('Use sample, all-times or all-times-modern audit');
if(!directory || !/^data\/engineering\/[a-z0-9][a-z0-9-]{0,63}$/.test(directory)) throw Error('Supply an owned engineering evidence directory');
const read=name=>{const bytes=fs.readFileSync(path.join(directory,name));return {bytes,data:JSON.parse(gunzipSync(bytes))};};
const source=read('source-owner-dated-display.json.gz'),raster=read('raster-neighbors.json.gz');
if(source.data.grid_manifest_sha256!==raster.data.manifest_sha256)throw Error('Dated display and neighbor graph pins disagree');
const keys=[...source.data.keys],all=new Set(),byDate=[];
const ordered=(a,b)=>a<b?JSON.stringify([a,b]):JSON.stringify([b,a]);
for(const date of source.data.dates){
  const adjacent=new Set(),nearby=new Set(),aliases=new Set(),namesByID=new Map();
  for(const n of new Set(date.owners.filter(Boolean))){
    const k=keys[n-1],[id]=JSON.parse(k);if(!namesByID.has(id))namesByID.set(id,new Set());namesByID.get(id).add(k);
  }
  const pairs=(locationPairs,out)=>{for(const [a,b] of locationPairs){const x=date.owners[a],y=date.owners[b];if(x&&y&&x!==y)out.add(ordered(keys[x-1],keys[y-1]));}};
  pairs(raster.data.adjacent,adjacent);pairs(raster.data.nearby,nearby);
  for(const names of namesByID.values()){const list=[...names].sort();for(let i=0;i<list.length;i++)for(let j=i+1;j<list.length;j++)aliases.add(ordered(list[i],list[j]));}
  for(const edge of [...adjacent,...nearby,...aliases])all.add(edge);
  byDate.push({year:date.year,adjacent:[...adjacent].sort().map(JSON.parse),nearby:[...nearby].sort().map(JSON.parse),concurrent_source_aliases:[...aliases].sort().map(JSON.parse)});
}
let complete=null;
if(tag.startsWith('all-times')){
  complete=read('all-time-contrast-constraints.json.gz');
  if(complete.data.source_index_sha256!==source.data.source_index_sha256 || complete.data.grid_manifest_sha256!==raster.data.manifest_sha256 || JSON.stringify(complete.data.keys)!==JSON.stringify(source.data.keys))throw Error('All-time contrast pins disagree');
  for(const pair of [...complete.data.adjacent,...complete.data.nearby,...complete.data.concurrent_source_aliases])all.add(ordered(...pair));
}
// The modern reference is resolved by the application's actual policy, including
// explicit unresolved polities. Original feature records are read, never changed.
const world=JSON.parse(fs.readFileSync('data/world-index.json'));
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const modernInputs=Object.fromEntries(['data/world-index.json',...world.parts.map(part=>path.join('data',part))].map(file=>[file,hash(fs.readFileSync(file))]));
const features=world.parts.flatMap(part=>JSON.parse(fs.readFileSync(path.join('data',part))).features);
const modern=resolveAttributes(features,2026),grid=JSON.parse(fs.readFileSync('data/canonical-grid/manifest.json'));
const boundsBytes=fs.readFileSync(path.join('data/canonical-grid',grid.bounds.path));
if(hash(boundsBytes)!==grid.bounds.sha256)throw Error('Modern raster identity bounds hash mismatch');
const bounds=JSON.parse(gunzipSync(boundsBytes));
const modernKeys=bounds.map(row=>{const state=modern.get(row.id);if(!state)throw Error('Missing modern reference subject');return state.owner==null?null:displayCategoryKey(state.category_ids.owner,state.owner);});
modernKeys.unshift(null);
for(const k of modernKeys)if(k&&!keys.includes(k))keys.push(k);
const modernPairs=pairs=>[...new Set(pairs.flatMap(([a,b])=>modernKeys[a]&&modernKeys[b]&&modernKeys[a]!==modernKeys[b]?[ordered(modernKeys[a],modernKeys[b])]:[]))].sort().map(JSON.parse);
const modernAdjacent=modernPairs(raster.data.adjacent),modernNearby=modernPairs(raster.data.nearby);
for(const pair of [...modernAdjacent,...modernNearby])all.add(ordered(...pair));
const edges=[...all].sort().map(JSON.parse),colors=assignCategoryColors(keys,edges);
const candidateColorsSHA=hash(JSON.stringify(colors));
const original=Object.fromEntries(keys.map(key=>[key,legacyCategoryColor(JSON.parse(key)[0])]));
const dates=byDate.map(d=>({year:d.year,adjacent_before:auditCategoryColors(original,d.adjacent),adjacent_after:auditCategoryColors(colors,d.adjacent),nearby_after:auditCategoryColors(colors,d.nearby),concurrent_aliases_after:auditCategoryColors(colors,d.concurrent_source_aliases)}));
const result={version:1,baseline_commit:raster.data.baseline_commit,source_index_sha256:source.data.source_index_sha256,grid_manifest_sha256:raster.data.manifest_sha256,
  inputs_sha256:{'source-owner-dated-display.json.gz':createHash('sha256').update(source.bytes).digest('hex'),'raster-neighbors.json.gz':createHash('sha256').update(raster.bytes).digest('hex')},
  criterion:{unit:'100 times Euclidean OKLab distance',budgets:contrastBudget,color_vision:'Modeled full-severity Machado2009 linear-sRGB transforms; not a physical certificate'},
  all_source_intervals_constrained:Boolean(complete),
  limits:[complete?'All exact prepared source intervals constrained; hosted-only overlays and future facts remain outside these pins':'Representative dates, not all historical instants','Nearby screen gaps are horizontal only, not geographic-distance claims','Sparse future or hosted-only categories absent from these pinned inputs require an updated audit','Original source owner IDs and names remain facts; composite keys are presentation only'],
  display_keys:keys.length,unique_constraint_edges:edges.length,before:auditCategoryColors(original,edges),after:auditCategoryColors(colors,edges),dates,
  candidate_colors_sha256:candidateColorsSHA,
  modern_input_sha256:modernInputs,
  modern_reference:{year:2026,adjacent:auditCategoryColors(colors,modernAdjacent),nearby:auditCategoryColors(colors,modernNearby)},
  reported_case:{prc:{source_id:'owner:Q148',name:"People's Republic of China",key:displayCategoryKey('owner:Q148',"People's Republic of China")},roc:{source_id:'owner:Q148',name:'Republic of China',key:displayCategoryKey('owner:Q148','Republic of China')}}};
const candidate={version:1,source_index_sha256:result.source_index_sha256,grid_manifest_sha256:result.grid_manifest_sha256,candidate_colors_sha256:candidateColorsSHA,colors};
fs.writeFileSync(path.join(directory,'palette-'+tag+'-candidate.json'),JSON.stringify(candidate)+'\n',{flag:'wx'});
fs.writeFileSync(path.join(directory,'contrast-'+tag+'-audit.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({display_keys:keys.length,edges:edges.length,before:result.before.models,after:result.after.models,prc:colors[result.reported_case.prc.key],roc:colors[result.reported_case.roc.key]}));
