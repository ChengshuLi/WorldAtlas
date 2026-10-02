# Worldwide geographic closure gates

`python scripts/review-global-semantic-closure.py` evaluates every current location, parent group, reference-owner group and country-policy profile. Its output is `data/global-semantic-closure.json.gz`. It reads the six independently prepared continent inspections and the current, migrated hierarchy. It never changes geography or historical records.

The first run covers 49,614 locations, 5,703 geographic groups, 252 reference-owner groups and 201 policy profiles. It is an exhaustive **review inventory and diagnostic pass**. It is not semantic approval of the world. The output deliberately distinguishes `audit_complete` from `semantic_complete`.

## What is checked

Each location has thirteen individually recorded checks: complete adjacent-tier membership; a valid positive-area land footprint; nonoverlapping interiors; published source role; source vintage/license; independently justified local geographic purpose; neighboring granularity; urban fragmentation; anonymous remainders; disconnected parts; repeated original source identities; source omissions/islands; and parent correspondence.

Areas use a WGS84 ellipsoidal polygon diagnostic with hole areas removed. Actual spatial intersections identify adjacent territories, point contacts and overlapping interiors. These diagnostics are separate from the precise antimeridian-safe historical ownership preparer. Latitude-dependent visual sizes are not used as territorial-size evidence.

A 20-fold contrast against adjacent-location median area, or a territory exceeding 50,000 km², triggers examination. It does not prescribe equal areas or demand a split. Dense cities, archipelagos, enclaves and remote geographical territories can have supported exceptions. Those exceptions require geographic evidence; an absence of overlap alone does not justify them.

Original source atoms are reconstructed from stable `source_member_ids` when an adaptation changes the collection name. A shared source atom raises a fragmentation question. It never forces a merge: named physical subdivisions can legitimately share their original administrative envelope. Dedicated source-union research supplies corrections for artificial political-mask partitions separately.

Each parent group receives checks for its member-derived footprint, independently supported tier purpose, repeated/coextensive tiers, remaining boundary questions and independently reviewed children. One supported boundary cannot close an unresolved branch. The six-continent source inventories are evidence of what was inspected, not blanket approval of their descendants.

## Completion and publication

`status=supported` requires every applicable rubric check to be supported and every child to be independently supported. `open` means evidence or a documented exception is still missing. `attention` identifies a measured trigger requiring investigation. A check can be `not-applicable` only with an explicit reason.

The script fails when reference-owner membership is stale, any active location lacks a reviewed-source crosswalk, a chain skips a tier, Antarctica appears, or an input changes during calculation. Input hashes pin the exact current geography and every frozen inspection file. Re-run after a footprint or hierarchy migration; do not relabel an old result as current.

A failed structural check returns a nonzero exit after saving diagnostics. Structural publication may use the atlas while exposing remaining semantic questions. A milestone claiming completed worldwide semantic review must additionally require `semantic_complete=true`; an exhaustive machine pass cannot authorize that claim. Future source-assisted contributors can work through the per-region and per-owner open lists without altering the renderer, entity IDs or attribute resolver.

Eleven focused gate tests run with `python test/global-semantic-closure.py`. They check unresolved-child propagation, absent evidence, explicit complete outcomes, duplicate/missing inventories, stable source atoms, source ADM numbers, a full six-continent fixture, land holes, antimeridian diagnostics and evidence-only resolutions that cannot override structural failures.

## Actionable worldwide work

1. Complete independent local-purpose and city-membership decisions for every source-policy profile. The prior inspections explicitly leave this question open; published source level or a named district alone is not a complete urban/granularity decision.
2. Resolve each measured adjacent-scale contrast against actual district, functional-city or physical-source geography. Keep justified islands/enclaves and remote regions as documented exceptions.
3. Audit all multipart territories and original-source partitions. Apply only exact, sourced geographic unions/splits; preserve old IDs, footprints and evidence. Do not merge legitimate ecological subdivisions merely because they share a source atom.
4. Resolve weak parent correspondence by exact administrative/functional membership or better compatible source footprints. A nearest-centroid assignment or a guessed coastline does not close the case.
5. Resolve all repeated/coextensive tiers with either a meaningful sourced intermediate grouping or an explicit compact-territory exception.
6. Resolve missing-island/source-land evidence independently of pixel representation. A grid covering every current polygon cannot prove that the source contained every island.

The machine-readable file contains every individual outcome and source-review pointer, plus the full 201-profile ↔ 252-reference-owner crosswalk and unmatched lists. No country or continent is exempted because it was not a user example.

## Every current region

Each of the 66 region branches below has every current location tested. The measured columns count triggers, not rejected territories. Independent geographic purpose and source-island completeness remain open where the underlying inspections lack those decisions. Counts overlap.

