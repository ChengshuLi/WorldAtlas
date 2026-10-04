# Valdez-Cordova source-vintage successor crosswalk

This one-subject follow-up resolves the official administrative identity question for the 2018 geoBoundaries ADM2 source feature `gb:USA:ADM2:52423323B16539688175930` (shapeID `52423323B16539688175930`, Valdez-Cordova) against the 2024 Census county-equivalent roster.

## Finding

The Census Bureau's 2019 Geography Changes page states that Alaska announced the split of Valdez-Cordova (02261) into two new Census Areas: Chugach (02063) and Copper River (02066). Its Alaska county-change table independently lists each as a new entity formed from the split, effective 2019-01-02, submitted through the 2019 Boundary and Annexation Survey. The retained 2024 TIGER features use GEOIDs 02063 and 02066 and Census county-equivalent class H5.

Recommend preserving the 2018 source ID and geometry as a distinct vintage and recording a versioned **one-to-many split crosswalk** to both 2024 Census GEOIDs with the effective date and Census citations. Do not rename the historical source to one current unit, infer political ownership, alter geometry, or transfer historical attributes. A Census county-equivalent record establishes statistical geography lineage; it does not establish a local government or a sovereignty claim.

The pinned #486 area overlay found 99.947342% of the 2018 source footprint overlapping the two successor polygons together and 0.040571% overlapping four other 2024 county-equivalent candidates. These are inherited equal-area screen ratios, not Census transition evidence. They show why the two sources must remain distinct and why the transition should not be represented as proof of an exact polygon partition. We do not alter the existing screen or shared geography.

## Scope context

The inherited #486 assessment records the complete parent chain Valdez-Cordova → Alaska → Pacific → Western North America → Northern America → North America. It also records nine geometry components, no interior rings, a 2024 Census Places screen with 28 polygon intersections, and a USGS GNIS screen with 46 populated-place hits. Its limits state that those settlement/land screens do not certify every settlement, island, coastline, land or water boundary. This follow-up preserves those findings and focuses on the one required source-vintage crosswalk.

## Sources and reproduction

Canonical citations, source vintages, licenses, retrieval dates, retained hashes and restoration instructions are in `sources-manifest.json`. Newly retained Census materials are the complete source page response and Alaska change table; the 2018 geoBoundaries source and 2024 TIGER subset remain untouched in #486 at baseline commit `276d72e1f316ad58d52c8fea7974a873c2ec9387`.

From the repository root:

```sh
python data/regional-review/valdez-cordova-successor-followup-2026/build_crosswalk.py
python data/regional-review/valdez-cordova-successor-followup-2026/verify_crosswalk.py
```

The build reads immutable parent inputs and the newly retained Census change records. It writes only `successor-crosswalk.json`. The verifier checks the direct predecessor/successor event, event date and source codes, both 2024 TIGER target identities, the one-to-many handling, inherited overlay totals, and negative controls for unsupported or duplicate successor codes. Run the build twice and compare the output SHA-256 for a deterministic reproduction.

This packet proposes a traceable crosswalk for engineering review. It does not approve Alaska or Western North America geography, change published boundaries, or authorize historical imports.
