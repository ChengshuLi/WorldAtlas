"""Apply the same parent division recursively, reusing verified unchanged outputs."""

import hashlib
from collections.abc import Callable, Iterator
from contextlib import ExitStack
from functools import partial
from pathlib import Path
from typing import Any

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import write_layer
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.division.contracts import CompiledDivision
from worldatlas.map_build.division.engine import ParentDivision, land_groups
from worldatlas.map_build.division.intervals import overlay, spans
from worldatlas.map_build.division.shores import ShoreGeometry, land_owner_order
from worldatlas.map_build.execution.runtime import Checkpoints, RunFilePins
from worldatlas.map_build.execution.timing import Timing
from worldatlas.map_build.inputs.selection_types import GeographicSelection
from worldatlas.shared.files import (
    JSONValue,
    json_bytes,
    read_json,
    write_bytes_atomic,
    write_json,
)


def definition(
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
    """Record only the inputs that affect the parent's assignment.

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
    operative = []
    for rule in rules:
        operative.append(
            {
                **{
                    k: rule[k]
                    for k in (
                        "id",
                        "operation",
                        "physical_class",
                        "unit",
                        "unassigned_only",
                    )
                },
                "features": {
                    role: [dict(id=f["id"], geometry=f["geometry"]) for f in features]
                    for role, features in rule["features"].items()
                    if features
                },
                "targets": [
                    dict(
                        entity_id=t["entity_id"],
                        point=t["point"]["geometry"] if t["point"] else None,
                    )
                    for t in rule["targets"]
                ],
            }
        )
    result = dict(
        parent_id=parent,
        grid=vars(grid),
        children=[
            dict(id=e["id"], physical_class=e["physical_class"])
            for _, e in sorted(children.items())
        ],
        rules=operative,
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


def membership(
    grid: Grid, ownership_directory: Path | str, parent: int, directory: Path | str
) -> dict[str, Any]:
    """Write a mask of the cells owned by one parent.

    Args:
        grid: Dimensions of the ownership grid.
        ownership_directory: Input row-run ownership grid.
        parent: Owner ID to select.
        directory: New directory for the mask.

    Returns:
        Row-run layer report for the parent's membership mask.
    """
    with open_grid(ownership_directory, grid) as owners:

        def rows() -> Iterator[tuple[int, list[tuple[int, int, int]]]]:
            """Find the intervals owned by the parent in each row.

            Yields:
                (row, spans) with value 1 for cells owned by the parent.
            """
            for y in range(grid.height):
                ends, values = row(owners, y, grid.width)
                records = spans(
                    np.r_[0, ends[:-1]], ends, (values == parent).astype(np.uint32)
                )
                if records:
                    yield y, records

        return write_layer(directory, grid, rows())


def substitute(
    grid: Grid,
    prior_directory: Path | str,
    parent_directory: Path | str,
    child_directory: Path | str,
    directory: Path | str,
) -> dict[str, Any]:
    """Replace a parent's cells with the owners from its subdivision.

    Args:
        grid: Dimensions shared by all layers.
        prior_directory: Ownership grid before the subdivision.
        parent_directory: Mask of cells owned by the parent.
        child_directory: Owners from the subdivision.
        directory: New directory for the combined ownership layer.

    Returns:
        Layer report for the combined ownership.
    """
    with ExitStack() as stack:
        prior = stack.enter_context(open_grid(prior_directory, grid))
        parent = stack.enter_context(open_grid(parent_directory, grid))
        children = stack.enter_context(open_grid(child_directory, grid))

        def rows() -> Iterator[tuple[int, list[tuple[int, int, int]]]]:
            """Read each row and replace owners inside the divided parent.

            Yields:
                (row, spans) containing owner IDs before and after the substitution.
            """
            for y in range(grid.height):
                starts, ends, (old, within, new) = overlay(
                    row(prior, y, grid.width),
                    row(parent, y, grid.width),
                    row(children, y, grid.width),
                )
                if np.any((within != 0) & (new == 0)) or np.any(
                    (within == 0) & (new != 0)
                ):
                    raise ValueError(
                        "child division does not match its exact parent membership"
                    )
                records = spans(starts, ends, np.where(within != 0, new, old))
                if records:
                    yield y, records

        return write_layer(directory, grid, rows())


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
        inputs: list[dict[str, str]],
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
        ownership = None
        receipts = {}
        for parent, compiled in self.compiled_divisions.items():
            directory = self.directory / ("parent-" + str(parent))
            directory.mkdir(exist_ok=True)
            parent_directory = directory / "membership"
            if ownership is not None:
                self.task(
                    "membership-" + str(parent),
                    partial(membership, self.grid, ownership, parent, parent_directory),
                    self.files.row_streams(ownership),
                    [parent_directory],
                )
            settings = definition(
                self.geography,
                parent,
                self.grid,
                self.physical,
                parent_directory if ownership is not None else None,
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
            definition_pin = {"path": str(selected.resolve()), "sha256": identity}
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
                land_settings = definition(
                    self.geography,
                    parent,
                    self.grid,
                    self.physical,
                    parent_directory if ownership is not None else None,
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
                    parent_directory=parent_directory
                    if ownership is not None
                    else None,
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
            if ownership is None:
                ownership = output
            else:
                merged = directory / "finest"
                self.task(
                    "substitute-" + str(parent),
                    partial(
                        substitute,
                        self.grid,
                        ownership,
                        parent_directory,
                        output,
                        merged,
                    ),
                    [
                        definition_pin,
                        *receipt["outputs"],
                        *self.files.row_streams(ownership),
                    ],
                    [merged],
                )
                ownership = merged
        if ownership is None:
            raise ValueError("no geographic division selected")
        for receipt in receipts.values():
            self.files.verify(receipt["outputs"])
        report = dict(directory=str(ownership), parents=receipts, grid=vars(self.grid))
        path = self.directory / "report.json"
        if not path.exists():
            write_json(path, report)
        return report
