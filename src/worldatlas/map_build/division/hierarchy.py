"""Apply the same parent division recursively, reusing verified unchanged outputs."""

import hashlib
from collections.abc import Callable, Iterator
from functools import partial
from pathlib import Path
from typing import Any

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import write_layer, write_run_rows
from worldatlas.map_build.core.rle import complete_row, open_grid, overlay, row
from worldatlas.map_build.division.contracts import CompiledDivision
from worldatlas.map_build.division.engine import ParentDivision, land_groups
from worldatlas.map_build.division.intervals import spans
from worldatlas.map_build.division.shores import ShoreGeometry, land_owner_order
from worldatlas.map_build.execution.control import check_cancelled
from worldatlas.map_build.execution.runtime import Checkpoints, RunFilePins
from worldatlas.map_build.execution.timing import Timing
from worldatlas.map_build.inputs.selection_types import GeographicSelection
from worldatlas.shared.files import (
    FilePin,
    JSONValue,
    json_bytes,
    read_json,
    write_bytes_atomic,
    write_json,
)


def parent_division_reuse_inputs(
    geography: GeographicSelection,
    parent: int,
    grid: Grid,
    physical: Path | str,
    membership: Path | str | None,
    configuration: dict[str, Any],
    *,
    compiled: CompiledDivision,
    files: RunFilePins,
    land_only: bool = False,
) -> dict[str, Any]:
    """Collect the inputs that must match to reuse a parent's subdivision.

    Args:
        geography: Frozen entities, rules, features and bindings.
        parent: Entity to divide.
        grid: Grid used by this parent.
        physical: Directory with the physical row-run grid.
        membership: Directory marking the parent's cells, or None for the whole
            grid.
        configuration: Build settings used by the selected rules.
        compiled: This parent's child entities and assembled rules.
        files: Attempt-local file checksum verifier.
        land_only: Whether to record the land calculation separately.

    Returns:
        Dictionary of operative rule settings, geometry, binding order
        and input file checksums. A wording or color edit leaves it unchanged.
    """
    children, rules = compiled.children_by_id, compiled.rules
    if land_only:
        rules = [rule for _, group in land_groups(rules) for rule in group]
    result = dict(
        parent_id=parent,
        grid=vars(grid),
        children=[
            dict(id=e["id"], physical_class=e["physical_class"])
            for _, e in sorted(children.items())
        ],
        rules=rules,
        land_owner_order=land_owner_order(geography, children),
        physical={
            Path(pin["path"]).name: pin["sha256"] for pin in files.row_streams(physical)
        },
        membership=None
        if membership is None
        else {
            Path(pin["path"]).name: pin["sha256"]
            for pin in files.row_streams(membership)
        },
    )
    if any(r["operation"] == "nearest_coastal_water" for r in rules):
        result["coastal_band_metres"] = configuration["coastal_band_metres"]
    return result


def write_parent_membership_mask(
    grid: Grid,
    ownership_directory: Path | str,
    parent_id: int,
    output_directory: Path | str,
    row_range: range,
) -> dict[str, Any]:
    """Write a mask of the cells owned by one parent.

    Args:
        grid: Dimensions of the ownership grid.
        ownership_directory: Folder with the immediate ancestor's subdivision.
        parent_id: Owner ID of the parent about to be divided.
        output_directory: New folder for the mask's row-run files and report.
        row_range: Rows with possible assignments in the ancestor result.

    Returns:
        Row-run layer report for the parent's membership mask.
    """
    with open_grid(ownership_directory, grid) as owners:

        def rows() -> Iterator[tuple[int, list[tuple[int, int, int]]]]:
            """Find the intervals owned by the parent in each row.

            Yields:
                (row, spans) with value 1 for cells owned by the parent.
            """
            for y in row_range:
                check_cancelled()
                ends, values = row(owners, y, grid.width)
                records = spans(
                    np.r_[0, ends[:-1]], ends, (values == parent_id).astype(np.uint32)
                )
                if records:
                    yield y, records

        return write_layer(output_directory, grid, rows())


def assigned_rows(report: Path) -> range:
    """Read the half-open range of rows with owners from a layer report.

    Args:
        report: Pinned report written alongside a layer's row-run files.

    Returns:
        Global row indices that may contain assignments. An empty layer gives
        an empty range.
    """
    bounds = read_json(report)["assigned_bounds"]
    return range(0) if bounds is None else range(bounds[2], bounds[3])


