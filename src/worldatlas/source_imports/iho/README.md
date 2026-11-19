# IHO S-130 areas

[`areas.py`](areas.py) contains `s130_areas` and its GML reader. It imports complete geographic surfaces from the cataloged S-130 archive into `atlas.source_features`. Map building consumes that stored geometry.

Each construction supplies `source_id`, `basis`, `gml_member`, `gml_sha256` and `selections`. A selection identifies the output `feature_id` and the provider MRN in `source_feature_id`. Complete linked surfaces sharing an MRN are retained, including holes, dateline crossings and polar caps. Imported coordinates keep the provider's representation.

Run through the common entry point:

```bash
worldatlas-import --recipe CONSTRUCTION_ID \
  --r2-endpoint R2_ENDPOINT --work-dir /absolute/path/to/worldatlas-work/inputs
```

Shared acquisition checks the archive's size and checksum. The S-130 reader verifies the selected GML member separately. [`test_areas.py`](test_areas.py) checks the command, member verification, collection completeness, holes, polar coverage, and longitude wrapping.

Ocean ownership and named-basin shore assignment are separate choices in `geographic_rules`; the importer uses the same area reader for both.
