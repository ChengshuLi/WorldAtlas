# Restore reviewed geography from a fresh Git checkout

`restore-reviewed-geography.py` reconstructs the exact original baseline and both reviewed geographic migration stages using only the pinned final geographic snapshot and tracked receipts. It requires no `.cache` history, credentials, hosted database, external download, or private service. It writes only a fresh output directory and never changes live geography or records.

```sh
python scripts/restore-reviewed-geography.py \
  --final data/world-index.json \
  --evidence data/geographic-repair-evidence \
  --manifest data/geographic-restoration-manifest.json \
  --output .cache/restored-reviewed-geography
python test/reviewed-geography-restoration.py
```

The final input must be the matching geographic revision: all 49,589 final identities, complete parent memberships, names and review metadata must match the immutable macro receipt. A later changed footprint or metadata revision cannot silently substitute for it. Use the matching Git revision if further geographic migrations have occurred.

The wrapper first verifies every source archive, source/macro linkage, decision file and compact original part-order manifest. It reverses the 30 changed macro location-property records and restores every prior group through `before_units`, accounting for all 7,631 changed ancestor/name chains. It then restores all 52 original source location features, including 25 retired IDs, and the complete original hierarchy. Claims stay on their original identities: full record archives accompany the output without transfer.

The original ordered ID/part layout is retained in `data/geographic-repair-evidence/original-location-order.json.gz`, only **441,793 bytes**. It records order and partition membership, rather than duplicating the 202 MB original geography. Raw original part hashes cannot be reproduced from an unordered set of IDs, so this is a necessary durable resume input.

The output includes:

- `baseline/`: original 49,614-location geography with complete original hierarchy; every original geometry-part, hierarchy and world-index **raw SHA256** must match.
- `source-stage/before/` and `source-stage/after/`: complete source-repair before/after snapshots, immutable receipts, original source/feature/claim archives and dated-footprint inputs. The entire source-after raw snapshot must match the macro-preparation pins.
- `macro-stage/before/` and `macro-stage/after/`: complete macro-migration snapshots preserving source geometry and all original IDs.
- `restoration-proof.json`: verified counts, footprint hashes, raw baseline/source-stage hashes, receipt pins and archive/chain status.

Serialization is deliberate: original baseline geometry parts include their trailing newline, while its original hierarchy and world-index do not; source-stage files omit it, and macro-stage files include it. Both raw serialization guards and canonical content guards are checked, rather than using a different serializer and reporting a false raw match.

## Executed full-data proof

The wrapper was run against the frozen final macro snapshot and tracked Git receipts. It successfully reconstructed both footprint hashes:

- Original: `1c8c1584520d7360375c8ac79f12fe840dd8a47efb10f3d05c8517689667dd58`, 49,614 locations.
- Repaired source/final: `5d7236fe7e9d2f83c07c0b5cc1d5e703bf685f860fd49c850edd18eea27c61a8`, 49,589 locations.

All **36 baseline raw files** and all **36 source-after raw files** matched their original pins. Every restored chain is complete; all archived identities and records remain intact; no historical claims are transferred. The durable result is `data/reviewed-geography-restoration-proof.json`. Six focused tests additionally reject changed geometry, altered final metadata, corrupted archived parent chains and mismatched reversal records, and check the explicit newline convention.

Restoration proves lossless reversibility and resume inputs. It does not approve unknown historical content, source semantics, or a later publication. The previously compiled ownership corpus retains all 6,834,664 original intervals through reuse/archives, as documented in `SOURCE_TERRITORY_REPAIR_MIGRATION.md`; subsequent derivation must use the appropriate immutable ownership corpus and record context.
