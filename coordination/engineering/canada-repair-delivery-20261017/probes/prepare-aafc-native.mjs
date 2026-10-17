// Prepare bounded existing adopted-provider operands. No native authority is asserted.
// Usage: node PATH/prepare-aafc-native.mjs REPOSITORY NEW_OUTPUT_DIRECTORY
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {pathToFileURL} from 'node:url';
const [repo,output]=process.argv.slice(2);
if(!repo||!output)throw Error('Require repository and fresh output directory');
const W=path.resolve(repo), O=path.resolve(output);
const H='c4ffca9ba743f68c877fd8542698b28804cf07cf';
const C='e60d3b77e8d';
const P='coordination/engineering/canada-repair-delivery-20261017';
const F='aafc:ecoregions:baseline-layer0';
const raw=(p,c=H)=>execFileSync('git',['-c','protocol.allow=never','-C',W,'show',c+':'+p],{maxBuffer:180*1024*1024});
const sha=b=>createHash('sha256').update(b).digest('hex');
const json=(p,c=H)=>{const b=raw(p,c);return JSON.parse(p.endsWith('.gz')?gunzipSync(b):b);};
const check=(ok,message)=>{if(!ok)throw Error(message);};
const pin=(p,c=H)=>{
 const b=raw(p,c), full=execFileSync('git',['-C',W,'rev-parse',c],{encoding:'utf8'}).trim();
 const r={path:p,commit:full,mode:'100644',git_blob_oid:execFileSync('git',['-C',W,'rev-parse',c+':'+p],{encoding:'utf8'}).trim(),bytes:b.length,sha256:sha(b)};
 if(p.endsWith('.gz')){const d=gunzipSync(b);r.decoded_bytes=d.length;r.decoded_sha256=sha(d);}return r;
};
const helper='coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
check(raw(helper).equals(fs.readFileSync(path.join(W,helper))),'Executed canonical-value helper differs');
const {valueSha}=await import(pathToFileURL(path.join(W,helper)));
function boxes(g){
 if(!g||!['Polygon','MultiPolygon'].includes(g.type)||!g.coordinates.length)return [];
 const polygons=g.type==='Polygon'?[g.coordinates]:g.coordinates;
 return polygons.map(p=>{let a=Infinity,b=Infinity,c=-Infinity,d=-Infinity;for(const ring of p)for(const [x,y] of ring){check(Number.isFinite(x)&&Number.isFinite(y),'Nonfinite coordinate');a=Math.min(a,x);b=Math.min(b,y);c=Math.max(c,x);d=Math.max(d,y);}check(a<=c&&b<=d,'Empty polygon');return[a,b,c,d];});
}
const intersects=(a,b)=>a[0]<=b[2]&&b[0]<=a[2]&&a[1]<=b[3]&&b[1]<=a[3];
const cataloguePath='coordination/engineering/original-geography-source-corpus-20261006/catalogue.json';
const catalogue=json(cataloguePath), sources=[], negativeFamilies=[];
for(const family of ['gb:CAN:ADM3','gb:USA:ADM1']){
 const r=catalogue.products.find(p=>p.key===family);check(r,'Missing original family');
 const original=Buffer.concat(r.parts.map(p=>{const b=raw(p.path);check(b.length===p.bytes&&sha(b)===p.sha256,'Encoded original differs');const d=gunzipSync(b);check(d.length===p.uncompressed_bytes&&sha(d)===p.uncompressed_sha256,'Decoded original differs');return d;}));
 check(original.length===r.original_bytes&&sha(original)===r.original_sha256,'Complete original differs');const features=JSON.parse(original).features;check(features.length===r.feature_count,'Original inventory differs');
 const seen=new Set();for(const f of features){const id=family+':'+f.properties.shapeID;check(!seen.has(id),'Duplicate original');seen.add(id);sources.push({id,geometry:f.geometry,boxes:boxes(f.geometry),bytes:Buffer.byteLength(JSON.stringify(f.geometry))});}
 negativeFamilies.push({source_id:family,original_bytes:r.original_bytes,original_sha256:r.original_sha256,feature_count:r.feature_count,parts:r.parts.map(p=>pin(p.path))});
}
const semantic=json('data/semantic-report.json'), changes=new Map(semantic.changes.map(c=>[c.id,c])), areaOf=new Map();
check(changes.size===semantic.changes.length,'Duplicate semantic node');let physicalNodes=0;
for(const c of semantic.changes)if(c.id.startsWith('atlas:physical:CAN-')){physicalNodes++;const area=c.id.split(':').at(-1);for(const id of c.replaces){check(!areaOf.has(id)||areaOf.get(id)===area,'Conflicting complete remainder');areaOf.set(id,area);}}
check(physicalNodes===273&&areaOf.size===2794,'Incomplete remainder');
const screening=json(P+'/source-review/source-target-screening.json',C), ownerInfo=new Map(screening.owners.map(o=>[o.index,o]));
const originalPackage=json(P+'/frozen-original-001/package.json',C), originalRows=originalPackage.native_blocks.flatMap(b=>json(P+'/frozen-original-001/block-'+String(b).padStart(3,'0')+'.json.gz',C));
check(originalRows.length===139042&&originalRows.reduce((n,r)=>n+r[2]-r[1],0)===438062,'Original denominator differs');
const foreign=json(P+'/source-review/foreign-original-intervals.json.gz',C), aafc=json(P+'/source-review/native-aafc-screen.json',C), remainder=json(P+'/source-review/native-remainder-screen.json',C);
check(remainder.counts.all===144097&&remainder.counts.intended_remainder===144097&&remainder.counts.other_original_contact===0&&remainder.counts.requested_boundary_ties===0,'Incomplete native remainder proof');
const held=new Map();for(const [y,a,z,owners]of foreign)for(let x=a;x<z;x++)held.set(owners[0]+':'+y+':'+x,{y,x,owner:owners[0],reason:'foreign-USA-original-contact'});
check(held.size===55,'Foreign scope differs');for(const r of aafc.held){const k=r.owner+':'+r.y+':'+r.x;check(!held.has(k),'Source hold sets overlap');held.set(k,{y:r.y,x:r.x,owner:r.owner,reason:'outside-unique-intended-AAFC',matched_ecoregions:r.matched_ecoregions});}check(held.size===103,'Source hold denominator differs');
const byOwner=new Map();for(const [y,a,z,owners,sources,kind]of originalRows){const owner=ownerInfo.get(owners[0]);if(!owner.target_properties.metadata.source_id?.startsWith('aafc:'))continue;const list=byOwner.get(owner.index)??[];let start=null;for(let x=a;x<z;x++){if(!held.has(owner.index+':'+y+':'+x)){if(start===null)start=x;}else if(start!==null){list.push([y,start,x,kind]);start=null;}}if(start!==null)list.push([y,start,z,kind]);byOwner.set(owner.index,list);}
check([...byOwner.values()].flat().reduce((n,r)=>n+r[2]-r[1],0)===144047,'Physical source ceiling differs');
const sourcePath='data/regional-review/regional-review-a9f03b364bdefa4a/sources/aafc-baseline-arcgis-layer0.geojson', product=json(sourcePath), productPin=pin(sourcePath);check(product.features.length===218&&new Set(product.features.map(f=>f.properties.OBJECTID)).size===218,'Complete AAFC inventory differs');
const sourceById=new Map(product.features.map((f,i)=>[F+':'+f.properties.OBJECTID,{feature:f,ordinal:i}]));
const common={version:1,kind:'source-target-native-evidence-v1',catalogue:pin(cataloguePath),families:[{source_id:F,parts:[productPin]}],physical_reproduction:pin('scripts/qualify-source-cohort.py'),source_membership:{index:pin('data/world-index.json'),lineage:pin('data/semantic-report.json'),parts:['data/geography/part-2.json','data/geography/part-29.json'].map(p=>pin(p))}};
fs.mkdirSync(O,{recursive:false});
function write(dir,name,body){const b=Buffer.from(JSON.stringify(body)+'\n');fs.writeFileSync(path.join(dir,name),b,{flag:'wx'});return {path:path.relative(W,path.join(dir,name)),bytes:b.length,sha256:sha(b)};}
const batches=[];let number=0;
for(const phase of [1,2]){
 const phaseText=String(phase).padStart(3,'0'), stagesPath=P+'/aafc-stage-001/aafc-'+phaseText+'-original-stage-inputs.json', stage=json(stagesPath,C), physicalPath=P+'/aafc-'+phaseText+'-physical-001/whole-target-support.json.gz', physical=json(physicalPath,C), physicalPin=pin(physicalPath,C), supports=new Map(physical.results.map(r=>[r.target,r])), sourceBindings=json(P+'/aafc-stage-001/aafc-'+phaseText+'-measurement-bindings.json',C);
 const ownerGroups=new Map();
 for(const s of stage){
  const b=sourceBindings.find(b=>b.source_id===s.target);check(b&&b.target_id===s.selected.id,'Measurement mapping differs');const info=ownerInfo.get(b.pixelIndex), node=changes.get(info.id), parts=info.id.startsWith('atlas:multipart:')?node.replaces:[info.id];check(parts.every(id=>id.startsWith('atlas:physical:CAN-')),'Unexpected physical ancestry');const areas=[...new Set(parts.map(id=>id.split(':').at(-1)))];
  const support=supports.get(s.target), classes=['mapped_land_support','mapped_inland_water_support'].filter(k=>boxes(support.support[k]).length), bounds=classes.flatMap(k=>boxes(support.support[k]));check(classes.length,'No nonempty physical class');
  const negatives=sources.filter(f=>!areas.includes(areaOf.get(f.id))&&f.boxes.some(a=>bounds.some(b=>intersects(a,b))));const r={stage:s,binding:b,classes,areas,negatives,negative_bytes:negatives.reduce((n,f)=>n+f.bytes,0)};const group=ownerGroups.get(b.pixelIndex)??[];group.push(r);ownerGroups.set(b.pixelIndex,group);
 }
 const groups=[];let group=[],budget=0;
 for(const members of ownerGroups.values()){const bytes=members.reduce((n,r)=>n+r.negative_bytes,0);if(group.length&&budget+bytes>18*1024*1024){groups.push(group);group=[];budget=0;}group.push(...members);budget+=bytes;}if(group.length)groups.push(group);
 for(const group of groups){
  number++;const name='batch-'+String(number).padStart(3,'0'), dir=path.join(O,name);fs.mkdirSync(dir);const targets=[],bindings=[],negativeInventory=[],owners=new Set(group.map(r=>r.binding.pixelIndex)),seenRows=new Set(),patchRows=new Map();let cells=0;
  for(const owner of owners)for(const [y,a,z,kind]of byOwner.get(owner)){const rs=patchRows.get(y)??[];rs.push([a,z,owner]);patchRows.set(y,rs);cells+=z-a;}
  for(const {stage:s,binding:b,classes,areas,negatives}of group){
   const original=sourceById.get(s.target);check(original&&valueSha(original.feature)===valueSha(s.consumed),'Measured whole AAFC differs');check(original.feature.properties.ECOREGION_ID===ownerInfo.get(b.pixelIndex).target_properties.metadata.ecoregion_id,'Ecoregion crosswalk differs');const scope=byOwner.get(b.pixelIndex).flatMap(([y,a,z])=>Array.from({length:z-a},(_,i)=>({y,x:a+i})));
   bindings.push({source_id:s.target,feature_ordinal:original.ordinal,source_property:original.feature.properties.OBJECTID,properties_sha256:valueSha(original.feature.properties),geometry_sha256:valueSha(original.feature.geometry),target_id:s.selected.id,pixelIndex:b.pixelIndex,base_geometry_sha256:valueSha(s.selected.geometry),decision:'Adopt only the exact original repair keys after complete 273-node area-remainder restoration and intended-AAFC predicates. Complete other CAN ADM3 originals, all USA originals and all AAFC competitors remain whole vetoes. Preserve source/vintage, parent/cross-source and historic #887/#607/#609 limits; no current-law or geographic approval.',scope});
   const t={id:s.target,target_id:s.selected.id,pixelIndex:b.pixelIndex,base_geometry:s.selected.geometry,source_family:F,source_receipt_sha256:physicalPin.sha256,coverage_classes:classes,territorial_exclusions:negatives.map(f=>f.geometry)};
   if(!seenRows.has(b.pixelIndex)){const rows=new Map();for(const [y,a,z,kind]of byOwner.get(b.pixelIndex)){const rs=rows.get(y)??[];rs.push([a,z,kind==='land'?'mapped_land_support':'mapped_inland_water_support']);rows.set(y,rs);}t.coverage_rows=[...rows].sort((a,b)=>a[0]-b[0]).map(([y,runs])=>({y,runs:runs.sort((a,b)=>a[0]-b[0])}));seenRows.add(b.pixelIndex);}targets.push(t);
   negativeInventory.push({source_id:s.target,target_id:s.selected.id,pixelIndex:b.pixelIndex,areas,negative_ids:negatives.map(f=>f.id),geometry_sha256:negatives.map(f=>valueSha(f.geometry)),rule:'Retain every whole CAN ADM3 original outside the complete recorded area remainder, and every USA original, whose polygon-part bounds intersect any complete positive physical-support part. No owner roster filter or geometric cropping.'});
  }
  const adopted=write(dir,'adopted-provider-families.json',{version:1,kind:'adopted-provider-source-families-v1',families:[{source_id:F,product:productPin,feature_count:218,id_property:'OBJECTID',id_prefix:F+':',bindings}]});
  const requested=write(dir,'requested-native-patch.json',{rows:[...patchRows].sort((a,b)=>a[0]-b[0]).map(([y,runs])=>({y,runs:runs.sort((a,b)=>a[0]-b[0])}))});
  const template=write(dir,'source-evidence-template.json',{version:1,selector:{commit:H,path:'data/ownership-selection.json'},preparation_allowance:{phaseBytes:2147483648,rssBytes:2147483648},source_evidence:{...common,physical_evidence:physicalPin,physical_input:pin(stagesPath,C),targets}});
  const negative=write(dir,'complete-negative-inventory.json',{families:negativeFamilies,semantic:pin('data/semantic-report.json'),targets:negativeInventory});batches.push({name,physical_phase:phase,owners:[...owners],source_features:targets.length,cells,adopted,requested,template,negative});console.log(JSON.stringify(batches.at(-1)));
 }
}
check(batches.reduce((n,b)=>n+b.cells,0)===144047,'Batch scope differs');
write(O,'applicability-decision.json',{kind:'reviewed-Canada-complete-source-restoration-applicability',original_cells:438062,original_intervals:139042,source_hold_cells:103,administrative_source_ceiling:293912,physical_source_ceiling:144047,independent_source_review:pin(P+'/independent-source-review/REVIEW.md',C),complete_native_remainder:pin(P+'/source-review/native-remainder-screen.json',C),complete_native_AAFC:pin(P+'/source-review/native-aafc-screen.json',C),foreign_contacts:pin(P+'/source-review/foreign-original-intervals.json.gz',C),negative_families:negativeFamilies,held:[...held.values()],batches,limits:['Every original cell remains accounted; source ceilings are not qualified outputs.','Complete 273-node area remainder rather than target intersection witnesses supplies the positive administrative domain. Archive simplification and five parent-chain discrepancies impose no invented clipping.','Actual native/physical qualification, current owner-zero, selected-native conservation and emitted consumer acceptance remain pending.','This source-relative restoration does not close #887/#607/#609, approve current-law geography, publish or import history.']});
