# Greenland island evidence packet (#527)

This packet audits both exact current v5 reference location IDs in issue #527: Qeqertarsuaq (Disko) and Milne Land. `assessment.json` accounts for every assigned island, all derived exterior/interior rings, mapped settlement candidates, current administrative-relation containment, complete adjacent-tier chains, source lineage, licenses, dates, hashes, and unresolved evidence. Both IDs are present in current `data/world-index.json` through the merged source-restoration additions; their regional semantic approval is still open.

Original PBF, GeoNames, GSHHG and prepared island source bytes remain in the earlier #41/#503 directories. This packet references their existing paths and hashes rather than copying or rewriting source evidence. It does not approve the full Greenland area or #457 region packet, create new locations, change shared membership or geometry, or transfer historical attributes.

Reproduce source/hash, settlement and administrative-containment checks from repository root:

```sh
python3 data/regional-review/regional-supplement-c75ef29bf58f095c/verify.py
```

The check reads existing source files and uses GDAL/OGR CLI tools (`ogr2ogr`, `ogrinfo`) with temporary files under the system temporary directory. It does not write into shared geography or the upstream evidence packages. Its containment test is against the pinned current OSM administrative relation, not an official cadastral boundary; see the source limitations in `assessment.json`.
