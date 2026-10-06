# Before-water connected components and original crosswalk, #1005 part 2

This stage reads complete immutable products from the merged part 1 audit and the original water-screened audit/component inventory. It does not rewrite their source data or interpret a gap as political affiliation. Every old/new fragment and component has a ledger entry. Original IDs and full-feature bindings survive; new components use a separate `physical-component:` namespace.

Exact coordinate equality, equal point sets, positive-area overlap, positive-length contact, point-only contact and failed/unknown overlays remain distinct. The crosswalk retains complete observed intersections and every nonempty difference atom, including numerical lines/points. There is no area cutoff, snapping, buffering, simplification, MakeValid or nearest-owner fill. Dateline comparisons shift copies by exactly 360 degrees and record the shift, preserving original input coordinates. Original five unmeasured shapes and old blocked domains must remain explicit.

Commit exact source bytes before any generation. Use Node 24 and Python with the existing pinned NumPy/Shapely/pyproj versions. Controls:

```sh
node --test test/physical-gap-crosswalk.test.mjs test/geographic-components.test.mjs
```

Whole-world generation (run twice into distinct new owned vintages):

```sh
python3 scripts/build-physical-gap-components.py \
  --commit c603befd3aaf4da90d59b12378e1e0739331efba \
  --output coordination/engineering/physical-gap-components-1005-20261005-local19/reviewer-reproduction-NEW
```

The exact original/native input subsets must agree between the earlier and new audits; all original complete bundles and full membership bindings are checked. All new point/line/clipping remnants remain pinned in their complete original part 1 bundles. The outputs must be compared by actual whole-file bytes and all report fields except the new output-vintage prefix. No worldwide completion/reproducibility result is claimed until both runs finish and their complete products pass comparison.

Choose a new unused reproduction prefix; `components-v1`, `components-v2` and `components-v3` are frozen original execution identities. For original numerical byte reproduction, use the exact five scientific code files from execution `6ed6406f9fad4c7c468b06a376346b216cb50db7` (retained unchanged in custody), its pinned software and input commit. A reproduction at a different current Git HEAD must truthfully record that execution commit; that report metadata differs from the original and must not be relabeled as the original execution.

Part 3 global priorities/source investigation partitions remain required. This diagnostic stage cannot approve geography, factual water, ownership, deployment or a default grid switch. Confirmed repairs and subsequent release/content/delivery checks remain the broader goal.

The reused legacy component `diagnostic_nearby_locations` field reads the old audit schema and does not summarize physical fragments' `exact_location_contacts`. An empty legacy summary cannot establish absence of contacts. `scripts/physical_component_contacts.py` resolves every exact contact through verified original full-feature bindings, preserving its geometry, source, year and fragment identity. Missing contact recording remains explicit unknown, distinct from a recorded empty list. Part 3 must use this resolver; contacts never assign administrative ownership.

## Actual executions and whole-file custody

The first execution at `8f6dc184d1a41b634cec4759bb57b3cc04dd980a` completed the comparison but failed the final export because a component ledger filename collided with a geometry bundle. Its complete partial exports, original failure log and incomplete receipt remain preserved without a success claim.

Two corrected executions at `6ed6406f9fad4c7c468b06a376346b216cb50db7` read immutable input commit `c603befd3aaf4da90d59b12378e1e0739331efba`. Each produced 48 whole output files. All actual encoded bytes and report fields agree, allowing only their original output-directory prefixes to differ. `physical-components-reproducibility.json` records the whole-file framing recipe and actual equal aggregate digest.

`custody-v1/index.json` retains all three original logical inventories and their exact original reports and code. Every logical path resolves to one complete unchanged encoded payload under `custody-v1/payloads/`; identical files share physical storage. This transport happened after the scientific executions and must not be described as their original input. Logical custody totals 296,707,059 bytes in 149 file aliases; 57 unique physical files occupy 105,927,484 bytes. Every payload, original encoded/decoded descriptor, report, incomplete trial and exact five-file execution-code roster is validated. Original science inputs are separately read against immutable Git and complete pins, never replaced by an extract.

The root evidence manifest counts every actual ordinary changed file and retained baseline scientific input under the unchanged 32 MiB per-file/decoded-file, 256 MiB total and 512 descriptor limits. Aliases do not waive limits on a whole original decoded file. The mandatory typed gate reconstructs the complete connected components/contact roster and checks every original/new identity, relationship, shape binding, unmeasured value and original blocked domain. Generic hash validation alone cannot certify these logical references.

```sh
python3 scripts/validate-physical-component-evidence.py
node --test test/physical-component-evidence.test.mjs \
  test/physical-component-evidence-controls.test.mjs \
  test/physical-component-custody.test.mjs test/physical-gap-crosswalk.test.mjs
```

The raw logical generation directories are intentionally not duplicated as committed outputs. Original full bytes remain recoverable through the custody ledger, complete unchanged payloads and archived executed code. Source authority, physical water truth, factual repairs and delivery remain unapproved.

### Reconstruction across platforms

Linux at Shapely 2.1.2 / GEOS 3.13.1 reconstructed one retained MultiPoint contact with its identical two members in reverse order. The reconstruction gate therefore compares exact structural geometry signatures: whole line reversal, closed-ring rotation/reversal, hole permutation and multipart-member permutation are allowed. Geometry types, exact numeric representations/dimensions, every vertex/member occurrence, ring closure, exterior/hole roles, extra geometry fields and all row metadata remain exact. No geometric point-set equality, rounding, tolerance, vertex removal, overlay or repair can satisfy this gate. Original encoded payloads, hashes and source bindings are untouched.

Whole-file byte reproduction remains a separate obligation tied to the original actual execution environment; structural reconstruction does not imply identical encoded products on another platform. `test/physical-component-structure.test.mjs` checks the observed Linux permutation and rejects tiny coordinate changes, lost/extra vertices or members, altered kinds/identities, type changes and erased positive-area shapes. Complete-world reconstruction still compares every retained record.
