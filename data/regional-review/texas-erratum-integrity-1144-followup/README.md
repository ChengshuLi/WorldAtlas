# Texas erratum producer-integrity correction (#1365)

Research snapshot: 2026-10-07 America/Los_Angeles. Reservation worker: `01a10948-7d38-75d0-bc01-4cc28ea41f49`. This additive packet is confined to the issue-owned path. It guards the exact 254-county interpretation output retained by #1138/#431; it does not rewrite those packets, original assessments, IDs, source bytes, parentage, classifications, or measurements.

## Claim and correction

The #1365 audit found that the actual #1138 producer (`data/regional-review/texas-source-interpretation-followup-431/reproduce.py`) consumed the issue contract, assessment rows, source feature collections, Census retrieval manifest and layer metadata from the mutable checkout. It did not authenticate all those complete consumed bytes before computation. The audit's coherent Panola/GEOID swap and changed `outSR` request were accepted by that original CLI, and its two original result writers replaced existing files. A late missing GEOID could fail after replacing the retained table with 253 partial rows. Those controls establish producer-integrity defects; they do not establish a wrong county join in committed evidence.

`input-pins.json` retains all 33 exact input hashes from the #1365 machine contract, plus the shared immutable evidence helper actually executed here. Every path and byte count is pinned to baseline commit `6a1c3b5410587289285f31809312792f0f085e87`; the immutable helper verifies the Git blobs and then verifies the complete materialized files before parsing. All reads used to produce outputs come from those authenticated byte strings. The exact GitHub acceptance body is retained in `issue-1365-snapshot.json`, SHA-256 `132fee5a55e104451d37d714b681ff15f72c0db3bcea81123aadbfa721ba2c89`.

The issue identifies `09c2dcff4f5acd92936fdd49378dd563332a1187` as the pre-#1144 comparison point. The source/producer paths introduced or retained by the affected #1144 merge are not present at that older commit. Therefore the new receipt uses the first fresh-main commit where the issue's 33 declared input pins are all present and match exactly; it does not misrepresent the older comparison commit as containing those later inputs.

For each exact issue ID, the producer now validates before output computation:

- The unique Atlas feature in the three pinned containing parts matches the row's exact ID, name, and parent; its retained source ID/name/URL, 2018 reference year, ADM2 tier, ADM1 parent tier, county role, and Texas area code agree with the original-source crosswalk.
- The pinned hierarchy contains that exact parent ID as the Texas province. The retained 2018 geoBoundaries USA ADM2 feature independently matches the row's source shape ID, name, and county tier.
- The complete 2018 and 2025 TIGERweb Texas collections each contain exactly 254 unique records. Every county row joins on its actual GEOID and independently agrees on Texas state code, basename, official record name, active government function status, and source vintage.
- The actual retrieval URLs are parsed and their `outSR=4326` and Texas-state query are checked. The Census service-layer metadata's native/latest WKIDs (102100/3857) are retained separately. The CBF ZIP's `.prj` is read from the authenticated archive and still declares NAD83/GRS1980; geoBoundaries separately declares CRS84.
- The original 254-row result and summary are reproduced byte-for-byte. All products publish only into an exclusively reserved fresh named vintage. The shared helper writes the completion receipt last; an interrupted directory stays incomplete and is never replaced.

## Territorial meaning, source roles, and limits

The 254 IDs are retained as ADM2 county units under the current Atlas Texas province parent. The Census guide retained in the original packet (191 pages; printed p. 161) states Texas has 254 functioning county governments with Commissioners Courts and distinguishes statistical county subdivisions. The older source review retained the 2018 geoBoundaries feature role as `Counties`, vintage 2018, type ADM2; its source metadata reports 2018 boundary year, source update 2023-01-19, build 2023-12-12, and 2018 ADM2 scope. These facts support the stated source identity and administrative tier for this packet. Census TIGERweb and CBF products are statistical depictions, not legal adjudications of jurisdiction or boundary lines.

The neighboring granularity note is inherited from #431's reviewed inventory: the West South Central ADM2 inventory comprises 470 records (254 Texas and 216 Arkansas, Louisiana, and Oklahoma). This packet does not recertify those neighboring regions or expand its Texas subject scope. It does not analyze island completeness, settle the #967 source-catalog hash lineage issue, or redo the 24 boundary comparisons assigned to #966.

