# Pacific #1288 replay preservation successor

This additive packet records a safe successor for the historical #1054/#1281
replay. It does not edit or re-certify either original packet. Run from the
repository root with Python 3.12.14 and the pinned scientific environment
(set `WORLDATLAS_PYTHON` to that interpreter if needed):

```sh
python3 data/regional-review/pacific-1288-replay-preservation-erratum/safe_replay.py
```

The command authenticates the complete immutable source inventory, reserves a
new output vintage before replay, runs the byte-identical historical CLI in
disposable packet mirrors, retains the actual process attempts and output
hashes, and publishes a completion receipt last. Choose a new vintage by
editing the explicit `VINTAGE` constant in a reviewed copy of the runner; an
existing vintage is never reused. Scratch directories are private and removed
only after attempt receipts and raw streams have been captured in the admitted
vintage.

The verified acceptance run is `vintages/replay-20261008-07/`. Earlier
vintages are retained as intermediate attempts; `RESEARCH.md` records their
specific limitations.

The historical `south-central-pacific-405-scope-validation-1054-erratum/`
packet and `regional-review-14a242c4cb0781a7/` packet remain immutable. Replay
success proves byte-level execution and scope-validator behavior only. It does
not resolve source completeness, territorial meaning, physical island
semantics, current shoreline boundaries, parent completeness, or source
policy. Those matters remain with their existing follow-ups.
