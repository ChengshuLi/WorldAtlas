# Selected metadata admission (#1754)

This corrects test selection, not science or package/import authority. The complete
merged PR1753 fixture is pinned to baseline
`7eb3293b739631f4e69d7e676c7a77ae7c22c107` and exact head
`1d67abb09f5b9d3009da115c06170678aa5cdf3f`: all 426 changed paths,
unchanged original scientific bytes, exact global metadata, historical registry
bodies and required role joins are retained. The earlier diagnostic used an
intermediate 425-file head; the additional final classification receipt is included.

## Design and limits

The fixed structural-role walk and exact selected/package/registry closure are
unchanged. Only its required metadata enters the shared phase cache. Other inert
supporting records are authenticated, validated and discarded one complete member
at a time. Syntax validation still requires reading supporting bodies; there is no
claim that their bytes or malformed contents can be ignored. This trades a bounded
sequential scan for the old cumulative retention cutoff.

Default raw-byte admission is one eighth of the lesser of Node's observed available
process memory and V8's available heap at entry. This leaves representation and
other gate headroom. `WORLDATLAS_SELECTED_METADATA_BYTES` may set a positive decimal
byte allowance no greater than that machine-derived ceiling. Invalid configuration,
missing resource observations or exhaustion conservatively retain full regression.
The optional function arguments support bounded probes and diagnostic observations;
no candidate file configures policy. This is cooperative admission, not an OS quota
or a guarantee that other allocations/concurrent work cannot exhaust memory.

Admission includes retained required bodies plus the current encoded supporting
body and its actual decoded body. Supporting volume does not accumulate. The
32 MiB encoded/decoded-member security bounds, role/schema bounds, exact Git body
identity, historical pins and full required-record validation remain independent
and mandatory. The ordinary API transport and its own cache/request bounds are
unchanged. No aggregate-byte allowance grants a package or reader role.

The full fixture exposed two representation seams beyond the original 16 MiB
cutoff. Supporting `.json.gz` / `.jsonl.gz` paths were already admitted by the path
prefilter but rejected by the later loop. They now undergo bounded complete gzip
decoding and JSON/JSONL validation. Concatenated members share the decoded-file
limit; every JSONL record, including the final record, is checked. All structural and supporting JSON rejects malformed UTF-8 before parsing; valid Unicode is preserved and the existing JSON BOM rejection stays unchanged. Two retained
resource logs exceed 128 KiB. Free-form text still keeps that limit; larger `.log`
files must be JSONL with each record at most 128 KiB and whole file at most 32 MiB.
Unknown opaque archives, new executable/configuration paths and unsupported roles
still fall back. These new inert representations confer no scientific authority.

## Actual replay and controls

From a checkout with the pinned Git commits and consumed bodies present:

```
node coordination/engineering/selected-metadata-admission-20261012/reproduce-pr1753.mjs FRESH_REPORT.json
node --test test/selected-data-profile.test.mjs test/pr-gates.test.mjs test/integration-proof.test.mjs test/deployment-budget-scope.test.mjs
```

The reproducer uses the complete actual Git diff and actual complete trees. It
never fetches or extracts data. Immutable tree-row sizes in the fixture avoid
hydrating unconsumed scientific payloads; every fetched body is authenticated by
the classifier. The unit fixture follows the existing historical delivery fixture:
it snapshots mutable/global metadata and retains every changed row; scientific
bodies stay in their original repository paths. Missing/drifted bodies refuse.

The old classifier refused the final head at 167 reads / 16,639,922 encoded bytes.
The corrected full replay completes at 349 reads / 38,981,635 encoded bytes, with
13,352,331 retained bytes and 27,109,018 peak admitted raw/decoded bytes. The unit
fixture succeeds with a 28 MiB operator allowance despite total read volume above
that allowance. A 20 MiB allowance refuses during decoded-member admission.
The initial corrected replay remains in `after-replay.json`; the exact reviewed UTF-8 correction is measured separately in `after-utf8-replay.json`. Observed elapsed time and process peak RSS are in these replay reports; process peak
includes the adapter/tree inventory, and is not a selector-only allocation measure.
No hosted end-to-end saving or new scientific execution is inferred from this replay.

Controls preserve the old full-package negative and exact SOURCE/native identity
and omission negatives. Added controls cover sequential aggregate exhaustion,
more than 256 supporting records / 16 MiB cumulative evidence, late malformed
records, malformed/concatenated/oversized gzip, resource-limited decode, structured
log record bounds, trailing content, body substitution, and unconsumed evidence
wrongly appended to package inputs. Normal exact-head review, CI and merge queue
remain required. Publication is unaffected.
