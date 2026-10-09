# Melanesia operational batch evidence handoff

Research-only exact-ID handoff for [issue #1643](https://github.com/ChengshuLi/WorldAtlas/issues/1643), child of the global coverage umbrella [#1202](https://github.com/ChengshuLi/WorldAtlas/issues/1202). It covers the complete existing operational batch `gap-operational-batch:241e2ce0cd7b6be8a234558b`: all 25 component IDs across 15 complete fine families.

## Selection and scope

The existing work index and source-fitness priorities identify this batch as a complete operational unit. Before claiming it, the exact 25-ID roster was compared with the retained original 363-component batch, the 318-component GEO3 next batch, the 4,674-component GEO5 North America batch, and all 13 source-fitness priority exclusions; the intersections were empty. Its country set is Indonesia, Papua New Guinea, and Solomon Islands, with aggregate extent `[131.16164961394534, -22.250895415971673, 167.18462171070186, -0.8014423863488105]`, geographically separate from the excluded Alaska/North America, Arctic, and pilot scopes. These are roster/scope checks against retained indexes, not a new global coverage computation.

## Result

The packet selects all 25 full candidate geometries from the existing custody-verified `components-v3` files and joins them to their original retained physical comparison rows and source-binding rows. It reuses #1424's full two-batch context and #911's New Caledonia source findings. No source retrieval, GIS overlay, water classification, authority review, or processing replay was performed.

| Evidence state | Count | Meaning |
| --- | ---: | --- |
| Exact component and physical rows | 25 | Full original component geometry plus the retained physical comparison row is in the packet. |
| Admin binding rows | 22 | Source relation is recorded; it does not itself establish a unique target. |
| Unique compatible source subjects | 8 | The exact source subject ID is retained for eight rows. |
| Reused native-ready evidence inputs | 5 | Full candidate, current target, source feature, original physical record pointer, and recipe/source binding are assembled from prior evidence. |
| No unique compatible target | 14 | Eleven partial/subject-unresolved records and three with no literal-domain source intersection remain held. |
| Missing admin-binding row | 3 | Two New Caledonia components and one Indonesia component have no retained admin binding. |
| Physical source fitness | 25 | Every row remains `unknown-source-fitness-and-observation-date`; physical authority is unapproved. |

The five reusable input rows are already covered by #1424: Isabel (`2b39965d`), Choiseul (`10f89b38`), Western (`721838ee`, `854f216a`), and Central (`8bce0aff`). These are source-relative evidence inputs, not approved edits or physical-land determinations. `native-ready-inputs.jsonl` contains each complete candidate geometry, its exact current target geometry, the corresponding retained source product feature, the existing admin binding, the original physical comparison row, and the exact GSHHG native-record subset offsets/hashes.

The three rows without an admin binding are:

- `physical-component:1c0757a8b6119db62215af58de5bf454137c634b347fe48a6a09d44a153fdb94`
- `physical-component:f81af9bb2943222d5554fb978efb394f4c24e1bfec12cb4e022c2b58d49fe6d3`
- `physical-component:d4b45985f5e76f82c8f4317b6b0453941c4ae25c72a999cdd20d8ec7ce6e3b23`

The first two are the New Caledonia components in family `gap-source-batch:72eb9ee2b20a1889cac1928e`. Their retained family record names `NCL-1259` as contact context; it does not establish a unique source or current target for either candidate. #911's official source review is reused as context and did not compare these candidate geometries. The third missing row has mixed physical support in Indonesia and likewise has no unique retained administrative target.

The remaining held records are exact-ID rows in `component-outcomes.jsonl`. Eleven have positive but partial or subject-unresolved source coverage; three have no source intersection in the literal comparison domain. Three additional components have unique source IDs but are mixed-support or outside mapped Level-1 context, so they are not promoted to native-ready candidates. No target is inferred from nearby names or contact relations.

## Source and physical limits

The Solomon Islands product is the simplified geoBoundaries ADM1 release at commit `9469f09`, represented year 2021. The retained metadata update date is 2023-01-19 and build date 2023-12-12; an effective boundary date is unknown. #1424 records unequal source/current contact geometries and preserves the attribution statements without interpreting them as approval.

The physical comparison uses retained GSHHG 2.3.7 Level-1 pointsets, release dated 2017-06-15. Its source documentation records heterogeneous or unknown observation dates. Mapped-land support is relative to those pointsets. It does not establish current dry land, shoreline truth, legal boundary, ownership, or cause. The retained license documents differ in version wording; this packet makes no legal interpretation.

For Indonesia and Papua New Guinea, the retained records identify `gb:IDN:ADM2` and `gb:PNG:ADM3` products with partial or unresolved subject relations. Where a binding row is missing, source coverage is absent, or a subject is not unique, the exact outcome stays held. Natural Earth remains generalized reference context only.

## Files

- `candidate-geometries.geojson`: all 25 exact original component features, preserving source coordinates and properties.
- `component-outcomes.jsonl`: one exact-ID joined disposition for every component, with full retained physical row, admin binding where present, target ID only when unique, and native source record pointers.
- `native-ready-inputs.jsonl`: five reusable, source-relative input bundles from #1424.
- `source-target-geometries.geojson` and `current-target-geometries.geojson`: the five exact identified Solomon Islands source and current target features used by those bindings.
- `family-outcomes.json`: all 15 complete family summaries for the batch.
- `evidence-quality.json`: byte-bound evidence inventory for issue #1643.
- `assemble.py` and `finalize_manifest.py`: deterministic standard-library selection, joins, and evidence manifest construction. They do not run spatial operations.

The evidence stage is complete with unresolved facts recorded. Geographic approval remains unapproved, and no current geography was changed.
