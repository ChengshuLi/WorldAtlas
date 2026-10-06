import {readFileSync, writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const root='data/regional-review/regional-review-626fdf640aab94e2';
const input=process.argv[2]||`${root}/sources/geoboundaries-rus-adm2-2017-original.geojson`;
const bytes=readFileSync(input), actual=createHash('sha256').update(bytes).digest('hex');
const expected='74012237384e53061aa63b6e20b9be24f94facfe615b52bbe72e62a81fa68ff0';
if(actual!==expected)throw new Error(`pinned source SHA mismatch: ${actual}`);
const data=JSON.parse(bytes.toString('utf8'));
const scope=JSON.parse(readFileSync(`${root}/baseline/issue-scope.json`,'utf8'));
const lineage=JSON.parse(readFileSync(`${root}/findings/current-lineage.json`,'utf8'));
if(lineage.base_commit!=='8e1162e3e364cebdec700ec796e2730379494922')throw new Error('current lineage was not extracted from pinned main');
const nativeIds=new Set(scope.member_location_ids.filter(x=>x.startsWith('gb:RUS:ADM2:')).map(x=>x.slice('gb:RUS:ADM2:'.length)));
const fragmentSources=new Set(lineage.rows.filter(x=>x.properties?.metadata?.source_id?.startsWith('resolve:')).map(x=>x.properties.metadata.original_id));
const expectedIds=new Set([...nativeIds,...fragmentSources]);
const selected=data.features.filter(f=>expectedIds.has(f.properties?.shapeID));
const selectedIds=new Set(selected.map(f=>f.properties.shapeID));
const missing=[...expectedIds].filter(x=>!selectedIds.has(x));
const duplicateCount=selected.length-selectedIds.size;
if(missing.length||duplicateCount||selected.length!==203)throw new Error(JSON.stringify({selected:selected.length,missing,duplicateCount}));
writeFileSync(`${root}/sources/geoboundaries-rus-adm2-2017-scoped-original-features.geojson`,JSON.stringify({type:data.type,crs:data.crs,features:selected})+'\n');
const rows=[];
for(const row of lineage.rows){
 const meta=row.properties?.metadata||{};
 if(meta.source_id==='gb:RUS:ADM2')rows.push({atlas_id:row.id,kind:'native-adm2',source_id:meta.original_id,source_name:row.properties.name,source_role:meta.source_role,parent_id:row.properties.parent_id,reference_year:meta.reference_year,license:meta.license});
 else rows.push({atlas_id:row.id,kind:'ecoregion-raion-fragment',source_id:meta.original_id,source_name:row.properties.name,source_role:meta.source_role,parent_id:row.properties.parent_id,ecoregion_id:Number(meta.source_id.slice('resolve:'.length)),reference_year:meta.reference_year,license:meta.license});
}
writeFileSync(`${root}/findings/source-crosswalk.json`,JSON.stringify({source_sha256:actual,source_bytes:bytes.length,source_feature_count:data.features.length,selected_original_feature_count:selected.length,native_scoped_feature_count:nativeIds.size,underlying_fragment_parent_count:fragmentSources.size,fragment_parent_source_ids:[...fragmentSources].sort(),matched_original_ids:[...selectedIds].sort(),rows},null,2)+'\n');
console.log(JSON.stringify({source_sha256:actual,source_bytes:bytes.length,source_features:data.features.length,native_scoped_features:nativeIds.size,fragment_original_sources:fragmentSources.size,scoped_original_features:selected.length,retained_extract_bytes:Buffer.byteLength(JSON.stringify({type:data.type,crs:data.crs,features:selected}))},null,2));
