# Divide a geographic parent

Read the parent's children and rules from the frozen input selection. Prepare its physical components and geographic scopes, evaluate independent claims, and reject disagreeing ownership. The same operations apply to any parent.

## Use

Run the [map builder](../README.md#use). It calls this engine for each selected parent. Edit the [geographic rules in Neon](../../../../database/README.md#schema) to change the scope, targets or geometry of a division.

## How it works

| Operation | Calculation |
| --- | --- |
| `assign_area` | Give eligible scope cells or components to one child. |
| `divide_area` | Split along the imported `boundary_line` features; imported label points identify child owners. |
| `nearest_land` | Assign each remaining whole component by its minimum WGS84 distance to selected reference shores. |
| `nearest_coastal_water` | Assign water within the configured coastal distance to its nearest assigned physical shore. |
| `nearest_basin_water` | Discover bordering owners from the full basin, then assign its water by their nearest shores. |
| `nearest_water` | Assign eligible water using all assigned physical shores. |

`scope_area` polygons and `scope_component` points select a union within the parent. With neither selector, use the parent. `physical_class` selects eligible output cells. `unassigned_only` filters them against the group's immutable input ownership snapshot. These filters never shorten reference sets, change component majority denominators or redefine the supplied dividing lines.

With `unit=component`, an area selects a whole component when it covers more than half its cells. Division requires one labelled face to contain more than half of the component’s cells. Cell mode can split a component. Missing labels or eligible unassigned cells stop the run. Boundary cuts use the exact stored coordinates. Only a centre on the line uses the tie convention, and reversing a line preserves the same split. A continuous face can include disconnected pieces of selected physical land. Sub-cell boundary geometry preserves that identity when cell-centre connectivity fragments a thin strip beside water.

Physical shores are extracted once. Their attached owners and distance indexes are reused. Nearest operations share exact WGS84 kernels with conservative spatial certificates; unresolved certificates perform complete searches. Source polygons are prepared once for repeated raster windows. Scope bounds skip empty rows while retaining the full extent of majority-selected components. Component intervals and owner lookups use arrays directly rather than repeatedly expanding them into individual Python records. Boundary divisions read face intervals from mapped arrays and attach their owners in batches. Reference intervals feed the distance index directly, without writing and rereading a temporary map stream. Basin masks are rasterized once and reused for participant discovery and query windows, including windows across longitude wrapping. A single eligible owner uses direct area assignment rather than a distance calculation.

Optional `connected_to` links retain cells connected to any of the linked points. Components are built over the parent, physical class and ownership snapshot before area selectors narrow the query. The same snapshot's component index is shared across rules. Invalid references stop the calculation; an empty eligible query needs no reference.

The four World ocean rules link to explicit reference points and use S-130 polygons to determine ownership within those components. Remaining pockets reach the final `nearest_water` rule. Strictly smaller computed distances win, including tiny differences. Exact equality uses the category binding order. A coastal cutoff includes its exact threshold. Conservative search margins never change those decisions.

Coastal and basin claims run independently against the same ownership snapshot, sharing shore positions and indexes. Their overlapping claims must agree. Land-stage receipts separately pin their actual definitions and outputs, so water-only edits can reuse verified land without reusing an outdated final parent division.

## Code and tests

| Files | Responsibility || --- | --- |
| `contracts.py` | Resolve frozen rule, feature and target links. |
| `intervals.py`, `scope.py` | Prepare compact query intervals and merge independent claims. |
| `connectivity.py` | Build shared connected-component domains for reference-point scopes. |
| `areas.py` | Uniform assignment and labelled geometric division. |
| `shores.py` | Shared physical shore extraction, owner attachment and indexes. |
| `nearest.py`, `policies.py` | Common distance kernels and four reference/scope policies. |
| `engine.py` | Parent execution, checkpoints, stage dependencies and coverage. |
| `hierarchy.py` | Select ancestors, reuse unchanged divisions and substitute each child's result into its parent. |
| `encoding.py` | Convert ownership and physical class to published map codes. |

Keep geographic choices in Neon and algorithms here. Generality and efficiency are equally required: reuse immutable geometry/indexes and vectorized intervals, measure substantial costs, and retain complete input coverage.

Tests beside the code cover rule contracts, area selection, connectivity, distance policies, merging claims and hierarchical reuse. Run the [map-building suite](../README.md#code-and-tests).
