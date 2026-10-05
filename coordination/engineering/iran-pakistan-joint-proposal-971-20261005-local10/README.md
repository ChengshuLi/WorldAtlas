# Saravan–Panjgur bilateral correction proposal

Refs #971. This packet stages a correction for the retained Iran–Pakistan example. It changes no core geography or live database and does not complete the issue.

The two retained current OpenStreetMap county responses contain identical shared original ways and nodes. The component-intersecting ways also occur as outer members of both counties and both national relations in the separately retained parent responses. Their assembled union covers the complete retained component. This is stronger evidence than combining a newer Pakistan polygon with an older Iran polygon. It does not establish official authority, a historical observation date or water classification.

`candidate-v3/report.json` keeps the complete before features, candidate features, original properties and component identity, member versions, source-parent links, all added/lost/outside/overlap geometries and all nonpolygon union remnants. New areal coverage is clipped to the original diagnostic component and the named current source; existing locations are not replaced wholesale. Identity and parent properties are preserved for inspection. Installing this candidate requires new mixed-source provenance; its unchanged old properties must not certify its new coordinates.

## Why installation remains unapproved

Both candidate polygons are valid in geographic coordinates. The exact combined `covers` predicate is false even though the retained component-minus-candidate overlay is empty. A tiny positive neighbor overlap and a positive Pakistan outside-source residual remain in the report. Zero-area line remnants are kept separately from polygon footprints, including the complete original union. No snapping, buffer, MakeValid, area cutoff or nearest-location assignment hides these results. `candidate-v2/` and the earlier failed geometry-type result remain immutable diagnostics.

The cell expectation check refuses to infer coverage from invalid projected polygons. The component is valid after straight-vertex Mercator projection, but both baseline polygons and the Pakistan candidate are invalid in that coordinate system. Consequently its status is `unknown-invalid-projected-geometry`, its counts are null, and it makes no compiled-grid claim. Projection validity must be resolved through a reviewed representation method before scan conversion. A geographic-coordinate validity result alone is insufficient.

Original OpenStreetMap sources are ODbL 1.0, attributed to OpenStreetMap and contributors. Source bytes and separate retrieval receipts are retained unchanged. Every assembled coordinate's member version/date is recorded; a relation edit timestamp does not date its entire geometry. The shared border's LSIB4b tag is not byte-verified equivalence to an official LSIB edition. Source authority, the stable county crosswalk, historical interpretation and physical-water/registration uncertainty remain unapproved. The earlier water pilot's date, raw-code interpretation and registration limits remain inherited.

## Reproduce offline

Use the committed requirements with Python 3.12. Fetch `refs/pull/987/head` to restore evaluation bootstrap `e8fa7a89e5e12236a3b787718c0e1e4b49833991` if needed. `inputs.json` names the immutable baseline and every full source file. All required originals are committed, including the prior Panjgur response; no API, browser or provider connection is needed. Use a fresh output filename. The exact command and registry descriptor are recorded in `evidence-quality.json`.

Run `python coordination/engineering/iran-pakistan-joint-proposal-971-20261005-local10/controls.py` and `python test/evidence-geography.py`. Controls include contradictory/incomplete source partitions, holes, tiny additions, changed shared node/way versions, separation preserving all lower-dimensional remnants, known cell-centre coverage and invalid-projection refusal. Generator receipts record actual wrong-registry, wrong-source and overwrite rejections and two byte-identical full reproductions.

## Integration work after this proposal

1. Independently assess source authority/date, exact stable subject crosswalk and physical-water evidence. Do not assign political affiliation or transfer historical facts from this geometry comparison.
2. Resolve exact geographic overlay residuals and projected validity with a documented representation method and adversarial controls. Preserve originals and every rejected candidate; do not waive residuals by area threshold. Require reproducible coverage, containment, no lost existing coverage and no new contradictory overlap.
3. Re-read current main and compare every affected input hash. Run a full current-world neighbor/collision scan covering both changed shapes, including shared borders and third-party contacts. The prior component contact scan is context, not a fresh candidate-world clearance.
4. Install only independently approved joint footprints with explicit mixed-source provenance, stable IDs/parents, a reviewed crosswalk and immutable before/after release evidence. Preserve original source vintages, hierarchy records and all historical claim footprint contexts.
5. Rebuild and validate affected prepared geography, ownership/environment derivations and the canonical integer grid. Audit all touched rows/cells, including boundary and outside-centre cells; compare decoded picking with drawing and expose uncovered/multiple states. The shape expectation in this packet cannot substitute for that check.
6. Revalidate release, region certificates and content import scopes against the new footprint pins. Existing regional research packets #121/#115 are preserved and do not become approved through this proposal.
7. Merge through the normal source/geometry/code review and queue checks. Deployment and live data changes remain deferred under the user's instruction. Issue #971 stays open while repair/integration acceptance is unresolved; #972 and #973 cover Iberia and exhaustive raster-only auditing separately.
