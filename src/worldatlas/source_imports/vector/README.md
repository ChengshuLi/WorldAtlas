# Selected vector features

Import selected source geometry into `atlas.source_features`. Each row has three required fields, `id`, `geometry`, and `construction_id`. Geometry uses WGS84 `[longitude, latitude]` in degrees. Map building reads the stored geometry to check spatial relationships against the current grid.

Raw files are pinned by their cataloged size and checksum. Neon checks the [recipe's argument names and types](../README.md#argument-validation) and the structure of stored coordinates. The importer checks that selected features exist and rejects invalid geometry, such as self-intersecting polygons.

[`features.py`](features.py) contains the typed constructor and vector reader. The shared source workflow verifies inputs and saves the results in one transaction.

Run the `selected_vector_features` method with the common import command.

```bash
worldatlas-import --recipe CONSTRUCTION_ID \
  --r2-endpoint R2_ENDPOINT --work-dir /absolute/path/to/worldatlas-work/inputs
```

## Vector selections

The recipe contains `source_id`, `basis`, `id_field`, and `selections`. Each selection identifies the provider record with `source_feature_id` and names the saved record with `feature_id`. Different output IDs can select the same provider feature. Provider attributes stay in the raw file.

- Set `member` to select an archived dataset and `layer` to select a layer in a file that contains several.
- Vector imports convert the source CRS to the stored coordinate system. Use `coordinate_operation` when the source needs a specific documented transformation. WGS84 GeoJSON retains its numeric coordinate values when no explicit transformation or collection operation is requested. Storage normalizes `-0.0` to `0.0`.
- A provider ID must select exactly one record by default. Set `collection: true` to combine all records that share the ID. `expected_feature_count` checks how many records matched.
- Set `polygon_containing: [longitude, latitude]` to select one part using a point in the stored coordinate system. The point must be strictly inside exactly one polygon. Points on boundaries or in holes fail the selection.

Polygons retain holes by default (`holes: "preserve"`). Set `holes: "outer_envelope"` to use the exterior rings and fill holes after `polygon_containing` picks a part. Geographic assignments can reference several imported polygons directly. Map building combines those areas when checking component membership.

## Tests

[`test_features.py`](test_features.py) checks selection, archive handling, coordinate conversion, and malformed geometry. The [shared storage tests](../shared/test_storage.py) check transactional saves and preserved relationships in disposable PostgreSQL.
