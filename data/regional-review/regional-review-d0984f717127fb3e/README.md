# Central India batch 1 source/semantic review (#81)

Status: initial evidence inventory and source identity screen. This packet does **not** certify the India Central region, approve any interior, authorize imports, or make geographic edits.

## Scope and method

This read-only packet follows the exact 230 location IDs in `issue-scope.json`: Madhya Pradesh 54/422 (partial), Chhattīsgarh 150/150, and the India Central geographic portion 26/26. It includes 37 scoped province groupings. Every scoped location and province is explicitly classified `insufficient_evidence` in its individual assessment. The classification is intentional: source-feature identity is verified, but current legal/official boundaries, full source completeness, exact parent crosswalk, coast/island coverage, and tier purpose have not been independently proven. No administrative count or structural check is treated as spatial proof.

`reproduce.py` verifies exact scope membership, one-to-one assessment coverage, exact retained source feature-ID matches, source byte hashes, and complete area/province rows. Its output explicitly limits what those checks establish.

## Source findings

The 2018 geoBoundaries ADM3 metadata identifies Sub-District, Pathways Data Pvt Ltd / LG Directory, and ODbL 1.0. The retained collection reproduces to provider SHA-256 `4ea6807d0a0c5aac0b46ee8e31ed7c30fbec273b44345bba1e4a2bb5f299f5fb` and compressed SHA-256 `211a72c2c80bb60d10214944fa8cc4764e9ba888116e802ce6d87084872f5301`. Its metadata says 6,836 administrative units; the verified GeoJSON contains 6,822. All 204 scoped IDs occur exactly once and source names match, but this does not resolve 14 absent nationwide records or coverage in the scoped geography.

The pinned 2021 geoBoundaries ADM2 source says District and ODbL 1.0. Metadata declares 736 units, while the retained collection has 735 features. All 26 scoped IDs occur; current legal status, current boundary equivalence and the one-feature discrepancy remain unresolved.

Current official Chhattisgarh pages say 33 districts and document five districts created on 17 April 2022. Thus the 2018 subdistrict source requires a post-change legal parent/boundary crosswalk. Census of India 2011 MPC/REL records are an official historical role cross-check for District/Sub-District, not current boundaries. LGD has state-level district/subdistrict downloads but this review did not retain data because the portal flow requires interaction and its current edition/reuse terms need verification. Exact source URLs, hashes, restoration instructions and use-limits are in `source-inventory.json`.

## Tier and unit-group findings

The three area groupings do not use a uniform source level: the Madhya Pradesh (54 scoped) and Chhattīsgarh (150) areas have ADM3 Sub-District locations grouped under district-named provinces; the 26-member India Central geographic portion has ADM2 District locations under state-named Uttar Pradesh/Uttarakhand provinces. This may be a scale convention but needs purpose-backed justification at the region level. Chhattīsgarh has 28 scoped province groups while current government pages report 33 districts, including five formed in April 2022; that is a crosswalk/completeness question and does not itself prove which Atlas unit is missing or wrong. Twenty-one of 204 ADM3 geometries are MultiPolygon and all 26 ADM2 geometries Polygon; this is only a format screen. `source-geometry-screen.csv` flags every scoped shape for official comparison.

Issue [#889](https://github.com/ChengshuLi/WorldAtlas/issues/889) records the exact 230-subject source/legal crosswalk, discrepancy reconciliation, area purpose and cross-region seam follow-up. It is blocked on #81 and requires serialized reservation after #81 merges.

## Unresolved geography

The 37 groups do not on their own establish geographic purpose, completeness or suitable granularity. Need explicit review of urban fragmentation, province-sized and oversized groups, unnamed residuals, disconnected/multipart features, islands/coastal omissions, duplicated tiers, boundaries against reliable current official sources, and neighboring state/region seams. The Madhya Pradesh area is partial here; its integrated area decision belongs to the region review. No current official boundary source was lawfully and reproducibly retained for these determinations. The ODbL 1.0 source datasets require attribution and carry share-alike conditions for derivative databases/public uses under the official license; source-inventory records the reported terms and attribution, and redistribution of future derivatives needs a license-specific review. See `findings.json`, `scope-risk-screen.json`, `source-geometry-screen.csv`, `area-assessments.json`, `province-assessments.json`, and `location-assessments.json`.

## Reproduction

From repository root:

```sh
python data/regional-review/regional-review-d0984f717127fb3e/reproduce.py
```

A pass proves scope/data identity and file integrity only. It does not prove geographic correctness, completeness, validity of license interpretation, current legal units or tier suitability.
