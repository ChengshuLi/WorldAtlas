# Preliminary Abin western-join map check

The 1941 Indiana University L-37-125 sheet, based on 1907–1909 surveying, covers the western join of the **second Abin splice** at 38.31791666666666 E, 44.59583333333336 N. The earlier description that the join lay east of 38.5 E referred to an older studied candidate and must not be applied to this newer western endpoint. The new candidate's eastern join lies on adjoining L-37-126; neither sheet alone establishes both joins. Source: https://digitalcollections.iu.edu/concern/images/8049hg215.

`west_iu_join_preview.py` draws a crop with the selected line in red, the hypothetical candidate in blue, and the candidate's start in white. It checks SHA-256 of the local sheet (`f51b6448d3717ad5e84dfaf145728e1f785d7a4907e94a84a9785d60b78bb635`), selected source file (`081f5909935023255cf9f0b13f06102aaa97cc19a15715b6cabb9964b7a20f25`) and unselected candidate (`f9e4e5da1687f3ffb118e0b621705fe2e6b43a5dc2abbc323699cb56fbf8dcb9`).

The preview shows the lines near the mapped Abin drainage and labeled 896.3 m summit. The coordinate overlay is only a frame-corner approximation that assumes WGS84; the sheet's datum, image deformation, independent controls and residual errors have not been verified. Its map marks and confluence crossings cannot be used to infer a precise watershed or validate either join. Their intersection was built into the candidate and is not independent evidence. No boundary or cell labels have been changed.

Obtain a controlled, sufficiently legible georeference of this western sheet and the adjoining sheet, or comparable independent detailed headwater mapping, to assess the two joins. The image and candidate are research evidence, not inputs to the selected pipeline; this note does not assert current R2 custody or a reuse license.

## Printed-grid sensitivity

The sheet's margins label a 2 km projected grid. A provisional local fit using six approximate vertical and five horizontal grid-line positions near the join has in-sample residuals up to 7.9 and 9.6 image pixels respectively. These are fit residuals, not independent validation. The numerical positions and reproduction are in `west_iu_grid_preview.py`.

If the printed grid is interpreted as zone 7 on a Bessel 1841 ellipsoid, with no established datum transformation to WGS84, the western join falls about 23 pixels from the previous frame-corner fit (roughly 100 m at the local printed grid scale). Repeating the same simplistic comparison with a Krasovsky ellipsoid shifts the point about 161 pixels from the corner fit (roughly 680 m). This large datum sensitivity explains why a later SK-42 assumption cannot simply be imposed on the 1941 sheet. An historical discussion describes Pulkovo 1932 using Bessel 1841, but it does not establish this sheet's actual coordinate reference or local datum transformation: https://s3.eu-west-2.amazonaws.com/redatlas/Mugnier2007.pdf.

This check makes the plausible Bessel preview more consistent with the original corner fit; it does not independently locate the watershed, establish an accuracy bound, or validate the candidate join. A documented sheet datum and independent ground controls are needed before drawing such conclusions.

## Candidate control points

The available OSM research extract contains two candidate summits near the western join: node 13276920139 (38.3115831 E, 44.5966511 N, elevation tag 921 m) and node 785474093 (38.3303118 E, 44.5944707 N, elevation tag 895 m). In the preliminary frame-corner overlay their offsets from the visually estimated symbol for the historic 896.3 m elevation are about 68 and 343 image pixels, respectively. At the local 2 km grid scale the first is roughly 280 m; this is a rough relative screen, not measured geodetic accuracy. The elevation differences and intervening contours do not establish either feature as the same summit. OSM's source lineage for these nodes has not been established, so they are not treated as independent verified controls.

`west_iu_peak_control_screen.py` reproduces the calculation from the local OSM extract SHA-256 `c447f5d1e7da385c7ca13b3d119d2c1b260b29315974a6f9b3db08f9c4fe35c8`. One library catalog identifies the same historical sheet as VAC9619-002433 (https://geodata.lib.berkeley.edu/catalog/VAC9619-002433), but the record returned HTTP 403 for direct access during this check. A separate Indiana DataCORE record for an adjoining sheet says that it was scanned and georeferenced with ArcGIS; it does not establish that this sheet has the same georeferencing or report control accuracy (https://datacore.iu.edu/concern/data_sets/wh246s994). No access restriction was bypassed. Authoritative coordinates or an independently documented georeferenced copy of this exact sheet remain necessary.

## Terrain check on proposed summit control

`west_iu_peak_dem_screen.py` samples the original JAXA N044E038 DSM, mask and stack layers at the preliminary frame-fit location of the visually estimated 896.3 m symbol and at both OSM summit coordinates. The approximate historic location samples 895 m; its mask is 0, stack count 5, and its 49 valid neighboring pixels span 856–911 m. The nearby OSM 921 m summit samples 926 m (mask 0, stack 3; neighboring range 903–933 m). The OSM 895 m summit farther east samples 890 m (mask 0, stack 5; range 834–895 m). All comparisons are approximate DSM values, not surveyed peak elevations.

The elevation agreement at the provisional historic location is a useful lead but can be coincidental: the historical symbol was visually located and frame registration/datum are unverified, DSM includes surface features, and the 7×7 relief is substantial. The OSM peak source lineage and exact match to the historical survey marker are unknown. This does not constitute an independent ground control or justify a boundary change.

## Regional 921.5 m watershed lead

A local geographic account by V. N. Koveshnikov describes the main divide turning northeast toward the Papay massif near the eastern slope of an unnamed 921.5 m high point on the Kotsekhur ridge (https://viktor-dnk.ru/toponymy/kotsehur-thab/). It describes drainage on the south slope and cites maps including a 2009 regional atlas. This is a useful regional description, not a surveyed polyline; source-map lineage and the exact location of the turn have not been independently established.

OSM node 13276920139 is a nearby unnamed 921 m summit at 38.3115831 E, 44.5966511 N (https://www.openstreetmap.org/node/13276920139). It plausibly corresponds to that description but identity is unproven. The pinned selected and complete unselected Abin splice are both approximately 103.6 m from this point at the same nearest location; the proposed western join is approximately 511.0 m away. Both routes share their approach there, and both head generally east then northeast over the following 2 km. These facts are consistent with the regional narrative but cannot distinguish the alternative from the selected line, establish the exact turn or prove the join. `west_abin_921_lead.py` reproduces the WGS84 coordinate-linear line screening.

No raw research page was added to R2 or Neon; no boundary or grid labels changed. An independently controlled headwater map or field drainage evidence remains necessary for a precise correction.

## Named Thab candidate control

The 1941 sheet visibly labels a triangulation symbol “г. Тхаб” with elevation 903.5 m. The OSM extract also contains a named Thab summit, node 544448880 (38.3522706 E, 44.5847407 N, elevation tag 905 m; https://www.openstreetmap.org/node/544448880). A regional guide describes a geodetic point at Thab (https://geocaching.su/cache/4830/). The name and close elevations make this a more specific correspondence candidate than the unnamed 896.3 m symbol.

Using the same approximate frame-corner overlay, the OSM point is about 24 pixels from the visually estimated historic triangle centre, or roughly 100 m at the local printed-grid scale. The Bessel-based provisional grid fit puts it roughly 28 pixels from the same estimate. The symbol centre, old datum, transformation, scan deformation and OSM coordinate lineage are not independently validated; the guide does not provide surveyed WGS84 coordinates. These are consistency screens, not ground-control residuals or an accuracy guarantee. The point is about 3 km from the western splice, and agreement at one feature does not certify the join. `west_iu_peak_control_screen.py` reproduces the frame-fit comparison; no geometry was changed.