def assemble_ownership(
    grid: Grid,
    world: Path,
    local_results: dict[int, Path],
    compiled: dict[int, CompiledDivision],
    directory: Path,
) -> dict[str, Any]:
    """Combine direct subdivisions into one grid of the deepest assigned owners.

    Args:
        grid: Dimensions shared by all layer files.
        world: World division output, covering every grid cell.
        local_results: Non-root subdivision output directories keyed by parent.
        compiled: Selected divisions in ancestor-first order.
        directory: New directory for the assembled row-run files.

    Returns:
        Layer report with final run count, assigned bounds and owner counts.

    Raises:
        ValueError: A local result contains the wrong owners or its cells
            differ from the exact set previously assigned to its parent.
    """
    depths = {child: 1 for child in compiled[0].children_by_id}
    parents_by_depth: dict[int, list[int]] = {}
    parent_by_child: dict[int, int] = {}
    for parent in local_results:
        depth = depths[parent]
        parents_by_depth.setdefault(depth, []).append(parent)
        for child in compiled[parent].children_by_id:
            depths[child] = depth + 1
            parent_by_child[child] = parent

    results = sorted(
        (bounds.start, bounds.stop, parent)
        for parent, path in local_results.items()
        if (bounds := assigned_rows(path / "report.json"))
    )

    def combined_rows() -> Iterator[tuple[int, np.ndarray, np.ndarray]]:
        """Read local results in row blocks and apply each level in order.

        Yields:
            (row index, exclusive run ends, owner IDs) for each complete row.
        """
        with open_grid(world, grid) as root:
            active: list[tuple[int, int, int]] = []
            next_result = 0
            for first in range(0, grid.height, 256):
                check_cancelled()
                stop = min(first + 256, grid.height)
                active = [result for result in active if result[1] > first]
                while next_result < len(results) and results[next_result][0] < stop:
                    active.append(results[next_result])
                    next_result += 1

                # Read one parent at a time so wide layers and many siblings
                # do not require keeping all their files open at once.
                patches: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
                for start_row, end_row, parent in active:
                    check_cancelled()
                    with open_grid(local_results[parent], grid) as children:
                        for y in range(max(first, start_row), min(stop, end_row)):
                            ends, owners = row(children, y, grid.width)
                            claims = spans(np.r_[0, ends[:-1]], ends, owners)
                            if any(
                                parent_by_child.get(owner) != parent
                                for _, _, owner in claims
                            ):
                                raise ValueError(
                                    f"division {parent} assigned a non-child"
                                )
                            patches.setdefault((y, depths[parent]), []).extend(claims)

                for y in range(first, stop):
                    ends, owners = row(root, y, grid.width)
                    for depth, parents in parents_by_depth.items():
                        claims = patches.get((y, depth), [])
                        if not claims:
                            if np.any(np.isin(owners, parents)):
                                raise ValueError(
                                    "division leaves exact parent membership incomplete"
                                )
                            continue
                        local = complete_row(grid.width, sorted(claims), minimum_code=1)
                        _, ends, (owners, children) = overlay((ends, owners), local)
                        ids, indices = np.unique(children, return_inverse=True)
                        expected = np.array(
                            [parent_by_child.get(int(child), 0) for child in ids],
                            dtype=np.uint32,
                        )[indices]
                        inside = expected != 0
                        if np.any(inside & (owners != expected)):
                            raise ValueError(
                                "division claims cells outside its exact parent membership"
                            )
                        if np.any(np.isin(owners[~inside], parents)):
                            raise ValueError(
                                "division leaves exact parent membership incomplete"
                            )
                        owners = np.where(inside, children, owners)
                    yield y, ends.astype(np.uint32, copy=False), owners

    return write_run_rows(directory, grid, combined_rows())


