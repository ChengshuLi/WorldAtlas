# Independent source and result review: PMM first observation

Reviewer `/root/mmr_review_key_accounting_sol`. This examines the newly acquired 25 January 2020 source and first actual PMM window result; it does not reopen prior Myanmar accounting or scientific outputs.

## Source applicability reviewed before the read

No substantive source/method objection to the authorized first observation. I independently read the actual `S2A_47PMM_20200125_0_L2A-item.json`, producer granule XML, first native plan/centre records, edge-exception record and exact reader adaptation under `worker1-mmr-physical-followup-001/new-dated-source-001/`.

The producer explicitly reports WGS84 / UTM zone 47N, EPSG32647; 10m origin `(399960,1200000)`, dimensions `(10980,10980)` and affine `(10,0,399960,0,-10,1200000)`; and corresponding 20m SCL shape `(5490,5490)` and affine `(20,0,399960,0,-20,1200000)`. The STAC fields agree. Producer sensing is `2020-01-25T04:05:18.697349Z`; STAC rounds to `.697000Z`, rather than describing a different acquisition. Optical bands B02/B03/B04/B08 retain literal uint16 DN with scale0.0001, offset0 and `earthsearch:boa_offset_applied:false`. SCL is uint8 at20m.

The ready scope is 2,107 unchanged original keys, 327 owner30350 / 1,780 owner30361, across40 native block contexts. The native plan's original key, request-row, original-package-row and sourceSIDs remain visible. The adapted kernel changes only the scene/count/block assertions and terminal counts, with its ROOT following the fresh directory. Supplying `planning_group` from the retained `physical_block` fixes the unchanged record input shape without moving a key or pixel. Existing native affine/shape/resolution/nodata/block checks, integer windows, complete array/mask outputs and operating guards remain intact.

The failed GEOS-disabled footprint predicate is excluded. The current scene bbox/native-domain plan is a candidate selection, not valid-footprint or clear-pixel proof. The separate context-edge key `(30350,123130,202593)` remains unread/held with its overlapping PMN alternative; the first PMM scope leaves2,737 parent keys unread. No metadata-only result earns physical completion.

For the actual read and any later interpretations:

- A valid source mask establishes observed native sample availability, not cloud-free surface. SCL/cloud/shadow, saturation, nodata and contradictory quality fields remain explicit.
- Native10m optical and20m SCL supports differ: their3x3 contexts cover approximately30m and60m respectively. Preserve the actual containing pixels and both full mask grids; no resampling or SCL-to-physical classifier follows.
- Fixed DN display stretching is for visual inspection. Preserve raw DNs/scale/offset, native transform, point registration and source masks. Coastline-edge and mixed-pixel uncertainty cannot be removed by a display overlay.
- Clear dated cover/water can support a bounded optical observation or, after substantive interpretation/adoption, its corresponding dated answer. It does not prove whole-cell extent, annual water/dryness, tidal datum, source2019 causal equivalence, owner truth, native authority, repair credit or hold clearance.

The parent explicitly rejected an additional RAM coordination ceremony. The existing fresh availableMemory admission and retained phase/RSS/disk/deadline guards remain the execution boundary; no new reservation/acknowledgment gate was requested by this review.

## Actual result

The same actual read completed successfully: exit0,40/40 blocks,2,107 observations in329.561561167seconds; reported process-lifetime peakRSS300,318,720B and terminal disk output426,553,034B. The execution receipt and complete native observations retain the actual CRS/affines/shapes/nodata/scale metadata and all five asset records per point. All centre source masks are255. The author reports562 complete inventory entries present with matching sizes; I did not repeat the complete562-file hash/inventory scan or re-read remote rasters. The observation body is9,861,264bytes, SHA256 `728d52e06bc8d00685fc44b7930643cbc3c557c25fe33842e5689a1f2b48b481`.

I inspected the actual execution, full result structure/summary and source metadata; literal point records151,170,167 and386; and the retained native RGB/NIR centre displays from blocks00-02 and01-03, plus RGB block00-05 showing cloud/shadow/shore context. These are actual newly produced native-window displays, not reconstructed classifications or newly rendered review fixtures.

**The two literal dated surface proposals are supported within their stated optical limits:**

| Index and original key | Actual sample and independent visible reading | Decision |
| --- | --- | --- |
|151: owner30350,y123185,x202659 | Native10m row820,col2210, local row820,col163: textured green canopy in RGB and co-located red canopy in NIR-red-green; NIR2194 versus red213/green401, with valid centre/3x3 masks. The centre lies inside the canopy patch in the inspected context. | Supports **visible vegetation cover at the acquisition date**. No substrate/always-dry or whole-cell claim. |
|386: owner30361,y123261,x202778 | Native10m row1957,col3994, local row934,col923: smooth green/blue water beyond the visible vegetated margin, dark in NIR; NIR159 versus red312/green700, with valid centre/3x3 masks. | Supports **visible water surface at the acquisition date**. No annual/tidal/whole-cell inference. |

The withdrawn index170 vegetation draft should stay withdrawn. Its actual row969,col2194 (local969,147) is waterlike in the native image and source observations, NIR189 versus red292/green695; the20m SCL neighbourhood also includes a nearby vegetation neighbour. The original vegetation reading confused label proximity with the sampled centre. I accept keeping this shoreline/context case unfinished; this review does not replace it with a new completed answer. Index167 is likewise not promoted merely because it appears in the inspected frame.

The block00-05 display visibly contains bright clouds and dark shadows despite all centre validity masks being255. Literal SCL centre observations include26 class9,20 class8 and13 class3, but **the other2,048 are not automatically clear**: the result also retains36 class2 and17 class7, and local neighbouring/cloud/shore conditions still matter. Neither mask availability nor any SCL code is a physical-completion classifier.

**No blocking result/method finding for these literal observations and two narrowly worded proposals.** They are independently reviewed proposals, not Main's actual adoption or remote publication. No blanket2,107-key clearance is supported; the remaining2,105 observed points have not been substantively answered by this bounded two-example review. The2,737 parent keys unread by this observation, including the separate PMM context-edge exception, remain unread. Holds, repair/native authority, ownership and all prior accounting remain unchanged. No source download, raster/native producer, old science, accounting join or test was repeated by this reviewer.
