# Angola–DRC shared-seam source and water follow-up

This source-only packet covers all ten frozen candidate components and all five contacts in issue #1243. It preserves each candidate and contact geometry, source bindings, original detector fragments, earlier JRC Global Surface Water assessment, and complete additional source bytes. It does not authorize a geometry change or determine the legal boundary, water status of a whole component, or cause.

## Results

`outputs/assessment-v1.json` reports pixel-centre class counts from the complete ESA WorldCover 2020 v100 and 2021 v200 source tiles, one selected native Sentinel-2 L2A Scene Classification Layer (SCL) grid per component, prior 2018 and 2019 JRC GSW evidence, and literal intersections with the latitudes printed in the 1894 Gazette. It gives every component a reproduced selection record tied to its saved Earth Search first-page snapshot. The producer confirms the chosen item is the first cloud-sorted result whose item geometry covers the component. Search snapshots return at most 50 items while `numberMatched` is larger, so selection is only verified within the preserved first page and is not claimed to be globally lowest-cloud.

The WorldCover class-80 permanent-water counts, by frozen component order, are 0, 63, 0, 0, 0, 0, 0, 0, 0, 0 in 2020 and 0, 593, 0, 0, 0, 0, 0, 0, 27, 0 in 2021. Class-90 herbaceous-wetland counts are preserved separately in the machine-readable output. The v100 and v200 algorithm versions differ; the year-to-year differences are not treated as land-cover changes.

The SCL grids contain one class-6 (water) pixel centre in component 9 and none in the other nine. Each is a single-scene, 20 m product label on a different acquisition date. Unknown, cloud, shadow, and unclassified cells remain visible in the output. These counts are candidate-scale evidence, not complete-footprint water classifications.

Pixel inclusion uses strict geometry membership at native pixel centres, evaluated with Shapely `contains_xy`. Candidate windows enclose the geometry bounds using floor/ceil before clipping to the raster. The frozen controls also compare a small edge-window case against an independent direct oracle that constructs each native centre as a point and evaluates `geometry.contains(point)`.

The 1894 Gazette ratifies the 26 June 1893 Lunda tracing, effective 31 March 1894, and names rivers and coordinate references. It states that five commission minutes contain the detailed approved limits. The Gazette scan does not include those minutes or their attached maps. Literal horizontal-coordinate intersections are therefore retained only as screens; they do not locate the finite river-bounded treaty segments or establish legal applicability.

The official archival inventory identifies a targeted source lead: Archives du Ministère des Colonies, AE1, file 331, “Lunda — tracing the boundary under the 25 May 1891 convention.” The inventory describes correspondence, reports, instructions, five original 1892–93 commission procès-verbaux, seven sketches, charts, and a general Lunda boundary map; it says the minutes are annexed to special letter 209 of 7 July 1893. The Belgian Archives Cartothèque catalog also lists a copy of the Lunda boundary map annexed to the declaration signed 24 March 1894 (`DEL.L-C.3A+B`). The inventory and Cartothèque are locators; these source records and map images have not yet been retrieved.

All ten whole-component water statuses and causal classifications remain `unknown`. All five complete neighboring contact geometries have explicit rows with source-feature bindings, source vintages, feature/geometry hashes, and unresolved water/boundary-authority status. They are retained as context; no new contact-level water assessment is made and no contact is interpreted as proof of a legal boundary or jurisdictional relationship.

## Reproduction and byte custody

`inputs/source-pins.json` records ordinary-byte sizes and SHA-256 hashes for the preserved source files and baseline inputs. `inputs/freeze-v1.json` records the superseded original run; `inputs/freeze-v2.json` records the first corrected execution, and `inputs/freeze-v3.json` freezes the final strict pixel-centre window method and its direct-centre control. `run_twice.py` verifies frozen bytes before and after each full producer execution, compares the outputs byte-for-byte, and writes `outputs/reproduction-receipt.json`. The superseded receipts and unsuccessful invocation are retained in `outputs/superseded/` and `outputs/execution-history.json`.

The recorded final pair of runs produced identical output bytes: see `outputs/reproduction-receipt.json` for the final byte count and SHA-256. The controls include a tiny edge-window case checked against directly constructed native pixel-centre points. The complete WorldCover tiles are pinned in `inputs/source-pins.json` and `sources/worldcover/retrieval.json`. To restore them from the official immutable object URLs and then reproduce, use Python 3.12 with rasterio, NumPy, Shapely, pyproj, and affine installed:

```sh
python restore_worldcover.py
PYTHONPATH="$PWD/.evidence-venv/lib/python3.12/site-packages" /Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12 research/geography/gap-source-angola-drc-boundary-water-followup-20261007/run_twice.py
```

The producer checks all frozen source pins, roster membership, raster CRS and coverage, and that unknown classifications remain unchanged. No snapping, buffering, repair, or ownership inference is used.

## Sources and terms

- ESA WorldCover 2020 v100 and 2021 v200 COGs are preserved whole under `sources/worldcover/`. ESA specifies CC BY 4.0 and the attribution in `sources/worldcover/retrieval.json`. Product versions and official references are listed there.
- Native Sentinel-2 SCL JP2s, STAC search results, item metadata, AWS listings, and retrieval receipts are under `sources/sentinel-2/` and `sources/earth-search/`. The source note records the Earth Search `proprietary` metadata versus the Copernicus legal notice for original Sentinel data. Attribution is recorded in the receipt; SCL remains a product label.
- The 1894 Gazette scan and retrieval receipt are under `sources/official-belgian-gazette/` in the research checkout; its complete ordinary-byte hash and retrieval facts are also retained in the source pin receipt. Its file-specific reuse rights are unresolved; no license or public-domain status is asserted.
- The archival inventory lead is cited at <https://www.arch.be/docs/invent/archives-africaines/AE1.pdf>, pages 40–41. The Cartothèque catalog entry is at <https://www.arch.be/docs/invent/archives-africaines/Cartotheque.pdf>, catalog entry `DEL.L-C.3A+B`.

## Preserved earlier work

The `outputs/` directory also includes the exact baseline component assessment, fragment-contact overlays, geometry overlays, and 2018/2019 physical-water and authority assessment. They remain separate from the new product observations. Original fragment and source binding bytes are in `inputs/`.
