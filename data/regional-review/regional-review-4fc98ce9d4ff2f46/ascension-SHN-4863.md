# Ascension row evidence: SHN-4863

## Scope and pinned identity

This is one row of review packet `regional-review:4fc98ce9d4ff2f46`, issue [#323](https://github.com/ChengshuLi/WorldAtlas/issues/323). The exact member is `SHN-4863`; the `data/macro-foundation/current-membership-inventory.json.gz` blob (`7029f60f8c1354f49e2bda10e21177ef2fa7322d`) at current main `8877709f440cac68c95c44238cf828dc4420f190` lists it as the sole member of area `framework:area:ascension:2054579c4579` (Ascension) and province `framework:province:ascension:4d6c8320d99c` (Ascension). That inventory is a membership crosswalk, not independent source evidence for the location's boundary or tier.

## Inspected source and fact

**Source:** Ascension Island Government, “Commonwealth Walkway Unveiled on Ascension Island,” September 2016 archive: <https://www.ascension.gov.ac/2016/09> (article title is on the archive page; publication day is not printed).

**Role:** first-party local-government announcement about a town heritage walkway and its opening. It is suitable to establish a contemporaneous civic/settlement fact, not a territorial boundary or administrative partition.

**Vintage:** September 2016 archive. The page states that the walkway opened “around Georgetown” and connects 10 of the town's historical highlights over a 7 km route; it also says the route begins outside Ascension Island Government offices. The cited page was retrieved 2026-10-19 01:28:31 UTC; the observed HTML response was 68,441 bytes, SHA-256 `9a3e7e5537a94de2f99bcb04a83bf744ab8b122279fdaa33cfae1c3644347c84`.

**Retained short extract:** “a 7 km pathway connecting 10 of Georgetown’s historical highlights.”

**License:** no open license or reuse grant was found on the page. Its footer displays “© 2022 Ascension Island Government.” This review retains the source URL, a short factual paraphrase, retrieval metadata and response digest; it does not redistribute the page, images, route or geometry.

**Original packet source hint:** issue #323 names Natural Earth and describes the retained source as an undated modern reference with a public-domain license, but omits a layer/version and feature ID. Natural Earth's [terms of use](https://www.naturalearthdata.com/about/terms-of-use/) confirm that its raster and vector map data are public domain. This verifies the generic license only; it does not identify which Natural Earth product or feature was used for this member.

## Assessment

**Classification: insufficient-evidence for the territorial member's semantic tier and source join.** The official notice independently establishes Georgetown as a town-scale civic place on Ascension and therefore shows that a populated settlement exists within the island context. It does not identify `SHN-4863`, define an island or settlement boundary, give a cadastral/administrative unit, or show whether the member is meant to represent the whole island, Georgetown, or another unit. The retained issue hint `natural-earth` does not name the exact Natural Earth layer, source feature, version or row-to-feature crosswalk; those remain unverified and must not be inferred from the atlas ID.

The source supports adding Georgetown as a settlement-context fact for follow-up review. It does **not** establish that `SHN-4863` is a city, that an island-wide location is wrong, or that any boundary should change. No correction is proposed from this source alone.

## Remaining evidence needed

To move this row beyond insufficient evidence, recover the original Natural Earth source layer/version and exact entity used for `SHN-4863`, inspect its attributes and geometry at the declared scale, and establish a traceable join to the atlas member. Then compare that representation with an authoritative Ascension territorial/administrative source at a suitable vintage. Keep Georgetown's settlement footprint separate from any outer island or government boundary. No geometry, hierarchy, alias, parent or other member was changed here; Saint Helena `SHN-4864` remains open.
