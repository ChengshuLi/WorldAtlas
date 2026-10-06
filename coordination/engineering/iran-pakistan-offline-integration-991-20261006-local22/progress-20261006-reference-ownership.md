# Offline integration progress — 2026-10-06 04:05 America/Los_Angeles

Refs #991. Worldwide gap goal remains active. No production change or deployment.

Completed since the previous physical/raster checkpoint:

- Recovered exact original vegetation source from the existing six-part semantic evidence archive. Full member hash d473404d20a918bf9bc64b020bda1250ffc93ef6c31e0b2006e837f4f1287aa8 matches the original reference manifest. The truncated current-provider export was rejected and is not used.
- Recomputed all 14 environmental rows against exact original climate, terrain and vegetation inputs. All 14 baseline rows reproduced exactly; independent reruns are byte-identical. Original classes and supported intervals remain unchanged; only three area-share values change.
- Retained a complete repaired reference bundle: 49,625 locations / 346,346 rows / 72 parts. Preserved original dictionaries, unaffected rows, old target rows and all previous archives. Mandatory original-source context validation and complete predecessor reconstruction passed. Stage budget: 92,634,149 bytes / 266 descriptors including review reserves.
- Existing application startup packaging succeeded: 2,017,571 compressed bytes, 9,657,444 decoded bytes, repaired footprint 6ea7c3613759d7b747c800c399b70c1be24e1f6aea21fc81c389cfdcc78d3eb1. Independent engineering review requested against immutable product head fd0a8effe1a066f68b38b179bd9bd217b8054c96; review is pending, not assumed.
- GEO source-custody audit independently verified all 68 baseline prepared ClioPatria inputs (47,875,964 bytes). These are the exact historical preparation dependencies, not the separate raw upstream ZIP; that distinction is retained.
- Complete checksum-pinned before/after compact ownership snapshots prepared: 49,625 locations, 139,620,004-byte / 152-descriptor stage. Snapshot loading now supports hash-checked array shards and retains legacy FeatureCollection support.
- Baseline historical semantics reproduced exactly for the two target IDs: Saravan 290 intervals, Panjgur 292 intervals, all 582 matching original evidence/values. Scanned 13,378 political source records with the original archived mathematical helpers. The empty non-example dated-boundary set matches the baseline fingerprint.
- Three relevant ownership checks passed: checksum corruption rejection, standalone staging, and runtime appended-evidence decoding without dictionary renumbering.

Currently running: scoped actual ownership recomputation against repaired geometries, preserving and exhaustively comparing all 49,623 unaffected locations. This is not yet reported successful. No `unknown_changed` fallback is used.

Remaining critical path: finish and independently verify repaired ownership history/runtime; integrate mandatory migrated-context and repaired source products into the actual build; preserve exact scientific source custody and genuinely bounded evidence stages; run complete offline build/render and regression checks; complete independent final review and the remaining coherent integration PR. The worldwide audit, other confirmed map repairs and regression/delivery acceptance remain part of the active parent goal. Merged source research packets are not reported as completed map repairs.

A snapshot staging attempt failed only at final receipt serialization due to an incorrect budget API name. Its byte-identical regenerable partial outputs were verified against the successful next version before removal; the failed attempt is retained in ownership-snapshot-failed-attempt-v1.json. A baseline verification first encountered an obsolete system Node; rerunning with the pinned Node 24 completed successfully.
