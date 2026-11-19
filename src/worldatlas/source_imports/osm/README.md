# OpenStreetMap imports

Both methods use the [common import command](../README.md#run-one-construction) with the construction ID, R2 endpoint, and work directory.

## Points and polygons

[`features.py`](features.py) contains `selected_osm_features`. It uses Osmium's geometry API to read selected nodes and closed outlines and assemble polygon relations. The resulting geometries go through the shared import workflow.

Each selection identifies an output `feature_id`, provider `source_feature_id`, and `object_type` (`node`, `way` or `relation`). The raw-file checksum pins the extract. Optional `expected_tags` verify provider tags.

Polygon imports preserve holes and return a `MultiPolygon`. Select a closed way or a relation tagged `type=multipolygon` or `type=boundary`. The archived extract must contain the ways and nodes that form the outline. Osmium assembles outer and inner rings and skips relation label nodes.

## Boundary lines

Use `osm_way_chain` to join individual archived `/api/0.6/way/{id}/full.json` responses. Each file contains one OSM way and its nodes and has its own record in `atlas.source_assets`. Store the explanation in the construction row's `basis` column and the selection and starting node in `arguments`.

```json
{
  "way_source_ids": ["first-archived-way", "second-archived-way"],
  "start_node_id": 100,
  "feature_id": "boundary-id"
}
```

The order of `way_source_ids` has no effect. [`ways.py`](ways.py) starts at the supplied endpoint, follows shared node IDs, and reverses individual ways as needed. It preserves the coordinates and requires one open, continuous, unbranched line without self-intersections.

The typed source list generates the database links to each way file. Checked local files are reused. The import result reports the saved feature ID and vertex count.

Use `evidence_source_ids` to cite additional sources that explain the selection.

## Tests

[`test_features.py`](test_features.py) covers selected points, closed ways, multipolygons with holes, source identity, and invalid geometry. [`test_ways.py`](test_ways.py) checks chain assembly, direction, and invalid geometry. [`test_way_import.py`](test_way_import.py) checks the Neon/R2 workflow and database transactions.

Run the tests from the repository root.

```bash
python .github/scripts/run_tests.py --suite source_imports
```

The runner creates a disposable database and includes the database write tests. Those tests cover complete builds, repeat runs, source updates, preservation of construction and geographic relationships, unrelated records, and failed-write rollbacks.
