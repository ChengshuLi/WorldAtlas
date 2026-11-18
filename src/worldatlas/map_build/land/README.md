# Components and land distances

Geographic rules run through the common [parent-division engine](../division/README.md). This folder supplies its connected-component and complete-distance calculations. It also generates the interactive area-assignment report.

| Files | Responsibility |
| --- | --- |
| `connected.py` | Find parent-relative physical components with longitude wrapping. |
| `components.py` | Read components, locate source points, and count polygon coverage. |
| `reference_index.py` | Index every supplied reference run and choose real witness cells. |
| `hints.py` | Obtain promising owners from real witness cells. |
| `certificates.py` | Prove an owner wins when conservative bounds exclude every competitor. |
| `exact_search.py`, `search_engine.py` | Search all remaining possibilities using exact WGS84 distances. |
| `assignments.py` | Calculate and store owner assignments for selected query components. |
| `assignment_report.py`, `.js`, `.css` | Show selected source areas and their actual component assignments. |

Reference cells are the selected components' actual physical shores. Distances are between cell centres; a source point only identifies a component. Whole query-component context remains available even when the emitted query scope contains only unassigned cells. Strictly smaller distances win; exact equality uses the supplied category order. Sample witnesses and pruning bounds never replace a complete search when the answer is unproved.

Generate a numbered, sortable report from saved inputs and run components:

```bash
python -m worldatlas.map_build.land.assignment_report \
  --selection RUN/input-selection.json --physical PHYSICAL_OUTPUT \
  --components PARENT_COMPONENT_OUTPUT --output REPORT_DIRECTORY
```

The report uses the production scope/majority code. Each source feature has its own outline color; the two maps show its original geometry and selected cells. The table and synchronized detail view share one page. Definitions remain in Neon and frozen inputs, rather than being copied into this code.
