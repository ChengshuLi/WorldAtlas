# Dated reference name attestations

This import adds 3,588 official name attestations on stable existing atlas identities. It does not establish continuous historical names or historical boundaries. US Census names are supported only in `[2020, 2021)`; Eurostat NUTS names only in `[2021, 2022)`. Outside those intervals the usual dated resolver must leave unsupported names unknown and show modern reference names separately.

## Actual source products

- [US Census 2020 national county Gazetteer](https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_Gaz_counties_national.zip): 3,233 source county rows; 3,153 exact location crosswalks. United States government work, public domain. Archive SHA-256 `02ef546e4c4f9c032c19616eabb9526caa016f778f41ede3b8c9755dacce20ef`.
- [Eurostat GISCO NUTS2021, 10M GeoJSON](https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_10M_2021_4326.geojson): 435 crosswalks, comprising 261 provinces, 158 locations and 16 areas in 16 countries. Source SHA-256 `db37daeeb4f7c1b9a4c25ec986319357a0c7b3bb7634ac612fedbf202e829471`. [Eurostat reuse notice](https://ec.europa.eu/eurostat/help/copyright-notice) permits acknowledged reuse of the relevant metadata; 233 UK rows outside the EU/EFTA/candidate-country flags were excluded under the notice's country exceptions. Original GISCO geometry is not republished here.

Attribution: Eurostat GISCO NUTS2021. Adapted by WorldAtlas; Eurostat is not responsible for these crosswalks.

## Identity and interval safeguards

Census candidates must have the exact normalized source county name and exactly one official internal point contained by the current location land. Only attested administrative suffixes are stripped; `City` remains part of names such as James City and Carson City. There is no fuzzy matching or transfer from a city point to a larger unrelated territory.

GISCO candidates must have the exact normalized source name and source-country namespace, with at least 95% correspondence in both directions between the official polygon and the current location or complete member-location union. These ratios are explicitly planar WGS84 diagnostics, not geodesic population weights. Coextensive ambiguous NUTS levels, incomplete coastlines and unmatched names stay open. There are 667 recorded unsuccessful crosswalk attempts, with exact IDs and reasons.

The source's epoch supports an annual snapshot. Boundary vintage, file modification date and modern labels are never evidence for a longer naming interval. Source geometry correspondence establishes conservative identity mapping, not historical boundary continuity.

## Files and consumer contract

`data/dated-reference-names/index.json` contains full hosted `sources` rows, the single `parts` path `names.json.gz`, counts, source hashes, preparation hash and migrated hierarchy hash. The hierarchy contains 5,132 provinces and 470 areas; SHA-256 is `d15b845246f74f2934b32dfa8df431fb4fe92f7762ca24c33732b8d1c19999d6`.

`names.json.gz` is an array of hosted name records with `id`, `entity_id`, `name`, `language`, `role`, `valid_from`, `valid_to`, `source_id`, `is_example` and attribute-specific `metadata`. `crosswalk.json.gz` records source GEOID/NUTS_ID and actual point/geometry evidence. `unmatched.json.gz` lists failed candidates; it is audit evidence, not an import queue to approve automatically.

Import source rows before names. Static temporal-history consumers convert `name` to `value`, use `field: 'name'`, preserve `language` and `role` as `name_role`, and join source provenance. Hosted name consumers use the record shape directly. All three paths must apply the same half-open intervals.

Reproduce with `python scripts/prepare-dated-reference-names.py` after placing the pinned source archives under `.cache/dated-reference-names/`. The script validates unique IDs, existing entities, one-year intervals and unique entity/language/year tuples. No hierarchy, geometry or archived history is modified.
