# Selected vector features

Import features whose geometry is already encoded in a vector file such as a Shapefile, GeoJSON, or GeoPackage. The importer saves each feature in `atlas.source_features` with its `id`, `geometry`, and `construction_id`. Geometry uses WGS84 `[longitude, latitude]` in degrees. Map building reads the stored geometry to check spatial relationships against the current grid.

## Use

Run the `selected_vector_features` method with the common import command.

```bash
worldatlas-import --recipe CONSTRUCTION_ID \
  --r2-endpoint R2_ENDPOINT --work-dir /absolute/path/to/worldatlas-work/inputs
```

## How it works

Raw files are pinned by their cataloged size and checksum. Neon checks the [recipe's argument names and types](../README.md#argument-validation) and the structure of stored coordinates. The importer checks that selected features exist and rejects invalid geometry, such as self-intersecting polygons.

### Vector selections

The construction arguments contain `source_id`, `id_field`, and `selections`. Set `id_field` to the name of the source attribute that identifies features, or use `@fid` for the native feature ID reported by GDAL. Each selection supplies the ID to look up in `source_feature_id` and the ID to save in `feature_id`. Different output IDs can select the same provider feature. Provider attributes stay in the raw file.

- For a ZIP, set `member` to the dataset path inside the archive. You can omit it when the archive contains exactly one `.shp` file. Set `layer` when the selected dataset contains multiple layers.
- GDAL converts coordinates from the source's declared coordinate system to WGS84. For GeoJSON already in WGS84, the importer reads the original coordinate values. PostgreSQL normalizes `-0.0` to `0.0` when saving.
- Each provider ID must match exactly one record in the selected layer.
- Set `polygon_containing: [longitude, latitude]` to select one part using a point in the stored coordinate system. The point must be strictly inside exactly one polygon. Points on boundaries or in holes fail the selection.

Polygons retain holes by default (`fill_holes: false`). Set `fill_holes: true` to keep only the exterior rings. If the selection also uses `polygon_containing`, the importer picks the part first. Geographic assignments can reference several imported polygons directly. Map building combines those areas when checking component membership.

## Code and tests

[`features.py`](features.py) contains the typed constructor and vector reader. The shared source workflow verifies inputs and saves the results in one transaction.

[`test_features.py`](test_features.py) checks selection, archive handling, coordinate conversion, and malformed geometry. The [shared storage tests](../shared/test_storage.py) check transactional saves and preserved relationships in disposable PostgreSQL.

Run from the repository root after the [database test setup](../../../../database/README.md#tests).

```bash
python .github/scripts/run_tests.py --suite source_imports
```
