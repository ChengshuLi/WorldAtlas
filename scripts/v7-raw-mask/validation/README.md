# Physical-mask difference diagnostic

This optional validation checks changed physical land/water cell centers against the new OSM land polygons and tests whether uniform integer- or sub-cell shifts reduce differences in a selected region. It reads a derived historical **land/water** mask, not historical continent labels. It is not a pipeline input and does not change the candidate map.

Copy `config.example.json`, replace the sample study box, each `/path/to/...`, and each `REPLACE` SHA-256 pin with the values for the exact inputs being studied. Pin the complete shapefile including `.shp`, `.shx`, `.dbf`, `.prj` and any present `.cpg`, `.qix`, `.sbn` or `.sbx` sidecars. The mismatch JSONL has `row`, `start`, `end`, `reference`, and `candidate`; spans are half-open and class codes are 1 for water and 17 for land. Every listed cell is checked against both pinned masks. Run:

```
/usr/bin/python3 cell_diagnostics.py /path/to/config.json > /path/to/report.json
/usr/bin/python3 -m unittest -v test_cell_diagnostics
```

One analysis of the pinned files, using the earlier narrower provenance/class water filter, found all 674 changed cell centers consistent with the new polygons: 305 changed from water to land and lay strictly inside, while 369 changed from land to water and lay outside. For the Hudson Strait study window, the unshifted alignment had 593 differences across 90,496 cells and was best among the tested integer, quarter-cell and half-cell shifts; the next-best sub-cell offset had 622 differences. The new-polygon raster at zero offset matched the new mask within that window.

These checks make a simple uniform offset less likely; they do **not** prove why the historical and current masks differ. The historical mask is a derived raster, and the historical OSM vector snapshot was unavailable. Source edits, vector versions and historical processing remain confounded. The user accepted the 674-cell difference for that comparison. The newer subtype-only water policy has not been run globally or compared to that historical mask. No result from this diagnostic is a geographic approval or a substitute for end-to-end validation.

## Water-selection comparison

`compare_water_selection.py MANIFEST MANIFEST_SHA256 --workers 4` scans the hash-pinned Overture water shards and counts how many records the old source/class filter and current subtype-only filter select, including additions and removals. It verifies each source hash and checks size and modification time again after scanning. This compares feature predicates only; it does not inspect geometry validity, rasterize, or compare resulting cells. Use the exact raw-source manifest and appropriate worker and I/O limits.

For the pinned 32-shard `2026-10-21.0` manifest with SHA-256 `96f5abd11155fb73763a96efb200c0f99fbbabd4bd10fa1005d7837b3eb3938c`, a hash-verified scan counted 66,814,038 records. Both predicates selected 66,494,085 records, with zero additions, zero removals and zero missing subtypes. This establishes identical feature selection for those bytes, not a fresh global rasterization or cell-for-cell comparison.
