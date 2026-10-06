# South America batch 4: baseline-linked crosswalk validation

**Issue:** [#1116](https://github.com/ChengshuLi/WorldAtlas/issues/1116)\
**Upstream work:** [#445](https://github.com/ChengshuLi/WorldAtlas/issues/445), [PR #935](https://github.com/ChengshuLi/WorldAtlas/pull/935), and later additive purpose/scale evidence in [PR #948](https://github.com/ChengshuLi/WorldAtlas/pull/948)\
**Evidence baseline:** commit `7245eca6d56ee71fd1f40631c72116167ac5037d`, the immutable snapshot named by #1116\
**Retrieved:** GitHub records through GitHub REST API and official source pages inspected 2026-10-06. Inherited source downloads retain their original 2026-10-05 retrieval dates.

This corrective packet addresses a specific false positive: the original #935 reproducer passes when one Chile `source_shape_id` is replaced with `FABRICATED-NOT-A-SOURCE-ID`. It checks the asserted `name_exact_match` flags and row totals but never compares those candidate source-member fields to the retained baseline's actual member ID and name. The reproduction log shows the old script still returning 214 “exact source name links.” A replacement validator now checks every candidate row against the exact #935 feature bytes and member metadata at the issue-pinned ancestor.

## What was checked

- All 215 issue subjects occur exactly once in the pinned `data/geography/part-2.json`, `part-20.json`, or `part-28.json`; those parts are present in the pinned world index. The roster agrees with the immutable #445 scope digest.
- The baseline crosswalk has exactly 215 unique rows: 167 Chile ADM3 records, 47 Paraguay ADM2 records, and the Asunción aggregate. For each row, the checker verifies the actual feature ID, name, parent ID, source tier/role, reference year, license field, geometry type and vertex count. For 214 unit rows it also verifies the candidate member ID and name against baseline `metadata.original_id` and feature `name`. The city aggregate correctly has no direct source-shape join.
- Each of the 39 distinct scoped parent IDs resolves to an actual hierarchy `province` record. Its name, area parent, candidate child count and the full 39-row parent review are checked. The machine scope and actual data contain 39 parents; an older prose count of 32 is not used as the roster.
- All five area records match the immutable issue scope and baseline hierarchy by identity, name, partial/full status and owned/full member counts. The retained scopes for companion work #444 and #446 remain outside this packet's subject ownership.
- Nine negative controls reject fabricated/missing/duplicate subjects; wrong names, parents, source tier, member ID/name or match flag; and consistently rehashed corrupted candidate rows. A valid positive control passes. The exact original false-positive is also reproduced without network access or changing any original file.

## Coverage numbers and meaning

| Evidence question | Result | What it means |
|---|---:|---|
| Declared subjects | 215 | Exact immutable issue roster |
| Baseline features found | 215 | Presence in the pinned Atlas snapshot, not source completeness |
| Actual parent IDs checked | 39 | Stored Atlas province relationships, not legal parentage |
| Candidate source-member ID/name pairs matching retained baseline metadata | 214 | Corrective candidate-to-baseline validation only |
| Original geoBoundaries feature rows independently rechecked in this packet | 0 | Full-country source files were not restored |
| INE 2022 response bytes independently rechecked | 0 | The exact recorded response was not retained or fetched again |
| Legal boundary, parenthood or regional approval established | 0 | All remain outside this corrective scope |

The phrase “214 baseline metadata matches” is deliberately narrower than a verified source join. The source register records Chile geoBoundaries ADM3 as 2020 / CC BY 3.0 IGO and Paraguay geoBoundaries ADM2 as 2012 / CC BY 4.0, with source-provider descriptions, original hashes and restoration instructions. The original full-country GeoJSONs are not in this packet. Chile is 171,783,952 decompressed bytes (SHA-256 `f3833ce1965394ae705e3793b50bdd007775b43da604251871deffed04f3bffd`); Paraguay is 45,589,273 bytes (SHA-256 `d42bd1f910070bf805e32dc46708230c91f58902a3c8792eda60928b22362858`). Both exceed the 32 MiB per-file evidence cap. This packet does not fetch, retain, partition or bypass that cap. `source-observations.json` gives exact URLs, commits, hashes, restoration instructions, license records and the unresolved boundaries of each claim.

## Subject role, parentage, vintage and neighboring granularity

The retained geoBoundaries metadata describes the Chile rows as communes at ADM3 with ADM2 province parents, reference year 2020, and the Paraguay rows as districts at ADM2 with ADM1 province parents, reference year 2012. The checker confirms that these recorded relationships are copied consistently into the candidate crosswalk and match its pinned Atlas features. It does not demonstrate that the labels or hierarchy are legally current.

For Chile, SUBDERE's official [2023 DPA notice](https://www.subdere.gov.cl/sala-de-prensa/subdere-publica-nueva-versi%C3%B3n-de-los-l%C3%ADmites-de-la-divisi%C3%B3n-pol%C3%ADtico-administrativa) describes national commune/province/region polygons, with interior lines from SUBDERE, international lines from DIFROL and the coast from IGM, and periodic checking against the statutory DPA descriptions. The linked 2023 archive is cited in the inherited source register but was not extractable in that review; no explicit reuse terms were located. It was not restored here, so it supports a better source lead, not row-level verification. The inherited packet also records a mismatch between geoBoundaries' 345 features and a 346-commune SUBDERE count. This discrepancy remains unresolved.

For Paraguay, the official [INE GeoNode district metadata](https://geonode.ine.gov.py/catalogue/csw_to_extra_format/fa775300-fe68-472d-9d75-e87594c2b093/distritos.html) identifies a 2022 census/statistical layer, published in 2024, and explicitly says its district limits are approximate, non-legal and for statistical use. It displays “Public Domain”; the inherited source register describes the exact 55,137-byte WFS response as public information with attribution required. Since the response is unretained, this license difference is left unresolved. INE's 47 recorded name/code/department rows are statistical candidate mappings only. The [National Cadastre's 2024 district-limits study page](https://www.catastro.gov.py/site/47/Estudio-de-Limites-Distritales-de-la-Republica-del-Paraguay_V2023) says its ongoing research reviews legal-framework uncertainty across 263 districts; it is national context, not proof about individual scoped laws.

The five inherited Atlas areas have a separate, non-administrative granularity question. PR #948's purpose review compares them with the historical WGSRPD plant-distribution framework; the same row counts do not indicate equivalent legal or operational units.

| Atlas area | Atlas province children | WGSRPD Level 4 rows in inherited review |
|---|---:|---:|
| Chile Central | 31 | 7 |
| Chile North | 10 | 3 |
| Chile South | 14 | 3 |
| Juan Fernández Islands | 1 | 1 |
| Paraguay | 18 | 1 |

Those Level 4 tables remain restoration-only because no reuse terms were located. Parent grouping, every neighboring seam, island/coast completeness, positional accuracy and current legal roles remain unresolved. The Asunción aggregate stays unresolved as an undated Natural Earth-derived capital territory with four recorded 2012 district members; their IDs do not establish a current legal unit, extent or parent. A duplicate display name for Valparaíso exists in two different baseline province IDs; only the Juan Fernández parent ID is in this subject scope, and this task does not merge or reparent either ID.

## Engineering and research follow-ups

- Existing Chile source/legal-boundary follow-up: [#932](https://github.com/ChengshuLi/WorldAtlas/issues/932). Obtain authorized current legal rosters and redistributable source polygons, then compare all scoped rows and neighboring edges before proposing changes.
- Existing Paraguay source/legal-boundary follow-up: [#933](https://github.com/ChengshuLi/WorldAtlas/issues/933). Reconcile each district's constitutive law and current statistical/cadastre identity, then use legally defensible geometry for boundary work.
- Existing Asunción handoff: [#930](https://github.com/ChengshuLi/WorldAtlas/issues/930), coordinated with the exact aggregate ID and its own scope.
- Preserve companion area workloads #444 and #446 and the distinct crosswalk audit in #1111. Do not combine their owned evidence, overwrite #935 files, or treat any one packet as approval of Southern South America.

## Reproduction

Requires Python 3.11+ and the repository Git objects. No packages, network access or original source downloads are used.

```sh
python3 data/regional-review/southern-south-america-batch4-validation-20261006/verify-packet.py --out-dir run-one
python3 data/regional-review/southern-south-america-batch4-validation-20261006/verify-packet.py --out-dir run-two
```

The script reads the immutable 7245 baseline using `git show`, compares the captured GitHub issue contract to the old subject scope, then emits a row-level audit and controls. The files under `run-one/` and `run-two/` are byte-identical for deterministic reproduction. `evidence-quality.json` names the complete baseline inventory, source limits, output hashes, per-result bindings and whole-file change receipts.

**Disposition:** the #1116 corrective validation acceptance is addressed, with limited upstream/source verification. No shared geography changed, no boundary was approved, and no import, publication or region certification is authorized.
