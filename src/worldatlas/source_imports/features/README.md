# Selected geographic features

Import selected source geometry into `atlas.decision_features`. Map building
reads these polygons and points instead of reopening their raw archives.

[`vector.py`](vector.py) reads selected provider IDs with GDAL, checks optional
identity properties and converts coordinates to WGS84 longitude/latitude.
[`geometry.py`](geometry.py) validates, checksums and saves the geometry.
[`build_features.py`](build_features.py) declares one typed entry point per feature
method and shares catalog lookup, the verified R2 cache and transactional storage.
Its signatures and nested types define the fields accepted by
[shared Python and database validation](../README.md#document-validation).
Unrelated evidence and relationships survive repeat imports; a failed import
leaves all selected records unchanged.

Use the common command:

```bash
worldatlas-import \
  --recipe CONSTRUCTION_ID VERSION --revision DECISION_REVISION \
  --r2-endpoint R2_ENDPOINT --work-dir /absolute/path/to/worldatlas-work/inputs
```

A `selected_vector_features` construction contains `source_id`, `source_version`,
`basis`, `id_field` and `selections`. Each selection supplies `feature_id` and
`source_feature_id`; it may check `expected_properties` or an
`expected_geometry_sha256`. Checksums use the stored coordinate representation:
floating-point negative zero becomes positive zero; other values are unchanged.
Select `member` for an archived dataset and `layer` when a file contains several
layers. An explicit `coordinate_operation` is
available when a source needs a particular documented CRS conversion.
WGS84 GeoJSON coordinates retain their original numeric values. Distinct existing
output IDs may select the same provider feature when backfilling current records;
provider IDs must still identify one source feature.
For a provider area stored as several records with the same identifier, set
`collection: true` on its selection. All matching polygons are included; an
optional `expected_feature_count` checks collection completeness.

Outputs normally use `OGC:CRS84`. Set `coordinate_reference` to retain another
declared CRS when grid queries need the original projected polygon edges.
The saved geometry declares that reference explicitly.

The `s130_areas` method uses the same storage workflow and
[`iho/areas.py`](../iho/areas.py) for complete S-130 surfaces and collections.
`selected_osm_features` uses [`osm/features.py`](../osm/features.py) to assemble
selected OSM points and polygons through that same storage workflow.

`selected_table_points` uses [`points.py`](points.py) for CSV, TSV and other
delimited point tables. Its construction supplies `id_field`, `longitude_field`,
`latitude_field` and `coordinate_reference: OGC:CRS84`, plus the same selections
and optional identity/checksum checks. Set `delimiter` for a non-comma separator,
`columns` for a headerless table, and `member` for a table inside a ZIP archive.
For example, a GeoNames construction names its published columns and checks each
selected record's name, feature type and country; those choices are data, not
separate island/airport implementations.

To import a selected set of candidate points, use `where` with exact property
matches, `feature_id_prefix` for the output IDs and optional `bounds_lon_lat`.
Any explicit `selections` are retained as well, including outside those bounds.
Map building then resolves these imported points against the current components;
it does not reopen the provider table.

`test_vector.py` checks selection, identity, archives, conversion and malformed
geometry. `test_storage.py` checks transactional saves, repeat imports, preserved
relationships, schema upgrades and rollback using disposable PostgreSQL.
