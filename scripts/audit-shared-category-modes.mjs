import fs from 'node:fs';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {resolveAttributes} from '../src/attributes.js';
import {presentedAttribute} from '../src/reference-context.js';
import {decodeReferences,decodeReferenceContext} from '../src/reference-records.js';
import {selectPreparedEvidence} from '../src/prepared-evidence.js';
import {categoryPresentationKey} from '../src/category-presentation.js';
import {categoryColor,levels} from '../src/model.js';
import {auditCategoryColors} from './build-category-palette.mjs';

const directory=process.argv[2];
if(!directory||!/^data\/engineering\/[a-z0-9][a-z0-9-]{0,63}$/.test(directory))throw Error('Owned evidence directory required');
const pins={},hash=b=>createHash('sha256').update(b).digest('hex');
const read=(file,expected)=>{const b=fs.readFileSync(file);pins[file]=hash(b);if(expected&&pins[file]!==expected)throw Error('Input hash mismatch: '+file);return JSON.parse(b[0]===31&&b[1]===139?gunzipSync(b):b);};
const catalog=read('dist/atlas-geography.json'),features=catalog.parts.flatMap(part=>read(path.join('dist',part)));
const grid=read('data/canonical-grid/manifest.json'),bounds=read(path.join('data/canonical-grid',grid.bounds.path),grid.bounds.sha256);
const raster=read(path.join(directory,'raster-neighbors.json.gz'));
if(raster.manifest_sha256!==pins['data/canonical-grid/manifest.json'])throw Error('Raster pins changed');
const ref=read('data/reference-attributes/index.json'),parts=ref.parts.map(p=>read(path.join('data/reference-attributes',p),ref.parts_sha256[p]));
const prepared=read('data/prepared-evidence/index.json'),preparedParts=prepared.parts.map(p=>({path:p.path,rows:read(path.join('data/prepared-evidence',p.path),p.sha256)}));
const featureByID=new Map(features.map(f=>[f.id,f])),units=new Map(catalog.units.map(u=>[u.id,u]));
const pairs=[...raster.adjacent,...raster.nearby],samples=[];
for(const year of [1950,2020,2026]){
  const evidence=selectPreparedEvidence(prepared,preparedParts,year),states=resolveAttributes(features,year,{records:[...decodeReferences(parts,ref,year),...evidence.records],referenceBaselines:decodeReferenceContext(parts,ref)});
  for(const mode of ['culture','religion','rank','topography','vegetation','climate',...levels]){
    const keys=[null],colors={},counts=new Map();
    for(const row of bounds){
      const feature=featureByID.get(row.id);if(!feature)throw Error('Missing fixed grid subject');
      let value,shown;
      if(levels.includes(mode)){
        let unit={...feature.properties,id:feature.id,level:'location'};
        while(unit&&unit.level!==mode)unit=units.get(unit.parent_id);
        value=unit?.id??null;shown={};
      }else{shown=presentedAttribute(states.get(row.id),mode);value=shown.value;}
      const key=categoryPresentationKey(mode,shown,value);keys.push(key);
      if(key){colors[key]=categoryColor(key);counts.set(key,(counts.get(key)??0)+1);}
    }
    const edges=[...new Set(pairs.flatMap(([a,b])=>keys[a]&&keys[b]&&keys[a]!==keys[b]?[JSON.stringify([keys[a],keys[b]].sort())]:[]))].sort().map(JSON.parse);
    const audit=auditCategoryColors(colors,edges);
    samples.push({year,mode,known_categories:counts.size,known_locations:[...counts.values()].reduce((a,b)=>a+b,0),unknown_locations:bounds.length-[...counts.values()].reduce((a,b)=>a+b,0),edges:audit.edges,models:audit.models,failure_examples:audit.failures.slice(0,25),total_failed_pairs:audit.failures.length,failure_examples_limit:25});
  }
}
const result={version:1,input_sha256:pins,samples,notes:['Assessment only; no classification or hierarchy identity is rewritten.','Reference environmental context is labeled by the same resolver as the browser.','Other categorical graphs have no global contrast guarantee; retained aggregate counts cover all tested edges and only the first 25 failing examples are shown.','Sparse culture/religion evidence is not completed historical coverage. Population remains numeric, not a categorical audit.']};
fs.writeFileSync(path.join(directory,'shared-mode-assessment.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(samples.map(({year,mode,known_categories,total_failed_pairs})=>({year,mode,known_categories,total_failed_pairs}))));
