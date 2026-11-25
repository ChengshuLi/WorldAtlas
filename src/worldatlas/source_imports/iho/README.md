# IHO S-130 areas

[`areas.py`](areas.py) reads sea areas from the XML file (GML) inside the cataloged S-130 ZIP and saves their polygons in `atlas.source_features`. Map building uses that geometry to assign ocean and named-basin water.

## Use

Run the [common import command](../README.md#run-one-construction) with `s130-selected-basins-construction` for named basins or `s130-ocean-features-construction` for ocean areas.

```bash
worldatlas-import --recipe CONSTRUCTION_ID \
  --work-dir /absolute/path/to/worldatlas-work/inputs
```

## How it works

Each construction supplies `source_id`, `gml_member` and `selections` as arguments. Each selection pairs an output `feature_id` with the IHO area ID, called a Maritime Resource Name (MRN), in `source_feature_id`. The reader assembles the complete area from its linked surfaces and preserves holes and polar caps. It converts the source's latitude-first coordinates to longitude-first GeoJSON and splits polygons at the antimeridian.

For example, the Arctic Ocean selection uses `urn:mrn:iho:00AA:01810:173944174678`. In the archived XML, the record for the whole area (`M.0012`) links to the records for its two polygon pieces (`M.0119` and `M.0120`). All three records share the same IHO area ID. Only the whole area is selectable by that ID.

Shared acquisition checks the archive's size and checksum, which also fixes the bytes of each member. The S-130 reader requires the exact GML member name to appear once.

## Code and tests

[`test_areas.py`](test_areas.py) checks the import command, member selection, XML IDs and links, holes, polar coverage, and both directions of dateline crossing. The command test uses a disposable PostgreSQL database and a small local ZIP in place of an R2 download.

```bash
python .github/scripts/run_tests.py --suite source_imports
```
