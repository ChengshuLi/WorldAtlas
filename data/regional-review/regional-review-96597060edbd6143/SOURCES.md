# Turkey interior batch 4 research packet

Issue #74 covers 229 Atlas identities in 23 complete province groups (23 of 81 provinces and 229 of 911 area members). This is a partial area packet. Each source feature and matching Atlas feature is compared in the reproducible report. The comparisons establish correspondence to the retained source, not administrative truth.

## Retained and pinned material

The 2021-referenced geoBoundaries ADM2 and ADM1 data are OSM-derived and were retained in issue #72. The ADM2 source metadata labels its canonical role “Districts”, declares 999 units, and identifies ODbL 1.0 plus OpenStreetMap attribution; the retained GeoJSON has 973 features, a difference of 26. The ADM1 comparison is 81 provinces, with CC BY-SA 2.0 and OSM attribution. The report resolves every scoped source ID, records exact source and baseline byte hashes, Atlas names/IDs/declared parents, geometries, source-vintage metadata, coverage diagnostics, component counts, national repeated-name findings, and inherited screening flags.

The issue #72 source archive also contains a current HGM boundary product. Its described product is indicative/display material and not official; it is current-vintage, so it cannot settle the 2021-claimed boundaries. It is not used to certify any row. The packet does not duplicate the archived sources; source receipt records point to their exact retained paths and hashes.

TurkStat's 2021 ABPRS results explain the 31 December 2021 reference date and that administrative dependencies and legal/name changes are reflected from Ministry administrative records. The 2021 national count convention reports 922 districts with a footnote excluding province centers/central districts. These official materials provide temporal/count context, not the exact 229-unit roster, immediate-parent crosswalk, boundary geometries, or completeness proof. Law No. 5442 supports the province-to-district administrative hierarchy and says administrative changes follow law; it does not furnish a row crosswalk. Current Interior Ministry and HGM materials cannot be projected back to 2021 without a dated legal history.

Raw official PDFs/pages were not redistributed because reuse terms were not stated or verified. `source-receipts.json` records the retrieval URLs, dates, exact hashes where captured, limits, and restoration instructions. Re-fetch from the exact URL, inspect current version and terms, and verify the stated whole-file hash before reuse. A hash recorded from an earlier packet is a receipt for that earlier retrieval, not proof that a live URL remains unchanged.

## Findings and engineering handoffs

- All 229 Atlas IDs resolve to unique features in the pinned 973-feature source; all names exactly match and declared parents are inside the 23 complete issue province scopes.
- All 229 source polygons overlap their declared province's 2021-referenced ADM1 feature by at least 95%, and all declared province names match the top spatial overlap. This is a same-release spatial screen, not independent parent evidence.
- One subject has Atlas/source IoU below 0.90 (minimum 0.84899241); one source multipart footprint is represented as a singlepart Atlas footprint. Two scoped subjects inherit multipart flags and four inherit weak-source-parent-match flags. These are precise candidates for official row/boundary investigation, not yet correction findings.
- Fifteen scoped source names include a `merkez` marker; fourteen have a remainder/centre marker. Eight names repeat elsewhere nationally; none collide within this batch. These require checking against an official roster to distinguish central districts, duplicates, and label conventions.
- The 973-versus-999 source feature discrepancy remains unexplained. TurkStat's 922 count cannot resolve the discrepancy arithmetically.
- Engineering handoff: obtain a 2021-12-31 official district roster with stable IDs, names, province parent, central-district conventions, and lawful boundary or crosswalk provenance; reconcile it against the 973 source features and 999 metadata declaration. Use that before proposing any Atlas correction. Resolve the one low-IoU and one multipart/singlepart candidate first, and investigate every `merkez`/remainder label and inherited parent/multipart flag. Preserve island/coastal, enclaves, and boundary-granularity review where the authoritative evidence distinguishes them.

All rows are `insufficient-evidence`. No regional interior approval, correction, production data change, publication, or import authorization is claimed.
