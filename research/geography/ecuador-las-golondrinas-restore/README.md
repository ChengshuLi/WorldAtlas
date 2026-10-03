# Las Golondrinas (EC9001) source restoration and review

Issue #575 assigns one location: `gb:ECU:ADM2:8360857B1829680752404`. This packet restores dated administrative evidence, records the lawful path to the full geometry source, compares that source to the pinned Atlas geometry, and identifies what remains unresolved. It proposes no hierarchy or boundary edit and does not infer physical geography from political ownership.

## Sourced administrative disposition

Ecuador's Organic Law published in Registro Oficial, Suplemento 999 (2017-05-08), Article 1 incorporates the zone known as Las Golondrinas into Imbabura Province and Cotacachi canton. Article 2 fixes a segment of the provincial boundary using named hydrography and coordinates. The law is effective upon publication. Cotacachi's ordinance published in Registro Oficial, Suplemento 406 (2019-01-15), Article 1 incorporates the area into García Moreno parish. The Consejo de la Judicatura resolution published in Registro Oficial, Tercer Suplemento 285 (2026-05-15) continues to refer to Recinto Las Golondrinas in Cotacachi, Imbabura, as part of a judicial-venue change. These are dated administrative descriptions, not proof of complete physical coverage.

This directly conflicts with the INEC/OCHA 2023 COD-AB table: its EC9001 row calls the ADM1 “Zona No Delimitada” (EC90). The 2024 INEC/OCHA gazetteer has no EC9001/name match. The tabular absence does not imply disappearance of land. Keep the existing stable Atlas subject and Imbabura parent pending engineering review; mark the source-role/tier assertion (“canton”) as requiring correction against the statute/ordinance. Do not treat the schema's Ecuador `reference_owner` as geographic evidence.

The 2026-04-13 Asamblea Nacional article only reports qualification of a draft that would amend the 2017 law. The legislative state after that dated report was not established in this packet. No conclusion is made that the law changed after May 2026.

## Geometry and whole-scope audit

The exact subject was uniquely found in `data/geography/part-7.json`; its complete parent chain is recorded in `geometry-reconciliation.json`, through Imbabura, Ecuador, Western South America, Andean South America and South America. The source feature has valid MultiPolygon geometry, 3,098 coordinates, two components and no holes. A 0.136 m² component is a sub-pixel source sliver, not evidence of an island. The Atlas feature at pinned baseline `cff18b92cd89210df844f118a6e0b5c2afc3fd75` has valid Polygon geometry with 36 coordinates and no holes.

In EPSG:6933 the source area is 127.918 km² and current Atlas area is 129.614 km². Intersection is 122.471 km²; symmetric difference is 12.589 km² (9.841% of source). Source outside current is 4.258% of source; current outside source is 5.510% of current. This compares vintages, not correctness, and is not a proposed contour. Independent WGS84 ellipsoidal area checks and an axis-order negative control are in the reproducible output.

The current indexed geometry contacts five ADM2 locations: Cotacachi (17.402 km), Quininde (40.832 km), Eloy Alfaro (0.164 km), Puerto Quito (13.515 km), Pedro Vicente Maldonado (17.432 km). No areal overlaps were measured. These are map diagnostics only, not legal/source consistency findings. This location and its listed neighbors remain within the Western South America baseline; no inter-region boundary correction was discovered.

Parent packet evidence includes a 2017 GSHHG level-1 centroid screen with zero hits. Its limitations make it inadequate to certify coastlines, small islands, water, complete land coverage or named settlement coverage. Imbabura government articles identify local services and Santa Ana school, but no complete settlement inventory was established. No authoritative, current georeferenced IGM/CONALI polygon for this exact zone was identified or retained. Physical land, islands, full settlements, water and source-to-current neighbor consistency therefore remain explicit unresolved findings.

## Bounded follow-up

Obtain a lawful current IGM/CONALI georeferenced boundary or document its unavailability; crosswalk it against the 2017 legal coordinates and hydrography and the retained 2019 feature. Obtain an authoritative current settlement roster and named physical-land/island coverage. Recheck the post-May-2026 legislative status. Compare the resulting source edges with the five named contacts above and coordinate any cross-region inconsistency with affected owners before proposing correction. Until then, do not change geometry or parent membership.

## Sources, licensing and restoration

Canonical source URLs, dates, byte counts, hashes, licenses and restoration instructions are in `sources.json`. Official Registro Oficial PDF bytes are not committed because the retrieved copies carry no explicit reuse license. Restore by downloading the canonical URLs and verifying the recorded byte count and SHA-256. The 2019 geoBoundaries feature and INEC/OCHA tables are already retained lawfully in the parent #496 packet; this packet records their paths and hashes rather than duplicating or modifying them. Parent source material is preserved unchanged.

## Reproduction

Run from the repository root with GDAL/OGR and pyproj available:

```sh
/usr/bin/python3 research/geography/ecuador-las-golondrinas-restore/reproduce.py --check
```

`geometry-reconciliation.json` is deterministically generated by the same script with `--write`. `scope.json` pins the baseline, exact assigned subject, owned path, and every geography part/index/hierarchy/membership and cited parent source file hash. The script verifies these inputs before calculation, confirms all indexed part files, asserts one exact subject occurrence and its complete parent chain, checks retained source hashes and administrative table records, validates geometry, performs projection/axis controls, and calculates all source/current metrics and current contacts. It refuses a changed baseline rather than silently measuring new data.
