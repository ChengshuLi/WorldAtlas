// The existing SOURCE stage's complete administrative product hash join.
// This does no polygon operation and grants no source or operator approval.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {canonicalValue} from '../../../../src/effective-footprint.js';
const here=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(here,'../../../..'),own=path.relative(root,path.dirname(here));
const [head,vintage]=process.argv.slice(2),git=(...args)=>execFileSync('git',['-C',root,...args],{maxBuffer:32*1024**2}),sha=b=>createHash('sha256').update(b).digest('hex'),digest=x=>sha(Buffer.from(JSON.stringify(canonicalValue(x))+'\n')),need=(v,m)=>{if(!v)throw Error(m);};
need(git('rev-parse','HEAD').toString().trim()===head&&/^[a-z0-9-]+$/.test(vintage),'Exact head and fresh vintage required');
const dest=path.join(root,own,'vintages',vintage);for(let p=dest;p!==path.dirname(root);p=path.dirname(p)){const s=fs.lstatSync(p,{throwIfNoEntry:false});need(!s?.isSymbolicLink()&&(p!==dest||!s),'Occupied/symlink destination');}
const names=[path.relative(root,fileURLToPath(import.meta.url)),'src/effective-footprint.js','scripts/additive-gap-repair.mjs',own+'/vintages/administrative-custody-002/comparison-rows.json',own+'/vintages/administrative-custody-002/consumed-source.geojson'];
const inputs=names.map(p=>{const b=fs.readFileSync(path.join(root,p));need(b.equals(git('show',head+':'+p)),'Unfrozen input');return {commit:head,path:p,bytes:b.length,sha256:sha(b)};});
const raw=fs.readFileSync(path.join(root,names[4]));need(sha(raw)==='69115100f6d6fa953651988ecb091b1c3a687a4a8a95782bfafaa950af66b3e4','Wrong whole source');const collection=JSON.parse(raw);need(collection.type==='FeatureCollection'&&collection.features.length===547,'Incomplete original product');
const features=collection.features.map(f=>({feature_sha256:digest(f),geometry_sha256:digest(f.geometry)}));
const original=JSON.parse(fs.readFileSync(path.join(root,names[3])));need(original.length===19&&new Set(original.map(x=>x.component)).size===19,'Wrong original scope');
const rows=original.map(c=>{const hits=c.feature_intersections.filter(x=>x.intersection.planar_area_coordinate_units_squared>0).map(x=>x.binding);return {component_id:c.component,source_product_compatible:hits.length===1&&hits.every(h=>{const m=features.filter(f=>f.feature_sha256===h.feature_sha256||f.feature_sha256===h.source_feature_sha256);return m.length===1&&m[0].geometry_sha256===(h.geometry_sha256??h.source_geometry_sha256);}),bindings:hits.map(h=>({original:h,actual_indexed_hashes:features[h.feature_index]}))};});
const result={execution_commit:head,inputs,rows,compatible_count:rows.filter(r=>r.source_product_compatible).length,limits:['Original whole-source product join only; no geometry operation or full SOURCE qualification.','Original Python hashes remain unchanged; incompatible JavaScript serialization is an explicit hold.']};
need(process.resourceUsage().maxRSS*1024<256*1024**2,'RSS exceeded');const body=Buffer.from(JSON.stringify(result,null,2)+'\n');fs.mkdirSync(dest,{recursive:false});fs.writeFileSync(path.join(dest,'result.json'),body,{flag:'wx'});fs.writeFileSync(path.join(dest,'publication.json'),JSON.stringify({version:1,status:'complete',outputs:[{path:path.relative(root,path.join(dest,'result.json')),bytes:body.length,sha256:sha(body),hash_kind:'file-bytes'}]})+'\n',{flag:'wx'});console.log(JSON.stringify({compatible_count:result.compatible_count,held:rows.filter(r=>!r.source_product_compatible).map(r=>r.component_id),peak_rss_bytes:process.resourceUsage().maxRSS*1024}));
