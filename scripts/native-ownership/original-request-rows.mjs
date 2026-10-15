const COLUMNS = ['category', 'y', 'start', 'end', 'owners', 'source_feature_indices', 'physical'];
const COVERAGE = new Map([
  ['land', 'mapped_land_support'],
  ['inland-water', 'mapped_inland_water_support'],
]);
const need = (condition, message) => { if (!condition) throw new Error(message); };
const positiveInteger = value => Number.isSafeInteger(value) && value > 0;

/**
 * Convert original seven-column cohort records to requested native operands.
 * Caller authenticates the whole original packet and chooses its exact owner.
 * `unknown` is an explicit held class; arbitrary/unrecognized labels fail.
 * No geometry, source membership, physical support or authority is inferred.
 * Interval boundaries, original row order, SID order and classes are preserved;
 * only patch/coverage output is sorted by coordinate. Adjacent spans stay separate.
 */
export function normalizeOriginalRequestRows(packet, {owner, size} = {}) {
  need(positiveInteger(owner) && positiveInteger(size), 'Explicit owner and native size required');
  need(packet && Array.isArray(packet.columns) && packet.columns.length === COLUMNS.length
    && [...packet.columns].every((name, index) => name === COLUMNS[index]), 'Original request columns differ');
  need(Array.isArray(packet.rows) && packet.rows.length > 0, 'Nonempty original request rows required');

  const requested = [], held = [], sorted = [];
  const counts = {cells: 0, requested_cells: 0, held_cells: 0, by_category: {}, by_class: {}};
  for (const original of packet.rows) {
    need(Array.isArray(original) && original.length === COLUMNS.length, 'Invalid original request row');
    const [category, y, start, end, owners, sids, physical] = original;
    need(category === 'repair' || category === 'physical', 'Unsupported original request category');
    need(Number.isSafeInteger(y) && y >= 0 && y < size
      && Number.isSafeInteger(start) && Number.isSafeInteger(end)
      && start >= 0 && end > start && end <= size, 'Invalid original native interval');
    need(Array.isArray(owners) && owners.length === 1 && owners[0] === owner, 'Wrong or ambiguous original owner');
    need(Array.isArray(sids) && sids.length > 0 && [...sids].every(positiveInteger)
      && new Set(sids).size === sids.length, 'Invalid or duplicate original source SID');
    need(COVERAGE.has(physical) || physical === 'source-relative' || physical === 'unknown',
      'Unsupported original physical class');
    need(physical === 'unknown' || (category === 'repair' ? COVERAGE.has(physical) : physical === 'source-relative'),
      'Original category and physical class disagree');

    const row = [category, y, start, end, [...owners], [...sids], physical];
    const requestedClass = category === 'repair' && COVERAGE.has(physical);
    (requestedClass ? requested : held).push(row);
    sorted.push({row, requestedClass});
    const cells = end - start;
    counts.cells += cells;
    counts[requestedClass ? 'requested_cells' : 'held_cells'] += cells;
    counts.by_category[category] = (counts.by_category[category] ?? 0) + cells;
    counts.by_class[physical] = (counts.by_class[physical] ?? 0) + cells;
    need(Number.isSafeInteger(counts.cells), 'Original request cell count overflows');
  }

  sorted.sort((a, b) => a.row[1] - b.row[1] || a.row[2] - b.row[2]);
  const patchRows = [], coverageRows = [], coverageClasses = new Set();
  let previous;
  for (const item of sorted) {
    const [, y, start, end, , , physical] = item.row;
    need(!previous || previous.row[1] !== y || previous.row[3] <= start,
      'Duplicate or overlapping original request intervals');
    previous = item;
    if (!item.requestedClass) continue;
    if (patchRows.at(-1)?.y !== y) {
      patchRows.push({y, runs: []});
      coverageRows.push({y, runs: []});
    }
    patchRows.at(-1).runs.push([start, end, owner]);
    coverageRows.at(-1).runs.push([start, end, COVERAGE.get(physical)]);
    coverageClasses.add(COVERAGE.get(physical));
  }

  return {
    patch: {rows: patchRows},
    coverage_rows: coverageRows,
    coverage_classes: [...COVERAGE.values()].filter(kind => coverageClasses.has(kind)),
    requested: {columns: [...COLUMNS], rows: requested},
    held: {columns: [...COLUMNS], rows: held},
    counts,
  };
}
