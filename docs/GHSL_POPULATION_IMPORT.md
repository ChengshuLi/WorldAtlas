# GHSL population preparation

This preparation allocates the actual GHSL GHS-POP R2023A 2020 native global raster to the atlas's fixed land footprints. Values are modeled residential population estimates, not exact census counts. The sole supported interval is `[2020, 2021)`. Other years remain unsupported; no interpolation, ancient labels or 2026 carry-forward is introduced. No rank or habitation value is inferred from population.

## Source and license

- [GHSL population product DOI](https://doi.org/10.2905/2FF68A52-5B5B-4A22-8F40-C41DA8332CFE).
- [Actual 2020 native 1 km Mollweide archive](https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/GHS_POP_E2020_GLOBE_R2023A_54009_1000/V1-0/GHS_POP_E2020_GLOBE_R2023A_54009_1000_V1_0.zip), SHA-256 `40ccf52af857a82cd327b882d1ebb901f84363b0e7e6806ccee56b0a85df6d2c`.
- [GHSL citation and license notice](https://human-settlement.emergency.copernicus.eu/GHSLhowToCite.php): CC BY 4.0, with source acknowledgement and the required methodology citation.
- Pesaresi et al., 2024, [Advances on the Global Human Settlement Layer by joint assessment of Earth observation and population survey data](https://doi.org/10.1080/17538947.2024.2390454).

Attribution: European Union / Joint Research Centre; Schiavina, Freire and MacManus. Adapted by WorldAtlas. The original downloadable ZIP, native GeoTIFF and allocation scratch ledger remain in `.cache/ghsl/`, outside deployable assets.

The actual product documentation describes Float64 people counts per native cell, NoData `-200`, ESRI:54009 Mollweide and 1,000 m cells. These are counts, not density: count multiplication by cell area would be incorrect. Epochs through 2020 are modeled estimates; 2025 and 2030 are projections. This milestone prepares 2020 only.

## Conservative land allocation

Each location is unwrapped and split at the antimeridian, then projected with adaptive edge subdivision. Quarter, midpoint and three-quarter curvature probes require a projected chord error below 0.0005 m. This numerical approximation has an independent per-cell conservation check; it does not assert a formal mathematical curvature bound.

Whole interior cells retain their count. A one-cell neighborhood of the rasterized boundary, including a halo beyond each strip, is checked exactly because line rasterization can omit tiny adjacent corners. Every intersecting boundary cell, hole and island is split by exact polygon intersection area in the native equal-area projection. Small pieces are retained even if no cell centre lies inside them. Disjoint polygon clipping partitions accelerate exact intersections and are checked against original polygon area. Processing uses bounded raster strips and a disk-backed allocation ledger.

A value is supported only when the source covers at least 99.9% of that location's applicable land. Otherwise the record's value is `null`, with the measured coverage and partial supported population retained as provenance. NoData is never interpreted as zero. Modeled counts are rounded to whole people for storage and explicitly labeled estimates; rounding does not establish census precision.

Source population outside atlas land, fractional coastal cells, geographic/source gaps and excluded Antarctica remains unassigned. Current fixed territories are a reference framework at the source epoch, not a claim that all their boundaries existed in 2020.

## Publication and schemas

Preparation emits part files while running, but consumers must wait for `data/population-ghsl/index.json`. The manifest is written only after every location has been inspected and both global conservation gates pass. Partial part files without a valid manifest are not publishable.

Before publication, the producer rechecks both the preparation algorithm and the geographic footprint hash. A concurrent geographic edit aborts the run before replacing the manifest; a previous valid export and its immutable parts remain intact. Synthetic regression checks exercise this rejection without expanding historical coverage.

The manifest's `parts` array has objects `{path, records, bytes, sha256, epoch}`. Its `epochs` array carries `{year, valid_from, valid_to, status, receipt, locations, supported_values}`. `footprints_sha256` pins stable location IDs and geometry, independently of renamed or reparented geographic groups.

Each gzip part contains hosted attribute rows: `{id, location_id, attribute: 'population', value: integer|null, category_id: null, source_id, valid_from, valid_to, method: 'estimate', status: 'estimate'|'unknown', is_example: 0, metadata}`. The source ID is `ghsl:population:R2023A:E2020`. Metadata records licensing, source hashes, coverage, source epoch, allocation method, estimate precision and unsupported reasons. The modeled-source database constraint requires `method: 'estimate'`;  `equal-area-cell-overlap` describes the detailed method within metadata.

`epoch-2020-receipt.json.gz` includes per-location land/source area and coverage, native grid metadata, source and algorithm hashes, source total population, allocated ledger total, independently summed per-location total, unassigned population, per-reference-owner summaries and numerical conservation results. Global checks reject any cell allocation exceeding `1 + 3e-6`, any overallocation of source population and a ledger/summary difference larger than `max(1 person, source total × 5e-8)`. No manifest is emitted when a gate fails.

Import the full hosted source row before attribute rows. Static, server and persistent consumers must load the same prepared rows and half-open dates. Use independent source intervals in inspectors and identify every supported numeric value as an estimate.

Reproduce after pinning the actual native archive at `.cache/ghsl/2020.zip`: `python scripts/prepare-ghsl-population.py --epoch 2020`. Meaningful algorithm checks: `python scripts/prepare-ghsl-population.py --self-test`, covering full-cell conservation, fractional neighbors, diagonal borders, holes, subcell islands, missing coverage and exact intersection partitions.
