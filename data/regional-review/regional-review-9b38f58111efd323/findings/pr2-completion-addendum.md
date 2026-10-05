# Yunnan packet 3: area, parent and boundary-lineage addendum

Assessment date: 2026-10-05. Scope: the exact 40 IDs in `scope.json` (canonical compact-JSON roster SHA-256 recorded in `area-purpose-parent-assessment.json`). This is the second bounded PR for issue #451; PR #916 remains preserved as the first roster/source review. No source, ID, geometry, release pin, or prior finding is replaced.

## Area purpose and neighboring granularity

The retained Natural Earth Admin-1 evidence groups Chongqing Municipality, Guizhou Province, Sichuan Province, Tibet Autonomous Region, and Yunnan Province under its own Southwest China region. It is a 2022 repository vintage, generalized source-defined context. The 2025 Yunnan Civil Affairs roster independently places these scoped county-level units within Yunnan. Together these sources support a candidate interpretation of Yunnan as a province-level territory grouped above prefecture-level units. They do not establish the Atlas's custom tier design, the completeness of all 125 Yunnan inventory IDs, or legal boundaries. The exact Natural Earth source commit, evidence table and register hashes are listed in `sources/pr2-source-access-register.json`.

## Parent findings

- **Honghe (13/13): insufficient evidence.** The official 2025 roster count agrees with the pinned set. That does not prove 2017-to-2020 parent lineage or boundary membership.
- **Qujing (8/9): correction needed.** The official roster names Qilin, Zhanyi and Malong districts, Xuanwei City, and five counties. Atlas has eight members and the source label `Qujingshi`; the 1997 official history says the former county-level Qujing City was divided into Qilin and Zhanyi. No polygon crosswalk identifies the retained shape. Preserve IDs and defer identity reconciliation to blocked #914.
- **Zhaotong (11/11): insufficient evidence.** Equal current and pinned counts do not resolve `Zhaotongshi` versus current Zhaoyang District or `Ludingshi` versus Ludian County, nor establish parent lineage or geometry. See #914 and #915.
- **Wenshan (8/8): correction needed.** Current count agreement does not resolve retained `Wenshanxian` and `Jianshanxian` against Wenshan City and Yanshan County. Names alone do not prove territory. See #914 and #915.

The current Yunnan-wide count of 129 at 2025-09-30 versus 125 in the 2017 source/inventory is a cross-vintage reconciliation signal only, not evidence of four omissions. Issue #448 receives the whole-region roster/code integration handoff.

## Boundary lineage comparison

Run `python3 data/regional-review/regional-review-9b38f58111efd323/compare_boundary_lineage.py` from the repository root. The script reads the exact frozen issue baseline commit in `scope.json`, matches the 40 retained source IDs to pinned Atlas polygon geometries and compares normalized coordinates rounded to four decimal places. Result: 0 of 40 geometries are equal at that precision; 40 differ. The source has 40 parts and 2,684 vertices; Atlas has 42 parts and 2,565 vertices. BBox equality is also recorded per row and is false for all 40. Counts vary by parent: Honghe 13/13 parts and 840/863 vertices (source/Atlas); Qujing 8/8 and 573/503; Wenshan 8/10 and 639/637; Zhaotong 11/11 and 632/562.

These are reproducible lineage/representation differences, not findings that Atlas is wrong: source and Atlas geometry vintages and derivation differ. This comparison does not establish positional accuracy, topology, adjacency, islands/fragments, legal completeness, or a correction direction. #915 owns validation of the 40 exact boundaries against authoritative evidence.

## Source access, limits and handoffs

The official Yunnan Civil Affairs roster and the four 2023 administrative-code standards were discoverable through official indexed material, but direct page/PDF retrieval timed out. No response bytes or hashes are claimed. The source register contains each URL, dates, factual use limits, rights status and concrete restoration instructions. The Qujing historical page was streamed and hashed by the prior source review, but its response body was not retained; its exact hash and restoration caveat are recorded. Natural Earth bytes are retained in the prior #449 packet and are bound by exact source table/register hashes.

The geoBoundaries derivative declares PDDL, but the upstream license/source chain has malformed third-party links. No original authoritative boundary source or verified reuse terms for official pages/PDFs were obtained. Preserve these as explicit limitations. Engineering/geographic handoffs: #914 for identity and Qujing roster discrepancies, #915 for all 40 official boundary/provenance checks, and #448 for whole-Yunnan reconciliation. This packet does not approve regional interiors, authorize imports, or certify the whole region.
