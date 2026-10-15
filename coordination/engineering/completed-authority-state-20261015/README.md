# Completed checkpoint authority state

Issue: #2000. Code-only correction, based on `4aa52927bf61765cc462a2d0824fa5bce83df919`.

The private `qualifyAppendedAuthorities` frame retains the original full wrappers
through the unchanged source qualification, native contract/denominator,
duplicate-component, exact added-scope and original-literal checks. Only after
those checks does it return `{entry, nativeOnly, patches}` for appended authorities.
The caller retires exactly the frame's `retain` reservations after return or unwind,
then retains the compact wrappers. It does not reduce the shared reader's used
bytes, charged inputs, floor or caller carry. Later ordinary phase admission and
RSS checks remain authoritative.

`expectedAdded` points into the original proof ledger. It ends with the helper
frame, including on failure. Native-only proof ledger runs can also alias original
patch runs; those patch objects remain live and are reserved in the compact view.
No proof object is mutated. Independently parsed selected ledger and rebind
`original_rows` values are preserved.

Every later `oldAuthorities` consumer uses the original patch arrays and/or
`nativeOnly`: `legacyRegistry`, `acceptedRebindCheck`, `finishCheckpoint`,
`qualifyProjectedRebind`, and later `qualifyTransition` membership, original-patch
union/overlap and rebind checks. Exact original entry preservation is checked
against the selected registry independently. Accepted seed authorities were already
compact. No cumulative union replaces the original per-authority patch arrays.

## Actual bounded comparison

Run from a managed repository checkout containing the pinned ancestor:

    node coordination/engineering/completed-authority-state-20261015/compare.mjs

The runner imports the same ordinary-Git fixture builders as the checkpoint tests,
loads the exact old module from the pinned Git ancestor, and executes both public
checkpoint/transition/source/native/census paths against the same immutable
candidate. Each run keeps an actual 64-KiB caller buffer strongly reachable across
its following phases. `compare-result.json` records equal complete semantic bytes,
original patch hashes, executed source/fixture/runner hashes and the exact canonical
full-minus-compact reservation delta. Distinct trusted execution provenance and
actual phase-byte counts are retained separately and checked honestly. New fixture
Git identities change between runs; this is within-run equivalence, not a claim
that separate fixture runs have identical provenance.

The focused tests cover a nonempty genuinely qualified native-only append, another
real transition and projection, exact complete row/scope/literal/contract/base and
source-denominator rejection, original exception preservation, original patch
reassignment refusal, duplicate components, and post-literal/duplicate failure
cleanup. A second unfinished authority demonstrably carries the first full wrapper
until its complete checks unwind. Strongly reachable caller buffers and tight
next-phase overflow refusal cover genuine live carry without resetting admission.

## Limits and disposition

This is synthetic ordinary-Git engineering proof. It does not rerun Indonesia
scientific qualification or the stock failed consumer. The observed stock refusal
retained neither its prospective cap/used values nor the refused pin, so this fix
alone is not proof that the refusal clears. The exact accounting delta is not an
RSS or speedup saving. Original qualification/output/RSS caps are unchanged.

The complete successful legacy issued-source-to-native qualifier chain is not newly
reexecuted here. Its moved contract/denominator/row checks are unchanged, and the
existing authentic original-rule/conservation tests and independent current-rebind
rejection-boundary probes apply. A successful new legacy producer is not claimed.
Early child-reader refusals before `appendAuthority` returns receive no new wrapper
retirement credit; this patch makes no new recovery claim for their preexisting
shared-floor behavior.

Original source authority, current-rebind, actual owner-zero/conservation,
scientific approval and publication requirements remain unchanged. Integration
uses the ordinary queue; the coordinating owner retains dispatch. Actual later
normal-delivery adoption is separate from this engineering acceptance.
