# Selected geographic features

Import selected source geometry into `atlas.decision_features`. Map building
reads these polygons and points instead of reopening their raw archives.

[`vector.py`](vector.py) reads selected provider IDs with GDAL, checks optional
identity properties and converts coordinates to WGS84 longitude/latitude.
[`geometry.py`](geometry.py) validates, checksums and saves the geometry.
[`build_features.py`](build_features.py) resolves the construction and raw source
in Neon, uses the verified R2 cache and saves the complete import in one transaction.
Unrelated evidence and relationships survive repeat imports; a failed import
leaves all selected records unchanged.

Use the common command:

```bash
PYTHONPATH=scripts/source-imports python3 -m run_import \
  --recipe CONSTRUCTION_ID VERSION --revision DECISION_REVISION \
  --r2-endpoint R2_ENDPOINT --work-dir /absolute/path/to/worldatlas-work/inputs
```

A `selected_vector_features` construction contains `source_id`, `source_version`,
`basis`, `id_field` and `selections`. Each selection supplies `feature_id` and
`source_feature_id`; it may check `expected_properties` or an
`expected_geometry_sha256`. Select `member` for an archived dataset and `layer`
when a file contains several layers. An explicit `coordinate_operation` is
available when a source needs a particular documented CRS conversion.

The `s130_areas` method uses the same storage workflow and
[`iho/areas.py`](../iho/areas.py) for complete S-130 surfaces and collections.

`selected_table_points` uses [`points.py`](points.py) for CSV, TSV and other
delimited point tables. Its construction supplies `id_field`, `longitude_field`,
`latitude_field` and `coordinate_reference: OGC:CRS84`, plus the same selections
and optional identity/checksum checks. Set `delimiter` for a non-comma separator,
`columns` for a headerless table, and `member` for a table inside a ZIP archive.
For example, a GeoNames construction names its published columns and checks each
selected record's name, feature type and country; those choices are data, not
separate island/airport implementations.

`test_vector.py` checks selection, identity, archives, conversion and malformed
geometry. `test_storage.py` checks transactional saves, repeat imports, preserved
relationships, schema upgrades and rollback using disposable PostgreSQL.
