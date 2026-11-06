# Historical evidence lead matcher

This matcher links exact diagnostic cluster spans to historical List 1 extents. A hit is a discovery lead, never a geographic selector, and a missing hit does not prove there is no relevant evidence. Outputs are diagnostics, not overrides.

The command requires pinned comparison-report and historical-index SHA-256 hashes. The matcher bounds its JSON inputs, checks disk availability during SQLite work, and uses file-backed SQLite temporary storage in the guarded output directory. It does not impose a memory cap, sample memory availability, or validate a memory watchdog report. It emits its report marker last. A reported post-link durability error has an uncertain outcome and requires inspection before any retry. Run the CLI as a single-threaded process because SQLite's temporary-directory setting is process-global.

From the repository's `scripts/v2-baseline/list1_reconciliation` directory, run `python -m unittest -q test_match_old_list1` for the focused synthetic tests. No geographic source data or build decisions are included.
