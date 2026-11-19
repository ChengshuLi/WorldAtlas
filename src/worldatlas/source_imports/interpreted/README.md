# Interpreted geometry

[`geometry.py`](geometry.py) contains `interpreted_geometry`. It saves the reviewed GeoJSON `Point` and `Polygon` geometries in the recipe. A point can label an area. A polygon can limit where a geographic rule applies.

Store the explanation in the construction row's `basis` column. In `arguments`, `source_ids` lists one or more distinct evidence IDs and `selections` pairs each output `feature_id` with its `geometry`. Supply at least one selection. Coordinates are WGS84 longitude first, latitude second. The importer checks evidence IDs against the Neon catalog. It reads the coordinates from the recipe and needs no R2 download.

## Example

The `ural-delta-division-context` recipe saves a polygon that includes the Ural River mouth in the Europe–Asia division. Its `arguments` are shown below.

```json
{
  "source_ids": ["osm-ural-river-relation-214415-full"],
  "selections": [
    {
      "feature_id": "ural-delta-division-scope",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [51.3, 46.8307054],
          [52.2, 46.8307054],
          [52.2, 47.24],
          [51.3, 47.24],
          [51.3, 46.8307054]
        ]]
      }
    }
  ]
}
```

With the [project environment and Neon connection](../README.md#run-one-construction) set up, run the recipe.

```bash
worldatlas-import --recipe ural-delta-division-context
```
