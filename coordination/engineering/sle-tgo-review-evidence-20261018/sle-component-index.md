# PR #2480 original-component index follow-up

**Disposition:** the retained original geometry files and their source pins are identified and locally hash-matched. All 1,213 exact-head observation rows have source polygon indexes within the pinned ADM2 features’ part counts, and their source/question component identities match. This is an index/reference integrity check only; it does not replay geometric membership.

## Original geometry sources located and pinned

PR #2480's `draft-input-pins.json` binds the consumed historical source corpus at commit `21984e9ec4ec7370bc807e2da23cea2228747698`:

- ADM2: `coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-SLE-ADM2-000.bin.gz`, 98,869 bytes, SHA-256 `442e43ff29142a52b4fc3ba1d49517c8d9a0661afde350110b240241cd30df09`; uncompressed 319,064 bytes, SHA-256 `79ab7eb1c08112c416074f8f3cc7fd641b3fd868525acddc4c74877014583aea`.
- ADM1 context: `coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-SLE-ADM1-000.bin.gz`, 66,864 bytes, SHA-256 `c9b3fcff4d80a3b5ea9ee535573a9ec39058dac313c45432538ebc53e572da07`; uncompressed 175,696 bytes, SHA-256 `2f991e1b481a4375185b71d71ecedf51066323314f7cf98120e94117b95b8368`.

The retained source packet at `africa-workers-20261017/worker2-mdg/next-scope-readiness/` contains `gb-SLE-ADM2-whole-original.geojson` and `gb-SLE-ADM1-whole-original.geojson`. Their observed SHA-256 values exactly match the respective uncompressed PR source pins above. I parsed only the JSON feature/geometry-type structure (no spatial predicates or GIS operations): the ADM2 whole-original contains 14 ordered features and 95 polygon parts in total; ADM1 has 4 features and 85 parts. These counts agree with the exact-head science review's reported 95 ADM2 source components and the retained four-ADM1/fourteen-ADM2 scope.

The associated historical archive custody record preserves gbOpen archive hashes `f86b437e8ac44a6f3e5f344d93795e562970283f629c35a930518771e4e9b8c7` (ADM1) and `b4cd638f5053f2d23f1064a2496f9794abf814d7532f514b6543f7fe0af96777` (ADM2), at geoBoundaries revision `9469f09592ced973a3448cf66b6100b741b64c0d`. The source metadata dates these as Province 2014 and Districts 2017. The exact PR input-pin manifest SHA-256 is `faf619ca7290e8eead858bcd1ef31bee757d647a143a28a264225b9a55330c44`; the local whole-original files' observed hashes above can be compared directly to that manifest.

## Per-observation component-index check

I read the exact-head `results-001/cell-observations.json` body supplied from the original PR worktree. It is 1,327,109 bytes and its SHA-256 matches the exact-head byte proof: `849a238f83e1660bb49cef6802704a6debf4df26d57bd7dd2613d6610715c0ae` (Git blob `c90f5d863401b891c26e89731b375e1b2cb1c645`). It contains 1,213 rows and 1,213 distinct `(y,x)` keys. Each row has exactly one `source_polygon_indices` entry.

I compared each row's `source_id` with the ordered features in the hash-matched original ADM2 GeoJSON; I checked that its single component index is a nonnegative integer below that feature's Polygon/MultiPolygon part count. I also joined the row's question ID source index against the retained original feature roster and checked that the component number embedded in the question ID equals the row's `source_polygon_indices`. All 1,213 rows passed: zero source-ID/roster mismatches, zero out-of-range component indexes, zero question-ID/index mismatches. There are 78 unique `(source_id, component-index)` pairs and 78 unique question IDs.

| Original ADM2 source | Feature parts | Observed component indexes |
| --- | ---: | --- |
| Pujehun | 1 | 0 |
| Moyamba | 2 | 0–1 |
| Western Area Rural | 5 | 0–4 |
| Western Area Urban | 1 | 0 |
| Kambia | 15 | 0, 1, 4–5, 7–14 |
| Bonthe | 46 | 1–25, 27–32, 36–45 |
| Port Loko | 18 | 0–3, 5–12, 14–17 |

The recorded `source_polygon_indices` are ADM2 feature-local component indexes. Each row's `secondary_source_membership` also resolves to a retained ADM1 feature (zero invalid ADM1 IDs), but the observations do not record an ADM1 polygon-part index, so no ADM1 part index was claimed or compared. The ADM1 feature/part inventory itself was checked structurally above: 4 features, 85 parts total.

This confirms index validity and source/question identity joins, not that a point geometrically lies in the indexed component. No spatial operation, GIS library, producer, or predicate was run. The earlier direct-check gap is resolved for source polygon index bounds; geometric membership remains the completed centre-observation's claim and was not replayed here.
