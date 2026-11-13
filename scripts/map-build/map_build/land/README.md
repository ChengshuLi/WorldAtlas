# Land assignment

Land calculations use imported geographic records and the current physical grid.
They do not reopen source archives.

- `components.py` reads current component runs, checks their physical coverage,
  locates source points and counts component centers inside source polygons.
- `affiliations.py` resolves the geographic selection in each affiliation's
  `evidence.component_selection`. Conditions select a point's component,
  intersecting components or wholly contained components. Rules can combine
  conditions, exclude features and check selected witnesses or identity areas.
- `composition.py` combines mainland assignments, component affiliations and
  scoped geographic polygons in one final land composition. Conflicting claims
  fail; physical water stays unassigned by land calculations.
- `line_groups.py` counts complete components on either side of a selected
  latitude-monotonic line. It also reads complete nearby competitor runs.
- `source_groups.py` applies selected source-backed group choices before
  `satellites.py` calculates direct WGS84 distances to independently named
  islands. Inferred satellites cannot become anchors for other satellites.
- `islands.py` connects those operations using selected lines, imported point
  and polygon features, geographic scopes and entity IDs from Neon.
- `partitions.py` builds scoped polygons from selected joined lines and two
  side witnesses. These rules apply during final composition and never change
  mainland distance seeds or search domains.
- `regional.py` connects the complete regional calculation and final land
  composition through ordinary Python calls.

Entity IDs and land codes come from registry bindings. Source identities and
geographic choices belong in Neon. Current component IDs are temporary run data.

Most imported geometry uses WGS84 longitude/latitude. A source can retain its
declared native projection when transforming its edges would approximate them.
Projected contact queries transform cell centers using the selected coordinate
operations and their geographic coverage. Unknown coverage and exact boundary
contacts remain explicit; no boundary-name branch chooses their treatment.

`test_regional.py` covers point and polygon selections, partial components,
longitude wrapping, projected queries, protected components, conflicting claims
and a complete small structured-input-to-land calculation.
`test_satellites.py` checks complete candidate searches and distances against
independent cell-pair calculations, source-group conflicts and no chaining.
