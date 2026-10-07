# Angola–DRC shared-seam source and water follow-up

This source-only packet covers all ten frozen candidate components and all five contacts in issue #1243. It preserves each candidate and contact geometry, source bindings, original detector fragments, earlier JRC Global Surface Water assessment, and the native Sentinel SCL source bytes. Full WorldCover COGs and the Gazette scan have separate local-retention limits below. It does not authorize a geometry change or determine the legal boundary, water status of a whole component, or cause.

## Results

`outputs/assessment-v1.json` reports pixel-centre class counts from the complete ESA WorldCover 2020 v100 and 2021 v200 source tiles, one selected native Sentinel-2 L2A Scene Classification Layer (SCL) grid per component, prior 2018 and 2019 JRC GSW evidence, and literal intersections with the latitudes printed in the 1894 Gazette. It gives every component a reproduced selection record tied to its saved Earth Search first-page snapshot. The producer confirms the chosen item is the first cloud-sorted result whose item geometry covers the component. Search snapshots return at most 50 items while `numberMatched` is larger, so selection is only verified within the preserved first page and is not claimed to be globally lowest-cloud.

WorldCover class-80 permanent-water and class-90 herbaceous-wetland counts are retained separately for each component and vintage in the machine-readable output. The v100 and v200 algorithm versions differ; the year-to-year differences are not treated as land-cover changes.

The SCL grids contain one class-6 (water) pixel centre in component 9 and none in the other nine. Each is a single-scene, 20 m product label on a different acquisition date. Unknown, cloud, shadow, and unclassified cells remain visible in the output. These counts are candidate-scale evidence, not complete-footprint water classifications.

Pixel inclusion uses strict geometry membership at native pixel centres, evaluated with Shapely `contains_xy`. Candidate windows enclose the geometry bounds using floor/ceil before clipping to the raster. Pixel coordinates are computed from the original dataset affine and global row/column indices, independent of crop-window offsets. Frozen controls compare a narrow edge-window case against a direct point oracle and detect floating-point drift from window-local affines.

The 1894 Gazette ratifies the 26 June 1893 Lunda tracing, effective 31 March 1894, and names rivers and coordinate references. It states that five commission minutes contain the detailed approved limits. The Gazette scan does not include those minutes or their attached maps. Literal horizontal-coordinate intersections are therefore retained only as screens; they do not locate the finite river-bounded treaty segments or establish legal applicability.

The official archival inventory identifies a targeted source lead: Archives du Ministère des Colonies, AE1, file 331, “Lunda — tracing the boundary under the 25 May 1891 convention.” The inventory describes correspondence, reports, instructions, five original 1892–93 commission procès-verbaux, seven sketches, charts, and a general Lunda boundary map; it says the minutes are annexed to special letter 209 of 7 July 1893. The Belgian Archives Cartothèque catalog also lists a copy of the Lunda boundary map annexed to the declaration signed 24 March 1894 (`DEL.L-C.3A+B`). The inventory and Cartothèque are locators; these source records and map images have not yet been retrieved.

All ten whole-component water statuses and causal classifications remain `unknown`. All five complete neighboring contact geometries have explicit rows with source-feature bindings, source vintages, feature/geometry hashes, and unresolved water/boundary-authority status. They are retained as context; no new contact-level water assessment is made and no contact is interpreted as proof of a legal boundary or jurisdictional relationship.

## Reproduction and byte custody

`inputs/source-pins.json` records ordinary-byte sizes and SHA-256 hashes for the preserved source files and baseline inputs. `inputs/freeze-v1.json` records the superseded original run; `inputs/freeze-v2.json` through `inputs/freeze-v6.json` record subsequent attempts; `inputs/freeze-v7.json` freezes the final strict-centre method, original-affine/global-index calculation, direct-centre controls, and directed SCL ambiguity controls. `run_twice.py` verifies frozen bytes before and after each full producer execution, compares outputs byte-for-byte, and writes `outputs/reproduction-receipt.json`. Superseded receipts and unsuccessful invocations are retained in `outputs/superseded/` and `outputs/execution-history.json`.

The recorded final pair of runs produced identical output bytes: see `outputs/reproduction-receipt.json` for the final byte count and SHA-256. Controls include a tiny edge-window case checked against directly constructed native pixel-centre points, an original-affine/global-index precision fixture, and a seven-class SCL fixture covering NoData, class 2, cloud, shadow, class 6, and rejection of corrupted ambiguous-class accounting. Restore WorldCover sources from their exact official URLs and verify the recorded ETags, lengths, and SHA-256 values before reproducing. The four raw COGs total 420,508,152 bytes and are not committed in the packet; the packet commits retrieval receipts, pins, and the restore script. Use Python 3.12 with rasterio, NumPy, Shapely, pyproj, and affine installed:

```sh
python restore_worldcover.py
PYTHONPATH="$PWD/.evidence-venv/lib/python3.12/site-packages" /Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12 research/geography/gap-source-angola-drc-boundary-water-followup-20261007/run_twice.py
```

The producer checks all frozen source pins, roster membership, raster CRS and coverage, and that unknown classifications remain unchanged. No snapping, buffering, repair, or ownership inference is used.

## Sources and terms

- ESA WorldCover 2020 v100 and 2021 v200 COGs were retrieved and measured as complete source files; their exact URLs, ETags, byte lengths, SHA-256 values, and attribution are recorded in `sources/worldcover/retrieval.json` and `inputs/source-pins.json`. The raw COGs are not committed because their combined size exceeds the ordinary evidence file budget. `restore_worldcover.py` downloads the complete files from those official URLs and checks each pin before use. ESA states CC BY 4.0; required attribution is in the retrieval receipt.
- Native Sentinel-2 SCL JP2s, STAC search results, item metadata, AWS listings, and retrieval receipts are under `sources/sentinel-2/` and `sources/earth-search/`. The source note records the Earth Search `proprietary` metadata versus the Copernicus legal notice for original Sentinel data. Attribution is recorded in the receipt; SCL remains a product label.
- The Gazette retrieval receipt is committed at `sources/official-belgian-gazette/retrieval.json`; the 11,821,646-byte PDF was retrieved and locally inspected, but the PDF itself is not committed. Its complete-file SHA-256 and retrieval facts are pinned, while file-specific reuse rights remain unresolved; no license or public-domain status is asserted.
- The archival inventory lead is cited at <https://www.arch.be/docs/invent/archives-africaines/AE1.pdf>, pages 40–41. The Cartothèque catalog entry is at <https://www.arch.be/docs/invent/archives-africaines/Cartotheque.pdf>, catalog entry `DEL.L-C.3A+B`.

## Preserved earlier work

The `outputs/` directory also includes the exact baseline component assessment, fragment-contact overlays, geometry overlays, and 2018/2019 physical-water and authority assessment. They remain separate from the new product observations. Original fragment and source binding bytes are in `inputs/`.
