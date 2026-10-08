## Purpose
Prepare a bounded, source-fit/no-loss proposal for the 15 selected components in the complete Norway family `gap-source-batch:3f21c83705d3cef5988b1295`. This is a research/proposal task only. It does not authorize changes to map geometry, hierarchy, databases, or publisher outputs.

## Pinned scope and custody
- Complete fine family: 400 physical components; preserve its full membership and family envelope `[11.76142546602688,65.06317643639146,17.7099,69.315253]`.
- Selected source-fit subset: the 15 components listed below. Do not redefine the family as these 15.
- Preserve all 36 complete positive-length Norway ADM2 neighbor IDs from the family source row; retain their source product feature IDs and zero-area contacts where applicable. Do not clip context to the selected subset.
- Relevant pinned records:
  - `coordination/engineering/global-source-comparisons-a-001-20261006/scientific/land-source-fitness-000.bin.gz` (family/route record)
  - `coordination/engineering/global-source-comparisons-a-001-20261006/scientific/components-000..011.json.gz` (component/source intersections and complete feature-contact rows)
  - `coordination/engineering/original-geography-source-corpus-20261006/catalogue.json` and preserved original payloads
  - `data/geography/part-17.json`, `data/hierarchy.json`, and `data/administrative-sources.json` (current target and recorded source lineage)
- Retained consumed source products: simplified NOR ADM2 (431 features, 4,724,258 bytes, SHA-256 `ab294b0b1dadfb937daa07963aa5995544fd8a16a6c9eb6261a82bb66401d90e`) and NOR ADM1 (11 features, 3,216,652 bytes, SHA-256 `a24bd867e42c8f2d7bdd07e723594f2d55736d50de8cf1e92062ae443a0f0f72`). Preserve exact edition, product URL, bytes, and hash in any result.

## Selected components and unique-compatible recorded subjects
- `153efbdb9c28eaba9ef8c4c834577ea44c875c2412493c2581530c2d9c7085f1` → `gb:NOR:ADM2:86288312B2671252892867` (Bindal)
- `1f453e7a436aa2f6a68edfb7433d3d1ec05c72b37ba78fac9b3d2542bc085efb` → `gb:NOR:ADM2:86288312B63422016976384` (Rødøy)
- `1f5426f5180aa4f5b7fd9991b5ae4816d56cb642c31d0937a4977da516f28f2b` → `gb:NOR:ADM2:86288312B44883610080028` (Dønna)
- `4f57d0af8235d8f547395c5d94bfeeb57e8e11168f65b7a566407213d17f1e5c` → `gb:NOR:ADM2:86288312B40270143357623` (Hadsel)
- `764b247eb21da38adac0b925bededbbb4dccaefa4b52b16976f20543a7ac3384` → `gb:NOR:ADM2:86288312B55921880538341` (Sortland)
- `7bad7bdf9b1203fe6c676eb2efde10b09ce394ad7d6d554eb557709d7704df35` → `gb:NOR:ADM2:86288312B55953165899475` (Lurøy)
- `8fb9f3f0d7df1c96ac452792fd4a9dbc7a45a576437550dd5b198424ceca14a9` → `gb:NOR:ADM2:86288312B75314465532393` (Meløy)
- `a82c3dc9980bf083cf15fb0edf1b98301259afb93761549c97ec57d73a41c5ce` → `gb:NOR:ADM2:86288312B44883610080028` (Dønna)
- `a92cac9c4c3d3a91286eca0e4890becd63441647c7fe7c4cdcc5e1aa167d4803` → `gb:NOR:ADM2:86288312B80996435697818` (Vefsn)
- `b6ba064b4525f0c75459a8d1aa05c25e9740cc46b9964f96983d61d6a9b4253a` → `gb:NOR:ADM2:86288312B95964377762384` (Leirfjord)
- `cc11d3c9c7f82d8c9073539568d8af915da17e21904a60a75d49eb5d2e63ae94` → `gb:NOR:ADM2:86288312B17604167467724` (Hábmer / Hamarøy)
- `dc92c796890cece117d3a70e1422fc2682a46caf3db64f06b2935b46e31b7a9f` → `gb:NOR:ADM2:86288312B99132950125054` (Øksnes)
- `e0bd74d0efc769aa5b98ba28ca22d0b37692f3387d344e32c14516b0fe062904` → `gb:NOR:ADM2:86288312B63422016976384` (Rødøy)
- `eb2b6c25d1a2b8ead2bcb67f7e0423b5f1cc5609ac3f600bb98cd6d5cb11db40` → `gb:NOR:ADM2:86288312B90944773523196` (Vevelstad)
- `f082e1ba3a2d1267b17f803511ec164c9c8649fd3fb9cc2bc752a4c833659508` → `gb:NOR:ADM2:86288312B2671252892867` (Bindal)

## Recorded fit and fail-closed findings
Current Atlas target metadata records all 15 under `framework:province:nordland:03c9b4c95d9e`, source `gb:NOR:ADM2`, reference year 2013, with `gb:NOR:ADM1` parent lineage. Candidate source records are unique-compatible recorded subjects; the preserved simplified ADM2 subject geometries cover the stored component/source intersections. This is exact recorded-target/source fit evidence, not proof of authority, accuracy, history, ownership, water status, or cause. Current member geometries are not byte/geometry identical to the retained source subject geometries.

