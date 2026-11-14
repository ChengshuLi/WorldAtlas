# Selected geographic features

Import selected source geometry into `atlas.source_features`. Each row contains
`feature_id`, `source_id`, `source_feature_id`, `geometry` and `construction_id`;
all five are required. Geometry always uses WGS84 `[longitude, latitude]` in
degrees. Map building reads these polygons and points instead of reopening their
raw archives.

Raw files are pinned by their cataloged size and checksum. Vector and table
imports select explicit provider IDs and reject missing or ambiguous matches.
Provider attributes remain in the raw source; these methods do not maintain
copied attribute expectations in Neon.
Map building checks spatial relationships against the current grid. Database
constraints reject malformed coordinate structures; imports also reject invalid
shapes, such as self-intersecting polygons.

[`vector.py`](vector.py) reads selected provider IDs with GDAL and converts
coordinates to WGS84 longitude/latitude.
[`geometry.py`](geometry.py) validates and saves the geometry.
[`build_features.py`](build_features.py) declares one typed entry point per feature
method and shares catalog lookup, the verified R2 cache and transactional storage.
Its signatures and nested types define the fields accepted by
[shared Python and database validation](../README.md#document-validation).
Existing relationships survive repeat imports; a failed import
leaves all selected records unchanged.

Use the common command:

```bash
worldatlas-import --recipe CONSTRUCTION_ID \
  --r2-endpoint R2_ENDPOINT --work-dir /absolute/path/to/worldatlas-work/inputs
```

A `selected_vector_features` construction contains `source_id`,
`basis`, `id_field` and `selections`. Each selection supplies `feature_id` and
`source_feature_id`. Imports verify the cataloged raw bytes and selected IDs;
there is no separate expected-geometry checksum setting. Floating-point negative
zero becomes positive zero for storage; other coordinate values are unchanged.
Select `member` for an archived dataset and `layer` when a file contains several
layers. An explicit `coordinate_operation` is
available when a source needs a particular documented CRS conversion.
WGS84 GeoJSON coordinates retain their original numeric values. Distinct existing
output IDs may select the same provider feature when backfilling current records;
provider IDs must still identify one source feature.
For a provider area stored as several records with the same identifier, set
`collection: true` on its selection. All matching polygons are included; an
optional `expected_feature_count` checks collection completeness.

Vector inputs may use other coordinate systems. The importer reads the source
CRS and converts its coordinates to WGS84 longitude/latitude before saving.

The `s130_areas` method uses the same storage workflow and
[`iho/areas.py`](../iho/areas.py) for complete S-130 surfaces and collections.
`selected_osm_features` uses [`osm/features.py`](../osm/features.py) to assemble
selected OSM points and polygons through that same storage workflow.

`selected_table_points` uses [`points.py`](points.py) for CSV, TSV and other
delimited point tables. Its construction supplies `id_field`, `longitude_field`,
`latitude_field`, plus the same selections. Set `delimiter` for a non-comma separator,
`columns` for a headerless table, and `member` for a table inside a ZIP archive.
A GeoNames construction names its published columns and selected IDs; it uses
the same table reader as other delimited point sources.

To import a selected set of candidate points, use `where` with exact property
matches, `feature_id_prefix` for the output IDs and optional `bounds_lon_lat`.
Any explicit `selections` are retained as well, including outside those bounds.
Map building then resolves these imported points against the current components;
it does not reopen the provider table.

`test_vector.py` checks selection, identity, archives, conversion and malformed
geometry. `test_storage.py` checks transactional saves, repeat imports, preserved
relationships and rollback using disposable PostgreSQL.
