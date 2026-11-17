# Build a map

The pipeline reads a saved selection of geographic records, creates the current
grid and writes a versioned map. Building does not publish the website.

## Run

Use the project environment on macOS or Linux. Set `NEON_DATABASE_URL` to the
working database and provide R2 credentials through the normal boto3 credential
chain, for example `AWS_PROFILE=worldatlas-r2`. Credentials stay outside code and
configuration.

```bash
worldatlas-build \
  src/worldatlas/map_build/config.json \
  /absolute/path/to/worldatlas-work/runs/preview \
  --work-dir /absolute/path/to/worldatlas-work
```

Create the `runs/` parent directory first. The work directory holds the reusable
`inputs/` cache; each build has its own output directory.

For identical physical inputs, add
`--reuse-from /absolute/path/to/previous-run`. The pipeline verifies the
physical grid and can reuse its aligned northern rows when the selected grid is
shorter. It also reuses a parent division when its geometry, membership,
bindings and physical inputs match. A water-only edit can reuse that parent's
verified land assignments. A descendant edit can reuse its unchanged ancestors.

### Exact physical rasterization

The project environment provides GDAL 3.10.3, its Python bindings and PROJ 9.6.0.
For byte-identical physical rasterization, build that GDAL library with
`-ffp-contract=off`. A stock prebuilt library may round a raster boundary
differently. Install CMake 3.16 or newer, a C/C++ compiler and Git separately;
they are setup tools, not pipeline runtime dependencies. Then run once inside the project
environment, choosing an absolute work directory:

```bash
export WORLDATLAS_WORK=/absolute/path/to/worldatlas-work
mkdir -p "$WORLDATLAS_WORK/runtime"
git clone --depth 1 --branch v3.10.3 https://github.com/OSGeo/gdal.git \
  "$WORLDATLAS_WORK/runtime/gdal-source"
cmake -S "$WORLDATLAS_WORK/runtime/gdal-source" \
  -B "$WORLDATLAS_WORK/runtime/gdal-build" \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$CONDA_PREFIX" \
  -DCMAKE_INSTALL_PREFIX="$CONDA_PREFIX" -DCMAKE_INSTALL_LIBDIR=lib \
  -DCMAKE_INSTALL_RPATH="$CONDA_PREFIX/lib" \
  -DCMAKE_C_FLAGS=-ffp-contract=off -DCMAKE_CXX_FLAGS=-ffp-contract=off \
  -DBUILD_TESTING=OFF -DBUILD_APPS=OFF \
  -DBUILD_PYTHON_BINDINGS=OFF -DBUILD_JAVA_BINDINGS=OFF -DBUILD_CSHARP_BINDINGS=OFF
cmake --build "$WORLDATLAS_WORK/runtime/gdal-build" --parallel
cmake --install "$WORLDATLAS_WORK/runtime/gdal-build"
python3 -c 'from osgeo import gdal; print(gdal.VersionInfo("RELEASE_NAME"))'
```

