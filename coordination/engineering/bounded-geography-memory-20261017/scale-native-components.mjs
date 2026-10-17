import fs from 'node:fs';
import {pathToFileURL,fileURLToPath} from 'node:url';
const checkout=fileURLToPath(new URL('../../../',import.meta.url));
const {repairVisibilityWitnesses,newVisibleRepairCandidates,visibilityDigest}=await import(pathToFileURL(checkout+'/scripts/check-effective-geographic-regression.mjs'));
const [text,kind='native']=process.argv.slice(2),count=Number(text),size=Math.max(8,count);
const geometry={type:'Polygon',coordinates:[[[-180,-85],[180,-85],[180,85],[-180,85],[-180,-85]]]},baseHash=visibilityDigest(geometry);
const snapshots=[],record=name=>snapshots.push({name,...process.memoryUsage(),maxRSS_KiB:process.resourceUsage().maxRSS});global.gc?.();record('before_input');
const candidates=Array.from({length:count},(_,i)=>kind==='native'?{representation:'native-cells',component_id:`component-${i}`,target_id:'A',pixelIndex:1,disposition:'assigned',base_geometry:geometry,base_geometry_sha256:baseHash,native_rows:[{y:1,runs:[[i,i+1,1]]}],native_bounds:[-180,-85,180,85],native_cells:1,source_receipt_sha256:'a'.repeat(64),authority_sha256:'b'.repeat(64),rule_sha256:'c'.repeat(64)}:{component_id:`component-${i}`,target_id:'A',pixelIndex:1,disposition:'assigned',native_cells:1,geometry});
const latitudes=Float64Array.from({length:size},(_,y)=>80-y*160/size);record('after_input');const start=performance.now();
const added=newVisibleRepairCandidates([],candidates),witnesses=repairVisibilityWitnesses({candidates:added,size,latitudes,beforeRows:[{y:1,runs:[]}],afterRows:[{y:1,runs:[[0,count,1]]}]});
if(witnesses.length!==count||witnesses.some((w,i)=>!w||kind==='native'&&w.x!==i))throw Error('incomplete exact component witnesses');
record('after_witnesses');
// Output bytes are a separate O(component-count) obligation, not constant-memory work.
let reportBytes=2;for(let i=0;i<witnesses.length;i++)reportBytes+=Buffer.byteLength(JSON.stringify(witnesses[i]))+(i?1:0);
console.log(JSON.stringify({kind,count,nativeIntervals:1,nativeWords:2,reportBytes,milliseconds:performance.now()-start,snapshots},null,2));
