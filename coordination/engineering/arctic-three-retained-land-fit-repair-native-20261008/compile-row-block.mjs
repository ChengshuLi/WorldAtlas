// A completed row-block phase of the existing native ownership algorithm.
// The caller must authenticate and admit the COMPLETE owner operand roster.
import {nativePolygonIntervals, NATIVE_GRID_METHOD} from '../../../src/native-grid.js';
import {coverageRow} from '../../../scripts/audit-grid-intervals.mjs';

export function compileRowBlock(index, {size, latitudes, rowStart, rowEnd, maxRunBytes = 32 * 1024 * 1024}) {
  if (!Number.isInteger(size) || size < 2 || size > 300000 ||
      !Number.isInteger(rowStart) || !Number.isInteger(rowEnd) || rowStart < 0 ||
      rowEnd > size || rowStart >= rowEnd || rowEnd - rowStart > 4096 ||
      !Number.isSafeInteger(maxRunBytes) || maxRunBytes < 0 || maxRunBytes > 32 * 1024 * 1024)
    throw Error('Require a complete bounded native row block');
  const coordinateBits = Math.ceil(Math.log2(size)), factor = 2 ** coordinateBits;
  const ownerBase = 2 ** (32 - coordinateBits);
  const maxOwner = Math.min(2 ** 32 - 1, ownerBase ** 2 - 1);
  let previousOwner = 0;
  const prepared = index.map(item => {
    if (!Number.isInteger(item.index) || item.index <= previousOwner || item.index > maxOwner)
      throw Error('Invalid stable original owner order/capacity');
    previousOwner = item.index;
    let minLat = Infinity, maxLat = -Infinity;
    if (!Array.isArray(item.polygons) || !item.polygons.length) throw Error('Missing native polygons');
    for (const polygon of item.polygons) {
      if (!Array.isArray(polygon) || !polygon.length) throw Error('Missing native polygon rings');
      for (const ring of polygon) {
        if (!(ring instanceof Float64Array) || ring.length < 8 || ring.length % 2 ||
            ring[0] !== ring.at(-2) || ring[1] !== ring.at(-1)) throw Error('Unclosed native ring');
        for (let k = 0; k < ring.length; k += 2) {
          if (!Number.isFinite(ring[k]) || !Number.isFinite(ring[k + 1]) ||
              Math.abs(ring[k]) > 180 || Math.abs(ring[k + 1]) > 90)
            throw Error('Invalid native lon/lat coordinate');
          minLat = Math.min(minLat, ring[k + 1]); maxLat = Math.max(maxLat, ring[k + 1]);
        }
      }
    }
    return {...item, minLat, maxLat};
  });
  // Validate every ring in every separately completed phase, including owners
  // outside this latitude block. Then use the same stock interval selection.
  const selected = rowStart === 0 ? prepared : prepared.filter(item =>
    item.minLat <= latitudes[rowStart] && item.maxLat >= latitudes[rowEnd - 1]);
  const native = nativePolygonIntervals(selected, {size, rowStart, rowEnd, latitudes});
  const rows = new Uint32Array((rowEnd - rowStart) * 2), words = [];
  const ownerCounts = new Map(prepared.map(item => [item.index, 0]));
  let totalRuns = 0, ownedCells = 0, multipleOwnerCells = 0;
  function append(start, end, id) {
    if ((totalRuns + 1) * 8 > maxRunBytes) throw Error('Complete row-block output exceeds admitted bound');
    words.push(id % ownerBase * factor + start, Math.floor(id / ownerBase) * factor + end - 1);
    if (++totalRuns > 2 ** 32 - 1) throw Error('Canonical row offsets exceed uint32 capacity');
    const cells = end - start;
    ownedCells += cells; ownerCounts.set(id, ownerCounts.get(id) + cells);
  }
  for (let y = rowStart; y < rowEnd; y++) {
    rows[(y - rowStart) * 2] = totalRuns;
    let pending = null;
    for (const segment of coverageRow(native.rows.get(y) ?? [], size)) {
      if (segment.owners.length > 1) multipleOwnerCells += segment.end - segment.start;
      const id = segment.owners[0] ?? 0;
      if (!id) { if (pending) { append(...pending); pending = null; } continue; }
      if (pending && pending[1] === segment.start && pending[2] === id) pending[1] = segment.end;
      else { if (pending) append(...pending); pending = [segment.start, segment.end, id]; }
    }
    if (pending) append(...pending);
    rows[(y - rowStart) * 2 + 1] = totalRuns - rows[(y - rowStart) * 2];
  }
  return {version: 2, method: NATIVE_GRID_METHOD, size, coordinateBits,
    row_start: rowStart, row_end: rowEnd, checked_rows: rowEnd - rowStart,
    checked_cells: (rowEnd - rowStart) * size, rows, runs: Uint32Array.from(words),
    total_runs: totalRuns, owned_cells: ownedCells, multiple_owner_cells: multipleOwnerCells,
    boundary_tie_records: native.ties.length, per_owner_cells: [...ownerCounts],
    scientific_approval: false, installation_ready: false};
}
