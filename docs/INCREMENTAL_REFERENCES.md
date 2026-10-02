# Incremental physical-reference preparation

`prepare-reference-incremental.py` prepares the same climate, potential-natural biome and topographic references after a geographic migration. It does not expand historical coverage, change live data, transfer retired-location claims, or interpolate missing values.

```sh
python scripts/prepare-reference-incremental.py \
  --before .cache/source-territory-repair-stage/before/world-index.json \
  --after .cache/source-territory-repair-stage/after/world-index.json \
  --receipt .cache/source-territory-repair-stage/migration-receipt.json \
  --references data/reference-attributes \
  --output .cache/source-territory-repair-stage/reference-attributes
```

Before/after inputs can be world-index manifests, explicit FeatureCollections or feature lists. IDs are stable strings, independent of positional indices or display names. The migration receipt must pin both published footprint hashes, exactly enumerate changed/added/removed IDs and include source evidence. Reuse requires exactly unchanged geometry under the same stable location ID. A future source replacement with hundreds of new/retired territories uses this same interface.

The output must be a new staging directory, separate from original products. The wrapper checks inputs before writing and builds into a temporary sibling directory. The complete product becomes visible only after all files and its index are written. Original source products remain intact.

## Reuse and source validation

Every frozen compact-v2 part must match its recorded SHA-256. Every row must refer to a before-snapshot location and valid existing type/value indices. Repeated resolved attribute intervals, unexpected historical intervals and unregistered row identities fail. Original category and source-type dictionaries retain their exact prefix; a genuinely new supported category may be appended.

The climate archive, extracted four native rasters, RESOLVE original geometry and EarthEnv original TIFF are verified against the frozen source proofs. Extracted climate files must match the archive entry length and CRC as well as their newly recorded SHA-256. The precise ellipsoidal area algorithm and existing EarthEnv summary helper must match their recorded algorithm hashes. Native climate and terrain formats and source classes are validated. Helpers and source files are pinned again before output is finalized.

Default sources are the existing licensed cached inputs. `--sources native-sources.json` may supply explicit paths using `climate_archive`, `climate_rasters` keyed by `1901`, `1931`, `1961`, `1991`, `vegetation` and `topography`. This relocates the same pinned source files; it cannot silently substitute a new climate/environment dataset. Source changes require a separately reviewed full preparation.

## Changed-footprint summaries

Only changed or newly added locations are recomputed. Unchanged compact row tuples are preserved; original parts with no affected locations are copied byte-for-byte. Retired rows are omitted from current data and archived, not reassigned to the surviving location.

Climate uses the original native cell-centre and cosine-latitude weighted categorical rule. The four supported intervals remain 1901–1931, 1931–1961, 1961–1991 and 1991–2021, with a separately labeled 2026–2027 modern reference using the 1991–2020 normal. Cell centres outside source support count toward the land denominator; less than half supported cells produces no claim. Tiny locations with no sampled native cell centre remain unknown.

Potential-natural biome uses the independently audited precise WGS84 surface-area helper. Same-biome source polygons are unioned before measuring, and coverage uses the entire location footprint. Source `N/A` remains an explicit unknown category with its evidence. These references describe potential-natural vegetation, not observed farmland.

Topography uses the existing EarthEnv geomorphon summary helper. Source windows are read directly from the SHA-verified original TIFF; an unverified native-array cache is never trusted. Bounded strips and the full out-of-source latitude denominator preserve polar behavior and limit memory allocation.

## Publication and retained evidence

The new `index.json` carries the after footprint hash, all updated part hashes/counts, original dictionary prefixes and the incremental receipt hash. `migration-before-records.json.gz` preserves every changed/retired location’s original tuples. `migration-new-evidence.json.gz` preserves precise biome assignment evidence. `incremental-receipt.json` records both footprint hashes, original index/source/algorithm hashes, affected IDs, reused/recomputed counts and unsupported changed-footprint outcomes.

The output index retains original source citations, original type definitions and their supported intervals. Previous vegetation numerical-review evidence remains linked, with its applicability explicitly limited to unchanged IDs; changed footprints use this incremental receipt. The original merged EarthEnv preparation index remains provenance for the original source snapshot, while current topography row counts are updated.

Before publishing a migration, retain the original preparation and these receipts/archives in durable versioned storage or tracked prepared-migration evidence. Validate current/server/static resolution against the new index. Never replace the old archive merely because another later migration uses the same staging filenames.

Run focused migration tests with `python -W ignore::PendingDeprecationWarning test/reference-incremental.py`. Fixtures exercise real native rasters and precise biome geometry, unchanged bytes, changed/added/retired identities, source-proof failures, unsupported source extent, unknown biome classes, interval preservation and larger source replacements.
