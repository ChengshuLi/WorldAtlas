# #421 reproduction guard erratum

Date: 2026-10-06 (America/Los_Angeles). This packet corrects how the retained batch 6 research can be reproduced. It does not replace or edit the original #421 packet, source bytes, report outputs, IDs, source vintages, hierarchy, or geographic findings.

## Exact scope and prior findings

The immutable issue scope contains 230 Atlas subjects: 226 Greece `gb:GRC:ADM3` records and four Kosovo `gb:XKX:ADM1` records. The 226 Greek rows match 227 native features in the retained 2010 source because Oraiokastro is one Atlas multipart assembled from two source features. The Kosovo source package is an ADM1 dataset with seven polygons while its metadata reports 48 units. The earlier packet cites a Kosovo statistical inventory of 38 municipalities; the official release page did not expose its body during this run, so that count is retained as prior evidence rather than freshly verified. These are source-era identity observations, not proof of present-day legal boundaries.

There are 17 referenced province parents and three referenced areas, not 20 new subject edits. The issue-pinned areas are Greece (201 of 281), Kriti (25 of 25), and Yugoslavia (4 of 1,169). The prior packet records them as inherited WGSRPD level 3 geographic/botanical-country groupings. `Yugoslavia` here is a legacy framework label and does not assert a present-day sovereign territory. The frozen region geometry and membership are unchanged.

The prior row-level assessment recorded 225 `insufficient-evidence` outcomes and five `correction-needed` rows. Those are carried forward unchanged. It remains unresolved whether every current Greek municipality/island/city fragment and every Kosovo district has the correct current legal identity, boundary, parent and neighboring granularity. A 2010 layer cannot establish current completeness. The source packet's 2016 Greek ADM2 layer is parent context only; the 2021 Kosovo ADM1 layer is not treated as a municipal boundary authority. The legacy area/IoU/adjacency screens are diagnostics only.

## Source and uncertainty review

The official Greek Ministry of Interior's 2024 local-government report distinguishes first-level municipalities from second-level regions and reports 332 municipalities and 13 regions as of 2024. It states the territorial area of a municipality comprises merged local-authority territories. This supports the role distinction and count, but supplies no exact feature-level crosswalk for these 230 historical subjects. The Ministry's 2019 circular documents five municipal dissolutions and twelve successor municipalities, reinforcing that the 2010 roster cannot be equated to the present roster without a legal crosswalk.

The Hellenic Parliament's revised Constitution, Article 105, describes Mount Athos/Aghion Oros as a self-governed part of the Greek State and describes administration through the twenty Holy Monasteries. That is material to the special-role question; the text does not establish the exact polygon for the retained source feature.

ELSTAT's published digital cartographic catalog labels its 2011 and 2021 Kallikratis boundary products as census products and lists administrative-level layers. These are useful dated statistical/cartographic evidence, not independent proof of current legal municipal boundaries. The catalog's 2021 settlement-cartography description uses 2015–2016 orthophotos, so it does not certify current island or settlement completeness.

The Kosovo Official Gazette identifies Law 03/L-041 on municipal administrative boundaries, published 2008, and lists subsequent amendments. This establishes a legal source path for future identity work, but neither the retained seven-feature source nor the page metadata alone proves a complete current 38-municipality crosswalk. The cited Kosovo Agency release page (8471) did not expose release content in the inspected response; no fact is inferred from that failed extraction. Its exact law annexes, consolidated current roster and boundary files still need source restoration and inspection under the existing follow-up work.

Kew's Plants of the World Online explains that its Level 3 WGSRPD units are “botanical countries” and may not follow political boundaries. This supports treating the three inherited area labels as a phytogeographic framework rather than political territories; it does not identify their exact polygon or certify the Atlas area geometry.

Neighboring granularity remains bounded to the exact context in the prior packet: adjacent North Macedonia packet #422 records a 2019 Statistical Office roster crosswalk against 2016 geometry. It is only a neighboring source-vintage lead; it does not establish the Greek/Kosovo border or a current cross-border parent relationship.

Inspected official references on 2026-10-06 (not copied into this repository):

