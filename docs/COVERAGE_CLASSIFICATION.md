# Physical-reference classification

The classification is an independent diagnostic on the fixed canonical grid. It never changes a location ID, administrative boundary, political affiliation, historical fact or release. Natural Earth 1:10m land supports class 1; its major lake/reservoir polygons override land with class 2. Remaining cells are unknown, including tiles blocked by invalid original water shapes. Ocean background alone is not a water certificate.

An unassigned location cell with class 1 displays an orange/pale hatch and explains a **possible geographic coverage gap**. Smaller rivers/lakes, shorelines and source-vintage differences remain uncertain. Class 2 explains reference water. Missing, stale or corrupt products fall back to “No mapped location; water or geographic coverage is not verified.” Mapped locations take precedence in both GPU and Canvas. Click explanations include coordinates and physical-source links; these modern references do not change with the selected historical year.

Prepare the product offline from immutable Git inputs with the pinned Python requirements:

```sh
python3 scripts/prepare-coverage-classification.py --geography-commit EXACT_MAIN_COMMIT --out data/coverage-classification
```

The output directory must be absent. Preserve an existing product/evidence vintage before preparing a replacement. The optional `--water-commit` defaults to the selected geography commit, which must contain the retained original lake source and its receipt; source receipts verify the original bytes. A separately pinned source commit can be supplied when needed. The generator uses sparse row intervals and half-open cell-center sampling rather than a dense world bitmap. Water takes priority over land; blocked tiles take priority over both. It preserves polygon holes and the non-Antarctic declared domain. No invalid reference is silently repaired. Output timestamps and runtime diagnostics are excluded from product bytes, permitting deterministic reproduction.

The manifest pins the geographic release, footprints, hierarchy and exact canonical-grid manifest. Static packaging validates every compressed/decoded part and run before copying it. Hosted packaging also compresses the existing recovery receipt losslessly; the versioned ownership delivery manifest records its original and transport hashes, and verifies decoded equality. Original preparation/source bytes remain unchanged in the repository; portable exports retain them directly. The browser bounds allocations, transport/decompression and concurrency, verifies the same pins and hashes, and rejects invalid classes/overlapping runs. GPU textures and the Canvas worker receive classification separately from ownership; navigation/styles do not compile or upload additional ownership.

Run the classification and isolated renderer controls:

```sh
node --test test/coverage-classification.test.mjs test/coverage-browser.test.mjs test/pixel-ownership.test.mjs
```

These checks prove the implementation contract, not complete hydrological accuracy. See `GEOGRAPHIC_GAP_AUDIT.md` for the global candidate inventory. Detailed water evidence and source-backed coordinated administrative repairs remain necessary before closing confirmed geography defects. Issue #920 separately tracks the differential integration gate and actionable repair reports. This rendering change does not install that gate or fix boundary geometry. Deployment is deferred at the user's request.

## Observe selected ownership, without source geometry

For “which selected product owns this original queue package?”, use only the bounded reader:

```sh
GIT_NO_LAZY_FETCH=1 GIT_NO_REPLACE_OBJECTS=1 \
  node scripts/observe-selected-owners.mjs --repo . --commit EXACT_DATA_COMMIT \
  --package gb-TUV-ADM1--repair-evaluation --out /path/to/new-observation.json
```

Use the exact package ID from the original `global-current-cell-work-queue-20261014`
queue. The existing extractor derives every original key from its pinned metadata
and package blocks. There is no arbitrary keys file, reduced-subset or certificate
option. Unknown packages and incomplete census counts fail before reading native
row/run bodies. The output parent must already exist without symlinks; an existing output
is never replaced. Use the committed reader in an owned checkout. The explicit
40-character data commit may differ from that checkout's HEAD: no checkout switch,
reset or ad hoc script copy is required. Executed source must match the checkout's
own committed code. The artifact records both revisions, the exact ordered key
digest, selected product pins, normative latitude bytes and actual consumed inputs.
`original_intervals` retains the exact block/row table bound by `original_intervals_sha256`;
its columns are the original package's `execution.output_columns` (end is exclusive).
Use its recorded owner/source-feature indices and original mask class directly, rather
than reconstructing them or replacing them with null. These are original queue observations,
not current physical or source qualification.
Use a Git implementation accepting `git --no-lazy-fetch --version`; a missing
required blob stops rather than fetching geometry or changing the reader's rules.

This replaces the separately transferred owner-example, latitude-companion and
package-specific finalizer recipes. It reads the selected retained additive product,
original package queue metadata/interval blocks, complete native row table, only the
needed run members, full patch, original
id/index roster and pinned normative latitudes. It never constructs a geometry
resolver, reads a source qualification certificate or offers a full-geometry mode.
Base and additive owners remain separate; overlap returns a null effective owner,
not invented precedence. Zero means no selected owner, not proof of physical water.
Current province/parent metadata is not inferred from the original owner roster.

