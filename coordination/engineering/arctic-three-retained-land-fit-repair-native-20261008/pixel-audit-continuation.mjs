import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const sha=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
export const PIXEL_TARGETS=['atlas:physical:CAN-15:NWT','atlas:physical:CAN-25:NUN'];
const BEFORE='b9a3c8bf375217dba3a50d1a022ec7e4ac6c6f1cdedff22845da953c805b7433';
const AFTER='2deeff1457ff9238cb3dbe599e9a858dcce29d8ba88e2a66abe2785ddec0aed9';
// Complete original records remain the authority for every unrelated value.
// The predecessor inputs are independently authenticated by the issuing caller.
export function continuePixelAudit(original,accounting,sourceAreas,{nativeManifest,releaseId,originalAuditSha}){
 assert.equal(original.locations,49625);assert.equal(original.records.length,49625);
 assert.equal(new Set(original.records.map(row=>row.id)).size,49625);
 assert.equal(original.footprints_sha256,BEFORE);
 assert.equal(original.native_manifest.sha256,'a71edb65cbd7986e245f626e8a34b70e12c12d081ca24fc936bdd84e1bb07885');
 assert.equal(originalAuditSha,'a49773818f963c15c27b52a0cad7be6dabcb6dddf9523bdbc253118e177c9cd8');
 assert.equal(original.covered_cells,13854401485);assert.equal(original.water_or_uncovered_cells,54876610071);
 assert.deepEqual(original.missing,[]);assert.deepEqual(original.high_distortion,[]);
 assert.equal(accounting.kind,'complete-original-order-two-target-pixel-accounting');
 assert.equal(accounting.rows,262166);assert.equal(accounting.run_parts,55);assert.equal(accounting.run_words,57617774);
 assert.equal(accounting.owners,49625);assert.equal(accounting.added_cells,141);assert.equal(accounting.removed_cells,0);
 assert.deepEqual(accounting.records.map(row=>row.id),PIXEL_TARGETS);
 assert.equal(sourceAreas.kind,'historical-cache-original-and-current-two-target-source-area');
 assert.deepEqual(sourceAreas.records.map(row=>row.id),PIXEL_TARGETS);
 assert.equal(sourceAreas.area_algorithm_sha256,'4ead1c5de909b257a7b300984e4d3dc56124e9a6c0d27240662024e44fd8ed12');
 assert.equal(sourceAreas.activated,false);assert.equal(sourceAreas.physical_approval,false);
 assert.equal(typeof releaseId,'string');assert(releaseId.startsWith('geography:review:')&&releaseId!==original.reference_release);
 assert.equal(typeof nativeManifest.path,'string');assert(/^[a-f0-9]{64}$/.test(nativeManifest.sha256));
 assert.notEqual(nativeManifest.sha256,original.native_manifest.sha256);
 let changed=0;
 const records=original.records.map(record=>{
  const index=PIXEL_TARGETS.indexOf(record.id);if(index<0)return record;
  const counts=accounting.records[index],areas=sourceAreas.records[index];
  assert.equal(counts.owner,[6666,6757][index]);assert.equal(counts.added_cells,[140,1][index]);
  assert.equal(counts.original.cells,record.cells);
  assert.equal(counts.original_stored_area_m2,record.grid_wgs84_area_m2);
  assert.equal(Number(counts.original.grid_wgs84_area_m2.toFixed(6)),record.grid_wgs84_area_m2);
  assert.equal(areas.original_source_wgs84_area_m2,record.source_wgs84_area_m2);
  assert.equal(counts.current.cells-counts.original.cells,counts.added_cells);
  assert.equal(Number(counts.current.grid_wgs84_area_m2.toFixed(6)),counts.current_stored_area_m2);
  assert(Number.isSafeInteger(counts.current.cells)&&counts.current.cells>0);
  assert(Number.isFinite(areas.current_source_wgs84_area_m2)&&areas.current_source_wgs84_area_m2>0);
  const error=counts.current_stored_area_m2/areas.current_source_wgs84_area_m2-1;
  assert(Number.isFinite(error)&&Math.abs(error)<=.25);
  assert.equal(record.status,'represented');assert.equal(record.reason,null);assert.equal(record.source_area_cells,null);
  changed++;
  return {...record,cells:counts.current.cells,source_wgs84_area_m2:areas.current_source_wgs84_area_m2,
   grid_wgs84_area_m2:counts.current_stored_area_m2,relative_area_error:error};
 });
 assert.equal(changed,2);
 const unchanged=original.records.filter(row=>!PIXEL_TARGETS.includes(row.id));
 assert.deepEqual(records.filter(row=>!PIXEL_TARGETS.includes(row.id)),unchanged);
 assert.equal(unchanged.length,49623);
 const result={...original,records,footprints_sha256:AFTER,reference_release:releaseId,native_manifest:{...nativeManifest},
  covered_cells:original.covered_cells+141,water_or_uncovered_cells:original.water_or_uncovered_cells-141,
  area_method:'WGS84 occupied cell areas from complete original-order selected-native accounting; original source areas from versioned authenticated historical caches, successor source areas from the literal original recipe under the pinned current runtime.',
  continuation:{kind:'two-arctic-source-area-and-selected-native-accounting',before_footprints_sha256:BEFORE,
   after_footprints_sha256:AFTER,changed_subject_ids:[...PIXEL_TARGETS],unchanged_complete_records:49623,
   unchanged_complete_records_sha256:sha(unchanged),original_audit_sha256:originalAuditSha,
   checked_rows:262166,run_parts:55,run_words:57617774,added_native_cells:141,removed_native_cells:0,
   prior_continuation:original.continuation,source_area_evidence:sourceAreas,
   full_geographic_audit_claimed:false,production_deployment_verified:false}};
 assert.equal(result.covered_cells+result.water_or_uncovered_cells,262166**2);
 return result;
}