A bounded exact lon/lat overlay against retained ADM2 and ADM1 products found:
- 13/15 candidate intersections covered by the recorded Nordland ADM1 parent; the two Rødøy candidate components above exceed the parent by small nonzero planar areas. Keep both explicit and unresolved; do not silently omit them.
- All 15 candidates add area beyond the current Atlas member. Strict `T.difference(T.union(C)).is_empty` no-loss passed 7/15; 8/15 had nonempty floating-residue differences (~1e-18–1e-17 coordinate-units²). No tolerance, snap, buffer, normalization, or repair was applied. Therefore no blanket additive/no-loss claim is supported.
- Source feature rows include 1–3 polygon intersections per component; retain every positive-area witness and every zero-area neighbor contact, distinguishing unique positive-area coverage from boundary-only contacts.
- Existing parent/target inconsistencies are inherited diagnostics and must be reported separately from candidate fit.

## Required proposal work
1. Reconfirm hashes, editions, exact source URLs, all 15 target metadata bindings, the full 400-member family, and all 36 neighbors against the pinned baseline.
2. Recompute and publish per-component exact predicates for source-subject coverage, parent coverage, current-target relation, strict no-loss, and all neighboring feature contacts. Preserve the two parent exceptions and eight strict no-loss failures explicitly. No tolerances or geometry repair.
3. Define a proposed bounded acceptance rule that fails closed on any wrong component/source/target/parent binding, missing family member or neighbor, source-byte/hash drift, missing contact, parent noncoverage, nonempty target-loss, invalid geometry, or adverse-control failure.
4. Include adverse controls that deliberately substitute a wrong source subject/edition/target/parent, remove a family neighbor/contact, alter a pinned source byte, and force nonempty target-loss. Each must be detected and prevent a positive proposal result.
5. State what evidence remains unavailable (complete ECO_ID0 geometry, registration accuracy, and Atlas feature-generation lineage). Keep authority, cause, water/ice status, history, rights, and ownership unknown unless separately evidenced.
6. Deliver a reviewable source-only proposal and exact predicate results. Any future geometry/GIS execution requires separate explicit admission and must satisfy its own issue contract. Do not write map/database/publisher data in this issue.

## Completion
A proposal may report only the exact candidates that satisfy every declared predicate. Any failed candidate remains explicitly unresolved with its adverse result. The work may conclude that no candidate is presently acceptable.

<!-- worldatlas-work:v1
{"max_prs":1,"depends_on":[],"scope":"Source-only Norway ADM2 source-fit/no-loss proposal for the 15 selected components, preserving the complete 400-component family, all 36 source neighbors, exact full/source/parent/target predicates, and fail-closed adverse controls. No map/database/publisher writes.","mode":"geography","owned_paths":["research/geography/norway-adm2-source-fit-1492/"],"evidence_quality":{"version":1,"manifest_path":"research/geography/norway-adm2-source-fit-1492/evidence-quality.json","subject_ids":["physical-component:153efbdb9c28eaba9ef8c4c834577ea44c875c2412493c2581530c2d9c7085f1","physical-component:1f453e7a436aa2f6a68edfb7433d3d1ec05c72b37ba78fac9b3d2542bc085efb","physical-component:1f5426f5180aa4f5b7fd9991b5ae4816d56cb642c31d0937a4977da516f28f2b","physical-component:4f57d0af8235d8f547395c5d94bfeeb57e8e11168f65b7a566407213d17f1e5c","physical-component:764b247eb21da38adac0b925bededbbb4dccaefa4b52b16976f20543a7ac3384","physical-component:7bad7bdf9b1203fe6c676eb2efde10b09ce394ad7d6d554eb557709d7704df35","physical-component:8fb9f3f0d7df1c96ac452792fd4a9dbc7a45a576437550dd5b198424ceca14a9","physical-component:a82c3dc9980bf083cf15fb0edf1b98301259afb93761549c97ec57d73a41c5ce","physical-component:a92cac9c4c3d3a91286eca0e4890becd63441647c7fe7c4cdcc5e1aa167d4803","physical-component:b6ba064b4525f0c75459a8d1aa05c25e9740cc46b9964f96983d61d6a9b4253a","physical-component:cc11d3c9c7f82d8c9073539568d8af915da17e21904a60a75d49eb5d2e63ae94","physical-component:dc92c796890cece117d3a70e1422fc2682a46caf3db64f06b2935b46e31b7a9f","physical-component:e0bd74d0efc769aa5b98ba28ca22d0b37692f3387d344e32c14516b0fe062904","physical-component:eb2b6c25d1a2b8ead2bcb67f7e0423b5f1cc5609ac3f600bb98cd6d5cb11db40","physical-component:f082e1ba3a2d1267b17f803511ec164c9c8649fd3fb9cc2bc752a4c833659508"],"pins":{"nor_adm2_simplified":"ab294b0b1dadfb937daa07963aa5995544fd8a16a6c9eb6261a82bb66401d90e","nor_adm1_simplified":"a24bd867e42c8f2d7bdd07e723594f2d55736d50de8cf1e92062ae443a0f0f72"},"review_kind":"source"}}
-->
