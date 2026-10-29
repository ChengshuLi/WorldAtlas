# Data strategy

WorldAtlas starts with a flat 2D display and a fixed, time-agnostic geographic framework from location through continent. Political affiliation is time-dependent: each location has exactly one political entity for each date, based on effective control. We will not maintain separate territorial-claims records.

Retain source geographic polygons and coordinates where available. A city’s representative point does not define its area; use the relevant boundary polygon for area-based assignments. Assign each grid cell to the location covering the largest share of its area. Assign each location to the political entity controlling the largest share of the location's area on the requested date. Every cell inherits its location's affiliation, even where a smaller part of that location lies under another controller. Thus cell assignments do not override the location-level rule.

Use reasonably recent, reliable administrative boundaries as fixed location footprints. Prefer current data, but use 2025, 2024, or older where needed; source years may differ by location, and record the actual date used. There is no required common reference date or mandatory 2026 coverage. Freeze chosen footprints across all history; only political control changes. These are selection criteria, not a chosen dataset.

Population means all inhabitants within a fixed location footprint at a given historical date, including rural areas and villages; estimates are encouraged when records are sparse. Label estimates with their basis and assumptions, do not present them as observed counts or double-count people in overlapping source areas, and leave handling of dates with no defensible estimate open.

Jointly administered locations still receive one entity. Use a documented administrative lead when one exists. Otherwise, choose the party with greater responsibility or resources when comparable evidence supports that judgment; if it does not, use an explicit deterministic fallback, to be decided. Keep a short selection rationale and never invent facts or a primary authority.

Approximation is acceptable only with a stated, understandable rule and its consequences. Investigate source-boundary gaps and overlaps rather than concealing them through cell assignment.

Still open: precise geographic granularity/location level; workflow for missing control evidence without fabricating an owner; final tie-breakers; grid design, resolution, and physical-area measurement; and data format/storage schema. A two-neighbor-polygon thought experiment is not a required pipeline. No implementation or infrastructure decision is implied here.
