# Source-negative polygon containment overlay

This code-only research overlay adds `component_containment_excluding_source_v1`. It is not activated by publication and does not include selected geography or change a map. Apply it on the reviewed Hanish, large-ZIP and archive-prefetch combined runtime, preserving those overlays and their sibling point and stage-2 modules.

The method resolves one authenticated positive Polygon or MultiPolygon, selects only components whose every land-cell center is covered, and then excludes any selected component with a center inside one independently authenticated negative Polygon. Positive containment and final exclusion counts are labeled separately. Source hashes, structured geometry, component generation, boundary-center rejection, protected mainland checks, and all mixed-claim conflicts must be verified. A source-defined management footprint is not necessarily a physical coastline, and a generalized group is not an exhaustive geographic roster.

The negative polygon is extracted from a pinned provider-original Federal Register PDF and must equal the structured geometry in the decision feature and its canonical geometry hash. The extractor requires Linux sealed `memfd` support, `/usr/bin/prlimit`, and `/usr/bin/pdftotext`. It bounds input and output, uses a timeout, checks the source before and after, and does not persist ephemeral roots as selectors.

Configuration code pins `federal_register_rectangle` and `negative_component_filter` are required together whenever this new method is selected. Old requests remain valid without them. Run the full mixed-runtime test suite and a monitored real-source/latest-claim preview before selecting a decision or building a map.
