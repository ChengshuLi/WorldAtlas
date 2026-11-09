# V8 regional island decisions

The editable `v8-regional-islands` revision in Neon contains the selected
island affiliations and the `lydekker-whole-island-regional-v1` rule set.
The [V8 pipeline](../../../../v7-pipeline/README.md) pins the revision's
decision export and rule, plus the source-derived Lydekker geometry.

The rule states the geographic extents, named witnesses and OSM feature
IDs. The regional stage reads GeoNames records and the pinned OSM
shapefile, checks each selected geometry hash, and intersects the source
features with the physical components from the current run. It requires
whole-component coverage and verifies that the named witnesses fall
inside the selected features. The report records the source IDs, the
witnesses and the resolved component IDs for that run.

The named group extents use NGA Sailing Directions. The Indonesian
national gazetteer and GeoNames provide island and reef witnesses, and
the OSM archive supplies the selected polygon geometries. The two
regional extent rules and four explicit source-feature groups are
editable in the same Neon rule set.
