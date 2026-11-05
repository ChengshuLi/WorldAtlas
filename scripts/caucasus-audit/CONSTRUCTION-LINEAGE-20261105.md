# Caucasus boundary construction-lineage audit

Read-only catalog inspection on 2026-11-05, branch `continent-review-v1`. This distinguishes exact archived source bytes from proof that those bytes produced the selected geometry. It does not accept geography or change any source or boundary.

## Selected input and stage-2 handoff

`atlas.decision_mainland_boundaries` records revision `v2-land-mainland-boundary-draft-1`, boundary `caucasus_blacksea_anapa_to_caspian`, `stored_linestring_v1`, CRS84, `selected_for_research`, geometry digest `9f4ae3bc778ebbcd0258a19868acf0fa655763f5e849361196160fb4289c0d52` under `binary64-sorted-compact-geojson-v1`. The revision is draft. It is one stored LineString, not four independently proven constructions. `atlas.decision_mainland_region_segments` references its full stored index range 0–2292 with `reverse=true` for `europe_mainland_region_v1`. This describes a research input reference, not a demonstration that any current stage-2 run executed it or that a historical grid used it.

The boundary record itself states `lineage_status: incomplete` and names sourcecut digest `b0401ee291aff8b6b5fdaabb4501e7321cbf6c8e9eba9be19cdca6e7ab846382`. A lookup for that digest, the selected geometry digest and the recorded proposal digest `fa14b5612db119285cf03820fc9dff932d0d63603cdc81e70da4128f85f73105` in `atlas.source_assets.sha256` returned no rows; those hashes may use different serialization or refer to artifacts outside this table. A lookup of `atlas.source_builds` by the exact decision revision returned no rows. These narrow negative queries do not prove that artifacts or earlier builds never existed.

## Exact R2 bytes verified, not confirmed construction

| Raw object | SHA-256 | Catalog relationship and limit |
|---|---|---|
| `sources/hydrosheds/hydrobasins/standard/europe/level-12/v1c/hybas_eu_lev12_v1c-21797d53e079.zip` | `21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03` | Research comparison, not proof this exact ZIP was used to construct the line. |
| `sources/trubetskoy/7aa03ec54a262e8e97e8273f60621c530ec4e998/asia_europe_border.geojson` | `c9d56b1291522573fbb8b0baa1a39cecfd192eda8f5e51650b24f562d13688e6` | Supporting geographic evidence, not complete construction lineage. |

Both objects were downloaded from R2 and their byte SHA-256 matched these catalog values on 2026-11-05. JAXA, Copernicus, OSM and SRTM items linked in the boundary record are research and quality-screening inputs; their existence does not establish that they produced the selected geometry.

## Four analytical sections

1. **Anapa:** prior 42-position comparison found a 4,037.35 m selected edge within 1 cm projected tolerance of shared HydroBASINS polygons 2120554610 and 2120005980. The selected first point lies on a separately retrieved OSM coast segment to numerical precision. These are strong source-relative correspondences, not recovered original basin IDs, transformation code, exact historical coastline bytes, or a coastline-clipping recipe. The currently available OSM land-shapefile inventory has only one .shp hash and lacks companion files and source snapshot.
2. **Western Black Sea/Azov:** previous 500 m projected comparisons found broad agreement with HydroBASINS edges; the input's exact original bytes and basin selection, line extraction, orientation, simplification and joins remain unproven. Sampling and any projected tolerance are historical comparative results, not a hash-exact reconstruction.
3. **Central Caucasus:** same HydroBASINS correspondence and same missing construction steps. Surface-model and river-network checks are later research, not demonstrated source inputs.
4. **Eastern Caucasus:** selected vertices 1894–2290, inclusive, match 397 consecutive vertices of the author source after binary64 parsing. The catalog notes 71 decimal-exact and 326 decimal differences of at most 4e-15 degrees. This confirms coordinate correspondence to the archived file, not author-file import history, the source's complete extent, the transition joins, or the exact Caspian shoreline clip.

## Concrete next steps and limits

Locate the original boundary extraction script or notebook, its sourcecut artifact and manifest, exact historical HydroBASINS and shoreline bytes including shapefile sidecars, basin identifiers, transformations and clipping rules; establish the record's sourcecut/proposal hash serialization. Reconstruct into a separate output, compare every coordinate and geometry digest, and verify all joins and stage-2 source inputs against a pinned decision export and physical-grid digest. If those artifacts are unavailable, explicitly preserve the boundary as a recovered research geometry with incomplete source construction lineage; do not promote the comparison files to proven inputs. Geographic watershed correctness and historical V2/V7 raster equivalence are separate checks. No current unresolved-cell total follows from these provenance checks.