class HierarchyDivision:
    """Divide each configured parent after its own owner is known."""

    def __init__(
        self,
        geography: GeographicSelection,
        grid: Grid,
        physical: Path | str,
        directory: Path | str,
        configuration: dict[str, Any],
        *,
        compiled_divisions: dict[int, CompiledDivision],
        checkpoints: Checkpoints,
        timing: Timing,
        reuse: Path | str | None = None,
    ) -> None:
        """Prepare the hierarchy, work directory, and optional reuse settings.

        Args:
            geography: Frozen geographic rules, entities and features.
            grid: The build's physical grid dimensions.
            physical: Directory containing physical row-run files.
            directory: Output directory for division results.
            configuration: Build settings used by the rules.
            compiled_divisions: Child entities and assembled rules keyed by parent ID.
            checkpoints: Checkpoint store for this run.
            timing: Run timer shared by all stages.
            reuse: Directory containing earlier division results.
        """
        self.geography, self.grid, self.physical = geography, grid, Path(physical)
        self.directory = Path(directory)
        self.directory.mkdir(exist_ok=True)
        self.configuration = configuration
        self.checkpoints = checkpoints
        self.timing = timing
        self.files = checkpoints.files
        self.compiled_divisions = compiled_divisions
        self.reuse = (
            {} if reuse is None else read_json(Path(reuse) / "report.json")["parents"]
        )
        self._shores = None

    def shores(self) -> ShoreGeometry:
        """Prepare and cache the grid's physical shore geometry.

        Returns:
            Shore geometry shared by divisions with the same physical grid.
        """
        if self._shores is None:
            with open_grid(self.physical, self.grid) as physical:
                self._shores = ShoreGeometry(physical, self.grid)
        return self._shores

    def task[Result: JSONValue](
        self,
        name: str,
        operation: Callable[[], Result],
        inputs: list[FilePin],
        outputs: list[Path],
    ) -> Result:
        """Run a hierarchy stage and return its calculated or saved result.

        Args:
            name: Checkpoint ID for this stage.
            operation: Function with all its inputs supplied.
            inputs: Pinned input files.
            outputs: Files or directories produced by the stage.

        Returns:
            Calculated or verified saved stage result.
        """
        return self.checkpoints.run_function(
            name,
            "division",
            operation,
            timing=self.timing,
            inputs=inputs,
            outputs=outputs,
        )

    def run(self) -> dict[str, Any]:
        """Divide parents in order and combine the results into one ownership grid.

        Returns:
            Division report with the final layer directory and each parent's
            output and reuse details.
        """
        outputs: dict[int, Path] = {}
        receipts: dict[str, Any] = {}
        entities = {entity["id"]: entity for entity in self.geography["entities"]}
        for parent, compiled in self.compiled_divisions.items():
            directory = self.directory / ("parent-" + str(parent))
            directory.mkdir(exist_ok=True)
            parent_directory = directory / "membership"
            ancestor = entities[parent]["parent_id"]
            if ancestor is not None:
                ancestor_output = outputs[ancestor]
                self.task(
                    "membership-" + str(parent),
                    partial(
                        write_parent_membership_mask,
                        self.grid,
                        ancestor_output,
                        parent,
                        parent_directory,
                        assigned_rows(ancestor_output / "report.json"),
                    ),
                    receipts[str(ancestor)]["outputs"],
                    [parent_directory],
                )
            settings = parent_division_reuse_inputs(
                self.geography,
                parent,
                self.grid,
                self.physical,
                parent_directory if ancestor is not None else None,
                self.configuration,
                compiled=compiled,
                files=self.files,
            )
            data = json_bytes(settings)
            identity = hashlib.sha256(data).hexdigest()
            selected = directory / "definition.json"
            if selected.exists():
                if self.files.pin(selected)["sha256"] != identity:
                    raise ValueError("parent definition changed on resume")
            else:
                write_bytes_atomic(selected, data)
            definition_pin: FilePin = {
                "path": str(selected.resolve()),
                "sha256": identity,
            }
            receipt_path = directory / "result.json"
            saved = (
                read_json(receipt_path)
                if receipt_path.exists()
                else self.reuse.get(str(parent))
            )
            if saved is not None and saved["definition_sha256"] == identity:
                self.files.verify(saved["outputs"])
                output = Path(saved["directory"])
                receipt = dict(saved, reused=True)
            else:
                land_settings = parent_division_reuse_inputs(
                    self.geography,
                    parent,
                    self.grid,
                    self.physical,
                    parent_directory if ancestor is not None else None,
                    self.configuration,
                    compiled=compiled,
                    files=self.files,
                    land_only=True,
                )
                land_identity = hashlib.sha256(json_bytes(land_settings)).hexdigest()
                prior_land = saved.get("land") if saved else None
                context = ParentDivision(
                    self.geography,
                    parent,
                    self.grid,
                    self.physical,
                    directory / "calculation",
                    self.configuration,
                    compiled=compiled,
                    parent_directory=parent_directory if ancestor is not None else None,
                    checkpoints=self.checkpoints,
                    timing=self.timing,
                    input_pins=[definition_pin],
                    shore_provider=self.shores,
                )
                try:
                    if prior_land and prior_land["definition_sha256"] == land_identity:
                        self.files.verify(prior_land["outputs"])
                        land = context.use_land(prior_land["directory"])
                        land_receipt = dict(prior_land, reused=True)
                    else:
                        land = context.land()
                        land_receipt = dict(
                            directory=str(land),
                            definition_sha256=land_identity,
                            outputs=[
                                self.files.pin(Path(land) / name)
                                for name in ("rows.u32le", "runs.u32le", "report.json")
                            ],
                            reused=False,
                        )
                    output = context.water()
                finally:
                    context.close()
                receipt: dict[str, Any] = dict(
                    directory=str(output),
                    definition_sha256=identity,
                    reused=False,
                    land=land_receipt,
                    outputs=[
                        self.files.pin(output / name)
                        for name in ("rows.u32le", "runs.u32le", "report.json")
                    ],
                )
            if not receipt_path.exists():
                write_json(receipt_path, receipt)
            receipts[str(parent)] = receipt
            outputs[parent] = output
        if not outputs:
            raise ValueError("no geographic division selected")

        ownership = outputs.pop(0)
        if outputs:
            combined = self.directory / "ownership"
            self.task(
                "combine-ownership",
                partial(
                    assemble_ownership,
                    self.grid,
                    ownership,
                    outputs,
                    self.compiled_divisions,
                    combined,
                ),
                [pin for receipt in receipts.values() for pin in receipt["outputs"]],
                [combined],
            )
            ownership = combined
        report = dict(directory=str(ownership), parents=receipts, grid=vars(self.grid))
        path = self.directory / "report.json"
        if not path.exists():
            write_json(path, report)
        return report
