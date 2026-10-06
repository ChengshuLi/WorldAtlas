# Yugoslavia parent-study reproduction erratum (#1189)

## Scope and method

This packet audits the exact 17 Atlas parent IDs and 278 native children declared in issue #1189 (295 subjects). It does not change Atlas hierarchy, polygons, parent assignments, releases, or the original #1018 packet. The issue snapshot captures the accepted contract and complete immutable pin set. `reproduce_guarded.py` verifies those whole-file Git object pins before it reads issue inputs, checks exact roster cardinality, source feature IDs and names, then runs the two original generators twice with only their output destinations redirected into fresh exclusive directories.

Both runs reproduced every historical product byte-for-byte:

| Product | Bytes | SHA-256 |
| --- | ---: | --- |
| parent-study.json | 152,977 | `7dc99f764c7f4148cd4e54d2e75b93afc7613ee04e7d9eea1d57959c2b4b1951` |
| issue-1016-overlap.csv | 4,710 | `5e33ac57ee4982803c72fca78bfe6226663b42c2e716b28bd46e2a6e6311bb0a` |
| geometry-comparison.json | 67,808 | `c365fceb6d68c011f82340a6693c6658b503e312c64a631ac2a4b63b1bb3c59d` |

The new per-parent erratum derives source vintage from `boundaryYear` in the corresponding pinned ADM1 metadata. It records source layer/type separately. Twelve Serbian district parent matches report 2017; two Slovenian cohesion-region matches report 2021. Ankaran, Izola and Piran are one-child Atlas wrappers with no independent parent source polygon, so their source vintage is unknown. The original product incorrectly copied `shapeType` (`ADM1`) into `parent_source_vintage`; the historical files remain unchanged.

## Guard behavior and reproducibility

All 44 immutable `commit:path -> SHA-256` inputs in the issue contract are checked against Git objects. Child roster exactness is checked against the pinned scope. Each of 278 child records must match the source collection, exact shapeID, and exact original `shapeName`. All 17 parent IDs must match the issue assessment roster. A separate source correspondence check catches the previously demonstrated one-field source-name alteration. Every output goes to a new directory; an existing directory is rejected without replacing any file. Run results and output digests are retained in `reproduction-runs/`.

Geometry diagnostics use the unmodified retained polygons, Shapely 2.1.2 / GEOS 3.13.1 and pyproj 3.7.2 / PROJ 9.5.1. The method transforms WGS84 lon/lat into EPSG:3035 (ETRS89 / LAEA Europe), uses planar 2D areas and symmetric differences, and performs no repair. A CRS round-trip control and geometry validity checks are in the reproduced report. These diagnostics compare source polygons and do not establish legal boundaries, territorial meaning, current membership, completeness, or source accuracy.

## Source and granularity findings

The Serbian GeoBoundaries parent layer has 25 features (metadata count 25), vintage 2017, boundary type ADM1, canonical `district`, and OSM/Wambacher source attribution under ODbL 1.0. Official Serbian RZS and MDULS sources describe 29 administrative districts; the 25-feature layer therefore does not establish current complete district coverage. Serbian NSTJ3 “areas” and administrative districts are different systems. The 145-feature Serbian ADM2 collection is also a 2017 OSM-derived layer, not a current official register.

The Slovenian GeoBoundaries ADM1 layer has two 2021 NUTS2 cohesion regions sourced to Eurostat/GISCO under CC BY 4.0. These are statistical regions, not municipal provinces. The 213-feature Slovenian ADM2 collection is a 2017 OSM-derived layer. GURS supplies 212 current municipalities and 12 statistical regions; SURS identifies NUTS3 statistical regions and the 8+4 cohesion grouping. Statistical membership and legal boundary equivalence are not established by this packet. Three Slovenian coastal parents are synthetic Atlas wrappers around individual municipal children.

The source packet's duplicate normalized Maribor name, older/current boundary-vintage differences, historical 2017 names, and absence of complete Serbia crosswalk geometry remain unresolved. The reproduced overlap and area figures are diagnostics. No regional or national granularity proposal is made.

## Acceptance limits and handoff

This is a reproduction and provenance correction. It does not certify all Yugoslavia parent/child relationships, current official completeness, legal or historical boundaries, or geographic approval. Official source access notices and national registers need direct per-unit archival/legal verification before any boundary or parent correction. Follow-up work must inspect the RZS spatial-unit register and Serbia district decree against a complete current geometry release; for Slovenia it must retain the dated GURS register and SURS NUTS membership notice. No production import or release change is authorized.
