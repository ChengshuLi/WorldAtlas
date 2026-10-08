# Lithuania–Latvia source fitness: complete 16-component family

Issue #1426 requests a source-only assessment of all 16 components and all three contact features. This packet retains the full family and makes no geography edit, import, legal boundary determination, or physical classification.

## Findings

Six administrative comparators were parsed as complete country products and compared in EPSG:3035. The two Atlas-consumed simplified products each had positive-area overlap with 12 of 16 components; the same-commit full-resolution Lithuania product, current official Lithuania INSPIRE product, and Latvia's official 2021 and 2026 products each overlapped 15 of 16. These are source-relative footprint counts, not physical classifications. Exact areas, coverage fractions, outside-union areas, overlapping source-feature records and all three contact comparisons are in the paired result files and evidence metric ledger.

The joins retain 16/16 component IDs and 3/3 contacts, with exact feature/geometry hashes, routing rows and physical-comparison row hashes. Each member row reports source-by-source supported and comparator-absent results, what physical evidence is absent, unresolved questions, the exact missing independent fact and its bounded next action. The accepted complete11/complete12 runs have different whole-result bytes because their input receipts name separate assembly vintages. After excluding only the run-specific `phase_input_pins` object, their canonical scientific payloads are byte-identical; the SHA-256 is recorded in reproducibility.json. The overlap differences describe administrative source footprints only; they do not establish dry land, inland water, shoreline position, a legal boundary, authority, historical applicability or original cause.

The exact baseline subject inventory maps all 16 component features to their eight authenticated custody payloads and all three contact features to `data/geography/part-13.json` at baseline `69a5f97161c36611fc974b626c9666fdf2941a31` (whole-file SHA-256 `90b032861ecae8a4df9a8b5386eccfb20a7243c264dbf79994b54c5297e6f6c1`). The three contacts resolve uniquely by their exact `properties.id` values. This retains full containing FeatureCollection evidence and does not change contact scope.

## Sources and limits

The Atlas-consumed simplified geoBoundaries products represent Lithuania ADM2 (2017) and Latvia ADM1 (2021). A same-commit full-resolution Lithuania product is a sensitivity comparator. The official Lithuania INSPIRE Administrative Units are current 2026 data; no full official historical 2017 Lithuania product was found. Latvia's official products cover 2021 and 2026; broader legal applicability is not inferred. Metadata, exact byte pins, attribution/license texts, retrieval records and decoded-GML validation are retained under inputs.

A Latvia GRPK SHP retrieval was abandoned at 787 MB; partial bytes were discarded and not consumed. The assessment obtains no date-stamped, high-resolution physical land/water evidence or tile observation dates. Physical status, source authority, source lineage and any correction remain unresolved.

## Reproduction and controls

Run the two source-fit commands recorded in evidence-quality.json with the declared Python environment. The accepted GML archive controls use a deliberately incorrect expected digest and exercise the production rejection path. Final paired stage outputs are in vintages/*-complete1 and vintages/*-complete2; the accepted GML archive-validation pair is in vintages/gml-validation-complete5 and vintages/gml-validation-complete6, and the accepted source-fit pair is in vintages/source-fit-complete11 and vintages/source-fit-complete12. The positive control is a real component/source overlap; the negative control swaps the GML coordinate axis order and produces no overlap. Prior provisional or failed attempts are summarized in execution-ledger.json. Superseded source-fit outputs and the historical GML validation pair with a vacuous wrong-digest claim are retained and explicitly labeled; the redundant double-prefixed source-fit attempt was removed. No superseded attempt is used for acceptance.

## Next evidence needed

Obtain lawful, date-stamped, high-resolution authoritative land/water evidence covering the whole family, with per-tile observation dates and positional accuracy. Reassess all 16 together before any geometry processing. This packet does not satisfy the remaining physical classification acceptance and does not close issue #1426.
