# Canonical derived NATIVE additions

Issue #1755. Work date: 2026-10-11 America/Los_Angeles.

The production change adds a lexicographic component-ID sort to the newly mapped per-target additions array in each of countyBatchProposalStage and administrativeBatchProposalStage. The unchanged strict effective-footprint reader already requires this order. The SOURCE scope, native scope, decisions and ledger rows retain their exact original order. No IDs are renamed or deduplicated; comparator equality leaves duplicate IDs for the existing admission/reader rejection. Full original geometry objects and all numerical/scientific operators are unchanged.

## Focused proof and boundary

The tests read the unchanged whole AUS handoff at its accepted source path (1,998,089 bytes, SHA-256 a86d07773cb98ac2e3b747b700eb07f845fb33da79da45c904927a2fa3b610b0). They authenticate its complete body and original target preimages. Both production constructor loops are extracted verbatim and executed with all original component IDs, original order and complete geometries. Synthetic zero-cell dispositions isolate serialization: these are not fresh SOURCE/NATIVE findings. Removing only the sort reproduces the strict reader refusal; the repaired output has canonical additions for all targets and preserves the original source/ledger inputs. Already-canonical inputs remain equal to the old constructor, and duplicate IDs still fail.

A separate bounded synthetic interval control exercises combineNativeBatch with genuine same-target nonlexical IDs. Expected patch and conserved old owner intervals are written explicitly, including same-owner shared-cell accounting and duplicate source/candidate/scope failures. Existing effective-footprint and native-grid tests also pass. The initial local test attempt exposed only an overly narrow expected error-message regex; it was corrected to the actual unchanged duplicate-candidate error before the final run.

Command: node --test --test-reporter=tap test/native-additions-order.test.mjs test/effective-footprint.test.mjs test/native-grid.test.mjs

Result: 15 passed, no failures/skips. Full applicable hosted CI remains required.

No original SOURCE/NATIVE run is claimed or replayed, no new gap/cohort is qualified and no selected release or production artifact changes. The actual historical AUS execution outputs were unavailable; no mixed old/new programme record is inferred from them.

## Existing code custody

SOURCE facts are authenticated against their issued SOURCE request's executed_code. Each NATIVE invocation independently authenticates its current request's executed_code against executing HEAD and binds that vector into its rule preimage. This existing separation is sufficient; no compatibility framework changes are made.

proposed-caller17.json lists the ordinary project files in the existing caller inventory and their current full-file hashes. Only scripts/additive-gap-repair.mjs differs from the latest accepted caller vector. After genuine independent exact-head code review, one new default catalogue record will use this same new vector for SOURCE and NATIVE. All original programme records and all current-rebind migrations must remain byte-for-byte unchanged; no28-file migration is required because its roster and bytes are unchanged.
