# Worldwide existing-release gap inventory

This diagnostic snapshot authenticates the existing main commit `cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1`. It does not wait for, consume, or install PR1150. It preserves the original physical-land detector measurement vintage and all source/date/water/area uncertainty.

`run-one/report.json` is the complete entry point: `source_descriptors` retains every actually read ordinary input file; `complete_products` references complete original fragment, residue, component and contact shards, using the original custody index for component aliases. All original raw and decoded shard bytes were checked. The existing complete products remain immutable; no duplicate geometry is needed when every full source byte and tile operand/query order is equal.

The committed adapter reconstructs every global fragment and residue, verifies complete world source/release/hierarchy/identity closure and every layered tile query, reruns connectivity including tile seams and dateline contacts, and requires exact canonical record equality against the complete original component/contact products. It fails on changed bytes or order. This identity producer cannot handle a changed release by guessing locality or silently reusing changed inputs; a repair requires an explicit successor run.

`identity-lineage.json.gz` describes an exact identity bijection over the complete fragment/component/residue rosters already retained in `complete_products`. Sorted roster hashes bind the membership domain; every source identity maps to itself, and no member is removed, added, split or merged. Five original unmeasured fragments remain unmeasured; political affiliations and water status are not inferred. This is lossless identity correspondence, not an overlay intersection ledger or new independent source truth.

`tile-queries.json.gz` preserves ordered source members and unknown status for every declared tile. `decoded-custody.json` preserves every decoded shard binding. Positive, negative and reproducibility receipts describe actual checks at committed code. The failed pre-final trial used Python tuple-versus-list equality; that representation error is preserved in its log and corrected by exact canonical JSON comparison, without geometry tolerance or repair.

Issue1164 owns this geometry/connectivity/lineage inventory. Issue1184 owns native-grid classification, source-context joins, priorities and disjoint actionable worker batches. It should consume these complete merged products and retain their original measurement limits. Later main revisions do not make this pinned snapshot the latest map; they require a dated successor. No geographic approval, core repair, production write, browser, deployment or publisher message occurs here.

## Reproduce

Use Python 3.12.14 with Shapely 2.1.2 and GEOS 3.13.1, a complete shared Git object store, and the committed producer source. Run twice into separate new directories:

```sh
python -B scripts/worldwide_gap_inventory.py --selected cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1 --output NEW-RUN-ONE
python -B scripts/worldwide_gap_inventory.py --selected cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1 --output NEW-RUN-TWO
```

Compare every complete encoded output byte, decoded gzip byte, and report; preserve both run directories. This producer checks its actual owned imported source files against its executed commit. Replaying the recorded execution commit reproduces the recorded executed-code pin. A later commit must retain its distinct execution vintage. The final runs recorded here executed commit `6dba91220dff2875f99169d3eb0116bd46c8624a`; adding evidence afterwards does not change those executed bytes.
