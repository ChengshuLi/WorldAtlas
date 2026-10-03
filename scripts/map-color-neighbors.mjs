// Read-only presentation graph from the exact immutable raster. Edges describe
// screen adjacency/proximity, never historical territorial or geographic approval.
export function rasterColorNeighbors(grid, {maxHorizontalGap = 0} = {}) {
  if (grid.version !== 2 || !Number.isInteger(grid.coordinateBits) || !Number.isInteger(grid.size) || grid.size < 2 || !Number.isInteger(maxHorizontalGap) || maxHorizontalGap < 0) throw Error('Invalid raster presentation graph');
  if (grid.rows.length !== grid.size * 2 || grid.runs.length % 2) throw Error('Incomplete packed raster');
  const mask = 2 ** grid.coordinateBits - 1, base = 2 ** (32 - grid.coordinateBits), adjacent = new Set(), nearby = new Set();
  const pair = (set, a, b) => { if (a && b && a !== b) set.add(a < b ? a + '/' + b : b + '/' + a); };
  const run = i => {
    const a = grid.runs[i * 2], b = grid.runs[i * 2 + 1];
    return [a & mask, (b & mask) + 1, (a >>> grid.coordinateBits) + (b >>> grid.coordinateBits) * base];
  };
  let expected = 0, previous = [];
  for (let y = 0; y < grid.size; y++) {
    const offset = grid.rows[y * 2], count = grid.rows[y * 2 + 1];
    if (offset !== expected || offset + count > grid.runs.length / 2) throw Error('Invalid raster row bounds');
    expected += count; const current = []; let left = null;
    for (let i = offset; i < offset + count; i++) {
      const r = run(i);
      if (!r[2] || r[0] >= r[1] || r[1] > grid.size || left && left[1] > r[0]) throw Error('Invalid raster run');
      current.push(r);
      if (left) {
        const gap = r[0] - left[1];
        if (gap === 0) pair(adjacent, left[2], r[2]);
        else if (gap <= maxHorizontalGap) pair(nearby, left[2], r[2]);
      }
      left = r;
    }
    if (current.length > 1) {
      const first = current[0], last = current.at(-1), gap = first[0] + grid.size - last[1];
      if (gap === 0) pair(adjacent, first[2], last[2]);
      else if (gap <= maxHorizontalGap) pair(nearby, first[2], last[2]);
    }
    let i = 0, j = 0;
    while (i < previous.length && j < current.length) {
      const a = previous[i], b = current[j];
      if (Math.max(a[0], b[0]) < Math.min(a[1], b[1])) pair(adjacent, a[2], b[2]);
      if (a[1] <= b[1]) i++; else j++;
    }
    previous = current;
  }
  if (expected !== grid.runs.length / 2) throw Error('Unreferenced raster runs');
  const decode = set => [...set].map(s => s.split('/').map(Number)).sort((a,b) => a[0] - b[0] || a[1] - b[1]);
  return {adjacent: decode(adjacent), nearby: decode(new Set([...nearby].filter(k => !adjacent.has(k))))};
}
