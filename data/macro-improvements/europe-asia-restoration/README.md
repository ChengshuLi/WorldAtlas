# Source-backed Europe and Asia land restoration (#505)

This is a **staged sparse patch**, not a geographic release or migration receipt.
The publisher composes it with other independently validated corrections under
#45. It never edits the current dataset, canonical grid, records or Site.

The eight non-Marcus modern query domains contain 25 verified dry-land polygons
at the retained comparison floor of 0.1 km². Named territorial purpose groups
these into five existing location IDs and one new complete-island location:

| Location | Decision |
| --- | --- |
| Megisti / Kastellorizo | Retain municipality ID and add sourced Ro land; other municipal islets remain open. |
| Malta | Retain compact-territory ID and add Comino/Cominotto. |
| Bailiwick of Guernsey | Retain territory ID and add Sark/Brecqhou/Herm/Jethou. |
| Cocos LGA | Retain original 14-part source identity; replace the tiny West Island fragment with coherent modern southern-island and North Keeling dry land. |
| Chagos / BIOT reference | Retain territory ID; replace partial Diego Garcia with whole dry-land source components and add compared Salomon islets. **Whole Chagos coverage remains open.** |
| Fugloy | New named island → sourced Fugloyar municipality province → existing Føroyar area → Nordic Europe → Northern Europe → Europe. |

Fugloy's municipality is a documented remote, coextensive local-tier exception,
not an Eysturoyar attachment based on owner. Its physical family is Norðoyar;
Eysturoy is a distinct island. The source-backed exception and new footprint
still require coordinated engineering integration. Existing FRO-1443 geography
and the Faroese regional-interior task are preserved. Marcus is excluded into
its reciprocal macro-association task.

`produce.py` reconstructs every selected source polygon from exact original
OSM XML with directed closed coastlines and inland/lagoon water masks. It checks
pinned retained WKB against reconstructed dry land, validates parent chains and
all-current-land overlap, and samples the existing fixed-grid implementation.
Original edit timestamps describe source versions, not historical validity.
Geometry is modern reference for 2026–2027; no ancient ownership or settlement
attributes are inferred.

`prepared/patch.json.gz` exposes the shared sparse fields
`existing_location_updates`, `existing_group_updates`, `added_features`,
`added_groups`, `creation_proofs`, `operations`, source checks and explicit holds.
The creation source wrapper pins exactly the generated Fugloy dry footprint;
its original OSM archive/XML hashes remain separate provenance. Exact old
features are archived in `prepared/before-features.json.gz`. Original GB
collections and the unchanged 85,315-entity identity registry context are
retained under `sources/`; historical records never transfer automatically.

Reproduce from a full checkout with Python preparation dependencies and Node 24:

```sh
python data/macro-improvements/europe-asia-restoration/produce.py --baseline data --output /tmp/europe-asia-reproduced
WORLDATLAS_BASELINE="$PWD/data" python data/macro-improvements/europe-asia-restoration/test_producer.py
```

The output directory must be fresh and separate from the baseline. No network,
database credentials, global-grid compilation or live import is required.
Sparse worker checkouts can pass a read-only full baseline elsewhere.

All 25 compared components have canonical cell centres (minimum five); unrelated
baseline overlap is zero. The 49,584 other locations stay untouched. These
checks do not certify every tiny coastal ring or complete regional interiors.
North Keeling's lagoon and Diego Garcia's retained water relation are subtracted;
coastline/tide/vintage precision remains explicit. Full Chagos, smaller unassociated
islets and regional semantic approval stay open. Spatial assignments, ancestor
unions, certificates and grid assets must be regenerated/revalidated by the
coordinated publisher before any release becomes current.

Source licenses: OSM database ODbL 1.0 (contributors attribution); original AUS
geoBoundaries CC BY 4.0, GRC CC0, MLT public domain per retained pinned metadata;
Wikipedia named-geography text CC BY-SA with contributor history attribution.
The official Fugloyar homepage is cited by URL/hash and factual paraphrase only;
its raw page/media are not redistributed because reuse terms were not verified.