This replaces the environment's native GDAL library; its existing Python
bindings use the same ABI. Do not point `DYLD_LIBRARY_PATH`, `LD_LIBRARY_PATH`,
or `PROJ_DATA` at a different installation. Reinstalling the Conda GDAL package
replaces this custom build. See the [GDAL build guide](https://gdal.org/en/stable/development/building_from_source.html).
Use `--reuse-from` to reuse verified physical outputs.

## Inputs and stages

The pipeline reads working hierarchy, rules, features and source records in one
repeatable-read, read-only transaction. It freezes geometry, construction settings,
entity bindings/colors and raw catalog records, then closes the transaction before
computation. Workers edit records by their IDs; the build needs no revision labels.

Use `--selection /absolute/path/to/input-selection.json` to replay a saved
selection. Resume uses the run's saved selection rather than rereading Neon.
Source IDs resolve through `atlas.source_assets`; downloads
are checked against the catalog's byte sizes and SHA-256 checksums.

The three physical inputs are `land_config`, `water_config` and `raw_manifest`.
They select the global coastline polygons and complete inland-water shard set.
They may contain inline JSON, local file pins, cataloged R2 references or selected
archive members. The endpoint is in `physical_controls.source_staging`.

Use repeatable `--divide PARENT_ID` to select divisions; necessary ancestors are
included. The default evaluates all parents with selected subdivision rules.

The calculation is:

1. **Physical:** rasterize coastline and inland-water sources into the one grid
   selected in build configuration, then compose the physical land/water mask.
2. **Land:** evaluate explicit area and boundary divisions together, rejecting
   disagreeing claims. Assign remaining components to the nearest selected
   reference shores. Every eligible land cell must have a child owner.
3. **Water:** extract physical shores once and attach final land owners. Coastal
   and complete named-basin claims use the same ownership snapshot and must
   agree wherever they overlap. Basin participants come from actual shores
   beside the original full basin. The ocean rules assign residual water
   inside their source polygons and connected open-water components. Nearest
   eligible shore completes the remaining cells.
4. **Package and comparison:** encode entity/physical-class pairs through the
   selected category bindings. Optionally compare with `--compare-release` or
   explicit reference streams, reporting removed grid rows separately.

All geographic operations share the same parent and scope contract. A rule's
`unassigned_only` setting filters its output scope once; it never changes
component populations, geometric faces or reference shores. Independent rules
in one group read the same snapshot, so execution order cannot hide conflicts.

The six operations and their preparation are documented in
[division](division/README.md). The coastal distance is the single
`coastal_band_metres` setting in build configuration. Strictly smaller computed
WGS84 distances win; exact equality follows category-code order.

Geographic features are imported beforehand through the supported
[source imports](../source_imports/README.md). Map building reads their saved
geometry rather than reopening those source archives. Large global physical
sources feed rasterization directly.

Implementation details are beside the code:
[physical](physical/README.md), [land](land/README.md),
[water](water/README.md) and [input selection](inputs/README.md).

## Outputs, resume and timing

`report.json` appears after the requested calculation and comparison succeed. It
points to the final streams and producer report; follow those paths rather than
assuming a fixed output subdirectory. Generated requests are in `configs/`;
phase receipts and failed attempts are retained under the run directory.

Continue an interrupted run with the same configuration and `--resume`. The
pipeline checks the actual saved inputs, grid and completed outputs. Code changes
are recorded as provenance and do not prevent reuse of compatible data.

Checkpoints retain completed physical units, parent components, individual rule
outputs, consolidated ownership and encoding.
A producer with its own partial checkpoints can resume those units. Other partial
outputs are preserved before that phase restarts.

`timing-events.jsonl` records start and completion events for stages, rules and
checkpointed work. `report.json` summarizes stage wall time. Overlapping rule
times count once in the stage total. Downloads are reported separately. When
reusing physical data, the run records its own verification time.

Durations never subtract clocks from different attempts. Downtime between
attempts is excluded. If an abrupt interruption loses a completion event, the
report marks the affected timing incomplete and retains a measured lower bound;
it does not invent the missing duration. Run checkpoints and timing survive only
while their local files are retained.

Release staging and publication are separate from cell generation. Keep the
published release fixed while reviewing a numbered candidate. Publish only after
the user approves that candidate.

## Package layout

- `inputs/`: freeze the selected Neon records and validate imported geometry.
- `core/`: grid coordinates, wrapping, row-run streams and WGS84 geometry.
- `physical/`: rasterize global coastline and inland-water inputs.
- `land/`: connected components and complete component-distance searches.
- `water/`: physical shores, basin participants and exact distance certificates.
- `division/`: shared scopes, six rule operations and ownership consolidation.
- `execution/`: phase checkpoints, cancellation and durable timing.
- `review/`: generate basin comparison images from completed map grids.

These folders are inside `map_build/`; tests live beside their corresponding
code. Release commands live separately in [map-releases](../map_releases/README.md).

## Source capture

Each build attempt saves its actual package sources and setup files in
`attempts/ATTEMPT_ID/source-code.json.gz`. Its producer record pins that archive.
Keep the code unchanged while an attempt runs; resume captures the code for the
new attempt and preserves earlier snapshots. Release staging includes these bytes
in the [release input archive](../map_releases/README.md#archived-code), so later
Git cleanup or squash merging cannot remove them. Older attempts without captured
source files remain identifiable by their existing provenance; their code is not
invented from today's checkout.
