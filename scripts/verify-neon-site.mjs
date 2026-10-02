import fs from 'node:fs';
import {storageExportV2Collections} from '../hosted/storage-export-v2-contract.js';
import {hydrateMapSnapshotPage} from '../src/map-snapshot-format.js';
import {hydrateHostedTemporalGeographyPage} from '../src/hosted-temporal-geography.js';
const origin=new URL(process.argv[2]??''),output=process.argv[3],writable=process.argv[4]==='--writable';
if(origin.protocol!=='https:'||origin.pathname!=='/'||origin.username||origin.password||origin.search||origin.hash||!output||process.argv.slice(4).some(x=>x!=='--writable')||!process.stdin.isTTY)throw Error('Supply HTTPS Site, receipt path and optional --writable with hidden terminal input');
process.stdin.setRawMode(true);console.log('Ready for private read-only verification credential on hidden stdin.');
const token=await new Promise(resolve=>{let value='';process.stdin.on('data',chunk=>{value+=chunk.toString();if(!/[\r\n]/.test(value))return;process.stdin.pause();process.stdin.setRawMode(false);resolve(JSON.parse(value.trim()).token);});});
async function get(path){const response=await fetch(new URL(path,origin),{headers:{'OAI-Sites-Authorization':'Bearer '+token},redirect:'error',signal:AbortSignal.timeout(60000)});if(!response.ok)throw Error('Live API rejected '+path.split('?')[0]+' HTTP '+response.status);return response.json();}
const [geography,marker,capacity]=await Promise.all(['atlas-geography.json','api/storage/v2/export-marker','api/storage/capacity'].map(get));
if(marker.backend!=='postgres'||marker.read_only===writable||Object.keys(marker.counts).length!==23||geography.contentCapabilities.datedGeography!==1||geography.contentCapabilities.storageExport!==2||geography.contentCapabilities.datedFootprints!==0)throw Error('Published backend/capabilities/maintenance mismatch');
const pins={release_id:geography.reference_release.id,hierarchy_sha256:geography.reference_release.hierarchy_sha256,footprints_sha256:geography.reference_release.footprints_sha256};
let next=0;const pages=[];await Promise.all(Array.from({length:4},async()=>{while(next<storageExportV2Collections.length){const collection=storageExportV2Collections[next++],page=await get('api/storage/v2/export/'+collection+'?limit=1');if(page.revision!==marker.revision||page.snapshot_marker.fingerprint!==marker.fingerprint||page.records.length>1)throw Error('Raw page is not a consistent bounded snapshot');pages.push(collection);}}));
const years=[];
for(const year of [-3000,-1,1,1000,1800,2025,2026]){
 const responses=await Promise.all(['records','withdrawals'].map(stream=>get('api/geography/temporal/snapshot?'+new URLSearchParams({year,stream,limit:200}))));
 for(const page of responses){hydrateHostedTemporalGeographyPage(page,{year,expectedGeography:pins});if(page.revision!==marker.revision)throw Error('Geographic revision drift');}
 const map=hydrateMapSnapshotPage(await get('api/map/snapshot?'+new URLSearchParams({year,limit:1})));if(map.revision!==marker.revision||map.year!==year)throw Error('Scalar/geographic revision mismatch');years.push(year);
}
const after=await get('api/storage/v2/export-marker');if(after.fingerprint!==marker.fingerprint)throw Error('Content changed during verification');
const receipt={verified_at_utc:new Date().toISOString(),url:origin.origin,read_only_verification:true,site_writable:writable,backend:marker.backend,revision:marker.revision,all_fact_tables:pages.sort(),fact_table_count:pages.length,catalog_sha256:marker.catalog_sha256,marker_fingerprint:marker.fingerprint,capabilities:geography.contentCapabilities,geography:pins,years,capacity,credentials_logged:false};fs.writeFileSync(output,JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify({verified:true,backend:marker.backend,revision:marker.revision,tables:pages.length,years,site_writable:writable}));
