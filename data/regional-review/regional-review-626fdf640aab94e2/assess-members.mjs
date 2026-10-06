import {readFileSync, writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const root='data/regional-review/regional-review-626fdf640aab94e2';
const scope=JSON.parse(readFileSync(`${root}/baseline/issue-scope.json`,'utf8'));
const lineage=JSON.parse(readFileSync(`${root}/findings/current-lineage.json`,'utf8'));
const xwalk=JSON.parse(readFileSync(`${root}/findings/source-crosswalk.json`,'utf8'));
const parents=JSON.parse(readFileSync(`${root}/findings/parent-crosswalk.json`,'utf8'));
const sourceMetadata=JSON.parse(readFileSync(`${root}/sources/geoboundaries-rus-adm2-2017-metadata.json`,'utf8'));
if(lineage.issue!==395||lineage.scope_count!==210||lineage.missing.length)throw new Error('Unexpected issue scope lineage');
const rowsById=new Map(lineage.rows.map(row=>[row.id,row]));
const sourceById=new Map(xwalk.rows.map(row=>[row.atlas_id,row]));
const sourceFeatures=JSON.parse(readFileSync(`${root}/sources/geoboundaries-rus-adm2-2017-scoped-original-features.geojson`,'utf8'));
const sourceExtractBytes=readFileSync(`${root}/sources/geoboundaries-rus-adm2-2017-scoped-original-features.geojson`);
const sourceExtractHash=createHash('sha256').update(sourceExtractBytes).digest('hex');
if(sourceExtractHash!=='7eb4cba61f0d17bfacb634c08aff3ec4873ece62734d518b51614bf061a5a129'||xwalk.source_sha256!=='74012237384e53061aa63b6e20b9be24f94facfe615b52bbe72e62a81fa68ff0')throw new Error('Pinned original-source extract or full-source crosswalk changed');
const featureBySource=new Map(sourceFeatures.features.map(feature=>[feature.properties.shapeID,feature]));
const issueMembers=new Set(scope.member_location_ids);
const matched=new Set(lineage.rows.map(row=>row.id));
if(issueMembers.size!==210||matched.size!==210||[...issueMembers].some(id=>!matched.has(id)))throw new Error('Issue membership is not exactly mapped');
const rows=scope.member_location_ids.map(id=>{
 const row=rowsById.get(id), source=sourceById.get(id), p=row.properties, meta=p.metadata;
 const native=source.kind==='native-adm2', feature=native?featureBySource.get(source.source_id):featureBySource.get(source.source_id);
 if(!feature)throw new Error(`Missing pinned original geometry for ${id}`);
 const sourceName=feature.properties.shapeName;
 const urban=/(город|округ|city|urban|okrug)/iu.test(sourceName);
 let status='justified', rationale='The Atlas feature ID resolves one-to-one to the pinned geoBoundaries RUS ADM2 source feature with matching source ID and name. This justifies source lineage and its represented 2017 administrative-dataset label only; it does not establish present legal status, authoritative boundaries, full completeness, or correctness against another national source.';
 if(!native){status='correction-needed';rationale='This Atlas member is an ecological-region portion derived from an ADM2 unit, but is placed in the district-level administrative roster with source_role Raion and a Raion-tier selection reason. Preserve the current geometry and ID while an engineering owner determines whether the intended scope is an administrative unit or a named ecological portion; no geometric replacement is authorized by this finding.';}
 else if(urban){status='insufficient-evidence';rationale='The pinned source name identifies a city/urban okrug rather than an ordinary rayon, while the Atlas metadata describes the row as Raion. A sourced current legal-status and hierarchy crosswalk is needed before affirming this role. Source identity is verified; role is not.';}
 else if(row.geometry.component_count>1){status='insufficient-evidence';rationale=`The pinned source contains ${row.geometry.component_count} polygon components. This supports a multipart source representation, but no independent official geometry review verifies component-by-component inclusion, omissions, or current boundaries.`;}
 return {atlas_id:id,atlas_name:p.name,parent_id:p.parent_id,province_name:parents.rows.find(x=>x.province_id===p.parent_id)?.province_name,atlas_source_role:meta.source_role,source_kind:source.kind,source_unit_id:source.source_id,source_unit_name:sourceName,source_boundary_year:sourceMetadata.boundaryYear,source_data_update_date:sourceMetadata.sourceDataUpdateDate,source_build_date:sourceMetadata.buildDate,source_dataset_license:'Open Data Commons Open Database License 1.0 (source metadata; OpenStreetMap and Wambacher attribution)',geometry_type:row.geometry.geometry_type,component_count:row.geometry.component_count,assessment:status,rationale,source_evidence:'sources/geoboundaries-rus-adm2-2017-scoped-original-features.geojson',source_evidence_sha256:sourceExtractHash,atlas_base_commit:lineage.base_commit};
});
const counts=Object.fromEntries(['justified','insufficient-evidence','correction-needed'].map(status=>[status,rows.filter(row=>row.assessment===status).length]));
writeFileSync(`${root}/findings/member-assessments.json`,JSON.stringify({version:1,issue:395,base_commit:lineage.base_commit,scope_count:rows.length,scope_ids_sha256:lineage.scope_ids_sha256,counts,rows},null,2)+'\n');
console.log(JSON.stringify({count:rows.length,counts},null,2));
