# Fixed environmental classifications

Topography, vegetation and climate resolve to one approved class or explicit unknown. The fixed registry is `src/environment-classifications.js`; it is application vocabulary, independent of factual content. Each class has a stable ID, one display label and an explicit list of accepted legacy spellings. Arbitrary descriptions, typos and case variants absent from that list are rejected by new imports.

Use the stable ID in new evidence, for example:

```json
{"attribute":"climate","value":"climate:Cfb"}
```

The normal claim fields—location ID, source, supported half-open interval, method and status—are still required. Use JSON `null` for unknown, never the string `"unknown"`. Store the source's original wording, finer descriptions and uncertainty in evidence metadata. A class does not establish that an observation applies to any unsupported year.

## Available classes

- **Topography: 12 classes.** Flatland, Peak, Ridge, Shoulder, Spur, Slope, Hollow, Footslope, Valley, Pit, Hills and Mountains. The first ten retain the geomorphon source distinctions; Hills and Mountains allow explicitly broad relief evidence without inventing a finer landform.
- **Vegetation: 16 classes.** The 14 WWF biome classes already used by the reference dataset, plus Farmlands and Woodlands. These include the tropical/temperate/boreal forest, grassland/savanna/shrubland, tundra, Mediterranean, desert and mangrove classes listed in the registry. Potential natural biome references are not observations of historical land cover. Farmlands requires actual supported agricultural evidence; Woodlands preserves broad woodland evidence.
- **Climate: 32 classes.** The 30 Köppen classes `Af Am Aw BWh BWk BSh BSk Csa Csb Csc Cwa Cwb Cwc Cfa Cfb Cfc Dsa Dsb Dsc Dsd Dwa Dwb Dwc Dwd Dfa Dfb Dfc Dfd ET EF`, plus broad Oceanic and Mediterranean classes. The broad classes remain separate from precise Köppen codes: an unspecific source saying “Oceanic” does not prove `Cfb`.

Get the full machine-readable ID/label/alias catalog at **`GET /api/classifications`** on the hosted or local server. Static exports include **`environment-classifications.json`**. The historical import dialog includes a collapsed list of all IDs and labels. These catalog reads do not require database contents.

## Enforcement and preservation

Import preview, local typed records, legacy state snapshots, dated entity attributes, hosted imports and prepared-producer validation share the registry. SQL guards independently block unsupported new values, including direct SQL writes. Existing frozen migrations are unchanged; hosted migration `0007_fixed_environment_classifications.sql` adds enforcement without updating or deleting claims.

Imported spellings remain stored as original immutable evidence. The shared resolver adds the fixed classification ID and displays the canonical label; aliases and IDs share a legend category, color and whole-location fill. Unmapped retained legacy text stays accessible as evidence but resolves to unknown, with the original value and reason in provenance. It cannot create a new arbitrary map category or silently select weaker evidence.

An exact hosted retry of an existing legacy claim remains idempotent. New IDs, changed unsupported values or other collisions cannot use that exception. Unknown remains distinct from any listed class.

Run:

```sh
node scripts/compile-environment-classification-guards.mjs --check
node --test --test-concurrency=2 test/environment-classifications.test.mjs test/environment-classification-db.test.mjs
```

Future changes to this vocabulary are a reviewed application/schema release, not a content import. Keep published IDs and migrations immutable; add a new migration when extending the registry. Never rerun a generator to overwrite an already-published migration. Factual expansion by Luna should use the existing fixed IDs without changing UI or geometry.
