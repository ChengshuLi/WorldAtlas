# OpenStreetMap imports

Import points and polygons from archived OpenStreetMap objects, or join archived ways into one boundary line.

## Use

Both methods use the [common import command](../README.md#run-one-construction) with the construction ID, R2 endpoint, and work directory.

## How it works

### Points and polygons

[`features.py`](features.py) contains `selected_osm_features`. It returns a `Point` for an OSM node and a `MultiPolygon` for a closed way or polygon relation. Use [`osm_way_chain`](#boundary-lines) for a `LineString`.

Each selection identifies an output `feature_id`, provider `source_feature_id`, and `object_type` (`node`, `way` or `relation`). Select each object at most once per recipe. The raw-file checksum pins the extract. Optional `expected_tags` verify provider tags.

Select a closed way or a relation tagged `type=multipolygon` or `type=boundary`. The archived extract must contain the ways and nodes that form the outline. Osmium assembles rings, uses their geometry to identify holes, and skips relation label nodes. An inconsistent `inner` role can therefore yield a separate polygon when its ring lies outside the other rings.

### Boundary lines

Use `osm_way_chain` to join individual archived `/api/0.6/way/{id}/full.json` responses. Each file contains one OSM way and its nodes and has its own record in `atlas.source_assets`. Store the explanation in the construction row's `basis` column and list the selected ways in `arguments`.

```json
{
  "way_source_ids": ["first-archived-way", "second-archived-way"],
  "feature_id": "boundary-id"
}
```

The order of `way_source_ids` has no effect. [`ways.py`](ways.py) checks that joins identify the same OSM nodes, then uses Shapely to merge the ways into one open, continuous, unbranched line. The output starts at the endpoint with the lower OSM node ID. Self-intersections fail validation.

The typed source list generates the database links to each way file. Checked local files are reused. The import result reports the saved feature ID and vertex count.

Use `evidence_source_ids` to cite additional sources that explain the selection.

## Code and tests

[`test_features.py`](test_features.py) covers selected points, closed ways, multipolygons with holes, source identity, invalid geometry, and saving a selected relation with its source link. [`test_ways.py`](test_ways.py) checks chain assembly, direction, and invalid geometry. [`test_way_import.py`](test_way_import.py) checks cache reuse, recipe edits, source links, and preservation of existing geometry on failed imports.

Run the tests from the repository root.

```bash
python .github/scripts/run_tests.py --suite source_imports
```

The runner creates a disposable PostgreSQL database. The OSM import tests use small fixture files served by a fake R2 client, so they require no network downloads.
