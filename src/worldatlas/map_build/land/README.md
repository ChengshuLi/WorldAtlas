# Land assignment

The land calculation reads imported geographic records from the run's saved
Neon selection. It uses the current physical grid and does not reopen source
archives or read an earlier map.

## Calculation

1. Find connected physical land, with longitude wrapping.
2. Use selected named points to identify mainland components. Assemble selected
   boundary sections and closure routes into the mainland regions.
3. Rasterize those regions on the native grid to create mainland seeds.
4. Assign other components to their nearest mainland using WGS84 distances.
5. Apply explicit affiliations, selected line sides, source-backed island groups
   and direct satellite relationships. Compose the final land once, including
   scoped geographic partitions.

Distance assignments supply defaults. Explicit geographic decisions take
precedence. Conflicting explicit decisions fail; physical water stays zero.
Scoped partitions never change mainland seeds or distance-search domains.

## Files

| Files | Responsibility |
| --- | --- |
| `connected.py` | Build four-neighbor physical components. |
| `components.py` | Read current components; locate points and query polygon coverage. |
| `witnesses.py` | Resolve imported named points, identity areas and selected component groups. |
| `regions.py` | Join selected line sections; check closure routes against the physical grid. |
| `seeds.py`, `seed_strips.py` | Rasterize selected regions and compose seed runs efficiently. |
| `seed_index.py` | Index every seed run and choose actual seed-cell samples. |
| `hints.py` | Choose a promising category from those samples. Hints are not final assignments. |
| `certificates.py` | Prove a hint wins when complete spatial bounds exclude all competing categories. |
| `exact_search.py`, `search_engine.py` | Search remaining possibilities using complete WGS84 distances. |
| `assignments.py` | Connect the distance calculations and write component-to-entity results. |
| `geographic_assignments.py` | Resolve selected point/component and polygon/component relationships. |
| `line_groups.py` | Count complete components on either side of selected latitude-monotonic lines. |
| `source_groups.py` | Apply selected source-backed island-group choices. |
| `satellites.py` | Find direct nearby named anchors, including every relevant competing component. |
| `islands.py` | Connect line, group and satellite operations using Neon choices. |
| `partitions.py` | Construct scoped land partitions from selected lines and side witnesses. |
| `composition.py`, `regional.py` | Combine the assignments and write final land in one composition. |

Entity IDs, category bindings, geographic extents, selected features, witnesses
and distance policies come from Neon. Component IDs are temporary run data.
Inferred satellites cannot become anchors for other satellites.

Working assignments read `atlas.geographic_assignments`. Each row contains
`assignment_id`, a target `entity_id`, a human-readable `rationale`, and
`feature_ids`: a nonempty array of distinct imported polygon feature IDs.

Map building unions the selected polygons, then assigns each whole component
with more than half its land-cell centers inside that union. An exact half does
not match. This is one shared rule, without per-assignment relation options.
Source polygons retain their original outlines and holes; the importer does not
replace them with bounding rectangles. Missing island coverage is represented
by another necessary source feature in the same assignment.

Empty selections, missing features, protected mainland selections and
disagreeing targets fail before composition. Retained release inputs preserve
their original single-feature, compound and projected-coordinate selections.

Current imported features use WGS84 longitude/latitude. Retained release inputs
may contain earlier single-feature or compound rules and projected geometry. Replay reads those
frozen formats without rewriting their stored records; they are not accepted as
new working assignments.

Generate a numbered visual review of working assignments with:

```bash
python -m worldatlas.map_build.land.assignment_report \
  --selection /absolute/path/to/run/input-selection.json \
  --physical /absolute/path/to/run/physical/physical \
  --components /absolute/path/to/run/components \
  --output /absolute/path/to/review-report
```

The report shows the selection geometry, actual selected cell runs, component and
cell counts, feature counts, other rules selecting the same components, and each rule's uniquely
covered components. It uses the run's grid and entity colors. Open `index.html`;
no database credentials or server are required. Add `--previous-selection` and
`--map-comparison` to show the earlier rules and an actual final-grid comparison.
The existing regional line/group policy is shown alongside explicit assignments.
Source features have distinct colors and a matching legend. Uncheck a feature
to hide its outline; this does not change the assigned cells.

## Tests

The tests beside these modules cover component identity and coverage, arbitrary
codes and region counts, complete seed construction, exact distance comparisons,
longitude wrapping, source-group conflicts, direct satellites and final
composition. Small independent cell calculations check the optimized algorithms.
The main-command tests also exercise the direct stage chain and checkpoint reuse.

Use `--feature-audit /absolute/path/to/feature-audit.json` to include measured
per-feature removal effects. The audit supplies a `retained` list with
`assignment_id`, `feature_id` and `changed_cells` for each current reference.
The report rejects an audit missing a selected feature.
