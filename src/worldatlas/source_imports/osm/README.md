# OpenStreetMap imports

[`features.py`](features.py) contains `selected_osm_features` and its reader for selected nodes, closed ways, and relation polygons. It reads each archived object graph once through osmium's Python API and saves the result through the shared import workflow.

Use the common command below with a `selected_osm_features` construction. Each selection identifies an output `feature_id`, provider `source_feature_id`, `object_type` (`node`, `way` or `relation`) and `object_version`. Optional `expected_tags` verify provider tags. The constructor joins member ways at shared node IDs in stable way-ID order.

Relations preserve inner rings by default. An explicit `holes: outer_envelope` selects the outer envelope, while `ignored_member_roles` identifies non-geometric members such as label nodes. Optional `ring_anchors` select particular rings by tagged node ID/version and member way; `parent_relation` checks a selected membership. These interpretations live in the construction record. The same implementation handles administrative, reef and archipelago sources.

`test_features.py` covers joining, holes, anchors, membership, source identity and invalid geometry.

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

Run the [common import command](../README.md) with the construction ID, R2 endpoint, and work directory. [`ways.py`](ways.py) contains `osm_way_chain` and its assembler. The typed source list generates the database links to each way file. Checked local files are reused. The import result includes the saved line's SHA-256.

Use `evidence_source_ids` to cite additional sources that explain the selection.

## Tests

[`test_ways.py`](test_ways.py) checks chain assembly, direction, and invalid geometry. [`test_way_import.py`](test_way_import.py) checks the Neon/R2 workflow and database transactions.

Run the tests from the repository root.

```bash
python .github/scripts/run_tests.py --suite source_imports
```

The runner creates a disposable database and includes the database write tests. Those tests cover complete builds, repeat runs, source updates, preservation of construction and geographic relationships, unrelated records, and failed-write rollbacks.

Provider-defined geographic `group` and `collection` relations can produce one island-group feature. The reader includes direct polygon ways and nested polygon relations, preserves child holes, and unions overlapping members. Construction settings explicitly identify ignored metadata roles. Missing members and cycles fail; a parent `/full` response alone may omit nested geometry, so the archived input must contain the complete recursive graph.
