# How we extract named seas from SeaVoX

**TL;DR.** The build opens the SeaVoX archive once, finds every sea selected for the map, and exports each one to a GeoJSON file. It checks each shape against the checksum recorded in the decision snapshot.

## Where this runs in the code

- The [pipeline runner](../../scripts/map-build/pipeline/run_pipeline.py) starts the extraction as part of the water stage.
- The [batch extractor](../../scripts/map-build/water/extract_seavox_features.py) checks the inputs, extracts the selected seas, and writes the batch manifest.
- The [feature extractor](../../scripts/map-build/water/extract_seavox_feature.py) finds shapes by ID, prepares their geometry, and writes the individual outputs. It also provides the standalone single-feature command.

## How it works

1. Read the decision snapshot to find the SeaVoX archive and the feature IDs selected for the build.
2. Verify the ZIP and unpack its shapefile into a temporary work directory.
3. Scan the shapefile’s IDs without loading any shapes. Use that index to load only the selected shapes.
4. Use GDAL to organize the polygons and convert their coordinates to WGS84. Write one `source.geojson` and one manifest for each decision.

This saves work because the build reads the archive once and loads geometry only for the selected features. The temporary directory is removed after extraction.

## How we verify the result

Exactly one polygon or multipolygon must match each selected feature ID. Before creating the output directory, the build checks every shape’s SHA-256 against the decision snapshot and rechecks the archive and snapshot hashes. It rejects missing or duplicate matches, invalid decision IDs, conflicting archive checksums, and changed inputs.

The fast coordinate writer uses the same precision as the GDAL reference writer. If the resulting geometry does not match the expected checksum, the build uses GDAL’s GeoJSON writer and checks the result again. GDAL also writes the feature properties.

Each sea keeps the `worldatlas-seavox-archive-extraction-v1` manifest format. The sorted `batch-manifest.json` records the input hashes, decision and entity revisions, GDAL version, and hashes of the shapes, output files, and individual manifests. On resume, the pipeline verifies the complete batch directory. It preserves incomplete attempts and starts a fresh extraction when a batch needs to be rebuilt.

## Implementation details

- **Reference paths.** Use `--scan-reference` to compare with GDAL’s filtered scan. The standalone feature extractor can also extract a single feature.
- **Coordinate formatting.** See the [GDAL formatting attribution](../../scripts/map-build/water/GDAL_FORMATTING_LICENSE.txt).
- **Timing.** The batch’s `processing_elapsed_seconds` covers validation, extraction, and writing the outputs. Per-sea elapsed fields cover only writing the individual files and are already included in the batch time. The water stage counts the batch once.
