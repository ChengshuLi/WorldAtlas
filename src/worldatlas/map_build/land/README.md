# Components and land distances

Geographic rules run through the common [parent-division engine](../division/README.md). This folder supplies its connected-component and complete-distance calculations. It also generates the interactive area-assignment report.

## Use

Generate a numbered, sortable report from a completed build. Omit `--parent` to use the root parent.

```bash
python -m worldatlas.map_build.land.assignment_report \
  --run RUN --parent PARENT_ID --output REPORT_DIRECTORY
```

## How it works

Reference cells are the selected components' actual physical shores. Distances are between cell centres; a source point only identifies a component. Whole query-component context remains available even when the emitted query scope contains only unassigned cells. Strictly smaller distances win; exact equality uses the supplied category order. Sample witnesses and pruning bounds never replace a complete search when the answer is unproved.

The report reads each polygon-based land rule's saved claim grid. The counts and filled cells include the effects of the rule’s connectivity and unassigned-cell filters. A reused land stage uses its original claim files. Each source feature has its own outline color; the two maps show its original geometry and selected cells. The table and synchronized detail view share one page. Definitions remain in Neon and frozen inputs, rather than being copied into this code.

## Code and tests

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

Tests beside the code compare optimized component-distance searches with exact references and check the report’s selection and counts. Run the [map-building suite](../README.md#code-and-tests).
