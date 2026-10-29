# Data strategy

WorldAtlas uses flat, two-dimensional geographic features in a fixed, time-agnostic geographic framework from location through continent. Political affiliation is time-dependent: each location has exactly one political entity for each date, based on effective control. We will not maintain separate territorial-claims records.

Retain source geographic polygons and coordinates where available. Represent each city by a representative point, not its urban area. Assign each grid cell to the location covering the largest share of its area. Assign each location to the political entity controlling the largest share of the location's area on the requested date. Every cell inherits its location's affiliation, even where a smaller part of that location lies under another controller. Thus cell assignments do not override the location-level rule.

Jointly administered locations still receive one entity. Use a documented administrative lead when one exists. Otherwise, choose the party with greater responsibility or resources when comparable evidence supports that judgment; if it does not, use an explicit deterministic fallback, to be decided. Keep a short selection rationale and never invent facts or a primary authority.

Approximation is acceptable only with a stated, understandable rule and its consequences. Investigate source-boundary gaps and overlaps rather than concealing them through cell assignment.

Still open: the location definition and boundary; workflow for missing control evidence without fabricating an owner; final tie-breakers; grid design, resolution, and physical-area measurement; and data format/storage schema. A two-neighbor-polygon thought experiment is not a required pipeline. No implementation or infrastructure decision is implied here.
