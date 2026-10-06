# Native-grid offline validation

The native rule represents original lon/lat polygons at the immutable inverse-projected canonical cell centres. Its method is `native-linear-evenodd-first-owner-v1`. It preserves true native holes, original owner precedence and exact finite-coordinate boundary treatment. It does not establish that the source polygons fit their real-world neighbors, classify water or approve territorial affiliation. Global physical/source omission work remains separate from correcting projected-grid discrepancies.

## Selection and regression prevention

The ordinary build continues to select the retained legacy grid. A native offline build explicitly names both a candidate manifest and its reviewed whole-file SHA-256:

```sh
ATLAS_NATIVE_GRID_MANIFEST=coordination/engineering/native-grid-candidate-1010-20261005-local16/candidate-v1/manifest.json \
ATLAS_NATIVE_GRID_SHA256=efe31373ff6a2c3f4ba5f11f8cbe37b25337778b344d9dbf1d3dfde301e3e722 \
node scripts/build-static.mjs
```

Use Node 24, installed committed npm dependencies and the Python requirements. This prepares local illustrative data; it does not read hosted live facts or deploy anything.

`scripts/select-build-ownership.mjs` rejects unpinned manifests and source/release mismatches. Native selections also pass `require-verified-selection.mjs`: the exact candidate digest must have a reviewed entry in `scripts/native-ownership/verified-candidates.json`. The gate reads a whole-file hash-pinned ordinary Git blob, checks complete-domain accounting, both deterministic product inventories and every ownership asset against the selected manifest. The packaged atlas retains this reference as `gridVerification`. It explicitly carries no installation approval.

Every explicit native static build also runs `validate-context-input-stage.mjs` against the retained original-to-compact stage manifest. This separately bounded prerequisite verifies all 43 original source files, immutable generator/readback code, both complete byte-identical product inventories, all 34 derivative parts, original geometry digest and all IDs/parents/indices. Missing, tampered, omitted or stale stage data fails the build. Its receipt is retained as `nativeContextInputStage`. The standard evidence checker validates stage bytes; this mandatory build validator additionally checks complete transform lineage. Neither is a factual source certificate. Each stage retains the existing 256 MiB/512 descriptor limits; this is not the legacy voluntary partition gate.

Future materializations require a fresh candidate, two complete reproducible generations and exhaustive asset-decoding/native-membership comparison for their own immutable source/release pins, followed by independent review and a new registered receipt. An older receipt cannot admit a changed candidate. The existing native preparation and verifier entry points require committed executed code and preserve byte budgets. Follow their source/topology admission and existing geography approval rules; changing the original source scope is separate coordinated geography work. A registry entry is not permission to change boundaries, import facts or publish a release.

Dated contexts use original native geometry, explicit dense display indices mapped to original IDs, and recomputation of every row affected by changed/removed/added geometry. Unaffected rows retain the verified base through that mapping. Both renderers consume the same completed grid. Source digest, owner mapping and normative latitude bytes are verified; cancellation does not replace the displayed year with an unfinished context.

## Offline readback and recovery

After the explicit native build:

```sh
node test/native-build-binding.mjs
node test/native-world-context.mjs
node --test test/native-materialization-gate.test.mjs test/select-build-ownership.test.mjs
node --test test/native-renderer.test.mjs test/native-dated-browser.test.mjs test/context-input-stage.test.mjs
```

The binding readback compares every packaged row/run word to the registered candidate; authenticates every original native footprint; verifies original IDs and parents; checks normative latitude bytes; preserves the complete original physical-class manifest, source limits and asset bytes except its ownership association; and verifies the retained prepared-evidence index. It also confirms the original legacy grid remains selectable with its original digest. The world context control duplicates an existing native vertex and requires every output word and original owner mapping to remain identical. This representation control is not a factual repair.

The renderer test launches a new disposable headless profile, restricts requests to its exact localhost port and removes the profile. It never attaches to the user's browser. Its software WebGL2/Canvas controls cover recovered native fill/picking, explicit identity mapping, low zoom, dateline sides, true holes, physical-reference gap/water/unknown rendering and explanations, palette changes and GPU recovery. Palette controls are not application-mode or content approval; software correctness is not physical-device performance acceptance.

Recovery selects the retained legacy manifest by running the ordinary build without the native selection environment variables. Original grids, source geometry, release/certificate records, identities and prepared content are retained. This is an offline recovery path; a hosting rollback has not been performed or authorized by these checks.

## Limits before delivery

Cold changed-geography preparation remains slow and whole-process memory measurements vary substantially. Incremental source authentication limits each serialization buffer to one feature; it does not bound total geometry or grid memory. Original geographic approval/certificates retain their existing meaning. Independent exact-head review, bounded evidence packaging, normal queue checks and a separately authorized verified delivery are required. No live facts were read back or mutated in this offline validation. Genuine source gaps and uncertain physical-water questions remain open for the global source audit and coordinated factual repairs.
