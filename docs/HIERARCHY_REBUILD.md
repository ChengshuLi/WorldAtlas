# Geographic framework rebuild

Goal: give every active location one defensible province → area → region → subcontinent → continent chain, independently of its dated owner. Counts are outcomes, not quotas. Antarctica remains excluded.

Acceptance criteria:

- Reconcile reports with the active dataset: retired groups never count as current geography.
- Preserve historical records and original identities when replacing a footprint. A new geographic grouping does not inherit population or names without evidence.
- Record source, grouping method, overlap and review status for each changed membership. An administrative label is not a universal atlas tier.
- Use named local territories or functional settlement catchments for locations; named local clusters for provinces; broader administrative/geographic groups for areas; macro-geography for regions. Single-child tiers require an explicit reason.
- Audit every location and every parent group, not only known examples. Separate structural failures from geographic judgments requiring further research. Do not describe an automated pass as certification of world history.
- Use complete location footprints to construct parent map coverage. Parent borders are derived from membership, never independently overlapping polygons.
- Load precompiled pixel ownership in the published site; retain original source geometry for dated-boundary changes and investigation.

Research findings used in this iteration:

- EU5DB exports an explicit game hierarchy and a location-ID bitmap. Its land-only counts are a scale reference, not a public geographic standard or evidence for all historical years.
- geoBoundaries gbHumanitarian CHN ADM2 (2020, 361 prefecture-level territories, CC BY 3.0 IGO) supplies a real tier between the existing county reference and provincial areas. It differs from gbOpen CHN ADM2, which is a county-level layer despite the same ADM number.
- The 2019 Outline Development Plan for the Guangdong–Hong Kong–Macao Greater Bay Area explicitly identifies Hong Kong–Shenzhen, Guangzhou–Foshan, and Macao–Zhuhai as cooperation poles (Chapter 3, Section 1). Where used, these are atlas geographic groupings, not invented official provinces or historical jurisdictions.
- ISTAT local labour systems group contiguous municipalities by commuting relationships. Regione Umbria SIAT publishes 610 systems in its 2011/2018 layer under CC BY 3.0. They provide named local catchments below Italy's provinces, without turning every small municipality into a peer of Hong Kong. They are a modern geographic reference, not medieval administrative units.
- Natural Earth supplies independently named regional and subregional memberships. The exact source fields and country-specific role decisions must be retained. Existing WGSRPD groups remain explicitly identified where a stronger replacement has not been established.

A technically complete chain and a semantically reviewed chain are different claims. Outstanding geographic reviews must be visible in the before/after report and inspector; they must not be concealed by a success count or a repeated label.

## First rebuild result

- 45,983 locations → 4,860 provinces → 461 areas → 66 regions → 29 subcontinents → 6 continents. These counts are outcomes, not achieved quotas.
- Every location has one complete chain; all polygon interiors pass the global overlap check (tolerance 1e-10 square degrees). Italy's replacement preserves the previous display coverage, with source seam adjustments recorded.
- The old report contained retired group IDs; current counts and review lists are regenerated from active members.
- 4,799 parent groups remain in the semantic review queue. Most are retained reference groupings. Structural completeness does not close those reviews.
- Italian commuting systems can cross administrative provinces: 76 of 610 have less than 80% overlap with their assigned reference province. They remain whole locations, and the affected atlas parent footprints follow membership. These cases are exposed for review.
- Region definitions are atlas macro-geography, not dated political boundaries. Europe and North America have explicit cross-country groupings; source assignments use spatial reference footprints rather than the ownership field.

Next research priority is the open queue: first single-child tiers and areas with over 20 provinces, then broad provinces with over 25 locations and low-overlap source matches. New evidence should replace retained groups through recorded crosswalks, preserving source identities and historical records. No unverified parent is silently described as settled historical geography.

Reproduction: `npm run data:prepare` restores the checksum-pinned snapshots in `data/framework-sources/`, stages Italian functional territories, rebuilds memberships, aggregates review evidence across all members, then runs the global publication audit. Per-location before/after records are chunked in the `framework-changes-*.json` files referenced by `hierarchy-report.json`. Original source geometry remains in the database and source archives. The production browser loads a compact catalog and precompiled ownership; full polygons are fetched only if a dated geometry/lifetime change requires rebuilding.
