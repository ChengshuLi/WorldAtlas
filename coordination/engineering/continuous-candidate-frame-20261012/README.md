# Bounded candidate custody in continuous validation

Issue: https://github.com/ChengshuLi/WorldAtlas/issues/1763

The coordinate children still authenticate each full selection and scan every whole
containing source. Baseline persisted-certificate validation still ends its snapshot
frame. Candidate persisted-certificate validation now keeps its one authenticated
snapshot through complete two-vintage certificate planning and candidate projection.
The frame returns only receipts, required rows and bounded projected features. It
ends before baseline required-source acquisition starts.

This removes the candidate required-source selected-state reload. It does not remove
the independent complete coordinate scan, source-body/feature/geometry inverse checks,
original invalidity handling, or the strict polygon comparison. Baseline is still
reacquired because the required-source closure is known only after both complete
certificates; retaining its snapshot too would change the memory/lifetime contract.

## Exact lifetime and admission

No module/global cache, user-supplied snapshot, callback escape or shared selected
reader is introduced. The private acquisition result is confined to completed
validation/projection helpers. Plan admission includes the complete live candidate
snapshot, resolver-owned image metadata and reader inventory alongside both persisted
products. Source projection charges that state, all caller custody and earlier
projections before opening another whole source. Baseline acquisition charges the
retained candidate projections. Snapshot/resolver WeakRef controls demonstrate that
they are collectable before the baseline source helper starts. A sampled process-group
RSS check is an observation, not a kernel-enforced quota or proof between samples.

## Compatibility and verification

Existing public validation and independent source-acquisition callers keep their
signatures and reauthentication. The shared scientific helper and supported-program
catalogue are unchanged. The Python wrapper, strict polygon operator and child native-GC
launch are unchanged. Historical execution receipts stay bound to their original code.

The focused suite exercises the actual entry, compares the new plan/projections to
independently reacquired originals, rejects commit drift and altered whole source,
feature and geometry inputs, refuses low admission before source opens, and verifies
that no selected snapshot escapes the frame. Existing complete-certificate custody,
missing-row/source, malformed-additive and sealed-lifetime controls remain applicable.

A larger single-process reduction is a separate opportunity, not this patch's claim.
The shared coordinate shard/join helpers currently reset metadata assuming isolated
children. Moving coordinate acquisition into the parent would require full external
custody accounting in those shared scientific bodies, a supported-program migration,
and a changed parent native-GC launch/lifecycle contract. This patch preserves those
boundaries rather than silently omitting their live state.

## Retained real-input proof

The retained proof uses the actual frozen code checkout at `1933d49ce3840d0d10bd76ba30e1d849e56c5233`
and explicitly distinct historical selected baseline/candidate commits. Its complete
encoded and decoded operand hashes and lengths exactly match the retained genuine
comparison. The original strict-polygon result is reused, not relabelled as a fresh
scientific execution. See `retained-proof-001/comparison.json`, actual child stage
clocks, complete publications and sampled process-group observations.

The corrected local run is shorter than the retained historical Node run, but these
are separate executions rather than a controlled concurrent benchmark. No hosted
saving is claimed. Current sampled aggregate RSS and the historical single-process
maximum measure different things and must not be compared as a memory reduction.

The independently reviewed routing collector also needs this exact new reader hash
in `AUDITED_READERS`; earlier audited hashes are preserved. The new frame adds no
input route. Omitting this coupled update would force later source-only checks back
onto the full geography path. A possible future cheap preflight could flag changed
audited-reader hashes for explicit review, but must never automatically approve an
unknown input route. No new preflight framework is introduced here.
