# V7 direct rebuild status

The target is raw geographic sources plus versioned Neon decisions to V7. A V2 physical land/water mask may be an intermediate or validation reference, but is not required; a continent-labeled V2 grid is not an input or product. Historical grids are validation references only. The user accepted the observed 674-cell physical-mask difference. SeaVoX v19 feature 24063 is selected for the Gulf of Carpentaria; Cenderawasih is not selected as a named continent sea.

This checkout remains a **research candidate, not a complete or publishable direct build**. The captured Neon research snapshot has no land affiliations, only partial mask-bound witness rules, and no accepted decision or entity revision. It also lacks a complete, reviewed coast/overlap policy and an approved shared-basin shoreline metric. The closed-water step, independent source-coverage checks, complete global run, attribution and UI build are still needed. Do not deploy or claim geographic equivalence from the synthetic tests.

## Available stages

- `../v7-raw-mask/DIRECT.md` describes the raw land and Overture water stages, optional validation, and manifest-driven physical builder. A full reference-free composition and the raw OSM land rerun each matched the saved candidate bit for bit. The water union of 32 saved shard masks also matched; only one shard has been independently rerun with the portable water rasterizer so far. The candidate source selection itself requires review.
- `../v7-decision-export/draft/` exports a read-only, distinctly labeled draft evidence snapshot. It cannot establish authorization or source-byte authenticity. The accepted-build exporter has a separate trust and locking workflow.
- `../v7-land/direct-neon-land/` compiles pinned physical components and explicit source-based Neon affiliations into land codes without a prior continent grid. It verifies component connectivity and fails on gaps and overlaps. A selected-rule diagnostic resolved 51 of 457,893 components; the remaining 457,842 are unassigned, so the compiler cannot yet produce global land assignments.
- `extract_seavox_feature.py` and `build_seavox_basin.py` build selected direct basin masks. Shared basins use a draft-only WGS84 ellipsoidal center-to-center geodesic method with explicit tie rules; the spherical-edge method is retired. `verify_basin_coverage.py` independently checks raster-to-span coverage, not polygon semantics. The Gulf direct run contained 3,582,504 cells and 6,150 spans; an independent raster-to-span check matched. The earlier selected GeoJSON mask differed by 13 cells, and source selection remains a review matter.
- `build_prefill_plan.py` binds land, physical, source, decision and layer hashes and checks declared precedence. `build_prefill.py` creates prefill with residual water code 0. Its historical V6-land path remains for replay only; the direct research path binds the decision-derived land report and does not read V2/V6 labels. Shared methods use the WGS84 ellipsoidal center-to-center geodesic metric. Layer completeness is still a generator assertion.
- `../v7-recovery/ocean/` contains the fresh ocean fill candidate; unseeded components are reported, not silently assigned. `compose_direct.py` composes a direct prefill and bound water layers without a prior continent grid, refuses unassigned cells and outputs a research-only audit. No complete direct global run has been performed. The older `compose_full_water_grid.py` is historical replay and still requires prior V2/V6 grids.

All snapshot-consuming builders remain unverified research tools and require explicit flags. A file's claimed revision status and hash do not authenticate review. Before a release, complete and review the missing Neon decisions and source lineage, independently validate all geometries and layer coverage, pin software and inputs, run global connectivity and physical/land checks, then verify the final map, attribution and UI. Keep raw inputs and generated maps in R2 and versioned decisions in Neon; no live publication is authorized by these scripts.

## Preserved code needed to investigate the Iceland v24 candidate

The Iceland v24 research candidate was made by changing an existing ocean
partition, not by running every stage afresh. Its final rows SHA-256 is
`103a47a8a70676a9d403155717c95a12ecbd6fd51cdd9c35679e9f42c7a7199f` and
runs SHA-256 is `cf14bcaf6f06a305b82205dc535584105e221bb79fc185a8f3371c41d61b7f78`.
Its split-ocean proof reused 442 previously classified unseeded components.
It is not evidence of a full source-to-map rerun.

Nine exact earlier code files identified by the provisional land report, stage2
configuration, and closed-water manifest are preserved in `../v7-recovery/v24-source-pins/`.
Their hashes and report roles are in `pins.json`. They are provenance copies,
not standalone entrypoints: imports, source and decision snapshots, manifests,
and runtime inputs must also be reconstructed and validated. These pins do not
establish completeness or permission to promote the candidate.

The 2026-11-07 custody check in `r2-custody-20261107.json` records fresh
R2 reads of 104 sources referenced by the retained water snapshot and land
polygon-custody report, plus the physical OSM land archive and its five run
sidecars. All matched the checked size and SHA-256 pins. The 32 Overture
shards are verified separately by the physical rerun. This scoped check does
not enumerate every source or decision and is not a geographic review.
