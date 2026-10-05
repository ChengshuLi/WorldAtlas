# PR 2 source-role and area-purpose addendum

**Retrieved:** 2026-10-05 (America/Los_Angeles); Natural Earth sources retrieved 2026-10-05 UTC.
**Scope:** additional evidence for the area and source-role findings in [the original issue #449 report](report.md). This addendum does not replace or repin that evidence.

## Natural Earth source role and vintage

The area metadata in `data/hierarchy.json` cites Natural Earth Admin 1 states/provinces at commit `ca96624a56bd078437bca8184e78163e5039ad19` (commit date 2022-06-02). The retained source README labels its theme 10m Admin 1 — States, Provinces, version 5.1.1, and describes over 4,500 internal first-order administrative units. It says the displayed default is *de facto* control rather than *de jure* boundaries, calls the theme beta and difficult to keep current, and says countries' Admin-1 units are frequently rearranged. Its methodology also says a separate version should be created for region groupings of Admin-1. The exact README and repository license are retained as deterministic gzip streams under `source/natural-earth-admin1/`; decompression reproduces the original bytes and the raw and compressed SHA-256 values are in `source-register.json`. The repository license states the Natural Earth map data is public domain.

The exact pinned source geometry/attribute files are retained in the same directory. The reproducible extractor `inspect_natural_earth_admin1.py` validates their bytes and hashes, confirms the DBF and shape-index record counts, and emits `natural-earth-admin1-southwest-china.csv`. In those source records, Chongqing (`CN-CQ`) is typed Municipality, Guizhou (`CN-GZ`) and Sichuan (`CN-SC`) Province; all three have source attributes `region=Southwest China` and `region_sub=Western`. The same source-defined regional grouping also contains Tibet and Yunnan, which belong to adjacent packets. This supports the regional group label and the source's first-order name/class role at its own vintage. It does not establish present legal status, current boundaries, fine-scale completeness, or current Atlas geometry agreement.

## Issue-scoped interpretation

All 228 issue locations remain `insufficient-evidence` for current identity, parent and boundary verification. The pinned 2017 gbOpen source remains an ADM2 / County Level historical source. Natural Earth's 2022 Admin-1 layer is a different, generalized source and cannot validate those ADM2 geometries or reproduce the separate 2020 greatest-overlap parent assignment. Only 3 of 228 Atlas geometries match the pinned 2017 source after the existing reproducer's 4-decimal comparison; the 225 reductions remain lineage questions, not polygon-error findings.

The three area subjects remain individually `insufficient-evidence` pending the complete role/member/boundary review. Natural Earth's attributes provide evidence for a Southwest China macro grouping and component province/municipality classes, but they do not independently prove the custom area tier. Chongqing is a single-child wrapper over a municipality; that is a review reason, not an error by itself. Guizhou's nine children are administrative prefecture-level groupings, not nine Natural Earth first-order provinces. Follow-up #934 owns the exact Chongqing and Guizhou area IDs for that tier-purpose question. Packet #450 reviewed its separately owned Sichuan area subset; #448 integrates shared conclusions. Follow-up #917 owns the 228-location current roster, parent and boundary lineage gaps.

## Current official roster access attempt

Search-indexed results identified the Chongqing Civil Affairs Bureau's `2025年12月重庆市行政区划及行政区划代码` page (2026-01-19), the Guizhou Civil Affairs Department's `贵州省行政区划统计表（截止2025年12月31日）` page (2026-01-28), and a Sichuan Civil Affairs Department 2025 year-end code table. Search snippets expose aggregate counts, including 37 county-level units in Chongqing, 88 in Guizhou, and 183 in Sichuan. Direct retrieval of the official Chongqing and Guizhou pages timed out in this runtime; the Sichuan year-end table bytes were likewise unavailable. These counts differ from Atlas's full area totals (33, 82, and 158) but are not evidence of which units are omitted or whether the population definitions match. No scoped row was matched from a search snippet. Exact original hashes are therefore unavailable, and #917 remains the actionable source-restoration/crosswalk follow-up.

Restoration leads (do not treat search snippets as retained source bytes):

- Chongqing Civil Affairs Bureau: <https://mzj.cq.gov.cn/zwgk_218/zfxxgkml/tzgg/202601/t20260119_15332641.html> (page identifies a downloadable 2025-12 Excel table). Chongqing Municipal Government summary, which reports 37 county-level districts/counties: <https://www.cq.gov.cn/zjcq/sqgk/cqsq/202601/t20260125_15350959.html>.
- Guizhou Civil Affairs Department: <https://mzt.guizhou.gov.cn/xwzx/tzgg/202601/t20260128_89347775.html>.
- Sichuan Civil Affairs Department source listing and 2025-12-31 table title: <https://mzt.sc.gov.cn/scmzt/mzxx/article_list_2.shtml>; retrieve the exact listed source table before row-level use. The Sichuan Provincial Local Records Work Office's 2025-09 report also states 183 county-level units and reports no 2025 county-level change through its report date: <https://www.scsqw.cn/upload/main/contentmanage/article/file/2025/09/22/202509220927406930.pdf>.

No count discrepancy is labeled a correction or omission without a full source crosswalk. No boundary was changed, certified or compared topologically in this addendum.
