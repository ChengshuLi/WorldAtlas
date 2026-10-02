# Three prepared reference-hierarchy corrections

These corrections are **candidates, not installed geography**. They reuse source-backed proposals from the exhaustive six-continent follow-up. They do not approve the affected branches or close worldwide semantic review. The active atlas, original identity registry, fixed grid and historical records remain unchanged.

| Correction | Retained identity | Candidate change |
| --- | --- | --- |
| Monaco | `framework:area:france:a85924a668ef` | Rename the sole-member area from France to Monaco. Its only location is `gb:MCO:ADM1:64170238B96397749018979`; its province is already Monaco. |
| Luxembourg | `framework:area:belgium:3a14f80912de` | Rename the sole-member area from Belgium to Luxembourg. Its only location is `atlas:territory:LUX`; its province is already Luxembourg. |
| West Virginia | `framework:province:west-virginia:4c9dc6438fb1` | Reparent Hancock (`gb:USA:ADM2:52423323B20661288428578`) to this existing 54-member province, yielding 55 members. Retire the duplicate province `framework:province:west-virginia:8d71dccb3165`, retaining its original identity and full reference record. |

Both West Virginia parents have the same South Atlantic area (`framework:area:south-atlantic:383dc695ee31`). Its direct child count changes from ten to nine; its entire location membership and member-derived footprint remain identical. All original location geometry bytes remain identical. No location identity is introduced, retired, merged or renamed.

## Source support and limits

