# Guangdong and Guangxi current-roster addendum

Research date: 2026-10-06. This supplement covers the exact 180 retained CHN ADM2 rows in the Guangdong and Guangxi issue scopes (92 and 88 respectively). The compact Hong Kong/Macao identities and 18 Hainan rows remain with their earlier evidence. The ordered 200-row v5 issue scope and all pins are unchanged.

## Current official roster evidence

The Guangdong Government's 2026-04-01 administrative-divisions article links a readable table current through 2025-12-31. It lists the current prefecture-level cities and county-level names by parent, with 21 prefecture-level and 122 county-level divisions. Its image and the article response were hashed during inspection, then removed because redistribution terms were not established; source/pr2-source-register.json records their exact observed byte counts, hashes, URLs and restoration instructions. The names permit current status leads for same-toponym legacy labels, but the table contains no code-to-2017-shapeID correspondence or geometry.

The Guangxi Government's official page, dated 2026-03-25 and sourced to the regional statistics and civil-affairs departments, reports 14 prefecture-level and 111 county-level divisions as of 2025-12-31 and lists the current counties beneath each city. The official indexed text lists Long'an County under Nanning; Zhaoping County under Hezhou; and no Zhaoping unit under Wuzhou. The official source host presented an expired TLS certificate here, so its original response bytes and hash are not claimed. Exact URL, access status and restoration steps are recorded in the source register.

## Exact row leads

The reproducible row ledger is findings/pr2-current-roster-crosswalk.csv. It retains all 180 source IDs, the 2017 source names, the Atlas's current parent IDs/names, prior row classifications and a conservative crosswalk disposition.

- **Long'an:** gb:CHN:ADM2:17275852B2033650787942 (Longanxian) is assigned to Atlas parent Chongzuo. The current official Guangxi roster lists Long'an under Nanning and not Chongzuo. This is a sourced parent-conflict lead. The 2017 source has no current code or parent key, so preserve the ID and geometry and validate the code-to-shape relationship before proposing a hierarchy edit.
- **Zhaoping:** two distinct source IDs named Zhaopingxian occur under Atlas parents Hezhou (gb:CHN:ADM2:17275852B21404145859662) and Wuzhou (gb:CHN:ADM2:17275852B79176055066883). The current official roster places Zhaoping under Hezhou only. Treat this as a duplicate-name/source-identity conflict; the evidence does not identify which shape is Zhaoping or what the Wuzhou shape represents.
- **Legacy names and status:** the scoped source includes same-toponym leads such as Panyu, Zengcheng, Conghua, Huadu, Nanhai, Shunde, Gaoming, Chenghai, Chaoyang, Qujiang, Huiyang, Dianbai, Xinhui and Gaoyao. The current Guangdong roster uses district names for these candidates. Guangxi's roster similarly shows current status/name changes for Pingguo, Tianyang, Jingxi, Hengzhou, Wuming, Yongning, Lingui, Lipu, Liujiang and Yizhou. IDs and exact candidate display names are in the row ledger; these are candidate name/tier crosswalks, not certified polygon identity or boundary corrections.
- **Declared source role:** findings/pr2-source-role-review.json lists 30 scoped source features whose names match current prefecture-level city names even though the 2017 geoBoundaries metadata declares County Level (ADM2). These records may be city-core or historical representations. Neither their tier nor the current Atlas parent can be resolved from the source's names and ADM number alone.

These findings leave all 180 rows insufficient-evidence for present-day legal boundary correctness, code-level parentage, source completeness, and neighbor alignment. The row-status classifications from PR1 are not promoted by a roster match or count. Roster counts are not used as proof of spatial completeness.

## Boundaries, neighboring units, and reuse

The Guangdong public standard-map portal permits public use of its standard map products with the review number shown and says modified maps need review. Its official map guidance calls out Dongsha, Hong Kong/Macao boundary depiction, and the Guangdong-Hainan line. These are useful island and neighbor checks, not machine-readable boundary evidence. The Guangxi Natural Resources Department's indexed standard-map page lists maps for its 14 cities, with entries dated 2023. The department's 2021 1:10,000 DLG catalogue notice is a possible vector-source retrieval path: the notice says administrative division layers were updated, but full-element updates covered selected areas only. Its catalogue extents, source vintage, permission and completeness remain unverified.

No current official legal GIS layer, stable current code crosswalk, boundary license decision, polygon overlay, topology test, or complete neighboring-edge check was obtained for these 180 rows. The retained geoBoundaries source reports 2017 vintage and PDDL 1.0, but its upstream source/license links are malformed; it has no present-day official administrative code or parent code. Official roster pages have no blanket reuse terms identified. Do not digitize official map images as a substitute for vector data.

## Handoff

Created bounded follow-up [#1063](https://github.com/ChengshuLi/WorldAtlas/issues/1063) for these exact 180 source IDs. It requests current official code/name crosswalks, lawful boundary-source restoration, and row-level parent, boundary, completeness, neighbor and reuse review. It retains the v5 pins and prohibits shared geography changes. Hainan remains in its separate follow-up #1053.

This is partial evidence for issue #408 only. It does not approve a region or certify current boundaries, and the PR must use Refs #408.
