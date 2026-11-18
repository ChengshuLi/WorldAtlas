# IHO S-130 areas

`areas.py` reads complete geographic surfaces from the cataloged S-130 archive. The `s130_areas` constructor in [`../features/build_features.py`](../features/build_features.py) saves them in `atlas.source_features`. Map building consumes that stored geometry.

Each construction supplies `source_id`, `basis`, `gml_member`, `gml_sha256` and `selections`. A selection identifies the output `feature_id` and the provider MRN in `source_feature_id`. Complete linked surfaces sharing an MRN are retained, including holes, dateline crossings and polar caps. Imported coordinates keep the provider's representation.

Run through the common entry point:

```bash
worldatlas-import --recipe CONSTRUCTION_ID \
  --r2-endpoint R2_ENDPOINT --work-dir /absolute/path/to/worldatlas-work/inputs
```

The catalog supplies exact source bytes and their size/checksum. Downloads are cached and verified; successful geometry and construction links save together. `test_areas.py` checks collection completeness, holes, source identity, polar coverage and longitude wrapping.

Ocean ownership and named-basin shore assignment are separate choices in `geographic_rules`; the importer uses the same area reader for both.
