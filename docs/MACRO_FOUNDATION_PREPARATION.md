# Global macro foundation preparation

GitHub #33 owns this bounded milestone beneath #32. The artifacts here are
**candidates, not installed geography or approval**. Regional interiors and new
location-attribute imports remain unapproved. Antarctica remains excluded.

The four `data/macro-foundation/*-review.json.gz` ledgers assess all current
6 continents, 29 subcontinents and 66 regions. Their original input hash and
compressed/decompressed hashes are retained in `review-index.json`. Supplemental
boundary decisions contain inspected source receipts, explicit geographic
conventions, named island routing and unresolved coverage. Sources are facts and
citations, not a claim that every publisher's complete document is archived.

The hierarchy is constructed bottom up. External evidence reviews a parent's
territorial meaning; membership corrections then rebuild that footprint from
its locations. Approval of an upper boundary never approves its descendants.
Named missing land has a fixed regional destination but remains a coverage gap.
Reference administrative envelopes are explicit conventions, not falsely precise
physical crests or inferred historical political ownership.

The prepared candidate has 49,589 unchanged locations, 5,132 provinces, 478 areas,
81 regions, 29 subcontinents and six continents. Brazil uses the five official
IBGE geographic regions; South Asia has ten sourced branches; Western Asia's
residual branch has three successors. Island and border-fragment corrections
retain original identities, source relationships and history.

Reproduce from the committed prepared baseline:

```sh
python scripts/build-global-macro-policy.py
python scripts/prepare-global-macro-geography.py
node scripts/prepare-geographic-release.mjs \
  --geography-data .cache/global-macro-foundation/after \
  --metadata-migration data/macro-boundary-migration.json.gz \
  --metadata-migration data/macro-foundation/migration-repairs.json.gz \
  --metadata-migration data/macro-foundation/migration-areas.json.gz \
  --metadata-migration data/macro-foundation/migration-regions.json.gz \
  --registry-manifest data/geographic-releases/index.json \
  --reference-date 2026-10-02 --reviewed-version 3 \
  --output .cache/global-macro-foundation/release
```

Version 3 is a candidate against retained release 2. Actual publication must
recheck the current live release; it must not reuse an occupied version.
The three ordered receipts preserve exact original unit records and disjoint
split crosswalks. They change zero location footprints and transfer no historical
claims. Preparation checks 291 historical-product files remain unchanged.
Large source collections use bounded, hash-pinned pointers into the retained
receipt rather than overflowing the API's 16 KiB per-record evidence limit.

Validation still needs complete actual envelope conservation, reconciled shared
edges, coherent active assets, matching hosted publication and fixed regional
handoffs. The retained initial envelope diagnostic exposed dropped source
polygons during bulk dissolution; it is failed evidence, not approval. Existing
physical-precision uncertainty and missing shorelines must stay explicit.