Reuse evidence is source-specific. Census records and the Census CBF are U.S. government work retained under the original packet's public-access/public-domain rationale; the guide itself does not print an explicit license statement. The geoBoundaries source metadata reports Public Domain, but derivative/project terms were not independently adjudicated, so that rights question remains open. Sources stay at their existing pinned paths in the original packets; this correction does not silently copy, relocate, or overwrite them. The complete pins, original source retrieval records, and restoration notes are retained as immutable baseline references.

The original constitutional retrieval did not retain Texas Constitution Article V §18. The 250,874-byte result is a navigation/selector shell, not section text. The #1138 restoration instructions remain in force: retrieve through the official Texas selector or actual PDF download, verify the returned content, and record final URL, time, status, type, length, SHA-256, vintage, and reuse terms. No legal conclusion is inferred from the missing source.

No geometry was recomputed. No boundary/legal completeness, island completeness, coordinate displacement, datum operation accuracy, regional approval, publication, import, or historical authority is claimed. The legacy NAD83-as-WGS84 treatment remains described as an undocumented approximation; its numerical effect was not measured. All 24 historical unresolved classifications and source bytes remain untouched.

## Reproduction and adverse controls

From repository root, run the corrected real producer twice with two fresh names:

```sh
python3.12 data/regional-review/texas-erratum-integrity-1144-followup/reproduce_immutable.py --vintage 2026-10-07-run-1
python3.12 data/regional-review/texas-erratum-integrity-1144-followup/reproduce_immutable.py --vintage 2026-10-07-run-2
python3.12 data/regional-review/texas-erratum-integrity-1144-followup/record_run_receipts.py
```

These two final runs use Python 3.12.14 and are retained under `vintages/2026-10-07-run-1/` and `vintages/2026-10-07-run-2/`. Each validation record binds the execution runtime, exact producer/helper hashes and baseline commit. For every run the table is 309,836 bytes, SHA-256 `0ac299d71139bae80567dbde66a05f1863c38acffe4f1a3bf9e6a0935ba9df28`; the summary is 3,554 bytes, SHA-256 `31f533b2fb485f71beb34599b343ece2b769d9e0f12f7efc58c10385620bcb45`; and the per-run validation record confirms exact output equality with the retained originals. `publication.json` binds every product hash and is written last.

`record_run_receipts.py` refuses to overwrite either receipt and uses exclusive creation. Its positive control binds the 254-subject scope, all four 254-row identity joins, the 313 CBF polygon components, and byte equality with the retained valid output. Its reproducibility control compares the ordered erratum table, summary, and validation bytes from both runs. The digest uses length-prefixed product names and bytes; the run-specific `publication.json` is listed separately because it includes a different vintage path in each run.

Run the isolated real-entrypoint adverse controls:

```sh
python3.12 data/regional-review/texas-erratum-integrity-1144-followup/verify_controls.py
```

The controls use a temporary detached checkout at the exact baseline, copy only the owned runner and its retained acceptance/pin files, and remove the fixture checkout after the run. Swapped 2018/2025 GEOIDs, a changed 2018 request `outSR`, a missing GEOID on the last subject, a duplicated subject, and helper-code drift each fail before an output directory exists. Existing-output and interrupted-output sentinels remain unchanged; a dangling destination symlink remains in place and is rejected. The control receipt binds `method_id`, `kind: negative-control`, and `outcome: passed`, and preserves changed-fixture hashes, restored source hashes, exact runner/pin/issue-snapshot hashes, and observed failure class. A failed experiment is not represented as a successful result.

## Engineering handoff

Use `reproduce_immutable.py` as the integrity-guarded evidence producer for the retained #1138 interpretation; do not repair the original historical producer or replace its output in place. Any future change to county/native joins, Census query semantics, CRS interpretation, source-license decisions, legal source restoration, boundary comparison, or cross-state completeness requires its own reviewed scoped evidence and the owning engineering issue. This packet closes only the #1365 producer-integrity work item if all of that issue's technical and process acceptance gates pass; it certifies no region.
