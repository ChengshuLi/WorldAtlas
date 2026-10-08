# Engineering handoff: original #1319 writer admission

Checkpoint: 2026-10-08 America/Los_Angeles. This is a geography-lane evidence handoff under #1485's only owned path. It does not change the archived #1319 producer, controls, geography data, or source pins.

## Confirmed writer defect

At current `origin/main` `54defba631914989b0b1ebef340ce0b04c39c430`, the original archived files under `data/regional-review/regional-review-0968ad79c26518d2/vintages/generator-integrity-erratum/` are unchanged from the prior pinned vintage:

| File | SHA-256 |
| --- | --- |
| `integrity_guards.py` | `36358f235c6fa28e636217a3f0376f0fbca8729462f8c75d0700b4fa1784c5ef` |
| `validate_controls.py` | `a547f321341b1a00382fa44c33c63935f7e7520066dc67948e385c1b3a322aae` |
| `reproduce_integrity_erratum.py` | `a257f09860ca4db277cbc155e78c937a5a59953f9f3213d9e4c56d868e59e24f` |
| `evaluation-inputs.json` | `e2f9c442883ea10768dd8ae4946061c9681cb3b9e15e4c1ff442f80c04e3a098` |

`integrity_guards.py::require_new_output` uses `Path.exists()` (lines 16–19). It accepts dangling symlinks and dangling symlinked ancestors. The unchanged actual `validate_controls.py` was copied byte-for-byte with its complete retained inputs into a private mirror under this owned path and invoked twice with separate fresh run IDs. For both `erratum-summary-actual-summary-r3.json` and `correction-ledger-actual-ledger-r3.json`, the CLI exited 0, printed positive/negative/reproducibility `passed`, and created the previously absent target outside the output vintage. The ordinary pre-existing summary control exited nonzero before creating its run directory and preserved sentinel bytes. See `validation/actual-controls-symlink-reproduction-r3.json`; the earlier harness attempt and its artifacts remain under `negative-fixtures/actual-controls-r2` and are not counted as proof.

The exact shared guard used by `reproduce_integrity_erratum.py` was also exercised directly without mocks: dangling final output and dangling symlinked ancestor were accepted; live symlink and ordinary existing-file sentinels were rejected and preserved. See `validation/historical-producer-guard-observation-r2.json`.

## Producer replay limit

The original producer computes the complete report before it calls `require_new_output(output_path)` at line 169, creates parent directories at line 170, and writes with `output_path.write_bytes(...)` at line 172. Its full source input has a retained compressed SHA-256 `211a72c2c80bb60d10214944fa8cc4764e9ba888116e802ce6d87084872f5301`; the pinned input manifest declares 40,040,002 decoded bytes. That exceeds the 32 MiB evidence-file admission limit. A full producer CLI run therefore remains unverified; no fragment or partial geometry run is represented as proof.

## Engineering action required

The geography reservation authorizes additions only below `research/geography/madhya-pradesh-output-preservation-1319-20261008/`. Applying a fix to the original archived CLI would modify `data/regional-review/...`, outside that contract. Route implementation to an engineering-owned issue/path or have Main explicitly revise the ownership contract before code integration. Issue #1086 currently owns different parent-correction work and is blocked on #82 and #1085; it is not an owner for this writer defect.

When an engineering owner is assigned, change the shared admission/write path so it:

1. Resolves and validates the declared output root and every ancestor without following symlinks; rejects ordinary existing paths, live/dangling symlinks, non-directory ancestors, traversal, and any destination outside the owned root.
2. Admits the *entire* producer/control product set before source loading or expensive computation, then revalidates at creation to handle races.
3. Creates each product exclusively without following a final symlink (`O_EXCL`/no-follow or an equivalent descriptor-based writer); never overwrites sentinels.
4. Publishes one completion/publication receipt last, binding every admitted product's relative path, size, and SHA-256. A partial failure leaves no successful completion receipt.
5. Exercises the documented original producer and control CLI with fresh run IDs twice, complete inputs, ordinary/live/dangling output and ancestor controls, traversal/escaped destinations, missing inputs, and a failure after computation. Preserve failed attempts and all originals.

Until that engineering change and the size-admitted complete producer replay are independently verified, #1485 remains partial. The retained 224-subject/27-province reports and the 16 Agar metadata changes are preserved, but no new geography, source-rights, current-boundary, or completeness finding is made. The original uncertainties (including the 6,822/6,836 source-count discrepancy and unresolved Sheopur roster) remain open.
