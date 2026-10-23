# Reconciliation: three center hits in pinned UGA geometry, outside in archived full release

Status: locally verified from retained artifacts; independent review requested; no disposition or credit change.

## Finding

The apparent contradiction is explained by comparing two different representations of the same named/identified features, not by different points or a whole-cell test. The original 930-key matrix reports whether the key's center point falls in the pinned 9469f09 simplified family feature. The later membership artifact tests the identical center point against the denser archived geoBoundaries 2.0.0 release feature. The crosswalk proves a vertex-preserving simplification relationship (the simplified ring's vertices are an ordered subsequence of the archived ring); it does not prove that the two polygon boundaries are identical. Connecting non-adjacent retained vertices replaces intervening boundary segments with chords, so point membership can differ near those segments.

## Exact pins and coordinate convention

- Original 9469f09 UGA ADM1 source family: decoded GeoJSON is 258,114 bytes, SHA-256 `75e5442c33f7023bcd2d7d72928835723b557c1a9523f3b4c9afe36d0e73af93`; compressed body is 85,208 bytes, SHA-256 `3e0dc23da310870739bc742483875a3e9a9b1614d46d9a67c77aac6ccb427425`. The retained manifest identifies 4 features, represented year 2017, ODbL 1.0, and the exact source URL/commit.
- Northern Region: original feature ID `17295835B80141219017784`, feature `Polygon` with 1,623 closed / 1,622 distinct exterior vertices; canonical compact-JSON geometry SHA-256 `8cecf5bb4fdb5eb5f37d8cc2f4e3e63e47aff03e1c4020857558ffff569978da`. Crosswalk counterpart is archived release shape ID `UGA-ADM1-2_0_0-B1`, whose full exterior has 13,135 closed vertices.
- Western Region: original feature ID `17295835B91329899113986`, feature `Polygon` with 2,276 closed / 2,275 distinct exterior vertices; canonical compact-JSON geometry SHA-256 `50ae8618aef7edae76f409de087fd8c1bd7c4a271b1a0119ae97db0df14d3a9c`. Crosswalk counterpart is archived release shape ID `UGA-ADM1-2_0_0-B4`, whose full exterior has 24,629 closed vertices.
- Both feature bodies declare `urn:ogc:def:crs:OGC:1.3:CRS84`; coordinates are `[longitude, latitude]`. The retained overlay and archived-release membership artifact carry the same exact coordinates for each key below.
- Archived release GeoJSON body: 1,765,418 bytes, SHA-256 `a297e269c40e570ebc19906527c8222d68c7b98ce1f547b38101dabafba9cac8`; metadata identifies release `UGA-ADM1-2_0_0-G582`, source names OpenStreetMap/Wambacher, year 2017, update 2020-01-15, ODbL 1.0.

## Reproduced three results

| Original key | Center `[lon,lat]` | Pinned simplified source feature | Archived full-release feature |
|---|---|---|---|
| `[14441,129388,153711]` | `[31.072908004851882,2.3262070155770944]` | Northern `17295835B80141219017784`: inside | B1: outside |
| `[14462,131655,152660]` | `[29.629700266243532,-0.7861184653021305]` | Western `17295835B91329899113986`: inside | B4: outside |
| `[14462,131673,152664]` | `[29.63519296934004,-0.810833228886297]` | Western `17295835B91329899113986`: inside | B4: outside |

The original matrix field `center_hit_count` means candidate center-point memberships in the retained family geometry, not grid-cell polygon intersection. The full-family overlay identifies the same values under `recorded_candidate_center_hits` / `full_537_feature_center_hits`; its limits explicitly say center-point comparison only. Thus the original matrix's three UGA hits are correct for the pinned simplified source features. The official-release artifact's three outside results are also correct for its dense release features. The prior shorthand that described the features as if the geometries were identical was inaccurate: the evidence supports exact ordered vertex retention during simplification, not geometric identity.

## Effect on the 16-key proposal

The 3 keys remain source-version/representation conflicts: they are UGA center hits in the original pinned simplified geometry but DRC-side/outside in both the retained full-release check and source-relative OSM side check. The 11 keys remain inside both UGA representations and on the Uganda-tagged side. The other 2 remain inside both representations but on the DRC-tagged side of the historically checked way. This correction strengthens the distinction between the original candidate and the later comparison; it does not resolve which source representation governs the original contract, alter the stock diagnostic, remove any hold, or award science credit. Keep the full 16-key proposal local pending independent reviewer verification.

The existing independent reviewer verified the original overlay hits and pinned-body point-in-polygon results, confirmed that the 2_0_0 full geometry is a separate denser representation, and concluded the correction does not require splitting the three keys out or leaving them pending for a separate lookup. The reviewer supports the exact 16-key researched-unresolved proposal only with the representation distinction, the 11/5 source-relative OSM-side split, no universal territorial adjudication, all native holds retained, and zero credit. This is not repair qualification or root acceptance.

## Evidence files and hashes

- Original 930-key matrix: 1,977,447 bytes, SHA-256 `1b3805a65d528b24d9327bd4c13f1e0b4a8cc0ef908addd728dc2482ff986174`.
- Complete pinned-feature center overlay: 799,945 bytes, SHA-256 `00fc57c3290d4d0cf1ef7df68860ac6d2c3ee82e67509d0ae2f9d1c550cdf24d`.
- Release crosswalk: 4,437 bytes, SHA-256 `2baf4c5c602febcdb5f5f1576f4d1c40dbba038c682551b60370cf0a3670546e`.
- Archived-release center membership: 12,495 bytes, SHA-256 `c7c3f6620ca8915aab1df68798e45cea88eff90ed9b5e4b6f5daba28095a750b`.
