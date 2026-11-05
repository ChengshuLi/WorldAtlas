# Qusarçay 1:50,000 sheet acquisition lead

The index at https://genshtab-yuga.narod.ru/index/0-22 lists `K-38-108-Б (2000).tif`, with its introduction describing a 2010 print date and the parenthesized year as terrain currency. The corresponding 1:50,000 sale page https://genshtab-yuga.narod.ru/index/0-4 describes 300 dpi TIFF sheets, a sample download and an order process. It was last updated in 2012 and lists an historical price; present availability, actual image resolution and whether the disputed headwater and both joins are legible have not been verified. The page mentions optional Ozi map registration, but no ground-control accuracy or datum transformation has been checked.

This is a potential source, not an acquired or authenticated copy. Its map lineage may overlap the 1978 General Staff sheet and must not automatically be called independent historical mapping. It may nevertheless provide a more legible control grid, legend and detailed drainage. No seller was contacted, no order placed, and no license or pipeline-use status is assumed.

The remaining evidence needed is a complete legitimately obtained K-38-108-Б / K-38-108-2 scan with its legend, date and coordinate grid, plus independent check points and a documented datum transform. Even that may not settle modern runoff in changing ice and snow terrain. NASA ASTER tile ASTGTMV003_N41E047 DEM and NUM layers offer a separate terrain comparison at approximately 30 m, but protected access and source quality screening remain necessary; they do not directly prove local drainage.

## Published basin hydrology

A 2018 paper published by the Azerbaijan Geographical Society and the Institute of Geography describes Qusarçay's source on Bazardüzü and reports observations at downstream stations. Its figure 4 is an ASTER GDEM-based model of the Qusarçay and Qudyalçay basins. The paper also says the high alpine/subalpine zones above 2,500 m lack observation stations. Thus it is useful broad basin context, but it does not provide a surveyed local drainage line or resolve the disputed gap and its joins; its ASTER-derived figure is not a field observation of those headwaters. Source: https://gsaz.az/ci/CORAFYA_V_TB_RESURSLAR/Co%C4%9Frafiya_v%C9%99_t%C9%99bii_resurslar_2018_N_1.pdf, PDF pages 42–44 (printed pages 42–44).

This paper is supporting research only and is not a selected pipeline input. It does not replace the required fine-scale headwater evidence.

## Named headwater evidence

The geography text *Azərbaycan coğrafiyası*, printed p. 46 (PDF page 46), describes Qusarçay as formed by Şahnabad and Yatıqdərə on the northeast slope, with Yatıqdərə treated as the main headwater and its source on Bazardüzü. Source: https://www.researchgate.net/publication/374452357_Azrbaycan_cografiyasi. A regional account likewise describes the upper Qusarçay running through Yatıqdərə valley before joining Şahnabatçay (https://www.scribd.com/document/1024908911/Qusar-tAM-%C4%B0%C5%9E-5). The two descriptions may share an underlying geographic reference; they should not be counted as independent surveys.

This is stronger named-drainage context than an unnamed valley alone, but neither cited description georeferences the disputed OSM crossing, identifies OSM way 1244882638 by name, or traces the 1.98 km proposed divide gap and joins. It therefore cannot establish that the mapped way is Yatıqdərə or select the candidate line. A controlled detailed map or field drainage survey remains necessary; no selected geometry was changed.

## Historic named-watercourse comparison

On the 1978 K-38-108 sheet (surveyed 1954–57, updated 1975), the blue label “Ятыгдере” appears alongside a watercourse northeast of Bazardüzü. The public scan is https://maps.vlasenko.net/smtm100/k-38-108.jpg. The regional text above identifies Yatıqdərə as a principal Qusarçay headwater. These observations are consistent with the 1978 sheet's regional identification, although the text's and map's underlying source histories are not established.

`east_yatigdere_map_preview.py` plots the selected line in yellow, OSM way 1244882606 in green, and the previously reported crossing way 1244882638 in magenta over the historic scan. In the pinned OSM extract, the two mapped ways share node 11572559585; the unnamed 2638 way is therefore a mapped tributary joining way 2606. On this provisional overlay, the green way is visually compatible with the historic valley leading toward the labeled watercourse. This supports investigating whether it is the mapped Yatıqdərə mainstem and whether the crossing way is a tributary; **it does not prove either identity**. The overlay uses six manually estimated 2 km grid controls in assumed EPSG:28408; datum operation, landmark errors, map symbols, and mapper lineage are not independently established. The map is a low-resolution historic scan and waterways, ice and snow can change.

The historic label and mapped confluence strengthen the broad Qusarçay drainage context. They do not establish the exact tributary or divide position, validate the 1.98 km proposed alternative gap, or resolve both joins. A controlled detailed map or field observation remains necessary before changing the selected line. The script checks local source-byte hashes; these research materials are not selected pipeline inputs.

### Source-lineage and color sensitivity

Both OSM ways were created in changeset 146899764 on 2024-01-31. A colleague read https://api.openstreetmap.org/api/0.6/changeset/146899764 and reported the comment “Азербайджан” with **no source tag**. That does not reveal whether its mapper used imagery, a historical map or another source, and the historical/OSM observations cannot be counted as demonstrably independent.

`east_yatigdere_blue_screen.py` screens map pixels within a 5×5 neighborhood around approximately one-pixel-spaced OSM way samples, using a simple blue-channel threshold and the same unverified six-control fit. For way 1244882606, 440/479 samples (91.9%) have blue-ish pixels nearby; offsets of 10 pixels left/right/up/down produce 23.0–59.5%. For crossing way 1244882638, 65/80 samples (81.2%) have blue-ish pixels nearby, but shifting 10 pixels north gives 76/80 (95%). This favors broad visual alignment of the longer line under the chosen fit, while demonstrating that the short crossing feature is sensitive to registration.

These are correlated, threshold-dependent image samples, not independent observations or a calibrated statistical test. Blue ink may represent water, ice, labels or other symbols; the datum transform and symbol interpretation remain uncertain. Neither result proves a modern channel, confirms the way's name, certifies a watershed or selects the 1.98 km alternate gap.
