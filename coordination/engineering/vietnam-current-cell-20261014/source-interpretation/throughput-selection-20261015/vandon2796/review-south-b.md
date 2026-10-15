# Southern Vân Đồn actual two-date imagery review

The actual January and December imagery supports **361 dated terrestrial island/islet-location answers among the529 assigned original centres**:237 supported by January, plus124 newly clarified by December. The other168 retain exact shoreline/mixed-pixel or tiny-islet/terrain-shadow/veiling questions. These are reviewer dispositions awaiting root adoption, not hold clearance or global completed counts. Both actual retained result sets and the successful continuation receipt were read before finalizing.

Assigned source blocks are09-03,09-04,09-05,10-02,10-04,10-05. `native-block-plan.json` binds all529 indices to unchanged owner48235 keys, original source-array indices and native subpixels. `review-south-b.json` preserves every assigned key and its exact January fact or residual question, with actual image references and retained date-specific January/December readings. The final answer/date fields select one supporting date; they do not assert universal agreement. No representative point is used to classify an unseen part of a block.

| Block | Assigned | January answers | Additional December answers | Final answered / unresolved |
|---|---:|---:|---:|---|
|09-03|95|59|0|59 /36|
|09-04|199|99|36|135 /64|
|09-05|132|58|38|96 /36|
|10-02|1|0|0|0 /1|
|10-04|34|21|0|21 /13|
|10-05|68|0|50|50 /18|
|Total|529|237|124|361 /168|

## Historical January geographic interpretation

**09-03: vegetated archipelago and small rugged islets.** The unmarked RGB shows distinct island masses, cliff/terrain shading and water channels; native NIR-red-green separates their vegetated surfaces from the surrounding water. The59 selected exact centres are on legible island/islet bodies in those views, including some terrain-shadow positions within a clearly depicted body. The36 residuals concern narrow protrusions, shores, tiny knobs and dark channels where this reading does not seal the unchanged centre's exact side. A SCL water/shadow code is not used either to force or forbid an island answer.

**09-04: elongated northern island, central branches and a separate eastern island.** Clear northern interiors show continuous vegetation and terrain, while the south-central part contains bright developed/exposed areas and a diagonal cloud veil. The99 answered centres are in the legible island-body groups or clear neighbouring islets, including clear portions of the eastern island. The100 exceptions retain their actual scope: narrow outer and internal water margins, small shadowed features, or the January cloud/shadow veil. The clouded lower settlement/coast is not promoted from the clear northern sample.

**09-05: long eastern island, exposed/developed patch and clouded southern continuation.** The58 selected positions have legible vegetated, exposed or developed terrestrial context on the visible island bodies. The southeast concentration is hidden by opaque cloud; additional west-facing shoreline and southern veiled margins remain exact-key residuals. The clearing visible near the upper island is a dated morphology observation, not proof that a particular prospective planning project had been built.

**10-02: one tiny feature at index2722.** The surrounding frame depicts clear water and nearby rugged islets, but the point's small dark feature/shore association remains unresolved at this resolution. It is not labelled water from its SCL2 or low NIR value.

**10-04: clear upper-right island and nearby small rocky feature.** The21 answered positions have legible terrestrial island/islet morphology, predominantly vegetated, with an exposed/rocky small-islet setting at index2713. Thirteen remaining positions lie along notches, narrow shore tips or the neighbouring small feature's shadow/edge. These retain the exact emerged-land-versus-adjacent-water question; no legal shoreline is asserted.

**10-05: opaque cloud at every assigned January location.** All68 centres are unresolved from this date. Neither the annual WorldCover prediction nor a neighbouring clear island fills the hidden surface. All these samples can have valid source masks while their physical surfaces remain obscured.

## December clarification of actual January residuals

The successful continuation supplies `S2A_48QYJ_20201231_0_L2A`, acquisition2020-12-31T03:32:14.812000Z. I viewed the six assigned December unmarked RGB and NIR/centre-labelled products. December has a textured thin-cloud/cirrus veil over much of the surrounding sea, but many island bodies and their interior terrain remain legible. The interpretation uses that actual local visibility; SCL cloud/cirrus flags neither automatically veto a visibly supported island location nor establish one.

In09-04,36 previously unsealed centres become legible on the central/western island tract, northern-eastern promontory, small western islet or southern terrestrial body; the January diagonal opaque/bright cloud no longer hides those surfaces. In09-05,38 centres are clarified on the southern continuation or the southeastern island that January cloud hid. Existing clear January answers on the northern island remain supported by January even where December is more veiled. In10-05, December depicts the curved vegetated island behind the former opaque January cloud:50 interior locations are now supported, while18 shoreline/notch/tip positions retain the exact-side question. This is a bounded dated terrestrial-location fact, not a claim about the year-long surface or a legally surveyed coastline.

The additional date does not resolve the36 small-islet/shore questions in09-03, the single tiny dark feature in10-02, or the13 notch/tip/rock-edge questions in10-04. Nor are the remaining64/36/18 questions in09-04/09-05/10-05 counted as answers merely because their surrounding island is visible. Every remaining key has its specific location, native subpixel and source-image references in the JSON.

## Evidence and source semantics

I actually viewed each of the six January `rgb-native.png`, `rgb-centres.png`, `nir-red-green-native.png` and `nir-red-green-centres.png` products. Their labels use the existing exact native subpixels and global plan indices. The raw imagery products were not modified. The complete January `native-observations.json` records all2796 points/24blocks; its assigned529 centre masks are255 in all five assets. That records source-data presence, not cloud-free visibility.

The dated source is `S2B_48QYJ_20200131_0_L2A`, acquired2020-01-31T03:32:07.183000Z. Native10m RGB/NIR supports and20m SCL remain distinct. This review uses visible morphology and geographical context with original-centre overlays; it applies no SCL/model threshold, spectral index, fitted shift or new classifier. `../interpretation-scope.md` and `../source-purpose-assessment.md` provide the established interpretation boundary and primary source context.

The original source is an administrative district feature. The retained2020 Vân Đồn planning decision distinguishes land and sea in its scope; it does not convert every original component into terrestrial ground or administrative water. The selected island-location answer is bounded to the visible dated body. It does not establish unflooded understory, whole150m-cell land coverage, annual persistence, local names, legal coastline, administrative ownership, selected-parent correctness, repair acceptance or hold clearance.

## Actual partial execution boundary

`failed-run-001-receipt.json` records `failed-deadline`, actual tool exit142 and a300-second OS alarm. It preserves a complete January result and only two completed December blocks; exact child wall time and peakRSS were not retained. This review does not claim the original combined operation succeeded. Root's fresh December continuation is separate. Missing or incomplete December output is not nodata and earns no interpretation. A clear January answer remains valid for its own date without mandatory cross-date agreement.

`failed-run-002-receipt.json` separately records a memory-admission refusal before any source read (exit1, source_reads0, empty output directory, no guard override). `remaining-december-blocks-003/execution-receipt.json` then records the actual fresh768MiB continuation:324.000672seconds, ended2026-10-15T13:38:37.642963UTC, observed process-lifetime peakRSS249085952B; root additionally confirmed actual exit0. It reuses the complete January result and completes all24 December blocks/2796point observations. This successful continuation does not erase the earlier failures or create a measured peak for001. The JSON now references both actual results and all three execution outcomes. January imagery was not reacquired or rerun by this reviewer. No network, raster sampling, source/native replay, new crop/enhancement, runtime installation or heavy operation was performed by this reviewer. No holds were changed.
