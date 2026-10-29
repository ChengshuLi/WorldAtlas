# Data strategy

## Selected decisions

Use a flat equirectangular (Plate Carrée) map and a fixed, time-agnostic hierarchy: location → province → area → region → subcontinent → continent. Use recent reliable administrative footprints, older where needed, and record source dates. No common reference date is required. Freeze footprints through history; only political control changes.

Complete geography before researching 20+ historical attributes per location. Begin with six land continents, excluding Antarctica, and ocean groups. The user approves each top-down partition before the next-level workers subdivide it (17 subcontinents is illustrative). Each subdivision must fully cover its parent without gaps, overlaps, or geometry outside it; check lower-level administrative units fit before approval. Detailed boundaries, datasets, and subdivision sizes are handled during this research; flag important inhabited-island exceptions at the first continent review.

Every included cell belongs to one six-level location: land or non-river water. Land-continent groups include nearby seas, island waters, and lakes; Pacific, Atlantic, Indian, and Arctic groups cover remaining waters. Oceania may include broad remote-island waters; large seas may split; Chukchi is Arctic. Non-river waters are named selectable locations. River-data overlays are selectable lines, cross locations without changing ownership, and retain minimum screen width. Small lakes/islands may disappear; no lake overlay.

For mixed cells, choose land or water by total covered area (land wins exact ties), then the location with greatest overlap within the winning type; stable location IDs break location ties. Use a 16,384 × 8,192 full-world reference grid, equirectangular step 0.02197265625°, crop Antarctica at nominal 60°S, and retain 90°N. Row alignment yields 16,384 × 6,827 cells (111,853,568), with southern edge 60.00732421875°S. Store one canonical, losslessly compressed grid without tiling initially, using unsigned 16-bit location IDs; reserve 0 during construction, leaving 65,535 usable IDs, and widen to 32-bit if needed. Every published cell is assigned. Compression size is unmeasured. Investigate source gaps/overlaps; state approximation rules and consequences.

Political affiliation is effective control: assign one entity per location/date by greatest controlled area when evidence supports it; cells inherit it. No claims records. Joint administration uses a documented lead or, with comparable evidence, greater responsibility/resources. Stable entity IDs break remaining ties as a model rule, not historical fact. Never invent a controller.

Population covers all fixed-footprint residents, including rural areas and villages. Encourage defensible estimates; record basis, show provenance on demand, and leave unknown only when no estimate is justified. Do not present estimates as observed counts or double-count sources. All land remains assigned; sparse areas get proportionate research, no impassable class. Zero requires evidence of no inhabitants; resident-only attributes are inapplicable only when genuinely uninhabited. Unknown means insufficient evidence. Sparse records, absent permanent settlements, or present population alone do not prove uninhabited status; consider seasonal/historical habitation.

## Storage and delivery

1. **Original evidence:** R2 stores source files; Neon tracks references, dates, and checksums.
2. **Editable research:** Neon/PostGIS stores researched boundaries and source-backed drafts.
3. **Generated app data:** code derives hierarchy, affiliation, population, and attribute tables in Neon plus the canonical cell-location grid in R2. No manual copies or patches.

Workers submit parent-bounded subdivision drafts, source references, and a base revision through one geography-apply workflow. Drafts can be saved for correction. Validate IDs, hierarchy, and complete affected-parent coverage (no gaps, overlaps, or geometry outside the parent); reject stale/conflicting edits against affected records and dependent parent boundaries, allowing unrelated areas to proceed concurrently. Intermediate stages need not wait for worldwide completion. Only validated, user-approved proposal versions feed next-level work or publication.

Review proposals on a visual map: parent outline, labeled/color-coded children, zoom/pan, selectable sources and rationale, flagged issues/inhabited-island exceptions, and shape/cell-resolution previews where available—not vertex lists. The user approves or requests corrections to a specific version.

Derive generated data from approved research. Serialize grid publication: upload a versioned R2 grid, recheck dependent revisions, then transactionally commit matching Neon results and grid reference. Draft saving is separate from publication; failures leave the prior published version intact, and the app reads matching revisions. No extra publisher, queue, or handoff. GitHub holds code, schemas, docs, and task issues; one workflow owner carries research through delivery, with future geography work parallelized across 10–20+ Luna workers. No research-only PR; the user merges code/schema/doc PRs.

## Deferred to the next PR

Per-location attribute definitions, including how to handle attributes that are not per-location, time/date conventions, and schemas are deferred to the next PR.
