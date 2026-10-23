# Tuvalu TUV45 source-relative disposition proposal

**Status:** prepared proposal; pending independent exact-head review. This packet does not change ownership, certify present-day applicability, repair geometry, or make a legal or sovereignty claim.

## Bounded original contract

This is the original `gb-TUV-ADM1--repair-evaluation` package only: 45 native land cells, 0 inland-water cells, 16 interval segments, three existing owners and three source features. The rows in `tuv45-intervals.json` use half-open x intervals `[x_start,x_end)` and retain the original `(y,x_start,x_end,owner_id,source_feature_index,physical_class)` assignment. They sum to 45 cells exactly. The package queue snapshot records `source_relative_cells=0`. A separate 101-cell TUV source-relative inventory and the Niulakita-specific #615 crosswalk are outside this contract.

## Retained source/contact restoration

The retained source is the geoBoundaries TUV ADM1 collection, with boundary source identified as “OpenStreetMap, Wambacher,” boundary vintage 2017, source-data update 2023-01-19, build date 2023-12-12, and ODbL 1.0. `tuv45-source-crosswalk.json` binds the three native feature indices and owners to exact geoBoundaries `shapeID`, `shapeISO`, and names in the retained GeoJSON. I also intersected every original half-open cell interval against every run in pinned source-candidate block 033, using matching y and x overlap. All 45 cells are covered by 16 intersecting candidate runs; the union is exactly source feature indexes 59796/59797/59798 and owners 43467/43466/43461. No additional candidate source feature or foreign owner appears in this block for these intervals. This establishes completeness of the *candidate-contact set in this pinned block* and identity against the retained 2017 collection; it does not prove current administrative applicability.

The retained citation names Dan Runfola (`danr@wm.edu`) as the geoBoundaries project citation/contact. This is not an identified contact for Wambacher or an individual OSM contributor, and the source files provide no per-feature editor/contact record. The provider/license and contact distinction are preserved explicitly in the JSON evidence.

## Current selected-owner disposition

At main `2b569815a7e37c5797586092688122d9b5d749b0`, the independently rejoined exact interval audit reports base owner 0, selected patch owner 0, and effective owner 0 for all 45 cells. Therefore 0/45 have accepted repair credit; 45/45 remain without an assigned selected owner. This proposal preserves all 45 as unresolved source-applicability exceptions. It does not infer that the 2017 source is currently applicable merely because the feature names and IDs match.

Selection pins and their digest types are recorded in `tuv45-source-crosswalk.json`. In particular, the manifest file SHA-256 and Git blob OID are distinct fields, as are the sidecar file SHA-256 and Git blob OID.

## Bounded limitation and next evidence

The unresolved limitation is current applicability of the three identified source features to the 16 original intervals: available evidence ties each candidate owner/name to a retained 2017 source feature, and the pinned candidate block shows no other candidate contact, but the packet does not establish that the 2017 boundaries remain the applicable current ADM1 representation for these cells. Candidate contact membership does not itself prove an exact geometry overlay or present-day applicability. The related #615 Tuvalu crosswalk treats Nui, Vaitupu and Nukufetau with cartographic source evidence and discusses the revised Falekaupule Act, but it is not coordinate-level proof for these 45 cells; its Niulakita/Niutao scope and warrant evidence cannot be transferred here. Useful next evidence could be a date-stated, compatible current boundary source (with vintage, CRS, scale, lineage and terms) that can be joined to the preserved intervals, or other explicit source documentation resolving those exact locations. No legal-authority criterion or sovereignty conclusion is asserted. Until then all 45 remain unresolved.

The source-relative exception path is compatible with the project’s explicit-geographic-exception framework: it can record a bounded unresolved exception and why the current source evidence is insufficient. That policy does not convert an unresolved candidate into a supported boundary or owner assignment. See `docs/GLOBAL_SEMANTIC_CLOSURE.md` (exceptions require geographic evidence; open means evidence or a documented exception is still missing) and `docs/TOP_DOWN_GEOGRAPHY_WORKFLOW.md` (complete branches require source vintage/license, island completeness, identity migration and explicit exceptions).

## Counts

- Accepted/qualified repair cells: **0**.
- Proposed unresolved exception cells: **45** across **16** original intervals.
- Remaining held/unassigned cells: **45**.
- Added repair credit: **0**.

These counts are scoped only to the original TUV45 package and are pending independent review. See `tuv45-source-crosswalk.json` for retained paths and source pins; the parent task’s conservation check supplied the current selected-owner result and independently reconstructed interval rows.
