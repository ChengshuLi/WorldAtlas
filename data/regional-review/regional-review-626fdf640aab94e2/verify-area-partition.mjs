import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const root='data/regional-review/regional-review-626fdf640aab94e2';
const base='8e1162e3e364cebdec700ec796e2730379494922';
const ids=new Map(),packetCounts={},duplicates=[];
const zlib=await import('node:zlib');
const macroPath='data/macro-foundation/current-membership-inventory.json.gz';
const macroBytes=readFileSync(macroPath);
const macroInventory=JSON.parse(zlib.gunzipSync(macroBytes));
const area=macroInventory.find(x=>x.id==='framework:area:west-siberian-russia:5ce23a54f178');
if(!area||area.member_location_ids.length!==270)throw new Error('pinned 270-member macro area missing');
const areaIds=new Set(area.member_location_ids);
const files=[{number:394,path:`${root}/baseline/related-issue-394.json`},{number:395,path:`${root}/baseline/issue-395-github-api.json`},{number:396,path:`${root}/baseline/related-issue-396.json`}];
for(const item of files){
 const issue=JSON.parse(readFileSync(item.path,'utf8'));
 const match=[...issue.body.matchAll(/```json\s*(\{[\s\S]*?\})\s*```/g)].map(m=>JSON.parse(m[1])).find(x=>x.area_scopes?.some(a=>a.id==='framework:area:west-siberian-russia:5ce23a54f178'));
 if(!match)throw new Error(`issue #${item.number} lacks West Siberian Russia scope`);
 const area=match.area_scopes.find(a=>a.id==='framework:area:west-siberian-russia:5ce23a54f178');
 const list=match.member_location_ids;
 if(list.length!==match.location_count||new Set(list).size!==list.length)throw new Error(`invalid scope roster in #${item.number}`);
 const owned=list.filter(id=>areaIds.has(id));
 const count=area.owned_member_location_count;
 if(owned.length!==count)throw new Error(`issue #${item.number}: scoped area count ${count} but relevant roster ${owned.length}`);
 for(const id of owned){if(ids.has(id))duplicates.push({id,issues:[ids.get(id),item.number]});else ids.set(id,item.number);}
 packetCounts[item.number]={title:issue.title,state:issue.state,created_at:issue.created_at,area_id:area.id,area_name:area.name,area_full_count:area.full_area_location_count,area_owned_count:count,area_partial:area.partial,issue_member_count:match.location_count,west_siberian_members:owned.length,scope_hash:match.member_location_ids_sha256};
}
const actualIds=[...ids.keys()].sort();
const areaRoster=[...areaIds].sort();
const out={version:1,base_commit:base,macro_inventory_path:macroPath,macro_inventory_compressed_sha256:createHash('sha256').update(macroBytes).digest('hex'),area_id:area.id,area_member_ids_sha256:createHash('sha256').update(JSON.stringify(areaRoster)).digest('hex'),partition_is_evidence_work_only:true,area_total:270,packet_counts:packetCounts,west_siberian_member_ids:actualIds,unique_west_siberian_member_count:actualIds.length,overlaps:duplicates,missing_area_ids:areaRoster.filter(id=>!ids.has(id)),unexpected_packet_ids:actualIds.filter(id=>!areaIds.has(id)),exact_partition:actualIds.length===270&&duplicates.length===0&&areaRoster.every(id=>ids.has(id)),validation_limits:['Confirms only disjoint issue ownership of the pinned 270-member area workload; does not independently validate the polygon or source completeness.']};
if(!out.exact_partition)throw new Error(JSON.stringify({unique:actualIds.length,duplicates,missing:out.missing_area_ids.length,unexpected:out.unexpected_packet_ids.length}));
writeFileSync(`${root}/findings/area-packet-partition.json`,JSON.stringify(out,null,2)+'\n');
console.log(JSON.stringify({packet_counts:packetCounts,unique:actualIds.length,overlaps:duplicates.length,exact_partition:out.exact_partition}));
