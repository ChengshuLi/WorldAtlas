import {execFileSync} from 'node:child_process';
import {readFileSync, writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const root='data/regional-review/regional-review-626fdf640aab94e2';
const base='8e1162e3e364cebdec700ec796e2730379494922';
if(execFileSync('git',['rev-parse','--verify',`${base}^{commit}`],{encoding:'utf8'}).trim()!==base)throw new Error(`Pinned baseline commit is unavailable: ${base}`);
const scope=JSON.parse(readFileSync(`${root}/baseline/issue-scope.json`,'utf8'));
const wanted=new Set(scope.member_location_ids);
const found=new Map(), inputs=[], currentFeatures=[];
let sourceIds=new Set();
const summary=g=>{
 if(!g)return {geometry_type:null,component_count:0,ring_count:0,vertex_count:0,bbox:null};
 const coords=[]; let rings=0;
 const walk=(v,depth=0)=>{if(!Array.isArray(v))return;if(typeof v[0]==='number'&&typeof v[1]==='number'){coords.push(v);return;}if(depth===2)rings++;for(const x of v)walk(x,depth+1);};
 walk(g.coordinates);
 const xs=coords.map(p=>p[0]),ys=coords.map(p=>p[1]);
 return {geometry_type:g.type,component_count:g.type==='MultiPolygon'?g.coordinates.length:1,ring_count:rings,vertex_count:coords.length,bbox:coords.length?[Math.min(...xs),Math.min(...ys),Math.max(...xs),Math.max(...ys)]:null};
};
for(let i=0;i<=33;i++){
 const path=`data/geography/part-${i}.json`;
 const bytes=execFileSync('git',['show',`${base}:${path}`],{maxBuffer:64*1024*1024});
 const text=bytes.toString('utf8'), data=JSON.parse(text);
 inputs.push({path,git_blob:execFileSync('git',['rev-parse',`${base}:${path}`],{encoding:'utf8'}).trim(),sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,scoped_matches:0});
 for(const f of data.features){const id=f.properties?.id;if(wanted.has(id)){found.set(id,{part:path,properties:f.properties,geometry:summary(f.geometry)});currentFeatures.push(f);inputs.at(-1).scoped_matches++;}}
}
const rows=scope.member_location_ids.map(id=>({id,...(found.get(id)||{missing:true})}));
sourceIds=new Set(rows.filter(x=>x.properties?.metadata?.source_id?.startsWith('resolve:')).map(x=>x.properties.metadata.original_id));
const duplicatedOriginals=[];
for(let i=0;i<=33;i++){
 const data=JSON.parse(execFileSync('git',['show',`${base}:data/geography/part-${i}.json`],{maxBuffer:64*1024*1024}).toString('utf8'));
 for(const f of data.features){const id=f.properties?.id||'', originalId=f.properties?.metadata?.original_id;if(sourceIds.has(id.replace(/^gb:RUS:ADM2:/,''))||sourceIds.has(originalId))duplicatedOriginals.push({id,part:`data/geography/part-${i}.json`,name:f.properties?.name,source_id:f.properties?.metadata?.source_id,original_id:originalId,geometry:summary(f.geometry)});}
}
const out={version:1,base_commit:base,issue:395,scope_count:scope.location_count,scope_ids_sha256:scope.member_location_ids_sha256,matched:found.size,missing:rows.filter(x=>x.missing).map(x=>x.id),inputs,rows,source_unit_lineage:{underlying_original_ids:[...sourceIds].sort(),current_main_matches:duplicatedOriginals}};
writeFileSync(`${root}/findings/current-lineage.json`,JSON.stringify(out,null,2)+'\n');
writeFileSync(`${root}/sources/current-scoped-features.geojson`,JSON.stringify({type:'FeatureCollection',features:currentFeatures})+'\n');
console.log(JSON.stringify({matched:found.size,missing:out.missing.length,parts:inputs.filter(x=>x.scoped_matches).map(x=>({path:x.path,matches:x.scoped_matches,sha256:x.sha256})),source_ids:[...new Set(rows.map(x=>x.properties?.metadata?.source_id))]},null,2));
