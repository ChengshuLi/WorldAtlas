Actual full-suite scheduling observations

Source implementation is merged as PR707. The independent migration declarations are preserved verbatim and execute as separate files with unchanged fixture/seed/assertion/cleanup logic. All discovered files remain covered once. This packet records actual completed full runs, including the slower intermediate attempt, rather than an asserted performance guarantee.

The final source run improves balance and the migration worker's elapsed time, but its total improvement over the earlier source sample is small. The normal integration run's critical worker is essentially unchanged from that earlier sample. Therefore these observations do not demonstrate a reliable total full-suite speedup. The build/parity worker remains the critical path. Cold process caches, concurrent CPU/memory demand and hosted build/test variation are explicit limits. No further speculative optimization is claimed.

Read measurement.json for all worker/test-step/Node-wall times and counts, with exact archived APIs, TAP bytes and per-run receipts. Source workflow metadata identifies the tested authored head. In the queue, metadata identifies the trusted workflow driver; the candidate checkout and accepted bot merge receipt separately identify the actual tested commit. Queue elapsed time includes preparation/final merge authority work and is not directly comparable to the source workflow total. Parallel job durations must not be summed into elapsed time.

Reproduce from repository root with the Python standard library:

python3 coordination/engineering/ci-duration-proof-706-20261004/measurement-parser.txt coordination/engineering/ci-duration-proof-706-20261004/reproduction-spec.json

The output path in the spec must be absent; select a fresh /tmp directory for another reproduction. Ordered known-interval and rejected reversed-interval controls are included. These are measurements of individual historical runs, not a controlled statistical experiment. No production data, publication, imports or credentials changed.
