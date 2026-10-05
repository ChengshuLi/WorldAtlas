# Findings: USA ADM2 source hash lineage

**Issue:** #981, exact scope of 279 `gb:USA:ADM2:*` subjects from #428.
**Baseline:** `ec33c238d801aeb9dfe83e87025560b9383c695d` (fresh `origin/main` when reserved).
**Upstream:** `wmgeolab/geoBoundaries` commit `9469f09592ced973a3448cf66b6100b741b64c0d`, committed 2023-12-13.

## Hash and source finding

The repository's `data/administrative-sources.json` record `gb:USA:ADM2` declares `simplifiedGeometryGeoJSON` at the pinned upstream commit and stores SHA-256 `16249e8d795aaded6a72910a8c72115a073814b25ee902d61ccc9a9490c6641a`. That digest is the exact Git LFS object ID and SHA-256 of the retained simplified GeoJSON (7,938,450 bytes). It is not the full GeoJSON hash. The full object is 10,500,644 bytes and hashes to `81fdd384df8012e5007ed2994a8ab306352f3c48e32cd8ea99182195e8647f43`; metadata JSON is 939 bytes and hashes to `a4d2a82a1cd434960b6ed49531bff3330d0881674eea9dc8711e1ad6bf049b9f`. The original LFS pointer files are retained and their object IDs and sizes match these objects byte-for-byte.

Both national GeoJSON variants have 3,233 features and 3,233 unique, matching `shapeID` inventories, consistent with metadata `admUnitCount=3233`. All 279 issue IDs join exactly once to each variant and occur exactly once across the 36 `world-index.json` parts. For this scope the Atlas IDs occupy parts 25 (55), 26 (149), and 27 (75); the existing parent packet's Census crosswalk associates 159 with Georgia and 120 with Kentucky. Full and simplified geometries differ for 210 of these 279 subjects, so those representations must not be conflated. The source's national `shapeGroup=USA` does not itself encode each county's state parent; parent interpretation is cross-referenced to the Atlas hierarchy and #428's reviewed per-subject Census crosswalk.

## Vintage, granularity, completeness, and reuse

Upstream metadata labels this product USA / ADM2 / Counties, boundary year 2018, sourced to the U.S. Census Bureau MAF/TIGER Database. It records source data update date January 19, 2023 and build date December 12, 2023. The metadata states Public Domain. This packet records that upstream assertion and its Census source attribution; it does not independently determine legal rights or legal boundary status.

The neighboring granularity reviewed here is the complete national ADM2 shapeID inventory of 3,233 units, with the 279 issue subjects nested under state-level Atlas parent records. A matching national count and ID inventory establish source identity and product completeness as represented by this pinned artifact only. They do not establish currentness, legal boundary correctness, universal equivalence to every county-like jurisdiction, treatment of every island/coastline, or completeness of any custom macro-region. The retained objects are historical reference evidence, not a present-day boundary authority.

The raw GitHub endpoint returned LFS pointers, not payloads. Full GeoJSON restoration was already recorded in the closed #428 packet and rechecked here; simplified GeoJSON and metadata objects were retrieved from the immutable `media.githubusercontent.com` commit URLs. Exact requests, retrieval dates, status, hashes, byte counts, pointers, and two not-retrieved object IDs (all.zip and TopoJSON) are documented in `sources/upstream-2018/retrieval.json`. Their LFS pointers are retained; the all.zip and TopoJSON payloads are not represented as restored.

## Reproduction and handoff

`findings/subject-crosswalk.jsonl` gives all 279 ID, name, parent, exact source joins, geometry-variant equality status, and prior Census GEOID/FIPS reference. `scripts/audit_lineage.py` verifies issue and parent scopes, immutable baseline, source pointer/object equality, source metadata/count, complete ID inventories, unique Atlas occurrences, parent joins, and exact hashes. `findings/input-manifest.json` preserves descriptors for all baseline pins, all indexed parts, parent #428 assessment/restoration evidence, and source retrieval inputs. `evidence-quality.json` binds those data and every packet output to exact file hashes.

**Engineering handoff:** Preserve the current catalog digest: it correctly matches the declared simplified artifact. Do not change it to the full-object hash to resolve the apparent discrepancy. If the catalog's checksum target is not clear to consumers, document the checksum-to-URL field contract in a separately scoped engineering change. This geography packet makes no shared catalog or boundary edits.

**Unresolved:** no legal/current boundary adjudication; no coast/island completeness certification; no claim that all `ADM2` records are interchangeable with local legal counties; no wider regional meaning certification. These are outside this source-lineage issue and remain explicit follow-up limits.
