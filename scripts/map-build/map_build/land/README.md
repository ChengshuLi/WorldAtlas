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
- `regional.py` connects affiliation resolution and composition through ordinary
  Python calls. Its caller supplies any additional geographic partitions.

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