The output kind is `literal-selected-owner-observation-v1`, explicitly not scientific
qualification. Its key count covers exactly that original queue package, not a larger campaign
or proof that the source qualifies. Full source-based residual work still uses the
retained original evidence, not the supported-only subset: `supported-inputs` already preserves
`original-scope-partition.json` → `original_inputs.source_evidence` and the exact
supported/held partition. A selected-base certificate is not package-specific source
or repair authority. The existing source/native qualification consumers continue to
require their own actual complete inputs; an observation cannot substitute for them.

## Diagnose source lineage and physical coverage

Use the distinct diagnostic below only to ask what the source geometries and
physical evidence say, not merely to look up ownership. It intentionally reads the
complete selected source roster and compares source membership. That necessary
scientific operation remains separate from the bounded observation above; neither
command installs a UI feature or changes geometry.

```sh
node scripts/diagnose-map-cell.mjs --repo . --commit EXACT_MAIN_COMMIT \
  --cell 126031,99379 --coordinate -87.979,47.727
```

Repeat `--cell X,Y` or `--coordinate LON,LAT` to inspect multiple points. Coordinates select
a canonical cell; all membership tests use its center and the pinned native
latitude bytes, never regenerated inverse-projection latitudes. Output goes to
stdout. The command reads immutable Git inputs, including sparse-checkout inputs.
Use a current checkout for the executable reader and an exact revision for data.

Optional repeated `--original`, `--consumed`, and `--physical` arguments name
existing committed GeoJSON files (plain or gzip). They do not create a new evidence
format or approval layer. Source joins use exact feature IDs, or geoBoundaries
`shapeGroup`/`shapeType`/`shapeID`, never proximity or matching names. A byte match
to retained administrative-source metadata carries its reference year; otherwise
missing source dates remain unknown. GeoJSON `date`/`metadata.date`, feature
`metadata.reference_year`/`source_timestamp`/`timestamp`/`date`, and collection
`coverage` are retained when present. An omitted upstream collection is an unknown
stage, not evidence that the original source missed the cell.

Physical GeoJSON must carry explicit physical semantics: OSM `natural=water`,
`waterway=riverbank`, `landuse=reservoir`, or Natural Earth lake/reservoir feature
classes identify mapped water. `physical_class=land` with `excludes_water=true`
describes an already-reconciled physical land mask whose mapped waters were
excluded. This is the source's known coverage, not proof that every unmapped small
water body is absent. Administrative polygons must never receive those labels.
For nested sources such as GSHHG, use the existing decoder and complete L1–L4
support masks, not a bare lake polygon that paints over lake islands. Periodic
source frames require their source decoder; this reader never clamps or wraps
out-of-domain longitudes. Source hashes, dates and known scope accompany results.

The default physical context remains the coarse Natural Earth product. Its
projected-edge classification is reported separately from native membership and
is never promoted to high-resolution truth. Water additionally requires a matching
explicit retained lake feature under the native rule. Source vintage and whether
the historical classification pins match the current selection are shown.

`diagnoseMapCell` in `src/map-cell-diagnosis.js` is a small reusable interpreter
for measured evidence. It returns **independent** `physical_status` and
`location_status`, plus `current_owner`, a source-supported `intended_location`,
and concrete ownership blockers. Existing design issues [#528](https://github.com/ChengshuLi/WorldAtlas/issues/528)
and [#534](https://github.com/ChengshuLi/WorldAtlas/issues/534) keep rivers/lakes as
separate features: physical water does not imply owner zero, a permanent territorial
exclusion, a proximity buffer, or a new hierarchy. This diagnostic specifies no
click precedence.

A positive water feature remains water-supported even when a coarser land mask
misses it; both source dates and the physical-source disagreement remain explicit.
Territorial membership is resolved independently by exact source identity joins.
One supported source location can coexist with water. Missing or competing source
locations, a source-vintage ownership conflict, an unexplained selected polygon
hole, or a native/selection mismatch stays unresolved. A hole needs its own
territorial/semantic evidence; water alone cannot explain why ownership is absent.
Exact boundary incidences are reported and use the existing native/source-defined
sampling rule; they do not invent a proximity buffer or an automatic owner-zero rule.
Already-assigned cells report current ownership without claiming it is
independently correct. Proposed additions still need actual physical source
coverage and exact source membership; absence of a known water feature is not
land evidence. The supporting lineage reports each joined source ID separately,
so an overlapping feature cannot hide another feature's loss. Feature-specific
dates take precedence over collection dates. No result replaces the repair path's
existing-owner conservation and territorial-semantics checks.

Run `node --test test/map-cell-diagnosis.test.mjs` for small independent numerical
and interpretation controls. Real-current-cell runs and source-specific held-out
findings belong in the linked PR/issue, not a second diagnostic registry.
