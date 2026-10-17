import fs from 'node:fs';import path from 'node:path';import {execFileSync} from 'node:child_process';import {gunzipSync} from 'node:zlib';import {createHash} from 'node:crypto';
import {polygonParts} from '../src/native-grid.js';
import {coordinateBounds,valueSha} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const W=process.cwd(),H=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),A=process.argv[2],sha=b=>createHash('sha256').update(b).digest('hex');
const raw=(p,h=H)=>execFileSync('git',['-c','protocol.allow=never','show',h+':'+p],{maxBuffer:100*1024*1024}),js=(p,h)=>JSON.parse(raw(p,h));
const codePath='coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs',code=raw(codePath).toString();
const begin=code.indexOf('const reconcile=(id,originals)=>{'),finish=code.indexOf('\n\n // Adoption belongs',begin);if(begin<0||finish<begin)throw Error('Functions not found');
const sel=js('data/ownership-selection.json'),rel=js(sel.additive_release.path),rp=rel.logical_asset_map.owner_roster,rb=raw(rp.path,rp.commit);if(sha(rb)!==rp.sha256)throw Error('Roster mismatch');const roster=JSON.parse(gunzipSync(rb)),owners=new Map(roster.map((o,i)=>[o.id,i+1]));
const memberOwners=new Map(),canonicalOwners=new Map(),semanticOwners=new Map(),lineage=js('data/semantic-report.json');
for(const change of lineage.changes){const s=semanticOwners.get(change.id)??[];s.push(change);semanticOwners.set(change.id,s);for(const m of change.replaces??[]){const r=memberOwners.get(m)??[];r.push(change);memberOwners.set(m,r);}}
for(const p of ['data/geography/part-2.json','data/geography/part-29.json'])for(const f of js(p).features)canonicalOwners.set(f.id,f);
const cat=js('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json'),product=cat.products.find(p=>p.key==='gb:CAN:ADM3'),chunks=[];
for(const p of product.parts){const b=raw(p.path),d=gunzipSync(b);if(sha(b)!==p.sha256||b.length!==p.bytes||sha(d)!==p.uncompressed_sha256||d.length!==p.uncompressed_bytes)throw Error('Original part differs');chunks.push(d);}
const source=Buffer.concat(chunks);if(sha(source)!==product.original_sha256||source.length!==product.original_bytes)throw Error('Original source differs');
const originals=new Map(JSON.parse(source).features.map(f=>['gb:CAN:ADM3:'+f.properties.shapeID,f]));
const local=(p)=>{const b=fs.readFileSync(path.join(A,p));return {value:JSON.parse(b),pin:{path:p,sha256:sha(b),bytes:b.length}};};
const mapping=local('source-review/admin-source-target-membership.json'),physical=local('admin-physical-001/whole-target-support.json'),evidence={targets:mapping.value.map(m=>({id:m.source_id,pixelIndex:m.pixelIndex,target_id:m.target_id}))};
const demand=(x,m)=>{if(!x)throw Error(m)},same=(a,b)=>valueSha(a)===valueSha(b);
const fns=eval('(()=>{'+code.slice(begin,finish)+';return {reconcile,splitCompetitor};})()');
const kinds=['mapped_land_support','mapped_inland_water_support'];let coverage=[];
for(const t of evidence.targets){const results=physical.value.results.filter(r=>r.target===t.id);demand(results.length===1,'Physical member missing');for(const k of kinds){const g=results[0].support[k];if(g.type==='GeometryCollection'&&g.geometries.length===0)continue;const polys=polygonParts(g);if(polys.length)coverage.push(...coordinateBounds({type:'MultiPolygon',coordinates:polys}).map(b=>({source:t.id,owner:t.pixelIndex,bounds:b})));}}
const intersects=(a,b)=>a[0]<=b[2]&&b[0]<=a[2]&&a[1]<=b[3]&&b[1]<=a[3];let counts={},failures=[],accepted=0;
for(const [id,feature]of originals){let boxes=coordinateBounds(feature.geometry),contact=coverage.find(c=>boxes.some(b=>intersects(b,c.bounds)));if(!contact)continue;accepted++;
 try{const split=fns.splitCompetitor(id,originals);if(split)counts.split=(counts.split??0)+1;else{fns.reconcile(id,originals);counts.resolved=(counts.resolved??0)+1;}}
 catch(error){counts[error.message]=(counts[error.message]??0)+1;failures.push({source_id:id,source_name:feature.properties.shapeName,error:error.message,bound_contact:contact,changes:(memberOwners.get(id)??[]).map(c=>({id:c.id,member_count:c.replaces?.length,selected_owner:owners.get(c.id)??null})),canonical: [...canonicalOwners.values()].filter(f=>f.properties?.metadata?.source_member_ids?.includes(id)).map(f=>({id:f.id,members:f.properties.metadata.source_member_ids.length}))});}}
const out={kind:'independent-complete-original-stock-prefilter-membership-probe',baseline:H,method:{path:codePath,sha256:sha(Buffer.from(code)),start:begin,end:finish},inputs:[mapping.pin,physical.pin],originals:originals.size,positive_sources:evidence.targets.length,coverage_part_bounds:coverage.length,retained_after_stock_spatial_prefilter:accepted,counts,failures,limits:['Runs exact stock reconcile/splitCompetitor bodies and production coordinateBounds with complete source and accepted ancestry, using both admitted physical classes. Not the whole authority constructor.','Bounding-box contact is the actual constructor admission, not geometric contact or exact native conflict. Failures cannot be translated into held-cell counts.']};
fs.writeFileSync('.scratch/prefilter-membership-result.json',JSON.stringify(out,null,2)+'\n');console.log(JSON.stringify({...out,failures:failures.slice(0,2)}));
