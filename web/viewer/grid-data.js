export function wrapColumn(x,width) { return ((x % width) + width) % width; }
// Lossless native-cell data. Every row stores ordered [exclusiveEndX, value] runs.
export function validateGrid(meta, rows, runs) {
  if (rows.length !== meta.height + 1 || rows[0] !== 0 || runs.length !== meta.local_grid.run_count * 2 || rows[meta.height] !== meta.local_grid.run_count)
    throw Error('Native grid dimensions do not match');
  for (let y = 0; y < meta.height; y++) {
    if (rows[y + 1] <= rows[y]) throw Error('Empty native row');
    let end = 0;
    for (let r = rows[y]; r < rows[y + 1]; r++) {
      const next = runs[2 * r], value = runs[2 * r + 1];
      if (next <= end || next > meta.width || (value & 15) < 1 || (value & 15) > 10 || value > 26)
        throw Error('Invalid native run');
      end = next;
    }
    if (end !== meta.width) throw Error('Native row is incomplete');
  }
}
export function cellValue(rows, runs, x, y) {
  let lo = rows[y], hi = rows[y + 1];
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (runs[2 * mid] <= x) lo = mid + 1;
    else hi = mid;
  }
  return runs[2 * lo + 1];
}
export async function loadLocalGrid(meta, base) {
  async function load(name) {
    const response = await fetch(new URL(meta.local_grid[name], base));
    if (!response.ok) throw Error('Native map could not load');
    const stream = response.body.pipeThrough(new DecompressionStream('gzip'));
    const buffer = await new Response(stream).arrayBuffer();
    const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', buffer))].map(v => v.toString(16).padStart(2, '0')).join('');
    if (hash !== meta.local_grid[name + '_sha256']) throw Error('Native map checksum mismatch');
    return new Uint32Array(buffer);
  }
  const [rows, runs] = await Promise.all([load('rows'), load('runs')]);
  validateGrid(meta, rows, runs);
  return { rows, runs };
}
