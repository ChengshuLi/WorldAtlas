# TUV45 retained-geometry correspondence and unresolved disposition

This packet supplements the original `gb-TUV-ADM1--repair-evaluation` review for the exact 45 native land cells in 16 half-open intervals. It is a proposed evidence disposition; `accepted` remains false, accepted cells and repair credit are zero, and all 45 cells remain held.

## What the retained geometries show

The source-census archive object (the pinned OSM/Wambacher 2017, ODbL ADM1 object) classifies all 45 original cell centers inside their named source feature. The separate retained regional-review GeoJSON has the same declared CRS/source metadata/vintage labels but classifies only 42 of those centers inside the named feature; three centers lie outside all eight retained features. No center-boundary ties were found. The packet gives all 16 intervals and each cell-center coordinate/classification for both objects.

The grid is OGC:CRS84, width 262166, with center longitude `360*(x+0.5)/262166 - 180` and center latitude `atan(sinh(pi*(1 - 2*(y+0.5)/262166)))*180/pi`. The pinned project method classifies centers; it does not prove full-cell polygon intersection or whole-cell containment. The version divergence is therefore documented, not resolved. Neither geometry establishes present applicability.

The retained metadata identifies `OpenStreetMap, Wambacher`, boundary year 2017, ODbL 1.0, and its update/build dates. The citation file names a geoBoundaries project contact, not a per-feature OSM/Wambacher editor. The exact block-033 candidate contact scan found only the three expected feature/owner pairs for these intervals and no additional source feature or foreign-owner contact within this pinned block. This is not a claim about contacts outside that block.

Block-033 physical support classifies all 45 cells as land; inland-water support classifies zero as water. These are bounded checks of the pinned support files. The package has 45 native cells, 16 intervals, and `source_relative_cells=0`; 101 other same-block source-relative cells are outside this package contract.

## Selection and disposition limits

Selection input identities and hashes are included in the JSON. A reviewer’s exact replay at main `2b569815a7e37c5797586092688122d9b5d749b0` reported base, patch, and effective selected owners as zero for all 45 cells and 45 unassigned. The selector/sidecar/patch/ledger identities are unchanged at current base `77609a1f159bfee954e52d48a883c5fe3e4b59f5`, whose intervening diff contains only the three earlier TUV evidence files. The replay was not persisted as a receipt and was not rerun by this author; this packet labels it inherited reviewer evidence, not a new reproducible receipt.

The proposed source-relative exception records an unresolved geometry-version/applicability gap. It assigns no owner, changes no geometry, grants no repair credit, and makes no legal or sovereignty claim. It does not close the package or satisfy acceptance by itself. Follow the project’s documented exception path only after the independent contract reviewer confirms it fits this original key. Any future positive assignment or closure needs separately verified current applicability and the original contract’s required independent acceptance. Do not transfer evidence for Niulakita/Niutao from #615 to these three islands.

## Evidence index

`geometry-correspondence.json` contains exact scope and interval rows, archive and regional-review geometry hashes, per-cell center results, full eight-feature comparison, candidate contacts, land/water support, selection input pins, inherited replay qualification, and proposed acceptance conditions. Source paths are repository-relative; no machine-local paths are used.
