# Engineering handoff: Matanuska–Susitna physical seam

This is a source research handoff for #1202 milestone 2 and regional integration #484. It reports the exact archived scope in #1205; it does not authorize a repair, a native grid change, an administrative owner assignment, regional approval, an import, or publication.

## What is established

The immutable #1205 baseline is `cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1`. The declared all-year predicate selects 282 unique interior components and the retained roster hash is `37b5efeb08f407cd19cc098186659a01899d748d8dd73b3c26bfccbd1d35fc66`. Exact custody and detector records close over 283 bound fragments and 571 source contact rows. Every component ledger row preserves original contact feature geometry, contact IDs, source fields and source lines.

The four declared contact subjects are:

* `atlas:physical:2a15134ff18942dc8e5e` — recorded `resolve:405`, Alaska–St. Elias Range tundra; 283 exact contact rows.
* `atlas:physical:6efac055720ebe84d7c2` — recorded `resolve:371`, Cook Inlet taiga; 4 exact contact rows.
* `atlas:physical:a20d41a6587ce2e2996b` — recorded `resolve:0`, Rock and Ice; 283 exact contact rows.
* `gb:USA:ADM2:52423323B25289890288494` — Denali ADM2; 1 exact contact row.

At the issue baseline, the three physical Atlas features point to the same recorded Matanuska–Susitna source member, `gb:USA:ADM2:52423323B34523976645917`. Their source ID tokens match the stored stable ID recipe in the retained refinement script. Their `reference_year: 2018` is Atlas feature metadata; it is not a RESOLVE source geometry observation date. All three also preserve the same eight recorded coastline adjustment entries. Those entries do not establish which operation affected any one fragment.

The archived 2018 ADM2 source comparison reports 281 of 282 component geometries intersecting Matanuska–Susitna and 3 intersecting Denali. The retained RESOLVE 2017 layer query includes full ECO_ID 371 and 405 geometries: 0 and 227 component intersections, respectively. The coordinate plane predicate counts and complete per-component values are in `results/run-one/source-overlay-ledger.json`; these do not measure physical area or assign a jurisdiction.

## What remains unknown

Every one of the 282 physical component classifications remains `unknown`: this research cannot decide source footprint omission, source disagreement, independently evidenced water or ice, or another cause. The official ECO_ID 0 query returned an incomplete HTTP 200 response after the unchanged 32 MiB cap; its partial bytes were discarded. The stable IDs authenticate to the recorded `ECO_ID` values, but the complete source geometry and per fragment processing lineage are unavailable.

The pinned refinement script contains validity repair, 0.001 degree simplification, 1e-8 overlay precision, small piece thresholds, and coastline buffer bands. These are plausible processing explanations. The execution commit, exact cached input geometries, and per fragment lineage through those operations are not established by the source output metadata. Do not infer that any specific buffer or cutoff caused an issue component.

## Inputs for downstream work

Downstream geometry review should preserve the original source and detector vintages, consult the exact source captures and full per component ledger, and establish source vintage and processing lineage before proposing a correction. The exact affected source set is the three RESOLVE feature IDs above, their shared Matanuska–Susitna ADM2 predecessor, and the separately recorded Denali contact. Use the full candidate feature and component bindings in the evidence ledger; a point observation or partial polygon intersection cannot classify a whole component.

Completed #486, #601, and #605 packets remain read only context. This issue does not repeat their broader Alaska role, county crosswalk, or settlement reviews. The later #1184 native grid queue must obtain its own current input and approval evidence; this archived detector inventory is not that queue.

## Evidence locations

* `evidence-quality.json` — issue subjects, immutable input pins, exact output hashes, metric bindings, validation receipts, source limits and research stages.
* `results/run-one/` and `results/run-two/` — independently generated source overlay outputs; all three corresponding files have identical whole file hashes.
* `results/controls/` — positive closure, four negative controls, and two run reproduction receipt.
* `sources/resolve-ecoid-0-receipt.json` — incomplete source response scope, hash and restoration URL.
* `sources/historical-subject-lineage.json` — exact baseline subject feature hashes and recorded source tokens.
