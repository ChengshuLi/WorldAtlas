// Exact merge preimage from a34b867ed48b8f324856fae4763f31afde194284.
const demand=(v,m)=>{if(!v)throw Error(m);};
export function mergeCompletedNativePatches(patches, size) {
  const byRow = new Map();
  for (const patch of patches) {
    demand(Array.isArray(patch.rows), 'Complete native intervals required'); let previous = -1;
    for (const row of patch.rows) {
      demand(Number.isSafeInteger(row.y) && row.y > previous && row.y < size && Array.isArray(row.runs) && row.runs.length,
        'Invalid complete native row'); previous = row.y; let end = 0;
      for (const run of row.runs) {
        demand(Array.isArray(run) && run.length === 3 && run.every(Number.isSafeInteger) && run[0] >= end
          && run[1] > run[0] && run[1] <= size && run[2] > 0, 'Invalid complete native interval'); end = run[1];
      }
      const runs = byRow.get(row.y) ?? []; runs.push(...row.runs.map(run => [...run])); byRow.set(row.y, runs);
    }
  }
  return [...byRow].sort((a, b) => a[0] - b[0]).map(([y, runs]) => {
    runs.sort((a, b) => a[0] - b[0]); const merged = [];
    for (const run of runs) {
      const last = merged.at(-1); demand(!last || run[0] >= last[1], 'Modern cells overlap the accepted cumulative patch or another original authority');
      if (last && last[1] === run[0] && last[2] === run[2]) last[1] = run[1]; else merged.push(run);
    }
    return {y, runs: merged};
  });
}

