# Whole-candidate coverage of the two retained dated scenes

**4221 of4367 remaining candidates lie inside both retained advertised scene footprints;146 remain outside both.** Nothing was dropped for coverage or batch size. This is metadata coverage, not a local image-quality or physical-classification result.

Input is the frozen `chosen-centres.json`,5839816B, SHA256`6e0fc1e33b8e7010cf606b11dd64f5b1aee721211867f2dab7bbe007f9b650b0`, `/candidate_records4367`. It already removes the exact five adopted CôTô keys from the original4372 source context. All4367 remaining keys are represented exactly once in `coverage-assessment.json`, either by covered key or complete uncovered-centre record. No territorial, foreign, city or other package was added.

| Original owner/group | Remaining candidates | Inside both | Outside both | Concrete missing footprint |
|---|---:|---:|---:|---|
|48235 VânĐồn|2796|2796|0|None in advertised metadata|
|48500 CátHải|1156|1032|124|99 west,25 south|
|48624 CôTô|415|393|22|22 east|
|Total|4367|4221|146|No boundary-zero cases|

Both actual STAC items have identical quadrilaterals:

- `../coto7-dated-evidence/dated-imagery-001/scene-item.json`: `S2B_48QYJ_20200131_0_L2A`, acquisition2020-01-31T03:32:07.183000Z.
- `../coto7-dated-evidence/dated-imagery-002/scene-item.json`: `S2A_48QYJ_20201231_0_L2A`, acquisition2020-12-31T03:32:14.812000Z.

The literal vertices are [106.93280255303439,21.69214219474222], [107.99319181439786,21.676390018196617], [107.97330084989277,20.685666438735453], [106.91994479904979,20.70063267603211]. Classification here uses the four clockwise GeoJSON longitude/latitude segment cross signs, with exact-zero boundary handled separately. It does not project centres, fit a map or interpret physical surfaces. Checking the quadrilateral avoids treating its larger geographic bbox as complete coverage.

**VânĐồn2796 is the largest complete original-owner group already covered by these two items.** Its centre bbox is [107.07681392705382,20.717847952568775,107.69611620118548,21.233281973550103]. It is a coherent fallback if additional imagery is unavailable; the124CátHải and22CôTô exclusions remain explicit unresolved coverage records, not silent removals. Root owns any same-pass adjacent-item metadata collection. No adjacent MGRS tile or acquisition date is guessed here.

## Native-frame and resource facts

Actual retained native-window observations agree on EPSG32648 and these source properties for both dates:

| Assets | Shape rows×columns | Affine | Actual source blocks | Type |
|---|---|---|---|---|
|red,green,blue,nir|10980×10980|[10,0,699960,0,-10,2400000]|1024×1024|uint16|
|scl|5490×5490|[20,0,699960,0,-20,2400000]|512×512|uint8|

The projected full-frame bounds are E699960..809760,N2290200..2400000. The upper bound is121 source blocks per band. Four complete RGB/NIR bands plus SCL charge **1046740992B per date** when charging entire source blocks, including edge blocks at their full block dimensions. The logical whole-frame data arrays alone are994623300B. These figures exclude masks, cache, encoded responses, output products, plotting and runtime. A monolithic whole-frame five-band decode therefore exceeds512MiB before those additions; this is not a claim that the actual sparse candidate layout must decode the full frame.

A prospective sequential aligned1024×1024 native10m footprint covers a512×512 SCL footprint. Its four uint16 data blocks plus one SCL block total8650752B; adding one uint8 mask per band gives13107200B (12.5MiB). This describes a possible bounded reuse layout, not measured live memory or a complete admission charge. Actual distinct touched blocks, neighbour/context needs, encoded I/O and output layout depend on root's later window plan. Reusing native blocks/context can preserve all keys without thousands of separately rendered crops or one oversized image.

The existing seven-centre CôTô observations retain10m window[col8504,row7868,width287,height260], and20m SCL window[4252,3934,144,130]. Those actual small windows support only their original centres and context; they are not extrapolated to the415CôTô candidates or the4367 batch. Existing January/December CôTô products remain unchanged.

Exact new native-window dimensions are intentionally unset: the frozen candidate table is unprojected, and root reserved any geographic→UTM transformation and block-union/window planning for a fresh admitted operation. No raster, GDAL/PROJ/native operator, network fetch, scientific classification or source-geometry replay ran in this coverage task.

## Interpretation limits

The catalogue's scene-level nodata percentage is0 on both dates, while cloud cover is6.976898% in January and9.062919% in December. Neither establishes local usability for4221 centres. Actual masks, cloud/shadow/saturation, registration, visible context and source purpose still govern any later exact-key grouped interpretation. One locally clear date can support a date-specific claim; this report does not require universal two-date agreement, convert SCL to truth, or count annual WorldCover predictions as physical decisions.

The paired JSON retains the complete uncovered146 centres and edge directions, both literal item footprints, inherited actual block/window facts and finite full-frame bounds. It is a coverage result for the existing batch, not a new framework, operator or approval gate.
