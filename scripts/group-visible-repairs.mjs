#!/usr/bin/env node
// Planning only: grouping never grants scientific approval or runtime admission.
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const integer = value => Number.isSafeInteger(value) && value >= 0;
const requireValue = (condition, message) => { if (!condition) throw Error(message); };
const span = value => Array.isArray(value) && value.length === 2 && value.every(integer) && value[0] < value[1] && value[1] <= 262166;
const defaults = {maxComponents:Number.MAX_SAFE_INTEGER, maxVertices:250000, maxRowWork:16384, maxSourceBytes:268435456};

export function groupVisibleRepairs(rows, options = {}) {
  requireValue(Array.isArray(rows), 'Screening rows required');
  requireValue(Object.keys(options).every(k => k in defaults), 'Unknown grouping limit');
  const limits = {...defaults, ...options};
  requireValue(Object.values(limits).every(n => integer(n) && n > 0), 'Positive explicit grouping limits required');
  const seen = new Set(), families = new Map(), deferred = [], groups = [];
  let current = null;
  for (const row of rows) {
    requireValue(typeof row.component_id === 'string' && row.component_id.length > 0 && !seen.has(row.component_id), 'Missing or duplicate component');
    seen.add(row.component_id);
    requireValue(hash(row.current_selection_sha256) && hash(row.patch_sha256) && hash(row.geometry_sha256), 'Missing immutable screening identity');
    const identity = `${row.current_selection_sha256}:${row.patch_sha256}`;
    requireValue(current === null || current === identity, 'Mixed current ownership snapshots'); current = identity;
    requireValue(['visible','invisible','unknown'].includes(row.status), 'Unknown visibility status');
    requireValue(row.current_unassigned_cells === null || integer(row.current_unassigned_cells), 'Invalid cell count');
    requireValue(integer(row.witnessed_unassigned_cells), 'Invalid witnessed count');
    requireValue(typeof row.complete_native_scope === 'boolean', 'Missing completeness');
    requireValue(span(row.required_rows) && span(row.checked_rows), 'Invalid native row extent');
    requireValue(row.checked_rows[0] >= row.required_rows[0] && row.checked_rows[1] <= row.required_rows[1], 'Checked rows outside required extent');
    if (row.complete_native_scope) {
      requireValue(row.required_rows.every((v,i) => v === row.checked_rows[i]) && row.current_unassigned_cells !== null, 'False complete scope');
      requireValue(row.current_unassigned_cells >= row.witnessed_unassigned_cells, 'Witness count exceeds complete total');
    } else requireValue(row.current_unassigned_cells === null, 'Partial scan cannot claim total');
    if (row.status !== 'visible') {
      requireValue(row.witnessed_unassigned_cells === 0, 'Positive witness mislabeled');
      if (row.status === 'invisible') requireValue(row.complete_native_scope && row.current_unassigned_cells === 0, 'Incomplete negative exclusion');
      deferred.push({component_id:row.component_id, reason:row.status}); continue;
    }
    const w = row.witness;
    requireValue(row.witnessed_unassigned_cells > 0 && w?.current_owner === 0 && integer(w.x) && w.x < 262166 && integer(w.y) && w.y >= row.checked_rows[0] && w.y < row.checked_rows[1], 'Visible candidate lacks checked owner-zero witness');
    requireValue(Array.isArray(row.containing_native_asset_ids) && row.containing_native_asset_ids.every(v => typeof v === 'string' && v.length > 0), 'Invalid native asset roster');
    requireValue(integer(row.estimated_native_work?.vertices) && integer(row.estimated_native_work?.rows), 'Missing native work estimate');
    if (typeof row.source_family_id !== 'string' || !row.source_family_id || !hash(row.source_product_sha256)) {
      deferred.push({component_id:row.component_id, reason:'source-unresolved'}); continue;
    }
    if (!integer(row.estimated_source_bytes) || !integer(row.estimated_decoded_bytes)) {
      deferred.push({component_id:row.component_id, reason:'source-size-unresolved'}); continue;
    }
    const key = `${row.source_family_id}:${row.source_product_sha256}`;
    if (!families.has(key)) families.set(key, []);
    families.get(key).push(row);
  }
  for (const [key, members] of [...families].sort(([a],[b]) => a.localeCompare(b))) {
    // Locality sort is deterministic and O(n log n), not a quadratic all-pairs search.
    members.sort((a,b) => Math.floor(a.required_rows[0]/4096)-Math.floor(b.required_rows[0]/4096) || a.containing_native_asset_ids.join('|').localeCompare(b.containing_native_asset_ids.join('|')) || a.required_rows[0]-b.required_rows[0] || a.component_id.localeCompare(b.component_id));
    let group;
    for (const row of members) {
      const sourceBytes = row.estimated_source_bytes + row.estimated_decoded_bytes;
      const oversized = sourceBytes > limits.maxSourceBytes || row.estimated_native_work.vertices > limits.maxVertices || row.estimated_native_work.rows > limits.maxRowWork;
      if (!group || oversized || group.oversized || group.components.length >= limits.maxComponents || group.estimated_vertices + row.estimated_native_work.vertices > limits.maxVertices || group.estimated_row_work + row.estimated_native_work.rows > limits.maxRowWork) {
        group = {source_family_id:row.source_family_id, source_product_sha256:row.source_product_sha256, components:[], witnessed_component_cell_sum:0, current_unassigned_component_cell_sum:0, estimated_vertices:0, estimated_row_work:0, estimated_shared_source_bytes:sourceBytes, containing_native_asset_ids:[], latitude_blocks:[], scientific_qualification:'required', runtime_memory_admission:'required', oversized, resource_adjustment:oversized ? 'Schedule individually after measuring and admitting the required working set; target limits are not repair eligibility limits.' : null};
        groups.push(group);
      }
      requireValue(group.estimated_shared_source_bytes === sourceBytes, 'Same source hash has conflicting byte estimates');
      group.components.push(row.component_id);
      group.witnessed_component_cell_sum += row.witnessed_unassigned_cells;
      group.current_unassigned_component_cell_sum = group.current_unassigned_component_cell_sum === null || row.current_unassigned_cells === null ? null : group.current_unassigned_component_cell_sum + row.current_unassigned_cells;
      group.estimated_vertices += row.estimated_native_work.vertices;
      group.estimated_row_work += row.estimated_native_work.rows;
      group.containing_native_asset_ids = [...new Set([...group.containing_native_asset_ids,...row.containing_native_asset_ids])].sort();
      for (let block=Math.floor(row.required_rows[0]/4096);block<=Math.floor((row.required_rows[1]-1)/4096);block++) if (!group.latitude_blocks.includes(block)) group.latitude_blocks.push(block);
    }
  }
  return {version:1, current_selection_sha256:rows[0]?.current_selection_sha256 ?? null, patch_sha256:rows[0]?.patch_sha256 ?? null, limits, groups, deferred:deferred.sort((a,b)=>a.component_id.localeCompare(b.component_id)), input_components:rows.length, note:'Source/locality planning only. Independent qualification may run in parallel within measured aggregate RAM; combine qualified groups in one delivery. Re-screen when current ownership changes.'};
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [input,output,config] = process.argv.slice(2);
  requireValue(input && output && [4,5].includes(process.argv.length), 'Usage: group-visible-repairs.mjs INPUT.json OUTPUT.json [LIMITS.json]');
  const result = groupVisibleRepairs(JSON.parse(fs.readFileSync(input,'utf8')), config ? JSON.parse(fs.readFileSync(config,'utf8')) : {});
  fs.writeFileSync(output, JSON.stringify(result,null,2)+'\n', {flag:'wx'});
}
