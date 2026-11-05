# WGS84 D8 distances

The priority flood preserves its elevation and barrier logic. For the subsequent D8 slope comparison, every neighboring-center distance is calculated on the WGS84 ellipsoid after transforming the projected raster centers to longitude and latitude. Four undirected edge planes cache the eight directional distances, at 32 additional bytes per grid cell, plus temporary arrays. Projected cell size is not treated as a ground distance. The raster must be north-up and projected, with finite elevations for all valid cells; terrain masks and finite nodata sentinels are honored.

The three-basin screen ranks its modeled four-neighbor transition midpoints by WGS84 distance from the target point. That is a nearest sampled midpoint, not a continuous or surveyed divide.

This is a research model, not an independently surveyed divide. The change can alter flow directions, outlet classifications and downstream proposed routes; outputs from earlier projected-distance runs must be labeled as historical and rerun rather than presented as results of this method. Other route and line diagnostics still require their own WGS84 migration; this change does not assert codebase-wide compliance.
