# Caucasus candidate comparisons

The selected boundary and its Neon source recipe remain unchanged. These
comparisons are local, bounded diagnostics, not a global map rebuild. The
companion `caucasus_boundary_visuals.py` renders the selected and alternative
line on the same extent, with mapped OSM water and elevation shading. The
water mapping may be incomplete; shading does not prove a drainage divide.

## Anapa

The preferred candidate starts on OSM coastline way 396539058 version 2 and
follows the published Trubetskoy route to its fifth intersection with the
selected line at 37.42406995874469 E, 44.84168781056519 N. This replaces
14,328.43 m with 11,809.93 m. The current line crosses the mapped Anapka
water polygon for about 65 m; the proposed cut had no intersection with 38
complete mapped waterway versions in the inspected extracts. Relations and
unmapped streams were not verified. At 100 m offsets, screened JAXA profiles
were higher at the candidate center at 70/111 valid stations, versus 19/141
for the selected opening. This supports the proposal but does not establish
the local divide conclusively. Recommend provisional adoption once its coast
closure and impact are checked against the current physical mask.

## Abin

The second splice replaces 44,503.05 m with 61,777.60 m and was reproduced
from its pinned source files and selected boundary. The candidate matches
the intended labels in 290/309 valid JAXA stations, versus 75/223 for the
selected cut, at 100 m offsets. Its construction uses SRTM and mapped-water
seeds; the terrain checks share those seeds. One join remains unresolved in
the Copernicus model. Prefer the candidate as the leading provisional route,
but retain the selected line until the joins have adequate support. An older
draft-93 screen identified 113 bounded candidate centers, five with an
ambiguous side; this is not a count against the current physical mask.

The current mask could not be identified from local old artifacts or the
empty Neon `atlas.source_builds` and `atlas.entity_grid_artifacts` tables.
Therefore no current land-cell impact is asserted. For Anapa, the changed
coastal endpoint also requires a valid water closure for a complete impact.
