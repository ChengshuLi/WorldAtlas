# Independent reading: actual 16 July 2020 Nha Trang imagery

**The saved dated imagery supports two emerged-looking island surfaces at the 20 original centre positions.** This is a stronger, specific physical observation than the prior undated land-use extent gap. It does not establish original administrative-component purpose or clear any hold.

I viewed all four actual Nha Trang PNGs: RGB and NIR-red-green, each with and without numbered centres. In the unmarked RGB image, a smaller elongated island lies northeast of a larger roughly rounded island. Both have visibly bounded pale margins/exposed patches and green interior areas, surrounded by darker water-looking texture. Their interiors become bright red in NIR-red-green, consistent with vegetation. The smaller island has relatively extensive pale exposed-looking areas; the larger island has a stronger green/red vegetated core. Two small bright intervening features are visible but have no cohort markers; they are not added to this20-centre reading.

The actual numbered overlay places labels 1–6 on the smaller northeastern body and labels 7–20 on the larger southwestern body. Pale margins and green/red interiors are spatially coherent with the centre pattern. Some markers approach the bright margins, so I do not extract a precise shore or declare every complete original native cell dry land. Nonetheless the scene does not show these 20 positions as an undifferentiated open-water patch.

## Source positions and the retained original keys

The source is `S2B_49PCP_20200716_0_L2A`, sensing time `2020-07-16T03:24:37.394000Z`. Actual observations record EPSG:32649, a native 10 m RGB/NIR window of 341 columns × 412 rows, window offset (2042,4031) in the 10980 × 10980 source grid, with affine `[10,0,320420,0,-10,1359730]`. The overlays use transformed **unchanged original longitude/latitude centres**, not manually fitted positions; the rendered grid is north-up UTM. No fitted registration shift or shoreline was introduced. These source/output georeferences and overlay code were read, not rerun.

| Visual group | Labels | Original owner/y/x keys |
| --- | --- | --- |
|Smaller northeastern body|1–6|48569/122067/210730;48569/122068/{210729,210730};48569/122069/{210729,210730};48569/122070/210730|
|Larger southwestern body|7–20|48569/122075/{210723,210724};48569/122076/{210722,210723,210724,210725};48569/122077/{210722,210723,210724};48569/122078/{210722,210723,210724};48569/122079/{210723,210724}|

The recorded centre samples are valid (mask 255); native 20 m SCL reports 10 centres as vegetation (4) and 10 as nonvegetated (5), with no centre cloud/water class. This agrees at a coarse vegetated/nonvegetated level with the retained WorldCover totals of 9 tree, 1 grass and 10 bare/sparse. The two products have different spatial and temporal meanings. SCL is a model mask, and WorldCover uses Sentinel observations, so this agreement is not independent ground truth. The RGB/NIR appearance is the additional direct dated evidence.

The broader window contains dark streaked areas, especially east/southeast, whose cause I cannot identify from colour alone. Its stored SCL counts include 18 medium-probability-cloud pixels, 15 dark-feature pixels and 50 unclassified pixels; they do not report class 3 cloud-shadow pixels in this window. Consequently I would not label every dark streak as cloud shadow or treat the whole context as cloud-free. No such centre class is reported.

## Meaning and next actual fact

For these exact 20 centres, the reusable statement is: **“Native Sentinel-2 imagery acquired 16 July 2020 places the retained original centres on two visible island-like land surfaces with vegetated and exposed-looking cover.”** That supports an emerged-island explanation for at least these source-only centre disagreements. It does not show why the retained physical mask differs, authenticate an exact coastline, determine tidal datum/seasonal persistence, establish 2020 ground truth at every point, or describe the unobserved remainder of any ADM2 component. The current-state WMS's eastern advertised extent remains a separate source-coverage limitation; it is not corroborating evidence of sea at these positions.

The exact next source-purpose fact is an **official island/commune or administrative-boundary record identifying the depicted island components and their relationship to the original nominal-2020 Nha Trang city member** `81297802B68033195953544`/VN51101. That documentary correspondence could support retaining a source-backed island-location interpretation without assuming that the original component intended administrative waters. A dated second scene can address persistence/seasonal ambiguity; it still cannot supply legal administrative purpose. No island name is guessed from appearance or coordinates here.

Reused actual native-window observations, existing execution receipt and the previously reviewed original-key/WorldCover/parent records. The operation's stored limits apply: partial native source windows, not authenticated complete remote COG objects; display-only fixed DN 0–3000 stretch; RGB/NIR 10 m and SCL 20 m remain separate. This review performed no new image processing, raster/source/native execution, geometry test, shoreline drawing, resampling, classification promotion or hold clearance. All 20 original holds remain unchanged.
