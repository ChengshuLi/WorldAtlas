# Map building

The builder uses raw coastline and inland-water files from R2 to mark each map cell as land or water. It then uses rules from Neon to assign each cell to a geographic entity. The finished map encodes both the owner and the cell type. [Release packaging](../map_releases/README.md)

## Use

Set up the project environment, the working Neon connection and R2 credentials. Run this from the repository root. [Environment and credentials](../../../README.md#pipeline-code)

```bash
mkdir -p /absolute/path/to/worldatlas-work/runs
worldatlas-build \
  src/worldatlas/map_build/config.json \
  /absolute/path/to/worldatlas-work/runs/preview \
  --work-dir /absolute/path/to/worldatlas-work
```

Supply `--work-dir` and an output directory for every build. The builder creates the work directory if needed and shares its `inputs/` cache across runs. Choose a new output directory inside the workspace for a fresh run and the existing run directory when resuming. Open the finished run’s `report.json` for the map file paths and timings.

| Option | When to use it |
| --- | --- |
| `--divide PARENT_ID` | Optional. By default, divide every parent with rules in the saved selection. Supply a parent entity ID to run only its division and the ancestor divisions it needs. For example, `--divide 0` divides World into continents. Repeat the option to select several parents. |
| `--reuse-from PREVIOUS_RUN` | Start a new build using the physical grid from an earlier local run. The grid and physical inputs must match. By default, the builder tries to reuse all compatible geographic assignments. It checks each complete parent division first and can reuse the land assignments alone if only the water rules changed. |
| `--recompute-division` | Off by default. Use with `--reuse-from` to reuse only the physical grid and recalculate the requested land and water assignments. |
| `--resume` | Continue an interrupted build using its saved selection and options. Pass the original config, output directory, and `--work-dir`. Omit `--selection`, `--divide`, `--compare-release`, `--reuse-from`, and `--recompute-division`. |
| `--selection INPUT_SELECTION.json` | Start a fresh build with a saved geographic selection. To rebuild a release, use its restored configuration, selection and captured code. |
| `--compare-release VERSION_OR_RC` | Compare every cell with an official release or numbered candidate on the same grid. This needs Neon and R2 access. |

To run a restored copy of the builder directly, use `python -m worldatlas.map_build.build` from the archive’s `src` directory in its recorded environment. [Restore a release for rebuilding](../map_releases/README.md#restore-inputs)

## How it works

### Inputs

#### Physical grid

The build configuration sets the grid, physical inputs, coastal distance and processing options. The checked-in grid has 131,072 columns and 54,613 rows. The east and west edges meet at the antimeridian. [Build configuration](config.json)

- `sources.land_config` selects the coastline dataset and the files to read inside its ZIP archive.
- `sources.inland_water.files` lists the raw water files for the selected dataset release. Catalog references supply `size_bytes` from Neon. Direct R2 references must supply it alongside the bucket, key, and SHA-256.
- `sources.inland_water.rasterization` sets which water features to include and how to draw them on the grid.

Set `r2_source` to the raw file’s Neon catalog ID, such as `"r2_source": "osm-land-polygons-split-4326"`. For a ZIP member, put the source ID inside its `archive` entry. The catalog gives the builder the R2 location, expected size and checksum. The builder checks the bytes before using them. `physical_controls.source_staging` supplies the R2 endpoint.

`physical_controls.max_parallel_shards` sets how many water files can be in progress at once. With R2, two workers let one download run while the other file rasterizes. `division_workers` sets how many independent rules within a group can run at once.

#### Geographic assignments

Source imports save the coordinates of boundaries, areas and reference points in Neon. The builder reads the coordinates, rules, entity hierarchy, map codes and source records in one read-only transaction, so they all come from the same snapshot. It closes the transaction before downloading files or processing the grid and saves the selected records in `input-selection.json`. [Source imports](../source_imports/README.md) · [Input selection code](inputs/selection.py)

### From source files to cells

| Stage | Reads | Produces |
| --- | --- | --- |
| Prepare | Build configuration and working Neon records or a saved selection | Saved geography and the resolved sources and settings for the physical build. |
| Build the physical grid | Coastline polygons, inland-water polygons and grid settings | A land/water grid. A cell is land if it falls inside the coastline mask and outside the inland-water mask. |
| Divide each parent | The land/water grid, the parent’s cells and its rules | An entity ID for each cell, using the most detailed division that was built. |
| Encode | The owner and cell type for each cell | Final map codes and the number of cells using each code. |
| Verify and compare | Final map files, input checksums and an optional reference map | The run report and, when requested, the locations and counts of changed cells. |

### Dividing the hierarchy

The builder processes parents before their children. It starts with the whole grid for World → continents. If Asia has a selected subdivision, the builder then runs the same process on just the cells assigned to Asia. A subcontinent can be divided in turn using its own cells and rules. Each division replaces only the assignments within that parent’s territory. [Hierarchy code](division/hierarchy.py)

### Inside one parent division

Each parent supplies its own rules. The builder uses the same step order for every parent and skips steps with no applicable rules.

- **Choose where the rule applies.** A `scope_area` polygon defines an area. A `scope_component` point selects the connected land or water component that contains it. The rule combines all its selectors. With no selectors, it uses the whole parent.
- **Choose how to assign the territory.** `assign_area` gives the selected territory to one child. `divide_area` cuts the scope into pieces using boundary lines. A label point in each piece identifies the child that owns it.
- **Choose the unit.** A cell-based rule can split an island. A component-based area rule selects an entire island when the polygon covers more than half its cells. A component-based division gives the whole island to the child whose labelled piece contains more than half its cells. The build raises an error if an eligible component has no majority.
- **Filter the cells the rule can claim.** `physical_class` limits claims to land, water or both. `unassigned_only` limits claims to cells still without an owner when that step begins.

| Order | Rule operations | Calculation |
| --- | --- | --- |
| 1 | Explicit `assign_area` and `divide_area` | Apply area and boundary rules. Area rules name one child. Boundary rules cut the scope and use points to label the resulting faces. |
| 2 | Land or mixed `assign_area` and `divide_area` with `unassigned_only` | Fill unassigned cells within each rule’s scope. |
| 3 | `nearest_land` | Assign each remaining land component to the owner of the nearest reference shore. Reference points identify which components supply those shores. Check that every land cell has an owner. |
| 4 | `nearest_coastal_water` and `nearest_basin_water` | Assign coastal water to its nearest eligible shore within the configured limit of 22,224 m. For a named basin, use only the shores of owners that border it. Both operations use the same land assignments. |
| 5 | Water `assign_area` and `divide_area` with `unassigned_only` | Use polygons or boundary lines to assign remaining water. At World, the four ocean rules claim water inside S-130 polygons that connects through remaining water to a rule’s `connected_to` point. |
| 6 | `nearest_water` | Assign any remaining water in the rule’s scope to the owner of the nearest eligible shore. At World, this fills the pockets left by the ocean rules. Check that every cell in the parent has an owner. |

Rules within a step can run in parallel because they all read the same starting assignments. The builder merges their claims before the next step. If two rules claim the same cell, they must agree on its owner. The builder also checks that the owner can contain that cell’s physical class.

A shore cell is a land cell that shares an edge with a water cell. The builder measures WGS84 distances between cell centres. The smaller distance wins. Exact ties follow map-code order. [Division guide](division/README.md) · [Water guide](water/README.md)

#### Which steps carry over to finer divisions?

- **Step 1. Explicit areas and boundaries.** Use direct area assignments or boundary lines wherever the geography defines which child owns an area. If these rules cover the entire parent, step 1 can do all the assignment.
- **Step 2. Fill land or mixed gaps.** Use an area or boundary rule to fill gaps within its scope while preserving assignments from step 1. For example, a district polygon can fill gaps even where it overlaps a more precise boundary rule.
- **Step 3. Nearest land.** Use this when whole land components still need an owner and the parent supplies reference shores for the distance check.
- **Step 4. Coastal and basin water.** Use shore ownership when it should determine the assignment of nearby water or a named basin. The basin can be inland, such as a lake with shores in several children.
- **Step 5. Water areas and boundaries.** Use an explicit polygon or boundary line for water that still needs an owner. The four S-130 ocean assignments are specific to World → continents. The same operation could divide a water-only parent such as the Pacific Ocean.
- **Step 6. Remaining water by shore.** Use the nearest eligible shore for water that remains unassigned. Skip this step when the earlier rules cover all water or the parent contains only land.

### Reading the output

Within each row, the builder groups consecutive cells with the same value into stretches called *runs*. A row with three land cells followed by two water cells has two runs.

- `runs.u32le` stores the stretches. Each entry gives the first column **after** the stretch and the value of the cells in it. In the example, `(3, 17)` means land (code 17) in columns 0 through 2. Then `(5, 1)` means water (code 1) in columns 3 and 4.
- `rows.u32le` tells the builder where each row's stretches begin and end in `runs.u32le`. The builder can jump straight to the row it needs.

Each layer has its own pair of files. The physical grid stores land or water. The ownership grid stores the IDs of World’s descendants and uses zero for unassigned cells. World itself has entity ID zero in Neon and serves as the starting territory for the division. The final map uses a number for each combination of owner and cell type. For example, Asia’s land and water have different map codes.

| File or directory | Purpose |
| --- | --- |
| `build-config.json` | Preserves the settings passed to the builder for inspection after the original configuration changes. |
| `input-selection.json` | Preserves the rules, geometry and catalog entries for resume and replay without rereading working records in Neon. |
| `run-identity.json` | Records the options and input checksums required to resume the same run. |
| `physical-build-config.json` | Holds the coastline settings, inland-water settings, and water file list with their checksums. The physical runner can use this request on its own. |
| `physical/` | Keeps the coastline mask, inland-water masks and combined physical grid so rasterization can resume and later builds can reuse the grid. |
| `division/parent-{ID}/` | Keeps calculations together for each parent. For example, World uses `division/parent-0/`. |
| `division/parent-{ID}/result.json` | Records where the parent’s ownership grid lives so the builder can resume after a completed division. A reused result can point to an earlier run. |
| `final/` | The finished map grid, encoded as map codes. |
| `final/report.json` | Counts the cells using each map code. Release staging uses the counts to check coverage and build the legend. |
| `report.json` | Marks the run complete and records final file paths, checksums and stage timings. Its `physical_directory` field locates the physical grid, including a grid reused from an earlier run. |
| `comparison/` | Changed cells and assignment totals when comparing two grids with matching dimensions. With both category mappings, the builder compares entity and cell type. With bare map files, it compares numeric codes. |
| `attempts/` | Records the code and runtime for each run attempt. Release staging uses these records to package the code needed for replay. |
| `checkpoints/` | Records inputs and outputs for completed steps so resume can verify and reuse them. |
| `checkpoints/{STEP}/attempt-{ID}/error.log` | The traceback for a failed step, kept beside that attempt’s checkpoint. |
| `timing-events.jsonl` | Keeps timing events as work runs so totals can be reconstructed after an interruption. |
| `failure.json` | Summarizes progress and timing when the builder catches an error or interruption. |
| `preserved/` | Holds files moved aside before a retry, for debugging only. Resume ignores this directory. |
| `run.lock` | Prevents two builders from writing to the same run at once. |
| `physical.lock` | Protects physical output from concurrent writers, including calls to the standalone physical command. |

**Timing.** If two rules run during the same ten seconds, those ten seconds count once toward the stage total. The report lists download time separately and counts only time while the build is running. If the build stops before recording when a task ended, the report gives the minimum time it can account for.

**Code snapshots.** Each attempt saves its WorldAtlas code and setup files in `attempts/{ATTEMPT_ID}/source-code.json.gz`. Its `producer.json` records the checksum. If you edit the code between attempts, resume can reuse verified outputs from the old code and run the unfinished steps with the new code. Release staging keeps each snapshot. [Archived code](../map_releases/README.md#archived-code)

**Stopping and resuming.** Press Ctrl+C to stop a build. Continue from verified checkpoints with the `--resume` command described above. If a rule fails, the builder cancels queued rules in that group and asks running rules to stop between batches.

## GDAL and release replays

New builds use the GDAL and PROJ packages from Conda Forge in the project environment. Python loads the GDAL library from that environment, and PROJ uses the data installed there. Reusing a verified physical grid skips rasterization. [Project environment](../../../environment.yml)

To reproduce an existing release byte for byte, follow the map-building instructions in its restored source archive. V8.3 uses GDAL 3.10.3 compiled with `-ffp-contract=off`. Different builds of the same GDAL version can round polygon edges differently. [Restore a release](../map_releases/README.md#restore-inputs)

## Code and tests

### Where to start

Start with `build.py`. Its `main()` reads the command options, and `Pipeline.run()` runs the build from input files to finished map. [Build entry point](build.py)

| Code | What it does |
| --- | --- |
| [`inputs/`](inputs/README.md) | Reads rules, coordinates and source records from Neon. Also looks up a release chosen for comparison. |
| [`physical/`](physical/README.md) | Turns coastline and inland-water polygons into the land/water grid. |
| [`division/hierarchy.py`](division/hierarchy.py) | Chooses which parents to divide, starting at World. Reuses earlier divisions when their inputs match. |
| [`division/`](division/README.md) | Runs the rules for one parent, merges the assignments and checks that each cell has an owner. |
| [`land/`](land/README.md) | Finds connected pieces of land and supplies the tools for assigning islands by distance. |
| [`water/`](water/README.md) | Finds shores and identifies which land owners border a basin. |
| [`division/encoding.py`](division/encoding.py) | Combines ownership and land/water to write the final map codes. |
| [`core/comparison.py`](core/comparison.py) | Compares every cell in two finished maps and records the locations and counts of changed assignments. |
| [`core/`](core/) | Shared code for cell coordinates, shapes and row-run files. |
| [`execution/`](execution/) | Saves progress for resume, records timing and captures the code used for each attempt. |
| [`worldatlas/shared/files.py`](../shared/files.py) | Reads, verifies and writes local files for map building and release staging. |

### Run the tests

Set up the PostgreSQL tools and the `pg_jsonschema` extension once. Then run this from the repository root in the project environment. [Database test setup](../../../database/README.md#tests)

```bash
python .github/scripts/run_tests.py --suite map_build
```

The runner starts and stops its own temporary PostgreSQL server. The tests use small local files and need no cloud credentials.

- The end-to-end test builds a small map from source files and checks the final assignments. [`test_end_to_end.py`](test_end_to_end.py)
- The resume tests verify that the builder reuses completed work and rejects changed inputs or outputs. [`test_resume.py`](test_resume.py)
- Tests beside the code check individual operations, such as cutting along a boundary, detecting conflicting assignments and finding the nearest shore.
