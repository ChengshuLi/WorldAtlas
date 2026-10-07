# China ADM2 gap families: source-fitness assessment

Issue #1337 is a source-fitness-only review of two complete declared families. The packet retains all 50 whole candidate components, all 14 full original/current contact features, both complete family records, and the input pins needed to restore their source context. The original issue permits explicit unknowns. The result below does not authorize any boundary, land, water, hierarchy, ownership, identity, or repair decision.

## Source and terms

The actually consumed administrative source is the **simplified** geoBoundaries gbOpen CHN ADM2 GeoJSON at the pinned raw URL ending `geoBoundaries-CHN-ADM2_simplified.geojson`, commit prefix `9469f09`. Its encoded Git body is 2,096,437 bytes, SHA-256 `7bcd6bb51042f63c2f4f1717b25d701874cfcd6f12eb79dc36cdff29f3b62f30`; decoding that body yields the complete 2,391-feature, 7,018,287-byte JSON body, SHA-256 `8c7dfa8e40842f9162453d9b0b614276a48bf635559ba371c7982cb288e7b303`. These identities are separate and both are retained. The un-simplified `gjDownloadURL` in metadata is not used as a substitute. The full source metadata records represented year 2017, ADM2 / “County Level”, source-data integration 2023-01-19, build date 2023-12-12, source `National Administration of Surveying, Mapping and Geoinformation of China, Revolutionary GIS`, and 2,391 units. geoBoundaries describes `boundaryYearRepresented`, primary-source, source-license and update-date fields as metadata; these are dataset claims, not a local boundary survey or legal authority ([geoBoundaries API field definitions](https://www.geoboundaries.org/api.html)).

The file is GeoJSON. Under [IETF RFC 7946](https://www.rfc-editor.org/rfc/rfc7946), its coordinates are WGS 84 / CRS84 in longitude, latitude order and decimal degrees. The pinned China metadata provides vertex-count summaries but no positional accuracy, boundary tolerance, survey scale, or per-feature observation date. Coordinate decimal digits are not a positional-accuracy claim. No precision threshold for these small components can therefore be cleared from this source.

The retained metadata states **Open Data Commons Public Domain Dedication and License (PDDL) v1.0** for the boundary data. The separately pinned geoBoundaries citation-and-use text says geoBoundaries code and derivative works are **CC BY 4.0**, requires attribution, and asks users of individual files to cite the source in the file metadata. This packet preserves both statements and the cited underlying-source information. The scope of those statements for these particular derivative geometries remains unresolved; no independent legal interpretation is claimed. Source bytes and terms are pinned in `evidence-quality.json` and `runs/final-1.json`.

## What can establish administrative meaning

China's official rules establish why a global harmonized ADM2 layer is insufficient to certify county boundaries. The State Council's [Administrative Regional Boundaries Management Regulation](https://xzfg.moj.gov.cn/front/law/detail?LawID=593) defines administrative boundaries through approved instruments and boundary agreements, describes physical boundary markers and agreed linear features, and identifies approved detailed boundary maps as the standard for depicting county-and-above boundaries. The State Council's [Map Management Regulation](https://www.gov.cn/zhengce/zhengceku/2015-12/14/content_10403.htm) says maps should use current materials and that county-and-above boundary depictions must follow approved standard boundary maps and other national rules. The Ministry of Natural Resources' [2023 public-map specification](https://big5.www.gov.cn/gate/big5/www.gov.cn/gongbao/content/2023/content_5752310.htm) likewise makes approved boundary diagrams and local-government public notices the basis for county-and-above boundary depiction and changes.

The [National Bureau of Statistics' 2020 code clarification](https://www.stats.gov.cn/hd/lyzx/zxgk/202104/t20210401_1815920.html) identifies its 2020 statistical code list as current through 2020-06-30, based on county-level-and-above divisions, updated after competent departments report changes, and primarily for statistical work. It can help cross-check names and codes at that date; it does not provide boundary geometry or settle coastal/island extent. No applicable official county boundary agreement, standard map, marker record, local change notice, or licensed authoritative county geometry for these 50 components was available in this packet. Administrative role, current validity, exact border, and ownership therefore remain unresolved.

## Physical, water, and contact evidence

The inherited physical comparison identifies its source vintage as GSHHG 2.3.7, released 2017-06-15, with heterogeneous observation dates. [NOAA's GSHHG description](https://www.ngdc.noaa.gov/mgg/shorelines/shorelines.html) says the product combines World Vector Shorelines (shorelines) and WDBII (lakes, rivers, and political borders) and provides five generalized resolution levels. [The University of Hawaiʻi project page](https://www.soest.hawaii.edu/pwessel/gshhg/) describes those source roles. It is useful as a global, source-relative shoreline / lake screening layer; its global vintage and heterogeneous dates do not establish the legal county boundary, exact local land-water edge, channel state, or current island registration for this scope.

The European Commission Joint Research Centre's [Global Surface Water summary](https://publications.jrc.ec.europa.eu/repository/bitstream/JRC143989/JRC143989_01.pdf) describes Landsat-derived 30 m surface-water mapping for 1984–2021, with seasonal/permanent distinctions. It also documents limits for water under canopy, small rivers/streams/ponds, cloud/observation availability, and dynamic coastlines. This is a suitable *candidate* for future dated water screening, not legal land ownership or a county-boundary source. This packet did not retrieve, process, or overlay that raster; no new physical or geometry science was run.

The source-ready closure preserves contact features and positive-length-neighbor IDs in separate fields. For Dalian the complete family has 9 contact features but 8 positive-length neighbor IDs; for Qingdao it has 5 and 5. Equal counts in the latter do not make the concepts interchangeable. No contact is promoted to an administrative assignment by contact alone.

## Whole-family assessment

| Complete family | Whole components | Full contacts | Prior administrative-source coverage classification | Prior physical-source classification | Disposition |
| --- | ---: | ---: | --- | --- | --- |
| `gap-source-batch:61a32ae390d6bc77599ca035` — Dalian context | 34 | 9 | 4 no-source-intersection in the literal domain; 30 mixed, partial, or subject-unresolved positive coverage | 10 mixed-source-support; 24 unknown | All 34 remain unapproved |
| `gap-source-batch:aae5d81537d301c52e5303d1` — Qingdao context | 16 | 5 | 1 no-source-intersection in the literal domain; 15 mixed, partial, or subject-unresolved positive coverage | 5 mixed-source-support; 1 outside mapped L1 context; 10 unknown | All 16 remain unapproved |

The complete 50-ID inventory, full component pointsets, per-component routing and numeric row bindings, complete family rows, per-contact original/current full features, and their hashes are in `runs/final-1.json` and `runs/final-2.json`. Each family's source-fitness prerequisite remains the source-review gate; neither family records a compatible original administrative land component. The accepted source-ready preflight reports five local constructed-difference contradictions with positive mapped-land context across these components. Those are diagnostics only: there is zero mapped inland-water support in the retained summary, and “no mapped water” is not dry land. The inherited per-component records retain mixed support, source gaps, current-context aliases, unknown cause, and observation-date/precision limits. None is resolved here.

All 14 contact records are fully included and matched by original source `shapeID` and current atlas ID in the two reproducible outputs:

| Original/current source name | Complete source IDs |
| --- | --- |
| Changhaixian | `17275852B12997706676088`, `17275852B26462026898013`, `17275852B28680875187505`, `17275852B32574814957612`, `17275852B8642781403558` |
| Jiaozhoushi | `17275852B18968160632662` |
| Wafangdianshi | `17275852B24476472807157` |
| Qingdaoshi | `17275852B36539700725824`, `17275852B620737032798` |
| Zhuangheshi | `17275852B49602881017994` |
| Xinjinxian | `17275852B66176667563352` |
| Jimoshi | `17275852B77518624384720` |
| Jiaonanshi | `17275852B79149802712659` |
| Dalianshi | `17275852B83272093468807` |

The full IDs retain their `gb:CHN:ADM2:` prefix in the machine closure. The issue contract's 14 contact subjects are a neighbor/source-contact inventory, not proof that each touches the candidate by a positive-length edge. Existing regional work #208 and #347 remains separate and supplies no authority or approval to this packet.

## Reproduction and limits

The frozen source-closure assembler uses only Node 24.19.0 built-ins. The input/base vintage is `e9190786dbf758524a3bde513fc4bb4d1ed6a3e7`; the helper itself was not in that Git tree. The exact whole helper SHA-256 at run time was `daeb6cb71fdb0f8d9b9938bf61259513670204e713214ff542f7f5bd753e5aaa`, recorded by the producer-freeze receipt. The exact two executed positional invocations are preserved in each run receipt and `evidence-quality.json`; no `--frozen` or `--output` CLI options are supported. It authenticates the copied preflight's whole 393,708-byte body, exact family/component/contact rosters, each geometry binding, the pinned gzip and decoded source identity, the full source metadata/terms/current-part files, and the actual current-main Git blob identities before writing the closure. Negative controls reject omission, duplicate and foreign IDs, altered source-body hashes, contact or family rebinding, and contact/candidate geometry mutation. The original failure (`runs/attempt-1-failure.json`) and superseded pre-run/code vintages are retained.

The two final full runs both exited 0 at base `e9190786dbf758524a3bde513fc4bb4d1ed6a3e7`; each output is 633,213 bytes with SHA-256 `ea270f3be4fe993dbe5e9d1d567d8efef4348f3ea1a27505b91b762ea8505340`. `runs/output-comparison.json` records byte-for-byte equality. This is source/body/identity reconstruction, not a new overlay, physical classification, numerical diagnosis, or processing-cause determination.

### Remaining source questions

- Which competent authority's approved boundary diagram, agreement, marker record, or dated notice governs each coastal/island segment, and whether it can be lawfully retained and used at the required scale.
- Whether the 2017 source's stated count, source lineage, current administrative subjects, and coverage fit every component and neighboring county at the relevant date.
- Which independently sourced, dated land/water/coastline evidence can distinguish open water, seasonal water, reclaimed or tidal land, narrow channels, islands, and generalization/registration effects for each component at fit-for-purpose precision.
- Whether the two different license statements apply to the consumed simplified geometry and these retained derivatives, beyond the attribution already recorded.
- Every local numeric, replay, registration, missing-source, and outside-context sibling unknown; the source assessment does not infer an operator cause or certify a repair.

Those questions remain on the original #1337 acceptance as explicit findings; any boundary correction requires a new coordinated engineering scope. Parent campaign #1202 remains unfinished. This packet changes no shared geography, release, grid, hierarchy, history, content, or production records.


## Review corrections

The first evidence-manifest draft contained two metadata errors: it expanded PDDL incorrectly as “ODbL PDDL” and listed unsupported assembler flags. The manifest now uses the source metadata’s full PDDL name and the exact positional invocations in the two run receipts. The e919 SHA is explicitly the input/base vintage; the separate helper SHA identifies the uncommitted producer code. Prior and corrected values are preserved in `producer-vintage-correction.json`. These are metadata corrections only; the accepted closure outputs were not regenerated.
