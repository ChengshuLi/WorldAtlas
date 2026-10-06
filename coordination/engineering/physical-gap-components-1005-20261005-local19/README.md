# Before-water connected components and original crosswalk, #1005 part 2

This stage reads complete immutable products from the merged part 1 audit and the original water-screened audit/component inventory. It does not rewrite their source data or interpret a gap as political affiliation. Every old/new fragment and component has a ledger entry. Original IDs and full-feature bindings survive; new components use a separate `physical-component:` namespace.

Exact coordinate equality, equal point sets, positive-area overlap, positive-length contact, point-only contact and failed/unknown overlays remain distinct. The crosswalk retains complete observed intersections and every nonempty difference atom, including numerical lines/points. There is no area cutoff, snapping, buffering, simplification, MakeValid or nearest-owner fill. Dateline comparisons shift copies by exactly 360 degrees and record the shift, preserving original input coordinates. Original five unmeasured shapes and old blocked domains must remain explicit.

Commit exact source bytes before any generation. Use Node 24 and Python with the existing pinned NumPy/Shapely/pyproj versions. Controls:

```sh
node --test test/physical-gap-crosswalk.test.mjs test/geographic-components.test.mjs
```

Whole-world generation (run twice into distinct new owned vintages):

```sh
python3 scripts/build-physical-gap-components.py \
  --commit c603befd3aaf4da90d59b12378e1e0739331efba \
  --output coordination/engineering/physical-gap-components-1005-20261005-local19/components-v1
```

The exact original/native input subsets must agree between the earlier and new audits; all original complete bundles and full membership bindings are checked. All new point/line/clipping remnants remain pinned in their complete original part 1 bundles. The outputs must be compared by actual whole-file bytes and all report fields except the new output-vintage prefix. No worldwide completion/reproducibility result is claimed until both runs finish and their complete products pass comparison.

Part 3 global priorities/source investigation partitions remain required. This diagnostic stage cannot approve geography, factual water, ownership, deployment or a default grid switch. Confirmed repairs and subsequent release/content/delivery checks remain the broader goal.
