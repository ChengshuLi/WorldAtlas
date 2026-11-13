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
| `affiliations.py` | Resolve selected point/component and polygon/component relationships. |
| `line_groups.py` | Count complete components on either side of selected latitude-monotonic lines. |
| `source_groups.py` | Apply selected source-backed island-group choices. |
| `satellites.py` | Find direct nearby named anchors, including every relevant competing component. |
| `islands.py` | Connect line, group and satellite operations using Neon choices. |
| `partitions.py` | Construct scoped land partitions from selected lines and side witnesses. |
| `composition.py`, `regional.py` | Combine the assignments and write final land in one composition. |

Entity IDs, category bindings, geographic extents, selected features, witnesses
and distance policies come from Neon. Component IDs are temporary run data.
Inferred satellites cannot become anchors for other satellites.

Imported geometry normally uses WGS84 longitude/latitude. A source may retain its
native projection when converting its edges would approximate them. Projected
queries transform cell centers with the selected coordinate operations and
coverage. Unknown coverage and boundary contacts remain explicit.

## Tests

The tests beside these modules cover component identity and coverage, arbitrary
codes and region counts, complete seed construction, exact distance comparisons,
longitude wrapping, source-group conflicts, direct satellites and final
composition. Small independent cell calculations check the optimized algorithms.
The main-command tests also exercise the direct stage chain and checkpoint reuse.
