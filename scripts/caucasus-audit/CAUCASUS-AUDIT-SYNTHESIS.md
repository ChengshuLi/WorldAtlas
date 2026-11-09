# Caucasus boundary audit: synthesis

Research status at 2026-11-05. The selected 2,292-vertex west-to-east LineString and its cell labels have not been changed by this audit. Its four sections are analytical subdivisions of one selected geometry, not four separately stored lines. A source match, a model, a map overlay, and a reference-grid mismatch are different kinds of evidence; none alone establishes the true watershed.

## Segment-by-segment assessment

| Section | Construction and source fidelity | Geographic confidence and remaining work |
|---|---|---|
| Anapa / coastal opening | The opening ~4 km edge was previously found to coincide with a HydroBASINS edge. Its physical shoreline clip and original construction inputs have not been recovered. | Low confidence in the exact coastal endpoint and connection. Verify the intended coastline and trace the first natural drainage divide; a basin-edge match is not a survey. |
| Western Black Sea / Azov divide | Much of the selected line tracks HydroBASINS, but the precise construction lineage has not been established. | Named valleys and independent ridge landmarks support investigating the alternative near Abin/Papay/Afips. Modeled drainage and OSM-based seeds favor parts of it, while other samples and joins remain unresolved. No continuous alternative has both source-supported joins. |
| Central Greater Caucasus | The selected line is strongly consistent with modeled HydroBASINS terminal separation in a 39–47E screening window, but exact original construction inputs remain missing. This is source correspondence, not proof of lineage. | Named Marukh and Mamison pass coordinates lie near the line, while Jvari and Klukhor are material unresolved leads described below. Limited OSM pass-window checks cannot validate the entire section. |
| Eastern Caucasus | Selected vertices 1894–2290 match 397 consecutive vertices of published source feature 463 after binary64 parsing. That is a strong check of source fidelity for the retained run, not proof of the author's method, shoreline clip, or exact watershed. | A mapped Qusarçay tributary crosses the line; screened JAXA and Copernicus terrain generally descends through it, but the connected modeled alternative has unresolved drainage and joins. A historical blue feature near that alternative also needs confirmation. |

### Anapa coastal source comparison

The selected geometry begins at 37.31730061393096E, 44.903966887846714N. The earlier comparison found a 4,037.35 m edge coincident with a shared HydroBASINS edge at 42 tested positions; that is evidence of geometric correspondence, not recovery of the clipping operation or proof that the edge is the desired physical divide.

[Trubetskoy's published method](https://sashamaps.net/resources/europe-asia-boundary/) states that his Caucasus route enters the Black Sea near Varvarovskaya Shchel, rather than prescribing the selected Anapa endpoint. In the previously retrieved author GeoJSON, zero-based feature 462 has its last nearshore vertex before a long offshore leg at 37.367733791968455E, 44.799378112163076N. Its WGS84 geodesic separation from the selected starting vertex is 12,287.57 m. This is a vertex-to-vertex comparison, not an exact comparison of shoreline intersections. The selected local opening is therefore not a faithful copy of this author's coastal approach. The two approaches are geographic alternatives; the difference alone does not establish which is the project's intended watershed.

Reproduction: parse the coordinate-linear LineStrings and use WGS84 inverse geodesic on selected coordinate 0 and author feature 462 coordinate -4. The local selected JSON used has SHA-256 `081f5909935023255cf9f0b13f06102aaa97cc19a15715b6cabb9964b7a20f25`; the author GeoJSON used has SHA-256 `c9d56b1291522573fbb8b0baa1a39cecfd192eda8f5e51650b24f562d13688e6`. The latter is the retrieved local file's byte hash, not an asserted stable hash of a changing upstream resource. Further work should recover the selected shoreline-clipping input and the specific HydroBASINS construction, then trace named watercourses on both sides and test an independently supported connection. The author route is an alternative to examine, not an approved replacement; its coastal entry and joins also need checking.

## Concrete leads and decisions

* **Western join:** The extended Abin alternative is geometrically constructible and relies on model-dependent joins and shared OSM seed assumptions. Independent drainage and an accurately controlled local map are needed.
* **Jvari:** OSM maps a stream crossing the selected line and links it through Bidara to the Terek; an ADB project assessment independently confirms the Bidara–Tergi relationship at regional scale. JAXA and Copernicus terrain support the mapped-crossing lead, but routes stop at pits/flats or artificial outlets. A 1:100,000 historical sheet shows a nearby blue watercourse; it and OSM may share 1:50,000 topographic lineage. Broader two-model seeded interfaces remain disconnected. Independently surveyed headwater and divide mapping around 44.42–44.49E, 42.48–42.53N, with both joins, is needed.
* **Klukhor:** Published pass locations lie approximately 252–302 m from the selected line. JAXA and Copernicus strict 5x5 median screens show a local depression at 100 m offsets, and both unconditioned flow probes cross from +100/+250 m before stopping in pits/flats. A historical sheet is visually consistent with the reported pass location, but may share its map lineage. An independently controlled pass or drainage survey and a complete connected route are needed.
* **Eastern headwaters:** A possible replacement cut passes through source intersections. Its southern drainage and joins need stronger evidence from mapped headwaters and a controlled topographic source.

Historical map fitted-grid residuals report internal scan fit only, not total geographic accuracy. Elevation samples are correlated and terrain models can contain ice, fills, pits and surface artifacts. Drainage seeds and crop edges are assumptions, not observed outlets. The source-supported boundary and realistic changed-cell impacts must be established before any selection.

## Data custody and cleanup

The [V8 source replay](CAUCASUS-WGS84-REPLAY.md) identifies the selected recipe and raw inputs.

The earlier audit placed explicitly unselected, temporary research in draft Neon provenance keys west_candidate_audit_20261105 (including its continuation, Copernicus, Ubin and Khabl subkeys) and east_source_grid_audit_20261105 (including source-intersection analysis). The western OSM research source/link and osm-caucasus-west-confluences@snapshot-2026-11-05-fbf18a3d08da source/link are also research-only. Confirm their current existence and dependencies, preserve needed evidence in R2/PR4, and remove them only after they are no longer needed and any applicable deletion authorization is satisfied. Do not remove selected pipeline sources or change selected geometry as part of research cleanup. This audit has not performed those deletions.

## Reproducibility and scope



### Selected-line topology

As a separate topology check, Shapely reports the 2,292-position locally hash-verified selected LineString is valid and simple, open, and has no repeated coordinate positions. This checks coordinate topology only; it does not validate drainage, historic lineage or the region polygon's external closure. No selected geometry or labels were changed.
