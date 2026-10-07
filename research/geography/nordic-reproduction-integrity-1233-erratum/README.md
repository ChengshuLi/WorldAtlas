# Nordic reproduction integrity erratum

Issue #1389 authorizes one additive, source-only mechanical erratum for exactly four frozen detector components and four Norway/Sweden ADM2 subjects from #1233. All new files are under this issue's owned directory. No source data was fetched again, no core geography or hierarchy was edited, and no import, release, deployment, regional approval, or publication was performed.

## Reproduction

Use Python 3.12.14 with Shapely 2.1.2 and GEOS 3.13.1. From the repository root, run the recorded command twice with two unused run IDs:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B research/geography/nordic-reproduction-integrity-1233-erratum/reproduce.py --run-id <unique-run-id>
```

Each successful run creates a new, exclusive directory in `vintages/<unique-run-id>/`, writes the complete result, then installs `receipt.json` last. It refuses occupied paths, traversal IDs, symlinked ancestors, and replaced destinations. It uses only whole Git blobs pinned in `source-lock.json`. The exact C and M Atlas parts are both pinned, including the older C part-17 bytes through their preserved snapshot at the current baseline; each final result also includes the four full source features, the four C Atlas features, and the four full component and referenced fragment features for independent row checks.

The two accepted fresh runs are `vintages/repro-v12-one-20261007/` and `vintages/repro-v12-two-20261007/`. Their canonical semantic outputs, full family scans, source joins, overlays, and controls match exactly; timestamps and each new receipt digest differ. `pairwise-reproducibility.json` binds both outputs. `validation-controls.json` and the four positive/negative control receipts record the actual outcomes. Earlier partial runs and failed attempts remain in `vintages/` or `attempt-history.json`; only the v12 pair is treated as the completed run.

## Scope and results

The runner authenticates all 57 issue-declared whole-file pins, the issue body, and the shared helper bytes. The complete physical-component family contains 95,174 features; exactly the four declared rows join byte-for-byte to the retained full features, including their fragment lineage. The 17 complete fragment shards contain 96,963 features and supply every fragment referenced by the four components. The complete contact product contains 4,889 rows and its exact join to the scoped component/fragment references matches the retained rows.

The two complete consumed simplified geoBoundaries products contain 431 Norway ADM2 features (registry vintage 2013) and 290 Sweden ADM2 features (registry vintage 2017). All four exact source shape IDs occur once. The runner compares each full source feature to both whole Atlas vintages, C and M. The four selected C/M Atlas features are identical between those vintages. Their recorded parents are preserved exactly: the three Norway IDs use `framework:province:troms-og-finnmark:38859f82963b`; the Sweden ID uses `framework:province:norrbottens-lan:a6d0306eee4c`. The Atlas rows declare Municipality / ADM2 with an ADM1 source-parent tier. This preserves the historical record; it does not validate that those parent joins are historically correct.

All four Atlas subject geometries differ from the corresponding consumed simplified source feature. Their symmetric-difference planar measurements are recorded in the run outputs, along with both directional geometries. The complete source-product overlays cover all four candidate components; scanning every national feature adds no coverage beyond the four contact-subject union. These are reproducible geometry comparisons only. Decimal coordinate representation is not positional accuracy, and planar square degrees are not physical area.

The complete retained Natural Earth land layer intersects the full area of each of the four component geometries; the Natural Earth lakes layer intersects none. The original detector records all four water statuses as unverified, no positive-area administrative-input overlap, and no assignment. These generalized modern references do not establish historic land, water, ice, coastlines, legal borders, or a territorial assignment.

All declared pin, source, component, fragment, contact, country-source, combined-overlay, and physical phases include raw and decoded bytes, project code, and derived result/fixture bytes. The largest measured phase is 157,731,319 bytes, below the 268,435,456-byte cap; each raw or decoded file is at most 32 MiB. The exact totals are in each run report.

## Source context and unresolved findings

The source packet `#1229` remains the owner of upstream source research; regional issues #336/#337 remain separate. The recorded Norway metadata names Geonorge / Mapping Authority of Norway and CC BY 4.0; the Sweden metadata names geoBoundaries / Wikimedia Commons and CC0 1.0. The advertised full geoBoundaries products were not fetched and these registry license assertions were not independently audited here. Complete coverage claims apply only to the exact simplified products retained in #1229.

Official identity context inspected 2026-10-07:

- Statistics Norway's archived 2017 municipality correspondence includes Bardu (1922), Målselv (1924), and Storfjord–Omasvuotna–Omasvuono (1939): [SSB municipality correspondence](https://dataportal.ssb.no/classifications/131/correspondences/190). This is a dated classification, not a source-geometry crosswalk.
- Kartverket's current multilingual name list, updated 2026-08-31, identifies Storfjord, Omasvuotna, and Omasvuono under Troms: [Kartverket place names](https://www.kartverket.no/til-lands/stadnamn/samiske-og-kvenske-fylkes-og-kommunenamn). The exact old label `Omasvuotna sme 2` remains unmatched.
- Kiruna Municipality's information describes borders with Norway, Finland, Pajala, and Gällivare: [Kiruna Municipality information](https://kiruna.se/download/18.70c3d424173b4900fc548d3e/1600606427810/engelska.pdf). It is context, not an authoritative 2017 boundary product.

The exact 2013 Norway ADM1 crosswalk, the old combined Troms og Finnmark parent relationship, the Omasvuotna legacy name mapping, and the source-to-current-hierarchy relationship remain unresolved. No bilateral boundary source, finer authoritative geometry, historical hydrography or ice evidence, or full processing-chain replay was acquired. The measurements do not identify which transformation produced the Atlas/source differences and do not establish a confirmed physical gap or a repairable boundary defect. No polygon or parent correction is proposed.

## Files and handoff

- `source-lock.json` and `issue-contract-source.txt`: full issue scope, all exact original pins and commit/path/byte mappings.
- `authority-context.json`: four identities, source vintages/registry assertions, official citations, dates, recorded Atlas parents, and explicit limits.
- `reproduce.py`: authenticated whole-file checks, full semantic scans, measurement comparisons, negative controls, output admission, and exclusive publication.
- `evidence-quality.json`: bounded manifest, per-file output hashes, result bindings, methods, source records, and limitations.
- `attempt-history.json`: failed and superseded attempts kept distinct from the final pair.
- `vintages/`: fresh results and receipts for each retained run; only the v12 pair is the final complete reproduction.

Engineering handoff: keep the historic parent/name/source crosswalk open under its existing owners. Any later correction requires that source owner to establish the exact historic join and a separate scoped engineering proposal. This packet makes no regional approval or release claim.
