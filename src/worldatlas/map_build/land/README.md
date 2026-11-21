# Components and land distances

Geographic rules use this folder to find connected pieces of land and calculate distances between them. [Parent division](../division/README.md)

## Use

The map builder calls these calculations when a parent has rules that assign land. [Map build guide](../README.md#use)

## How it works

Reference cells are the selected components' actual physical shores. Distances are between cell centres; a source point only identifies a component. Whole query-component context remains available even when the emitted query scope contains only unassigned cells. Strictly smaller distances win; exact equality uses the supplied category order. Sample witnesses and pruning bounds never replace a complete search when the answer is unproved.

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

Tests beside the code compare optimized land-distance searches with independent calculations. [Map-building tests](../README.md#code-and-tests)
