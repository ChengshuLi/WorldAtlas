# Restore unchanged selected-geography applicability (#1746)

## Result and scope

Source-publication candidates can return `not-applicable` before the expensive
selected prefetch/native/continuous checks only after the trusted checker proves
that its explicit complete selected input and relevant method identities are
unchanged. The authored source-path restriction is admission, not equivalence.
The actual baseline/candidate trees, including baseline-only changes, are compared.

The typed collector covers the selected catalogue/source bank, ordinary native
materialization and absence, transport fragments, artifact metadata, additive
registry/ledger, original SOURCE/NATIVE custody and aliases, original selectors,
current-rebind products/external custody, code vectors, and strict historical and
same-path fallback routes. Unknown reader versions/layouts, changed identities,
missing strict inputs and exceeded bounds retain the existing full checker.
Audited reader profiles include the exact separately reviewed #1747 helper bytes.

Only routing metadata bodies are acquired and parsed. Scientific leaves retain
ordinary immutable mode/Git-OID identities, without geometry/native-array decoding
or a new scientific qualification. The executing checkout supplies policy for both
sides; a candidate cannot choose its own lighter policy. Baseline-equals-baseline
requests never use this shortcut, preserving the genuine finite-transition proof.

Cold partial checkouts acquire exact routing blob OIDs in discovery batches. Missing
strict historical roots use explicit `blob:none` fetches, never current-path
substitution. Shallow markers are preserved. Graph acquisition has prospective
root/batch/time controls and a separately labeled post-import object/byte guard;
it is not claimed to have a hard prospective network/disk byte cap. The wrapper's
120-second optional phase reaps its owned process group before falling back.

## Measurements (different boundaries, not interchangeable)

Original immutable pair:
- baseline `32103b9c717ae43e7e88b067a9c1dfe5a07e8c73`
- candidate `9231460981bf2cc7cfb574e762cd60ab0f6abb68` (PR #1743)

[Original hosted run 38159718877](https://github.com/ChengshuLi/WorldAtlas/actions/runs/38159718877)
completed in 11m14s. Its geography job took 655s and checker step 633s; the focused
regression remained 12s. The log records 28.876s selected prefetch, 315.346s native,
285.720s continuous, then `not-applicable` with zero changed owners. This was a
geography applicability regression, not escalation to three full regression shards.
The old hosted checker was not rerun during this change.

The final **cold collector** replay took **66.591s** on that exact pair. It began
with zero blobs in an isolated Git store, imported 112 routing objects (4,120,159
bytes) in 10 batches, and recovered six strict historical roots in two graph-only
batches. Those added 600 commit/tree objects (1,715,409 uncompressed bytes), with
zero unexpected blob imports and an unchanged shallow marker. Two tree API queries
provided size admission. Initial baseline/candidate metadata fetches took another
7.550s and are reported separately. See `cold-historical-1743-*.json` for full
identities, code-byte provenance, transport counters, initial state and limits.

Earlier **warm** measurements are retained separately, before the cold transport
adapter was added: the exact-pair collector took 8.456s, and the complete isolated
Python wrapper took 11.680s. The latter republished the exact original #1743 packet
subtree at a fresh synthetic source path on implementation commit `6268bedb`, using
ordinary immutable checkout verification. It did not request `--fetch`; it is not
the original historical candidate, a cold run, or a hosted workflow. These records
are `historical-1743-*.json` and `wrapper-replay-*`. Their pinned implementation
bytes/commits identify the earlier measured version rather than the final adapter.

No final hosted-workflow timing or universal sub-minute guarantee is claimed.

## Focused verification

- `node --test test/unchanged-selected-geography.test.mjs test/geography-prefetch.test.mjs`
  passed 25/25, zero skips, on the final transport/collector bytes (73.550s).
  This includes zero-blob partial clones, strict versus fallback origins, preserved
  shallow markers, batched metadata acquisition, unknown code/layouts, nested
  custody changes, absent native alternatives, unsafe modes and transport bounds.
- `node --test test/trusted-geography-check.test.mjs` runs the full 50 Python
  controls, including finite transition invariants, early ordering, wrong-provenance
  refusal, ordinary fallback, and owned-process cleanup. Its final log is retained.
- `node --test --test-name-pattern=Linux test/additive-gap-repair.test.mjs`
  passed 3/3. This adjacent CI correction freezes the old approved Linux issuer and
  supervisor specimens rather than hashing moving live files. Existing adverse
  method/byte-pair tests remain; the separately approved #1747 output-budget
  supervisor is explicitly refused as that older transition. No production
  authority, finite migration map, or #1747 seven-file postimage was changed.

The original source/evidence review, exact-head ownership/scope gates, consumer
outcomes, full applicable validation and authoritative combined-tree queue remain
required. This code does not approve geography, activate a release, or publish.
