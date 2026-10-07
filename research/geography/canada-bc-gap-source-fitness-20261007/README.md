# British Columbia complete gap-family source-fitness packet

This is a bounded, source-only assessment for issue #1362. It preserves the complete accepted routing family `gap-source-batch:63d748f318d7dfeb738447ea`: all 43 physical components, full contact `atlas:district:CAN-5917:BRC`, all 28 numeric siblings (including nine demonstrated local construction contradictions, 18 unresolved numerical/context prerequisites, and one original replay mismatch), the 15 nonnumeric siblings, and all 146 original query relationships. No active Atlas geography, source data, or live service is changed.

## Findings

The family is marked source-fitness and physical-authority unapproved in the accepted routing record. Its 43 physical rows remain 15 `mixed-source-support` and 28 `unknown`; mapped-water and contradictory-support sums are zero, which does not prove dry land. The inherited emitted impact is 116441477.74262899 m² and is diagnostic accounting only.

The current contact is an undated modern aggregation with 22 retained source-member IDs and an ArcGIS item locator. A retained Statistics Canada 2021 Census Division feature identifies CDUID 5917 / Capital (RD); it is a dated statistical-unit cross-check, not a legal boundary or physical-land source. Both geometries are valid, but the current contact is not topologically equal to the retained 2021 feature. A retained GSHHG 2.3.7 full-resolution artifact supports only a 2017 generalized coastline/mapped-land screen. The representative-point/centroid screen covers neither all contact geometry nor any complete component proof. No source is accepted here as complete, current, legally authoritative, or sufficient to resolve physical status.

The nine numeric contradictions remain construction-local diagnoses. They do not validate source membership or imply a correction. All 43 source-fitness dispositions remain unapproved. See `source-assessment.json` for the complete source-role limits and `component-review.jsonl` for the row-level records, original physical row hashes, all query bindings, candidate hashes, routing status, and numeric disposition.

## Reproduction

Use Python 3.12 with Shapely and a checkout containing the exact pinned source paths. From the repository root, set `PYTHON` to that runtime and create a new, absent output directory for each run:

```sh
"$PYTHON" research/geography/canada-bc-gap-source-fitness-20261007/build_packet.py \
  --repo . \
  --out research/geography/canada-bc-gap-source-fitness-20261007/vintages/run-NN
"$PYTHON" research/geography/canada-bc-gap-source-fitness-20261007/controls.py \
  --packet research/geography/canada-bc-gap-source-fitness-20261007/vintages/run-NN \
  --out research/geography/canada-bc-gap-source-fitness-20261007/vintages/run-NN-controls.json
"$PYTHON" research/geography/canada-bc-gap-source-fitness-20261007/assemble_manifest.py
```

The producer authenticates all accepted routing and diagnosis chunk receipts, reconstructs the complete family, obtains each complete original physical source blob from the immutable accepted routing commit, verifies Git blob identity and every selected row hash, and reads the current contact plus retained source artifacts. It admits the exact output set with the shared immutable new-vintage helper and publishes a complete receipt last. The directed controls exercise exact roster matching, omitted/duplicate/foreign members, query closure, numeric classification, contact roster, non-equivalence of the two administrative geometries, the actual family-row hash and a mutated-family negative case, occupied-destination preservation and retained physical uncertainty. A control output is not included in the producer's run hash inventory; the top-level manifest separately binds the control results.

Two independently produced vintages (`run-15` and `run-16`) and directed-control outputs are retained under `vintages/`. Their six producer payloads are byte-identical; each run's 14 directed controls passed. The run publication receipt differs only by vintage path and correctly lists that run's complete payload set. The issue-declared top-level `evidence-quality.json` inventories every changed file and binds the current active contact feature, source pins, numeric results, limits and controls.

## Immutable evidence and limits

The packet pins the accepted routing report at commit `0198938719a5666b6726fb6a1e45779926eefeb2`, the accepted numeric diagnosis report at `bec82842ad5d9cf07e38a78395df8d5e7a6f4591`, and current retained inputs by Git commit, path, mode, blob OID, byte length, and SHA-256. `source-input-pins.json` records whole original physical files and row-level selected closure. Inputs are not copied or overwritten. Restoration uses the repository Git blobs, not network services or a rerun of the original operator.

The full retained Statistics Canada BC Census Division response is 38,880,150 compressed bytes, above the shared 32 MiB single-file evidence limit. It remains in the prior packet. Its full-file byte count and SHA-256 are checked against that packet's retained `sources-manifest.json` and are recorded in `source-input-pins.json`; the limit is not waived, and the file is not copied into this packet. A reviewer can inspect the original tracked blob and its CDUID 5917 record directly.

This is research evidence, not a geographic approval, correction proposal, publication authorization, or release. No legal-boundary interpretation, cadastral/shoreline authority, current source acquisition, completeness of the 22-member aggregation, or physical classification of unknowns is claimed. Source and reproduction results do not close dependencies outside this bounded family.
