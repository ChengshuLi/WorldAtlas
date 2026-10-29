# Geography data strategy

## Fixed geography

Use a flat equirectangular (Plate Carrée) 2D map with equal longitude/latitude steps and a time-agnostic hierarchy: location → province → area → region → subcontinent → continent. Use reasonably recent reliable administrative sources, older where needed; record source dates, with no common reference year. Freeze chosen footprints across history. Start with six land continents excluding Antarctica plus ocean groups. User approves each top-down subdivision before child work; check lower-level boundaries fit first.

Within map coverage, every land cell belongs to an ordinary location; sparse areas receive proportionate research and may use larger locations without a size limit. Every cell belongs to exactly one land or non-river-water location. Land-continent groups include nearby seas and island-region waters; ocean groups cover remaining waters. Broad waters may be grouped with relevant continents, and large seas may be shared among adjacent groups. Small lakes and islands may disappear at this resolution. Flag inhabited islands too small to resolve at the first continent review and assess whether higher resolution is warranted.

Choose each cell's land/water type by greatest total covered area (land wins an exact tie), then assign the greatest-overlap location within that type; stable location IDs break ties. Investigate source gaps/overlaps and document approximation rules and consequences.

Use equal equirectangular steps of 0.02197265625°. The 16,384 × 8,192 full-world reference grid, cropped at nominal 60°S and retaining 90°N, row-aligns to 16,384 × 6,827 cells (111,853,568), with southern edge 60.00732421875°S. Store one canonical, losslessly compressed grid, initially unpartitioned. Each unsigned 16-bit value is the numeric location ID itself; reserve 0 during construction (65,535 usable IDs), and widen to 32-bit if needed. Every published cell is assigned; compression size is unmeasured.

## Evidence, research, review, and app data

1. **Evidence:** R2 stores original sources of any size; Neon tracks references, dates, and checksums without duplicate copies.
2. **Editable geography:** Neon/PostGIS stores geographic units with stable numeric ID, name, level, parent, and source polygon; locations also have land/water type. Versioned parent proposals retain sources, reasoning, and review status. River records store stable ID, name, line, sources, and linked locations with river access.
3. **Generated geography:** code derives approved hierarchy/names and app tables in Neon, river display/selection data, and the canonical cell-ID grid in R2.

One geography-apply workflow accepts parent-bounded drafts, sources, and a base revision. Incomplete or invalid drafts may be saved for correction, but only valid user-approved versions feed the next level or publication. Validate IDs, hierarchy, and source-geometry usability; investigate source-geometry gaps/overlaps. Validate each proposal against the approved parent map cells: every parent cell is assigned exactly once, with no missing, multiply assigned, or outside cells. Check conflicts only against affected records and relevant parent boundaries so separate areas proceed concurrently; intermediate levels need no worldwide completion.

At every level, rasterize proposals to actual map cells at the chosen resolution, using IDs for that hierarchy level; level previews are transient, with only the final location grid canonical. The user reviews and approves the rendered cell map: show the approved parent-cell boundary and labeled/color-coded child cells, zoom/pan, selectable sources and rationale, and highlighted issues or inhabited-island exceptions. Each child partition must cover the approved parent cells exactly once. Changes to a parent require renewed cell-map approval.

After all locations are finalized, conduct a dedicated river-data and map-review pass before time-dependent attribute research. Rivers are selectable line overlays with names, details, practical hit tolerance, and minimum visible width. Each river links to all nearby locations that have access to it; cell location IDs remain intact beneath the overlay.

Load and reuse the single compressed grid in the app, with local cell picking by ID and pan/zoom redraws. Keep rivers, labels, highlights, and details as separate overlays loaded as needed. Verify desktop/mobile responsiveness during implementation.

One workflow owner carries research through validation and delivery; geography work can be parallelized across separate areas. Serialize shared grid publication: derive from approved geography, upload a versioned R2 grid, recheck relevant revisions, then transactionally commit matching Neon results and grid reference. Draft saving is separate from publication; failed publication leaves the prior version active, and the app reads matching revisions. GitHub holds code, schemas, docs, and task issues; the user merges code/schema/doc PRs.

## Deferred to PR #3

PR #3 covers time-dependent attributes, per-location or otherwise, including political affiliation and population, plus their definitions, date conventions, and schemas. Agreed principles: affiliation records store effective control only, assigning one controller per location/date by greatest controlled area when supported; joint administration uses a documented lead or comparable responsibility/resources; stable IDs provide the final deterministic tie-break. Never invent a controller. Population covers all fixed-footprint residents; encourage labeled estimates with recorded basis and provenance on demand, avoid double-counting, and leave unknown only without a defensible estimate. Zero requires evidence; not-applicable means genuinely inapplicable. Sparse records, absent permanent settlement, or present population alone do not establish uninhabited status; consider historical and seasonal habitation.
