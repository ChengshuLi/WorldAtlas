# Selected-point batching

A point-component request may opt into `point_runtime.py` with a `runtime`
file pin containing its canonical path and SHA-256. The resolver authenticates
that module before execution and rechecks it before returning. Requests without
the pin retain the reviewed single-item execution path.

The runtime scans each selected GeoNames archive member once, retaining only
selected raw records. It reads the complete member, checks UTF-8 and line framing,
and rejects duplicate selected IDs. Each record then goes through the original,
unchanged extractor with the original archive metadata and matching raw lines.
Source, selector, identity, coordinate and geometry checks remain in that checker.

All named-identity requests run in one isolated `/usr/bin/python3 -I` process.
The unchanged pinned checker checks each item. Source JSON is authenticated and
parsed once per path/hash, then every source is rehashed before successful exit.
Per-request and per-result framing retains the reviewed validation limits; the
number of requests and total batch size have no application-imposed ceiling.
There are no execution timeouts or memory watchdogs.

Claims, extraction records, geometry results and reviewed code hashes are
unchanged. The report adds `equivalent_runtime` to identify the separate runtime,
its substitutions and the unchanged geographic policy. The resolver's own code
hash changes as usual. Full regional replay comparisons must retain all scientific
fields and normalize only these declared implementation/provenance differences.

Run focused tests with `/usr/bin/python3 -m unittest discover -s <this-directory>
-p 'test_*.py'`, selecting a persistent workspace `TMPDIR` when needed.
