# Remove repeated native visibility searches

The accepted PR #2459 geography run 39087706416 measured 1,035.737 seconds in
native comparison. This change removes its repeated native-component witness
searches. Current base owner-zero validation and interval conservation remain.
No geography, ledger, patch, source, selected data or accepted evidence changes.

## Exact private-boundary argument

`qualifyTransition` checks every old ledger primitive and authority unchanged.
`qualifyAppendedAuthorities` joins every additional ledger row to a newly appended
authority's original row; a new component cannot hide under an existing authority.
The native completed-constructor verifier joins those component interval unions
to the exact original patch. `equalMergedPatchRows` then checks that the candidate
cumulative patch is exactly the old patch plus the appended patches.

Crucially, `disjointPatchRows` runs unconditionally after that union check. Every
new interval must be disjoint from every old cumulative interval in its row. This
rejects full and partial overlap even when the owner is identical. Union
coalescing alone would not establish this invariant.

Consequently each new native component's nonempty first interval is in the
candidate patch, absent from the old patch, and on a changed row. The consumer
still visits the complete original base on every authenticated changed row and
rejects any overlap with either cumulative patch. Only after this succeeds, and
after an explicit no-loss check, does it emit the component's first cell as its
deterministic zero-to-owner witness. Failed base checks produce no invented
witness. Source custody and private live-transition authentication are unchanged.

Legacy polygon components retain their actual polygon/native witness search.
The public, unqualified `repairVisibilityWitnesses` helper is unchanged and still
checks actual before/after cells. `newVisibleRepairCandidates` is also unchanged,
including arbitrary iterable semantics. There is no public trust or skip-validation
option, ordinal-selection optimization, or new authority/cache brand.

## Observed work and limits

The exact accepted artifact is 12121783044, 7,778,908 bytes, SHA256
`4bf9dea868bae1b02a58581f3db46e01412eb3c5c9c2a06e5c136bf1a3b186ef`.
Its `geography-check.json` is 510,244 bytes, SHA256
`6a8f4953e761ac16b07804daea2c24f833f45f3d650ed18d0c48a5b9f70c3eaa`.
The retained combined ledger is Git blob
`6fbe85e13cb45ab45714bf8c4aa0c27583221f20`, 57,989,593 bytes, SHA256
`2b0431686879ef2382c0901ba387273d49b89c4ad3270b70469b05cd9457e0df`.
All were read and checked at accepted main
`252f2aa1e6309b6990985dec73611d6df0e11c70`.

`bounded-probe.json` records the numerical diagnostic, not a new source or
checkpoint acceptance. Its 565 first-cell witnesses exactly matched all actual
accepted witnesses, including order, authority, cell and complete native-row
digest. The old 138 visibility batches traversed 5,838 cumulative additions per
batch, including 5,745 native components. That repeats 805,644 component visits,
171,859,404 native interval validations and 80,080,296 base-geometry vertices.
The separately proposed private projection fix removes redundant validation but
does not remove this repeated cumulative filtering or native witness search.

The actual 17,593 changed rows contain 4,970,502 original base intervals. A bounded
384-row sample (first, middle and densest 128-row blocks) decoded and validated
146,380 intervals in 31.24 ms, plus 857.00 ms for authenticated containing-body
acquisition. One eager cumulative native validation took 752.68 ms; direct
construction/hash comparison of all 565 witnesses took 49.84 ms. These are local
component measurements, not attribution of the hosted phase or an end-to-end
speedup. Eager validation excludes disk-backed metadata reads, and the base sample
excludes production async iteration and patch overlap work. No full geographic
replay or new source science was performed. Keep the genuine full-base scan for
this change; optimizing its query windows is separate work if later measurement
justifies it.

## Controls

`test/selected-native-witness.test.mjs` exercises genuine original and completed
authority transitions with full and both partial same-owner overlaps, a component
misattributed to an old authority, zero cells, actual current base occupancy,
multirow first-cell parity, unchanged legacy history, and forged/expired handles.
`test/visible-gap-eligibility.test.mjs` checks an arbitrary branded sequence whose
iterator and indexed lookup disagree, plus arbitrary mixed native/polygon callers
including already-owned and absent cells.
Existing checkpoint, joint CLI, interval streaming, authority identity and native
conservation suites remain applicable.
