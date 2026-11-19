# Selected geographic features

Import selected source geometry into `atlas.source_features`. Each row has three required fields, `id`, `geometry`, and `construction_id`. Geometry uses WGS84 `[longitude, latitude]` in degrees. Map building reads the stored geometry to check spatial relationships against the current grid.

Raw files are pinned by their cataloged size and checksum. Neon checks the [recipe's argument names and types](../README.md#argument-validation) and the structure of stored coordinates. The importer checks that selected features exist and rejects invalid geometry, such as self-intersecting polygons.

[`build_features.py`](build_features.py) declares the typed methods for vector, OSM, and S-130 imports and shares their catalog lookup and verified R2 cache. [`geometry.py`](geometry.py) validates and saves each method's results in one transaction. Repeat imports preserve existing relationships, and failed imports leave selected records intact.

Run any of these three methods with the common import command.

```bash
worldatlas-import --recipe CONSTRUCTION_ID \
  --r2-endpoint R2_ENDPOINT --work-dir /absolute/path/to/worldatlas-work/inputs
```

## Vector selections

`selected_vector_features` uses [`vector.py`](vector.py) to read provider records with GDAL. The recipe contains `source_id`, `basis`, `id_field`, and `selections`. Each selection identifies the provider record with `source_feature_id` and names the saved record with `feature_id`. Different output IDs can select the same provider feature. Provider attributes stay in the raw file.

- Set `member` to select an archived dataset and `layer` to select a layer in a file that contains several.
- Vector imports convert the source CRS to the stored coordinate system. Use `coordinate_operation` when the source needs a specific documented transformation. WGS84 GeoJSON retains its numeric coordinate values when no explicit transformation or collection operation is requested. Storage normalizes `-0.0` to `0.0`.
- A provider ID must select exactly one record by default. Set `collection: true` to combine all records that share the ID. `expected_feature_count` checks how many records matched.
- Set `polygon_containing: [longitude, latitude]` to select one part using a point in the stored coordinate system. The point must be strictly inside exactly one polygon. Points on boundaries or in holes fail the selection.

Vector and OSM polygons retain holes by default (`holes: "preserve"`). Set `holes: "outer_envelope"` to use the exterior rings and fill holes. For vector selections, this happens after `polygon_containing` picks a part. Geographic assignments can reference several imported polygons directly. Map building combines those areas when checking component membership.

## Other feature methods

- `selected_osm_features` uses [`osm/features.py`](../osm/features.py) to assemble selected OSM points and polygons. A selection can use `expected_tags` to check specific attributes of the archived object.
- `s130_areas` uses [`iho/areas.py`](../iho/areas.py) to import complete S-130 surfaces and collections.
- `interpreted_geometry` uses [`interpreted.py`](interpreted.py) to save points and polygons supplied in the recipe, such as region labels and computation scopes. It checks the cited source IDs in Neon. Run it with `worldatlas-import --recipe CONSTRUCTION_ID`.

## Tests

[`test_vector.py`](test_vector.py) checks selection, archives, coordinate conversion, and malformed geometry. [`test_storage.py`](test_storage.py) checks transactional saves, repeat imports, preserved relationships, and rollback using disposable PostgreSQL.