The [Monaco Statistics population page](https://www.monacostatistics.mc/Population-and-employment/Population) corroborates Monaco's territorial identity. The retained successful inspection has SHA-256 `c23e34be7ab80def14f1c157ec7e278ffd3da9d648fc6d36500021dd18573f47`. It supports the sole-member reference label; it does not establish an historical administration or an ideal atlas-tier role.

The [GISCO 2024 NUTS label GeoJSON](https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_LB_2024_4326.geojson), SHA-256 `14722ec89f2db5a61cb931af3ca1201bbe09f8a24f8b866864308711bf083b49`, names Luxembourg at codes LU, LU0, LU00 and LU000. The exact sole current Luxembourg member justifies the atlas reference label. NUTS statistical levels are not automatically mapped to atlas tiers.

The [US Census 2025 county Gazetteer](https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_Gaz_counties_national.zip), SHA-256 `4c90d0f805779923b5958ab13d0c1e9b99fe4932b786bfcf75dd739bb2dcb4ea`, contains 55 West Virginia counties. All 55 current location names match independently after removing the official County suffix. Both province portions independently match the same pinned geoBoundaries source parent, `gb:USA:ADM1:66186276B64762166704956`, ISO `US-WV`, whose geometry SHA-256 is `a3569955c5429a57b618f4bb0a84ede2ad84d7ddab580fee2edafa4c079221b3`. Their member-to-original-parent coverage shares are 0.99853126 and 0.99554741. Source-parent diagnostics remain name-and-area evidence rather than legal identity certification.

The source-proof archive retains these successful response receipts, all 55 official registry rows, exact source-parent diagnostics, every involved current ID and original proposals. This preparation reuses the frozen inspections; it does not claim new network inspections. Source coastal vintage, local granularity, West Virginia's suitability as one local cluster and full branch semantics remain open. The old Luxembourg metadata describing two members is an earlier inspection: actual current membership contains one location. Original metadata remains preserved as evidence context.

## Reproduction and complete impact

Run from a fresh checkout with Python 3 and Node.js 24; no downloads or additional Python packages are required:

```sh
python scripts/prepare-reference-hierarchy-corrections.py
python scripts/prepare-reference-hierarchy-corrections.py --check
```

The script requires the precise active baseline and all six frozen follow-up reports matching the global validation receipt. It rejects missing source proof, nonunique source-parent identity, changed member inventories, an already applied correction or unexpected geometry. It verifies every one of the 49,589 location footprints against the global closure evidence and every complete six-tier chain before and after. Before finishing it checks that every pinned input stayed unchanged during preparation.

The only durable data outputs are:

- `data/reference-hierarchy-corrections/source-proof.json.gz`: source receipts and exact proposal/registry/parent evidence.
- `data/reference-hierarchy-corrections/migration-receipt.json.gz`: complete 5,705-unit original hierarchy, all changed group records, the retired parent record, exact Hancock property crosswalk, all 49,589 unchanged geometry IDs, every affected descendant chain and every affected parent membership/footprint proof.

Gzip timestamps are zero and canonical JSON is deterministic. `--check` compares both archives byte for byte without rewriting them. It regenerates the untracked candidate geography at `.cache/reference-hierarchy-corrections/geography`, with its own world index, hierarchy and all 34 geometry parts. This full approximately 211 MB directory is never a tracked or deployment asset; a future checkout reconstructs it from committed inputs.

The receipt inventories **57 affected locations and 14 affected ancestor groups**. Exactly **three location chains** change: Monaco's and Luxembourg's ancestor names, and Hancock's province identity. The other 54 West Virginia members retain their complete chains; the surviving province's footprint grows by the exact Hancock member footprint. Five group records change: the two renamed areas, retained and retired West Virginia provinces, and South Atlantic's direct child count. Candidate counts are **49,589 locations → 5,132 provinces → 471 areas → 66 regions → 29 subcontinents → six continents**.

The original aggregate prepared footprint hash remains `5d7236fe7e9d2f83c07c0b5cc1d5e703bf685f860fd49c850edd18eea27c61a8`. Historical and environmental payloads are not transferred, reassigned or rewritten. Their manifest pins and immutable-registry/migration pins are retained in the receipt; this is a reference-membership change without a historical effective year.

## Technical-maintainer installation still required

After reviewing this candidate and completing the backend migration, use the versioned [geographic-release workflow](GEOGRAPHIC_RELEASES.md) to stage, verify and publish a new complete reference version. The original registry rows, published old reference releases and dated claims must remain immutable. The retired West Virginia parent stays registered and inactive in the new reference release, with an explicit same-tier `merge` crosswalk to the retained province. This cartographic consolidation transfers no historical record to the survivor.

The release preparer validates this receipt's `group_changes`, `changed_location_properties` and explicit `relationships` through `--metadata-migration`, alongside the retained macro-boundary receipt and existing geometry repair manifests. For an opt-in relationship receipt it checks complete before-unit archives, exact archived predecessor records, registered same-tier endpoints, complete adjacent-tier chains, one relationship per retired parent, the exact union of descendant location identities and unchanged containing-parent membership. Counts alone cannot establish conservation. Missing, duplicated, extra or contradictory merge endpoints reject preparation before output.

It emits the explicit West Virginia `merge` crosswalk with the receipt hash, exact original relationship JSON and source-evidence receipts, rather than a generic retirement. Frozen old decisions remain unchanged. Receipts without a `relationships` field retain the existing preparation path and manifest bytes. Carry original registered identities from the prior release manifest; no new identity is needed for these corrections. The preparation fixture reconstructs the complete candidate without depending on `.cache`; `node --test test/reference-hierarchy-release.test.mjs` verifies the full 49,589-location release, exact original baseline manifest and malformed crosswalk rejection. This is local preparation validation, not proof of a published release.

A reviewed preview can be prepared locally after reconstructing the candidate:

```sh
node scripts/prepare-geographic-release.mjs \
  --geography-data .cache/reference-hierarchy-corrections/geography \
  --metadata-migration data/macro-boundary-migration.json.gz \
  --metadata-migration data/reference-hierarchy-corrections/migration-receipt.json.gz \
  --registry-manifest data/geographic-releases/index.json \
  --reviewed-version 3 \
  --output .cache/reference-hierarchy-corrections/release
```

Version 3 is a local preview against the retained version 2 manifest, not a claim that version 3 is available to publish after intervening releases. Compare the live reference version and registered identity proofs before any actual staging. The preview has zero new entities and retains the exact original baseline definition; all output remains untracked.

Stage against the latest published version and its matching registered-identity/source proofs, rather than hardcoding a release number. Verify imported memberships, counts and crosswalk hashes, inactive predecessor context, unchanged dated evidence, and matching prepared/server/static release pins. Regenerate only the approved reference hierarchy and reusable parent-boundary metadata; location ownership, environmental values and canonical pixel ownership do not need new computation because location footprints and IDs are unchanged. No publication or active-geography write is performed by this preparation script.
