# WorldAtlas V8 data strategy

## Sources, decisions, and releases

R2 holds the original source files. The Neon source catalog records their
versions, object keys, and checksums. Neon also holds the editable geography
and review decisions, with source links and revision IDs. The
[V8 configuration](../scripts/pipeline/config.json) selects the source and
decision revisions used by the [pipeline](../scripts/pipeline/README.md).

To change geography, edit a draft decision and generate a map preview for
review. Review the assigned cells at map resolution. Publication uses approved
decisions and records the two verified row-run objects in Neon. The
[current viewer](../web/current/README.md) reads the published grid from R2.

## Geographic grid

V8 uses an equirectangular grid with a step of 0.00274658203125° in both
directions. It covers 131,072 columns and 54,614 rows, from 90°N to a southern
edge of 60.0018310546875°S. Longitude wraps. Each cell has one published
category. The six land continents and the ocean groups provide the geographic
framework.

The physical stage establishes land and water before the land decisions
assign continents. Ordinary open coasts use a 12 nautical mile (22.224 km)
buffer, measured between water-cell centers and represented physical coastal
land-cell centers by WGS84 ellipsoidal geodesic distance. The nearer coast
resolves overlaps, with an explicit priority for ties. Named basins use their
selected source extents and assignment rules. The [water-stage guide](../scripts/water/DIRECT.md)
covers the basin, coast, ocean, and closed-water steps.
