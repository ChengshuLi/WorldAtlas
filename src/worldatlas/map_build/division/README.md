# Divide a geographic parent

Read the parent's children and rules from the frozen input selection. Prepare its physical components and geographic scopes, evaluate independent claims, and reject disagreeing ownership. The same operations apply to any parent.

| Operation | Calculation |
| --- | --- |
| `assign_area` | Give eligible scope cells or components to one child. |
| `divide_area` | Split using imported lines; imported label points identify child owners. |
| `nearest_land` | Assign each remaining whole component by its minimum WGS84 distance to selected reference shores. |
| `nearest_coastal_water` | Assign water within the configured coastal distance to its nearest assigned physical shore. |
| `nearest_basin_water` | Discover bordering owners from the full basin, then assign its water by their nearest shores. |
| `nearest_water` | Assign eligible water using all assigned physical shores. |

`scope_area` polygons and `scope_component` points select a union within the parent. With neither selector, use the parent. `physical_class` selects eligible output cells. `unassigned_only` filters them against the group's immutable input ownership snapshot. These filters never shorten reference sets, change component majority denominators or redefine the supplied dividing lines.

Both area operations select whole components by strict majority when `unit=component`. Division requires a majority in one labelled face. Cell mode can split a component. Missing labels or eligible unassigned cells stop the run. A continuous face can include disconnected pieces of selected physical land; sub-cell boundary geometry preserves that identity when cell-centre connectivity alone fragments a thin strip beside water. This adds no geographic labels.

Physical shores are extracted once. Their attached owners and distance indexes are reused. Nearest operations share exact WGS84 kernels with conservative spatial certificates; unresolved certificates perform complete searches. Source polygons are prepared once for repeated raster windows. Scope bounds skip empty rows while retaining the full extent of majority-selected components. Component intervals and owner lookups use arrays directly rather than repeatedly expanding them into individual Python records. Boundary divisions read face intervals from mapped arrays and attach their owners in batches. Reference intervals feed the distance index directly, without writing and rereading a temporary map stream. Basin masks are rasterized once and reused for participant discovery and query windows, including windows across longitude wrapping. A single eligible owner uses direct area assignment rather than a distance calculation.

An optional `connected_to` feature link filters query cells by eligible parent connectivity. Point features supply reference locations directly; linked polygons are combined to derive one interior point. Components are built over the parent, physical class and ownership snapshot before area selectors narrow the query. The same snapshot's component index is shared across rules. Invalid references stop the calculation; an empty eligible query needs no reference.

The four World ocean rules use this filter to retain open-water components. Their S-130 polygons determine ocean ownership within those components. Remaining pockets reach the final `nearest_water` rule. No separate ocean-seed records, location-specific exceptions or new assignment method are involved. Strictly smaller computed distances win, including tiny differences. Exact equality uses the category binding order. A coastal cutoff includes its exact threshold. Conservative search margins never change those decisions.

| Files | Responsibility |
| --- | --- |
| `contracts.py` | Resolve frozen rule, feature and target links. |
| `intervals.py`, `scope.py` | Prepare compact query intervals and merge independent claims. |
| `areas.py` | Uniform assignment and labelled geometric division. |
| `shores.py` | Shared physical shore extraction, owner attachment and indexes. |
| `nearest.py`, `policies.py` | Common distance kernels and four reference/scope policies. |
| `engine.py` | Parent execution, checkpoints, stage dependencies and coverage. |
| `hierarchy.py` | Select ancestors, reuse unchanged divisions and substitute each child's result into its parent. |
| `encoding.py` | Convert ownership and physical class to published map codes. |

Keep geographic choices in Neon and algorithms here. Generality and efficiency are equally required: reuse immutable geometry/indexes and vectorized intervals, measure substantial costs, and retain complete input coverage.

Coastal and basin claims run independently against the same ownership snapshot, sharing shore positions and indexes. Their overlapping claims must agree. Land-stage receipts separately pin their actual definitions and outputs, so water-only edits can reuse verified land without reusing an outdated final parent division.
