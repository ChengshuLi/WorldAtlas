# Equivalent polygon runtime

`polygon_runtime.py` is an optional, explicitly pinned execution dependency of
`apply_selected_mixed.py`. Set `polygon_runtime` to its `{path, sha256}` file pin.
The driver authenticates it before loading, checks input hashes on construction
and completion, and records its code pin, NumPy version and substitutions in
`report.polygon_equivalent_runtime`.

The reviewed polygon/Bering modules and their geographic policy pins are not
changed or monkey-patched. Private function bindings retain the original GDAL
rasterization, feature order, witnesses, per-root counts, Bering transformations,
containment decisions and reports. The runtime changes only repeated mechanics:

- Map the authenticated row indexes and run bytes read-only instead of repeatedly
  reading and decoding the same rows. Row iteration still yields Python integer
  records in the original order.
- Validate physical/component coverage with array comparisons, then reuse that
  check for the same row in the same unchanged stream generation.
- Compute full-root populations once with exact integer-valued reductions. Grid
  bounds keep every partial sum below `2**53`, so the NumPy float64 accumulator
  represents all population integers exactly.
- Convert each exact coordinate once per vertex and solve boundary/grid-center
  coincidence using integer congruences. No coordinate is rounded. Boundary
  rejection and visit-limit behavior match the reviewed Fraction algorithms.

There are no saved roots, cell patches, memory limits, watchdogs, geography
shortcuts, or source-extraction changes. All source and complete stream hashes
are still rechecked by the original resolver/driver and the optional runtime.

## Checks

From a persistent workspace, set `TMPDIR` to a workspace directory and run:

```
PROJ_NETWORK=OFF /usr/bin/python3 -m unittest discover \
  -s scripts/v7-land/research-mixed-runtime/lydekker-regional-writer-integration \
  -p test_polygon_runtime.py -v
```

Nine focused tests cover randomized exact boundary/visit-limit parity, random
coverage unions, complete intersection/witness/profile report equality, root
populations, changed-stream rejection, module isolation, and a real pinned
polygon runtime through the mixed writer. The full mixed-runtime test suite
also passes when run from the workspace containing its archived test fixtures.
A completed full-source benchmark is required to establish production timing
and scientific parity; unit checks alone do not establish that result.
