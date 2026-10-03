# Western Polynesian Islands batch 1: initial geography source review

Issue: [#134](https://github.com/ChengshuLi/WorldAtlas/issues/134)
Baseline: `origin/main` commit `dd83dcad2ec486b89844a78e5e137935b101c167` (2026-10-03).
Owned path: `data/regional-review/regional-review-a5b86fc6ff2463cd/` only. This packet records evidence and proposed follow-ups; it makes no hierarchy, footprint, grid, source-catalog, or application changes.

## Exhaustive pinned scope

The issue assigns 24 current location IDs and 24 one-to-one province wrappers across six areas. `assessment.json` has one explicit classification and sourced assessment for each exact location ID, each exact province ID, and all six area purposes. `baseline-extract.json` preserves full ancestry and the complete parent membership inventory. The reviewed published region has 25 members, one of which is outside this issue; this packet does not decide combined membership. No location is omitted from the assessment just because it is small or a whole-country identity.

The review classified Tonga’s five geoBoundaries division features as provisionally suitable at the named division tier, with caveats. Tuvalu’s eight-feature ADM1 source is correction-needed for an affirmative official census crosswalk gap: the 2022 census counts nine islands including Niulakita (36 enumerated residents) while the source has no Niulakita feature. The official Kaupule o Niutao 2021–2024 Island Strategy names both Niutao and Niulakita, showing a joint local planning relationship, but does not establish statutory jurisdiction or boundary geometry. The packet therefore proposes no assignment or shared boundary correction. A bounded follow-up is recorded as [#615](https://github.com/ChengshuLi/WorldAtlas/issues/615). Niue/Samoa are Natural Earth country-level aggregations, and Tokelau/ASM/WLF have unverified source-purpose and/or completeness questions; they are individually marked insufficient evidence. Every province wrapper is assessed separately; a complete parent chain does not independently justify a tier. Every area is individually assessed, with Tokelau Archipelago’s two unowned-to-this-issue members explicitly cross-referenced.

## Main evidence and limitations

* `sources-manifest.json` gives canonical source references, date/vintage, license status, inspected tables/pages, hashes/bytes for official reports, lawful retention/restoration notes, and limits on what each reference establishes.
* Complete original Tonga and Tuvalu geoBoundaries files and metadata are retained under `sources/TON/` and `sources/TUV/` under the stated ODbL 1.0 data terms and citation notice. The retained source citation file is the full 4,316-byte upstream notice, not the Git LFS pointer.
* Official Tonga 2021 PHC glossary page 10 and printed page 20 support the five division/district/village levels. Official Tuvalu 2022 PHC printed page 1 and tables 3–4 on pages 6–7 establish nine named islands and the Niulakita population crosswalk. Official Samoa 2021 PHC printed pages 1 and 20–22 document 51 political districts, nested settlement reporting, and villages on Manono Uta, Faleu and Apolima; that country-level census evidence does not turn Samoa into a 51-part legal polygon dataset.
* Tokelau Government statistics/village pages document three atolls, census availability and settlements (including 62 Fakaofo islets and two settlements, and Nukunonu’s Fale/Motuhaga); they do not settle the conventional Tokelau-Manihiki botanical grouping’s treatment of Swains/Olohega.
* Natural Earth is Public Domain but is a cartographic reference; its exact source vintage and unit semantics are not enough to endorse legal ADM1 borders. The issue explicitly says original source-policy crosswalks for ASM and WLF are missing. ISEE’s 2019 census result page was accessible but did not establish polygon source/completeness or district footprint semantics. Recovery of the exact eight Natural Earth fallback profiles is tracked in blocked follow-up [#616](https://github.com/ChengshuLi/WorldAtlas/issues/616). Niue PRISM redirected to niuestatistics.nu and returned proxy 403/502; no facts were inferred from that failure.
* `gshhg-land-screen.json` and `screen_gshhg_land.py` screen all assigned footprints against every GSHHG 2.3.7 full-resolution L1 land candidate in two Pacific windows, retaining positive overlap records and ten nearest unmatched features for each assigned identity. GSHHG is physical coastline evidence, mixed-vintage and possibly misregistered; atoll lagoons, tiny islets and differing boundary products preclude interpreting area differences as administrative defects. Its licensed source archive is not duplicated in this packet; exact-byte restoration is specified in `sources-manifest.json`.

## Assessment meaning

`justified-with-caveat` is provisional source-tier support, not a boundary certificate. `correction-needed` means an authoritative count/source discrepancy warrants a bounded source-crosswalk follow-up; it does not authorize a shared geography edit. `insufficient-evidence` is an affirmative unresolved result, not presumed correctness. Political sovereignty, administrative jurisdiction, physical island land and historical presence are separate claims. GSHHG, census population, macro coverage and published ancestry cannot substitute for authoritative political or legal demarcation.

No shared boundary change is proposed. The region’s macro envelope, subcontinent and outer neighbors remain pinned; any cross-parent or area-purpose resolution must coordinate all affected packets. This initial review is not a regional approval and cannot enable location-attribute imports.

## Reproduction and checks

Use Python 3.11+ (standard library) for the evidence verifier. Geometry reproduction requires `pyshp==2.3.1`, `pyproj==3.7.2`, `shapely==2.1.2` plus the archive restored per the manifest. All generated output paths are inside this owned directory.

```sh
python3 data/regional-review/regional-review-a5b86fc6ff2463cd/verify_packet.py
python3 data/regional-review/regional-review-a5b86fc6ff2463cd/build_baseline_extract.py
```

The second command refreshes the exact source-pinned baseline extract only; inspect the repository status and preserve the assessment’s explicit row-by-row findings when regenerating.
