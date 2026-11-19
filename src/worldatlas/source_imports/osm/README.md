# OpenStreetMap imports

Both methods use the [common import command](../README.md#run-one-construction) with the construction ID, R2 endpoint, and work directory.

## Points and polygons

[`features.py`](features.py) contains `selected_osm_features` and its reader for selected nodes, closed ways, and relation polygons. It reads each archived object graph once through osmium's Python API and saves the result through the shared import workflow.

Each selection identifies an output `feature_id`, provider `source_feature_id`, `object_type` (`node`, `way` or `relation`) and `object_version`. Optional `expected_tags` verify provider tags. The constructor joins member ways at shared node IDs in stable way-ID order.

Polygon imports preserve holes and return a `MultiPolygon`. Use `ignored_member_roles` to identify non-geometric members such as label nodes. The same implementation handles administrative, reef and archipelago sources.

Provider-defined geographic `group` and `collection` relations can produce one island-group feature. The reader includes direct polygon ways and nested polygon relations, preserves child holes, and unions overlapping members. Construction settings explicitly identify ignored metadata roles. Missing members and cycles fail. A parent `/full` response alone may omit nested geometry, so the archived input must contain the complete recursive graph.

## Boundary lines

Use `osm_way_chain` to join individual archived `/api/0.6/way/{id}/full.json` responses. Each file contains one OSM way and its nodes and has its own record in `atlas.source_assets`. The construction record supplies the selection and starting node.

```json
{
  "way_source_ids": ["first-archived-way", "second-archived-way"],
  "start_node_id": 100,
  "feature_id": "boundary-id",
  "basis": "Join the selected OpenStreetMap ways into a boundary."
}
```

The order of `way_source_ids` has no effect. [`ways.py`](ways.py) starts at the supplied endpoint, follows shared node IDs, and reverses individual ways as needed. It preserves the coordinates and requires one open, continuous, unbranched line without self-intersections.

The typed source list generates the database links to each way file. Checked local files are reused. The import result reports the saved feature ID and vertex count.

Use `evidence_source_ids` to cite additional sources that explain the selection.

## Tests

[`test_features.py`](test_features.py) covers joining, holes, nested groups, source identity, and invalid geometry. [`test_ways.py`](test_ways.py) checks chain assembly, direction, and invalid geometry. [`test_way_import.py`](test_way_import.py) checks the Neon/R2 workflow and database transactions.

Run the tests from the repository root.

```bash
python .github/scripts/run_tests.py --suite source_imports
```

The runner creates a disposable database and includes the database write tests. Those tests cover complete builds, repeat runs, source updates, preservation of construction and geographic relationships, unrelated records, and failed-write rollbacks.