| Region | Locations | Scale contrasts | Multipart | Weak parent | Urban-role fragments |
| --- | ---: | ---: | ---: | ---: | ---: |
| Arabian Peninsula | 579 | 15 | 81 | 40 | 0 |
| Australia | 943 | 99 | 434 | 19 | 0 |
| Baltic | 317 | 32 | 18 | 19 | 0 |
| Brazil | 765 | 61 | 199 | 15 | 0 |
| Britain | 174 | 17 | 17 | 47 | 0 |
| Caribbean | 550 | 4 | 48 | 96 | 0 |
| Caucasus | 384 | 24 | 33 | 11 | 0 |
| Central America | 1225 | 5 | 61 | 95 | 0 |
| Central China | 307 | 1 | 0 | 6 | 0 |
| Central Europe | 1385 | 39 | 70 | 63 | 0 |
| East China | 512 | 2 | 1 | 26 | 0 |
| East Tropical Africa | 581 | 14 | 38 | 37 | 0 |
| Eastern European Plain | 2010 | 134 | 95 | 85 | 0 |
| Equatorial Micronesia | 3 | 0 | 2 | 2 | 0 |
| France | 323 | 1 | 17 | 7 | 0 |
| Iberia | 655 | 11 | 71 | 72 | 0 |
| Indian Subcontinent | 4686 | 21 | 324 | 111 | 0 |
| Indo-China | 2194 | 6 | 95 | 206 | 0 |
| Interior North America | 1108 | 24 | 36 | 2 | 0 |
| Ireland | 45 | 4 | 7 | 9 | 0 |
| Italy | 612 | 1 | 317 | 76 | 0 |
| Japan | 1688 | 22 | 104 | 170 | 1686 |
| Korean Peninsula | 335 | 3 | 29 | 38 | 0 |
| Low Countries | 388 | 1 | 4 | 54 | 0 |
| Macaronesia | 62 | 0 | 4 | 36 | 0 |
| Malesia | 2278 | 42 | 275 | 410 | 0 |
| Mexico | 2442 | 17 | 59 | 102 | 0 |
| Middle Asia | 550 | 49 | 79 | 29 | 0 |
| Middle Atlantic Ocean | 2 | 0 | 0 | 2 | 0 |
| Mongolia | 339 | 17 | 3 | 6 | 0 |
| New Zealand and Southwest Pacific Islands | 94 | 5 | 16 | 13 | 21 |
| Nordic Europe | 961 | 12 | 208 | 200 | 0 |
| North China | 366 | 10 | 11 | 3 | 0 |
| North-Central Pacific | 7 | 2 | 2 | 4 | 0 |
| Northeast China | 189 | 3 | 9 | 7 | 0 |
| Northeast Tropical Africa | 1238 | 32 | 73 | 30 | 0 |
| Northeastern North America | 464 | 34 | 116 | 11 | 1 |
| Northern Africa | 2236 | 89 | 96 | 122 | 0 |
| Northern South America | 415 | 7 | 19 | 32 | 0 |
| Northwest China | 352 | 17 | 15 | 14 | 0 |
| Northwestern Pacific | 54 | 0 | 12 | 48 | 0 |
| Papuasia | 377 | 23 | 63 | 53 | 0 |
| Russian Far East | 160 | 40 | 51 | 7 | 0 |
| Siberia | 679 | 147 | 87 | 2 | 0 |
| South Atlantic Islands | 2 | 0 | 1 | 1 | 0 |
| South Atlantic Islands | 2 | 0 | 2 | 0 | 0 |
| South China | 200 | 0 | 4 | 16 | 0 |
| South China Sea Islands | 5 | 2 | 2 | 5 | 0 |
| South Tropical Africa | 548 | 30 | 51 | 10 | 0 |
| South-Central Pacific | 23 | 0 | 6 | 20 | 0 |
| Southeastern Europe | 1852 | 5 | 85 | 199 | 0 |
| Southeastern North America | 1422 | 20 | 36 | 39 | 0 |
| Southern Africa | 422 | 12 | 23 | 20 | 0 |
| Southern Indian Ocean Islands | 4 | 0 | 3 | 0 | 0 |
| Southern Melanesian Islands | 25 | 0 | 21 | 12 | 0 |
| Southern South America | 1116 | 7 | 48 | 55 | 0 |
| Southwest China | 488 | 9 | 22 | 6 | 0 |
| Subarctic America | 125 | 37 | 79 | 0 | 0 |
| Taiwan and Penghu | 197 | 3 | 4 | 17 | 0 |
| West Tropical Africa | 2713 | 45 | 123 | 136 | 0 |
| West-Central Tropical Africa | 1000 | 48 | 43 | 74 | 0 |
| Western Asia | 2061 | 7 | 67 | 116 | 0 |
| Western Indian Ocean | 145 | 4 | 13 | 22 | 0 |
| Western North America | 533 | 25 | 87 | 8 | 0 |
| Western Polynesian Islands | 29 | 0 | 10 | 23 | 0 |
| Western South America | 1668 | 15 | 52 | 24 | 0 |

## Filling review evidence without changing the website

The optional `--resolutions path/to/independent-review.json` accepts a data-only map keyed by current entity ID. Each entry supplies the `footprint_sha256` printed in the diagnostic output, plus individually sourced `checks`. Each check has `status` (`supported` or `not-applicable`), `rationale` and nonempty `evidence` items with a public source `url` and an `inspected_fact`. The pipeline validates this content before accepting it. Missing checks remain open; stale footprint hashes fail. Location review hashes use SHA-256 of the sorted-key compact GeoJSON geometry JSON; group review hashes use sorted `[location ID, location review hash]` pairs for all members. These are explicitly review-context hashes, separate from normalized WKB and prepared-ownership asset hashes.

Independent evidence can justify an archipelago, restore confidence in published parent membership, or establish an explicit compact-territory tier exception. It cannot override incomplete chains, invalid geometry, overlapping interiors, member-derived footprints or unresolved children. Structural changes require a sourced geographic migration and a fresh diagnostic run. This keeps the review interface and its gates stable while future contributors add evidence as data.