- Hellenic Ministry of Interior, *Structure and Operation of Local and Regional Democracy, Greece, Situation in 2024*: <https://www.ypes.gr/wp-content/uploads/2024/06/STRUCTURE-OPERATION-LRD-ENGLISH-VERSION-2024.pdf>. Page 3 permits reproduction with source attribution; source attribution is retained here. The report is a structure/count authority, not the missing feature-level boundary source.
- Hellenic Parliament, Constitution, Article 105: <https://www.hellenicparliament.gr/vouli-ton-ellinon/to-politevma/syntagma/article-109/>. The official page's current revision metadata reaches the 2019 revision; the article describes status and administration, not a polygon.
- Hellenic Ministry of Interior, Circular 15 / 24740 (2019): <https://www.ypes.gr/wp-content/uploads/2019/04/egk24740-03-04-2019.pdf>. It identifies five dissolved municipalities and twelve successors; it is not a full scoped-identity crosswalk.
- ELSTAT, Digital Cartographic Backgrounds: <https://www.statistics.gr/digital-cartographical-data>. Its administrative-boundary products are explicitly grouped by census years 2011 and 2021; rights and current legal applicability of individual downloadable layers remain unverified.
- Kosovo Official Gazette, Law 03/L-041: <https://gzk.rks-gov.net/ActDetail.aspx?ActID=2518>. The catalog page identifies publication and amendments; annex-level features and current consolidation were not verified here.
- Kosovo Agency of Statistics, Release 8471: <https://ask.rks-gov.net/Releases/Details/8471>. The page body was not available in the inspected response; no underlying release values are asserted.
- Royal Botanic Gardens, Kew, Plants of the World Online, About: <https://powo.science.kew.org/about>. It describes Level 3 as botanical countries and cautions these units may not follow political boundaries; it is a classification-purpose source, not a boundary product.

The original `source-inventory.json` and `evidence-quality.json` remain byte-pinned at packet merge `11e0633d40a7c23dc6cda2f71c98edf48a9e0f2e`. Their source release URLs, retrieval dates, source hashes and restoration instructions remain authoritative for this packet. In particular, the 2010 Greek source's contradictory license fields remain unresolved; Kosovo GeoBoundaries attribution/share-alike terms do not by themselves settle Atlas redistribution compatibility; six official source bodies remain restoration-only in the historical packet. This erratum adds no copied official source data and closes none of those gaps.

## Guarded reproduction

`original-input-pins.json` preserves all 47 complete-file input pins at their actual commits: 14 older baseline files at `5b72dc3adf48b089c3319b18c3a447468196176a` and 33 batch packet files plus the shared immutable helper at `11e0633d40a7c23dc6cda2f71c98edf48a9e0f2e`. The guarded runner verifies every pinned Git blob and any materialized worktree copy before execution, rejects symlinks in pinned working-tree paths, limits each object to 32 MiB and each full run admission to 256 MiB, then intercepts historical output paths lexically before resolution and redirects only the eight known output names to new exclusive run folders under this owned packet. Existing source/report files are never write targets. It verifies the inputs again afterward and compares generated outputs to the original whole-file report hashes.

Run using Python 3.12.14, Shapely 2.1.2 and pyproj 3.7.2 from repository root:

```sh
python3 data/regional-review/southeastern-europe-batch6-reproduction-421-erratum/reproduce_guarded.py --run-id UNIQUE-LOWERCASE-VINTAGE
```

Run IDs are exclusive: if a run directory exists, choose a new ID and preserve the previous outputs. The runner executes each retained mechanical phase twice, rejects wrong baseline/source/code bytes, exercises the previously demonstrated whole-file Kosovo name-drift probe in memory, refuses an existing output sentinel and a symlinked historical output whose target is an external sentinel, and emits typed positive/negative/reproducibility receipts. The original scripts remain unchanged and must not be run directly because their historical output paths are overwrite-capable.

The final run's date and execution results are in `runs/verify-20261006-symlinkfix/reproduction-results.json`; the two roster and two geometry output sets and typed receipts are stored beside it. All 16 generated-output observations (eight files, two runs each) match the original reports byte-for-byte. Earlier attempts remain preserved in their own folders for traceability; only the `verify-20261006-symlinkfix` run supplies the completed typed validation receipt set, including the symlink-output control. This proves reproduction identity under the recorded environment, not legal boundary truth, source licensing compatibility, complete territorial coverage or regional approval.
