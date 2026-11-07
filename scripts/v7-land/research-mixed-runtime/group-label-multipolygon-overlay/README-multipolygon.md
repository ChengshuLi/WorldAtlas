# MultiPolygon containment

The existing generic component-containment method accepts a valid GeoJSON MultiPolygon. The resolver validates the complete geometry, processes each polygon part through the existing boundary-center and intersection checks, combines the per-root counts, and selects only components for which every represented land-cell center is covered. The source remains one feature and its existing source and geometry pins still apply.

Each part must intersect at least one represented land component. A part with no represented land fails closed, rather than being silently ignored. A center exactly on any part boundary also fails closed. Shared point touches between valid parts cannot duplicate an accepted center. Holes are excluded from coverage.

A source feature's geometry and checksum do not establish its geographic meaning or independence from other evidence. A generalized label is not necessarily a coastline, a complete island roster, or an independently verified group boundary. Source identity, lineage, and the geographic interpretation must be assessed separately before a decision is selected.
