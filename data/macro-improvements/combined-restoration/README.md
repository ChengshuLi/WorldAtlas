# Combined macro land correction, issue #45

This package composes the merged, immutable source stages #501/#502/#503/#505/#506. It is an offline producer, not an import or deployment. All underlying source files remain in their respective source-owned packages, pinned by `inputs.json`. Each package retains original source bytes, attribution, license, and reconstruction methods. OpenStreetMap geometry is ODbL; GeoNames identity evidence is CC BY 4.0. GSHHG comparisons do not replace source-backed footprints.

Release-3 baseline: 49,589 locations. Result: 49,623 locations, 34 creations and eight new groups, six retained-ID footprint corrections, three present-day location label corrections plus one metadata provenance update, and two province reference labels. Location IDs, original geometries, original catalog, previous releases, and historical claims are preserved. No historical attributes are invented or transferred. Kingman Reef and Gardner Pinnacles remain source-backed zero-cell holds. Chagos restoration is explicitly partial. Regional interior approvals remain open.

Run from a full, hash-matched checkout, with a fresh output directory outside the repository:

```sh
python3 scripts/compose-macro-restoration.py --root "$PWD" --output /tmp/worldatlas-macro-candidate
python3 scripts/validate-macro-restoration.py --root "$PWD" --stage /tmp/worldatlas-macro-candidate --output /tmp/worldatlas-macro-candidate/independent-validation.json
node --max-old-space-size=4096 scripts/prepare-macro-restoration-proofs.mjs --root "$PWD" --stage /tmp/worldatlas-macro-candidate
python3 scripts/compose-macro-install-proof.py --stage /tmp/worldatlas-macro-candidate
```

Run the full-baseline checks serially. The first step links untouched geography parts and materializes only edited parts. These links are read-only preparation inputs: final installation must use materialized validated assets. The independent Python checker replays each replacement from original coastline/water source bytes, streams every final location for positive land overlap against the 40 changed/added territories, and checks all archived polygons against the 34 proposed identities. The existing generic creation contract then verifies exact source wrappers, complete adjacent tiers, unique identity, name homonyms and unchanged predecessors. The existing release producer independently reconstructs the complete original footprint and identity sequence.

Output directories `baseline`, `reference`, `replacement`, and `creation` make operations explicit. `reference-receipt.json` accounts for modern reference metadata. `replacement-migration/index.json` accounts for six same-ID footprint changes. `creation-migration/index.json` accounts only for pure additions. `identity-proof-sequence.json` pins the original geometry repair, all four historical metadata receipts, then the new reference receipt, replacement proof and pure-creation proof. `geographic-release` contains bounded API batches and `preparation-summary.json` reports their actual byte sizes and preservation hashes.

The installer must receive the explicit current-baseline replacement→creation geometry proof descriptor, as well as the separate reference receipt. A combined source receipt cannot pretend the six replacements were pure creations. This producer does not compile the world grid, reuse obsolete derived ownership, approve regional interiors, import a release, or publish a Site. Those are the root publication gates, including canonical-grid representation, stale ownership/environment invalidation, macro envelope routing, matched static/hosted assets and hosting/storage limits. Private registry/claim preflight is a separate authorized publication gate and must be recorded at an exact live revision; credentials never belong in this package.

`aggregate-source-receipt.json` retains exact installed pre-reference originals and relocates the 34 child creation wrappers. `geometry-proofs.json` pins current-baseline replacement→creation plus the explicit reference receipt; it deliberately excludes the original repair, which belongs to the complete release chronology. The installer validates all ordered proofs before accepting the compound stage.

`installation-proof.tar.gz` retains the descriptor, separate reference receipt, both child proof manifests and every SHA-pinned member together. `installation-proof-index.json.gz` pins the exact compressed container and member bytes. Documentary JSON snapshots in this evidence directory do not resolve proof paths by themselves; replay the producer or safely extract the verified archive to a separate staging directory. Do not execute an import merely because an offline proof exists.
