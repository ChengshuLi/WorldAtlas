# Full-shape offline integration verification

Refs #971. This is the final bounded verification part of the investigation, not an installed repair. The candidate remains geographically unapproved.

The pinned existing regression detector compares the two proposed shapes against every current location. It finds no lost coverage or geometry errors, but preserves new positive overlap fragments between Saravan and Panjgur. There is no area threshold or waiver. The full findings retain before/after geometry, exact coordinates and source-shape areas.

The application verification uses every current world-bounds-selected neighbor intersecting the full changed-shape rectangle plus a cell halo. It preserves original global integer owner indices and checks stored bounds using the exact application projection. Every rectangle cell is compared through the actual rasterizer, ownership compiler, packing, byte-shuffle/gzip roundtrip, packed sampling and picking. Independent single-location masks count overlaps before deterministic priority can hide them. Run-length change records retain every changed cell, including outside-component and previously owned cells. The component mask follows the application's half-open even-odd rule; it is not strict GEOS containment.

The resulting pixel behavior is encouraging, but it does not resolve the candidate's exact geographic overlay residuals, projected invalidity, source authority/crosswalk/date or physical-water uncertainties. It does not compare reconstructed baseline ownership with the original encoded canonical partitions. Original encoded-grid comparison needs a separate bounded packet: including those partitions together with all current original world shapes exceeds the existing whole-file evidence budget. No evidence limit is raised or dataset omitted from the full-world check to bypass that bound.

All inputs are ordinary whole-file pinned Git blobs at the recorded baseline. Results name their actual evaluation commits. Original before shapes, IDs, parent properties, historical claims, release pins, all earlier sources/candidates and other workers' packets remain unchanged. Original OpenStreetMap/geoBoundaries source attribution and limits are inherited from PRs #985/#987. The candidate's old metadata remains inspection-only; installation requires explicit mixed-source provenance.

## Reproduction and controls

Use Python 3.12 with the committed pinned NumPy/Shapely/pyproj requirements and Node 24. Restore the evaluation commits from this PR head. Exact registry/staged descriptors and commands are recorded in the evidence manifest. All outputs use fresh filenames/directories; no browser, provider, live database or deployment connection is needed. Two complete geometry-stage reproductions and two complete application compilations must match their respective retained reports byte-for-byte.

`controls.mjs` uses a known two-cell stripe at the actual integer grid width with high global owner IDs, detects overlap independently of picking priority and rejects wrong widths, stale bounds, incomplete neighbors and oversized domains. The existing world-regression controls cover lost coverage, new/tiny overlap, invalid inputs and unchanged geometry; shared scientific controls preserve method/immutability checks. Actual CLI wrong-pin/overwrite rejections are recorded separately.

## Repair remains open

The next correction must retain a consistent shared edge through geographic overlay and projection, pass the full-world regression without hiding positive fragments, prove original encoded-baseline parity, and preserve every source/identity/history context. Then rebuild and revalidate derived products, grid, immutable releases, affected certificates and content scopes. PR #987's integration plan retains these obligations. Publishing remains deferred by user instruction. Positive pixel behavior cannot authorize a core installation or close a still-unresolved repair.
