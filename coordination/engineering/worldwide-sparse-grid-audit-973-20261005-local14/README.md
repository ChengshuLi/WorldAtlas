# Worldwide sparse grid audit — work in progress

Issue #973, fresh baseline `5b72dc3adf48b089c3319b18c3a447468196176a`.
Implementation is diagnostic only; no geography/grid/release/content edit or live
operation. All physical-water and geographic/source approval remain separate.

`scripts/audit-grid-intervals.mjs` compares complete sparse row intervals using the
actual application's projected edge arithmetic and deterministic first-owner
rule. It retains holes, islands, overlapping owner sets, half-open centre ties,
and exact checked-cell accounting, without a full world-sized per-cell matrix.
Eight independent controls compare against the actual rasterizer/compiler and
exercise a grid-only gap away from a component sample plus malformed inputs.

`scripts/audit-canonical-rows.mjs` consumes immutable Git inputs, all original
encoded/decoded ownership parts and the full original 49,625-location roster.
It verifies original ID/parent mappings, hierarchy/release/grid pins and all run
ranges. Every differing stored/executed projected bound remains in the output;
there is no tolerance waiver. Selection uses the actually executed projection.
Original run assets occupy bounded memory; fresh generated comparison products
use sparse intervals over at most 4,096 rows. Each output states checked and
unchecked world rows/cells explicitly. No source ownership or water is inferred.

Initial unreviewed 64-row smoke run checked 16,778,624 cells; zero stored/grid
coverage or owner differences, zero projected multiple owners, and 715 bitwise
projected-bound differences retained. It precedes the immutable execution guard
and remains local scratch, not accepted scientific/global evidence.

Next: execute all world-row partitions at a committed exact implementation,
measure memory/time and output budgets, run actual-data two-run equality and
negative CLI controls, retain complete discrepancy/tie inventories, prepare
whole-file evidence and distinct review before any normal queue integration.
Worldwide source gaps from #946 and incomplete physical-reference tiles remain
unresolved even if representation parity passes.
