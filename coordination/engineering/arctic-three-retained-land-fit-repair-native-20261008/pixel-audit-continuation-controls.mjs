// Actual original whole schema and finished predecessor products, no GIS/area work.
import fs from 'node:fs';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';
import {continuePixelAudit,PIXEL_TARGETS} from './pixel-audit-continuation.mjs';
const inputs=JSON.parse(fs.readFileSync(process.argv[2]));
const read=pin=>{const s=fs.lstatSync(pin.path);assert(s.isFile()&&!s.isSymbolicLink());assert.equal(s.size,pin.bytes);assert.equal(s.mode&0o777,0o644);const raw=fs.readFileSync(pin.path);assert.equal(createHash('sha256').update(raw).digest('hex'),pin.sha256);return JSON.parse(raw);};
const original=read(inputs.original),accounting=read(inputs.accounting),areas=read(inputs.sourceAreas);
assert.equal(inputs.original.sha256,'a49773818f963c15c27b52a0cad7be6dabcb6dddf9523bdbc253118e177c9cd8');
const binding={nativeManifest:{path:'data/canonical-grid/arctic-v9/manifest.json',sha256:'1'.repeat(64)},releaseId:'geography:review:'+ '2'.repeat(64),originalAuditSha:inputs.original.sha256};
// Placeholder binding tests continuation arithmetic only, not release qualification.
const result=continuePixelAudit(original,accounting,areas,binding);
assert.equal(result.records.length,49625);assert.equal(result.covered_cells-original.covered_cells,141);
assert.equal(original.water_or_uncovered_cells-result.water_or_uncovered_cells,141);
let unchanged=0;
for(let i=0;i<original.records.length;i++)if(!PIXEL_TARGETS.includes(original.records[i].id)){assert.equal(result.records[i],original.records[i]);unchanged++;}
assert.equal(unchanged,49623);
for(const id of PIXEL_TARGETS){const old=original.records.find(x=>x.id===id),next=result.records.find(x=>x.id===id);for(const key of Object.keys(old))if(!['cells','source_wgs84_area_m2','grid_wgs84_area_m2','relative_area_error'].includes(key))assert.deepEqual(next[key],old[key]);}
let negatives=0;
function reject(change){const args=[{...original,records:[...original.records]},structuredClone(accounting),structuredClone(areas),structuredClone(binding)];change(args);assert.throws(()=>continuePixelAudit(...args));negatives++;}
reject(a=>a[0].footprints_sha256='0'.repeat(64));
reject(a=>a[0].records.pop());
reject(a=>a[0].records[0]=a[0].records[1]);
reject(a=>a[1].records[0].id='foreign');
reject(a=>a[1].records[0].original.cells++);
reject(a=>a[1].records[0].original_stored_area_m2++);
reject(a=>a[1].records[1].added_cells++);
reject(a=>a[2].records[0].original_source_wgs84_area_m2++);
reject(a=>a[2].records[1].current_source_wgs84_area_m2=NaN);
reject(a=>a[2].records.reverse());
reject(a=>a[2].area_algorithm_sha256='0'.repeat(64));
reject(a=>a[3].releaseId=original.reference_release);
console.log(JSON.stringify({positive:1,negative:negatives,actual_original_records:49625,unchanged_same_objects:unchanged,new_target_fields:4,placeholder_release_binding:true,areas_computed:0,grid_rows_computed:0}));
