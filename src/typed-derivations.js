/** Validate provenance only; this does not calculate or approve domain facts. */
export function derivationInputIds(row) {
  const ids = row.metadata?.derivation_input_ids ?? [];
  if (!Array.isArray(ids) || ids.length > 128 || new Set(ids).size !== ids.length
    || ids.some(id => typeof id !== 'string' || !id.trim() || id.length > 2000)) {
    throw Error('Invalid derivation input IDs');
  }
  return ids;
}

export function validateTypedDerivations(roots, inputs, sources) {
  const sourceById = new Map(sources.map(row => [row.id, row]));
  const example = row => row.is_example === 1 || row.status === 'example'
    || sourceById.get(row.source_id)?.status === 'example';
  const state = new Map(), factualSubjects = new Set();
  function visit(row, depth) {
    if (depth > 64) throw Error('Derivation chain exceeds 64 levels; split or review its provenance');
    if (state.get(row) === 'visiting') throw Error('Circular derivation evidence');
    if (state.get(row) === 'done') return;
    state.set(row, 'visiting');
    for (const id of derivationInputIds(row)) {
      const input = inputs.get(id);
      if (!input) throw Error('Derivation input is absent');
      if (!example(row) && example(input)) throw Error('Factual derivation cannot consume example evidence');
      visit(input, depth + 1);
      if (!example(input)) factualSubjects.add(input.subject_id ?? input.location_id);
    }
    state.set(row, 'done');
  }
  for (const row of roots) visit(row, 0);
  return [...factualSubjects];
}

/** Original territorial meaning is evidence, never a caller-selected repin. */
export function validateTypedGeography(rows, pins) {
  for (const row of rows) {
    if (row.is_example === 1) continue;
    const retained = row.metadata?.expected_geography;
    if (!pins || !retained
      || Object.keys(retained).sort().join(',') !== 'footprints_sha256,hierarchy_sha256,release_id'
      || ['release_id', 'hierarchy_sha256', 'footprints_sha256'].some(key => retained[key] !== pins[key])) {
      throw Error('Factual typed evidence requires retained matching geography pins; revalidation is required');
    }
  }
}
