# Western county water-edge evidence supplement (#598)

## Scope and status

This packet addresses exactly the 16 issue-assigned county-equivalent location IDs and all 17 named GEOID pair leads. It is evidence and a proposed disposition only. The issued reservation is recorded in `scope.json`; base commit is pinned there. The source packets for #486 and #487 are inputs and remain untouched.

## Findings

`findings.json` reproduces all 17 pair measurements in a temporary EPSG:5070 projection with longitude/latitude axis order explicitly fixed. Invalid inputs fail closed; no geometry repair is performed. Strict shared boundary lengths and polygon gaps are reported to millimetre precision as a computational screen, not a claim of legal boundary accuracy.

Across these exact 17 leads, 2018 geoBoundaries has one >1 m contact (Alameda–San Francisco), 2018 official Census TIGER has all 17, 2024 Census TIGER/Line has all 17, and current Atlas has none. Within these pair leads, the 2018 Census and 2024 contact sets are identical; two shared lengths differ modestly by source vintage. The parent #487 graph independently records 219, 234, and 218 internal contacts across its larger set of 97 CA/WA county predecessors; its full edge arrays and hash are pinned in `findings.json` inputs. Those parent counts are not the 16-location scope count.

All 2024 pair members have nonzero Census `AWATER`; this confirms that the county polygons include county water in aggregate, but does not locate water on any particular shared edge. The separate physical screen compares every 2024 shared line with retained full-resolution GSHHG level-1 physical land records from the parent #487 packet. Fourteen contacts lie entirely outside those retained land records; three intersect land for a minority of their length. The result supports a water-dominant interpretation at this source scale, while remaining a screen: the retained subset is not a complete hydrographic inventory and outside-mask length is not proof of water. No county-specific legal marine line is established, so no boundary move is recommended.

### Alameda–San Francisco

The geoBoundaries 2018 derivative has a 357.251 m contact; direct official Census TIGER 2018 and TIGER 2024 both have a 21,322.488 m contact. Current Atlas has no contact and a 4,442.292 m gap. The apparent source-vintage change is resolved: the 2018 derivative's geometry representation is materially different from the official Census source, while the official 2018 and 2024 contacts agree. This does not prove the correct current county-water footprint or line. The contact is 1,101.547 m inside and 20,220.940 m outside the retained GSHHG land mask. The evidence supports treating it as water-dominant, not moving the boundary. A controlling legal marine source remains unavailable.

### Clatsop–Pacific

This is the sole cross-state lead. The 2024 edge is 41,324.968 m; 2018 and current have no contact, with current gap 5,372.349 m. It is assigned jointly across the Oregon and Washington parent packets. This packet does not treat source overlap/contact as proof of state or county political ownership. The retained GSHHG screen places 560.533 m inside land and 40,764.435 m outside the land mask, so the contact is strongly water-dominant at this source scale. A coordinated review with #486, #487 and the regional integrator is still required; absent authoritative joint marine/coastal boundary evidence, retain the legal line as unresolved and make no unilateral shared-boundary proposal.

## Change accounting

The generated `findings.json` contains 1,780 lines for 17 pair-by-source measurements, four explicit pair-contact sets and hashes, and the complete 16-subject ledger. Other text/code/manifests total about 517 lines; the retained Census 2018 subset is 255,129 compressed bytes. This is one coherent evidence packet, and the generated measurements are separated from the methods and interpretation below.

## Sources, dates, licenses, retained bytes

The machine-readable source record is `sources.json`. It records canonical URLs, date/vintage, lawful retained files and byte hashes, and restoration steps. It intentionally references immutable bytes already retained under #487 instead of copying or altering another worker's files:

- geoBoundaries USA ADM2 (2018 vintage; metadata/build dated 2023): Census MAF/TIGER origin as declared by source metadata; federal Census source is public domain. Retained compressed bytes: 3,264,221, SHA-256 `f42991ac...8044a`.
- U.S. Census Bureau TIGER/Line County and Equivalent (2018 and 2024 vintages): public-domain federal data. A lawful selected 16-county TIGER 2018 extract is retained in this packet and the six-state TIGER 2024 subset is retained under #487. Both contain `ALAND`/`AWATER`; neither field adjudicates a legal county marine line.
- GSHHG full-resolution physical land (release 2.3.7, 2017-06-15): licensed LGPL v3 or later, with license and bytes retained under #487. Its 79 selected full-resolution land candidates provide a physical coastline mask screen, not official county or complete hydrographic evidence.
- Current published Atlas baseline: repository `data/world-index.json` and its referenced part files at the pinned base commit; internal project data, no external license applies. Hashes are included by the script inputs for `world-index.json`; source part files are deterministic members of that baseline and are not recopied.

## Reproduction

From repository root, run:

```sh
python data/regional-review/regional-supplement-western-county-water-edges-2026/reproduce_pairs.py
```

Required versions: Shapely 2.1.2 and pyproj 3.7.2. The script reads only the owned packet and immutable baseline sources, makes no source repairs, asserts parent 97-county graph totals, and rewrites only this packet's `findings.json`. The pair-edge set hashes are hashes of compact canonical JSON arrays in `findings.json`; the larger parent graph hash is explicitly separate. `verification.json` records two-run identical output hashes and positive/negative controls, including an exact issue-value check, dropped-pair rejection, axis-order control, and no-repair geometry control. Repository scientific controls were also run and their results are recorded there.

## Proposed engineering disposition

No correction is supported by this evidence packet. Keep the 17 source/current contacts as review leads, resolve Alameda–San Francisco in a dated official county-water source review, and coordinate Clatsop–Pacific across both packet owners and the integrator. If official evidence later identifies a shared-footprint discrepancy, file one joint bounded engineering follow-up listing every affected county location. Do not alter shared boundaries, hierarchy, geometry, grid, certificates, or live data here.
