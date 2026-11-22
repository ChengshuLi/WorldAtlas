"""Apply the same parent division recursively, reusing verified unchanged outputs."""

import hashlib
from collections.abc import Callable, Iterable, Iterator
from contextlib import ExitStack
from pathlib import Path
from typing import Any, cast

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import write_layer
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.division.contracts import CompiledRules, compile_rules
from worldatlas.map_build.division.engine import ParentDivision, land_groups
from worldatlas.map_build.division.intervals import overlay, spans
from worldatlas.map_build.division.shores import ShoreGeometry
from worldatlas.map_build.execution.runtime import Checkpoints, Timing
from worldatlas.shared.files import (
    json_bytes,
    pin_file,
    read_json,
    verify_pins,
    write_json,
)


def selected_parents(
    geography: dict[str, Any], requested: Iterable[int] | None
) -> list[int]:
    """Find the requested divisions and include their ancestors.

    Args:
        geography: Frozen entities and subdivision rules.
        requested: Parent IDs to divide, or None for all configured parents.

    Returns:
        Entity IDs ordered with ancestors before descendants.

    Raises:
        ValueError: A parent needs missing rules or the hierarchy has a cycle.
    """
    entities = {e["id"]: e for e in geography["entities"]}
    available = {r["parent_id"] for r in geography["rules"]}
    chosen = available if requested is None else set(requested)
    if chosen - available:
        raise ValueError("requested parent has no selected subdivision rules")
    selected = set()
    for ident in chosen:
        while ident is not None:
            if ident not in entities:
                raise ValueError("geographic hierarchy has a missing ancestor")
            if ident in selected:
                break
            selected.add(ident)
            ident = entities[ident]["parent_id"]
    if selected - available:
        raise ValueError("a required ancestor has no selected subdivision rules")

    def depth(ident: int | None) -> int:
        """Count the path from an entity to the top of the hierarchy.

        Args:
            ident: Starting entity, or None above the root.

        Returns:
            Number of entities on the path, including the starting entity.

        Raises:
            ValueError: The path visits the same entity twice.
        """
        seen = set()
        while ident is not None:
            if ident in seen:
                raise ValueError("geographic hierarchy contains a cycle")
            seen.add(ident)
            ident = entities[ident]["parent_id"]
        return len(seen)

    return sorted(selected, key=lambda ident: (depth(ident), ident))


def definition(
    geography: dict[str, Any],
    parent: int,
    grid: Grid,
    physical: Path | str,
    membership: Path | str | None,
    configuration: dict[str, Any],
    *,
    compiled: CompiledRules,
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
        land_only: Whether to record the land calculation separately.

    Returns:
        Dictionary of operative rule settings, geometry, binding order
        and input file checksums. A wording or color edit leaves it unchanged.
    """
    children, rules = compiled
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
        binding_order=[
            (b["entity_id"], b["physical_class"], b["code"])
            for b in sorted(geography["category_bindings"], key=lambda b: b["code"])
            if b["entity_id"] in children
        ],
        physical={
            name: pin_file(Path(physical) / name)["sha256"]
            for name in ("rows.u32le", "runs.u32le")
        },
        membership=None
        if membership is None
        else {
            name: pin_file(Path(membership) / name)["sha256"]
            for name in ("rows.u32le", "runs.u32le")
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
        geography: dict[str, Any],
        grid: Grid,
        physical: Path | str,
        directory: Path | str,
        configuration: dict[str, Any],
        *,
        compiled_divisions: dict[int, CompiledRules] | None = None,
        requested: Iterable[int] | None = None,
        reuse: Path | str | None = None,
        checkpoints: Checkpoints | None = None,
        timing: Timing | None = None,
    ) -> None:
        """Prepare the hierarchy, work directory, and optional reuse settings.

        Args:
            geography: Frozen geographic rules, entities and features.
            grid: The build's physical grid dimensions.
            physical: Directory containing physical row-run files.
            directory: Output directory for division results.
            configuration: Build settings used by the rules.
            compiled_divisions: Child entities and assembled rules keyed by parent
                ID. When omitted, compile the rules here for a standalone division.
            requested: Parent IDs to divide, or None for all.
            reuse: Directory containing earlier division results.
            checkpoints: Optional store for completed work.
            timing: Optional timing log for the division.
        """
        self.geography, self.grid, self.physical = geography, grid, Path(physical)
        self.directory = Path(directory)
        self.directory.mkdir(exist_ok=True)
        self.configuration = configuration
        self.checkpoints, self.timing = checkpoints, timing
        self.parents = selected_parents(geography, requested)
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

    def task(
        self,
        name: str,
        function: Callable[..., Any],
        args: tuple[Any, ...],
        inputs: list[dict[str, str]],
        outputs: list[Path],
    ) -> Any:
        """Run one division step or load its completed result.

        Args:
            name: Checkpoint name.
            function: Function that performs the work.
            args: Positional arguments for the function.
            inputs: Input paths and checksums.
            outputs: Files or directories the task produces.

        Returns:
            Step result, read from the checkpoint if one exists.
        """
        if self.checkpoints is None:
            return function(*args)
        return self.checkpoints.run_function(
            name,
            "division",
            function,
            args,
            inputs=inputs,
            outputs=outputs,
            timing=cast(Timing, self.timing),
        )

    def run(self) -> dict[str, Any]:
        """Divide parents in order and combine the results into one ownership grid.

        Returns:
            Division report with the final layer directory and each parent's
            output and reuse details.
        """
        ownership = None
        receipts = {}
        for parent in self.parents:
            compiled = (
                compile_rules(self.geography, parent)
                if self.compiled_divisions is None
                else self.compiled_divisions[parent]
            )
            directory = self.directory / ("parent-" + str(parent))
            directory.mkdir(exist_ok=True)
            parent_directory = None
            if ownership is not None:
                parent_directory = directory / "membership"
                self.task(
                    "membership-" + str(parent),
                    membership,
                    (self.grid, ownership, parent, parent_directory),
                    [
                        pin_file(ownership / name)
                        for name in ("rows.u32le", "runs.u32le")
                    ],
                    [parent_directory],
                )
            settings = definition(
                self.geography,
                parent,
                self.grid,
                self.physical,
                parent_directory,
                self.configuration,
                compiled=compiled,
            )
            data = json_bytes(settings)
            identity = hashlib.sha256(data).hexdigest()
            selected = directory / "definition.json"
            if selected.exists():
                if selected.read_bytes() != data:
                    raise ValueError("parent definition changed on resume")
            else:
                write_json(selected, settings)
            receipt_path = directory / "result.json"
            saved = (
                read_json(receipt_path)
                if receipt_path.exists()
                else self.reuse.get(str(parent))
            )
            if saved is not None and saved["definition_sha256"] == identity:
                verify_pins(saved["outputs"])
                output = Path(saved["directory"])
                receipt = dict(saved, reused=True)
            else:
                land_settings = definition(
                    self.geography,
                    parent,
                    self.grid,
                    self.physical,
                    parent_directory,
                    self.configuration,
                    compiled=compiled,
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
                    parent_directory=parent_directory,
                    checkpoints=self.checkpoints,
                    timing=cast(Timing, self.timing),
                    input_pins=[pin_file(selected)],
                    shore_provider=self.shores,
                )
                try:
                    if prior_land and prior_land["definition_sha256"] == land_identity:
                        verify_pins(prior_land["outputs"])
                        land = context.use_land(prior_land["directory"])
                        land_receipt = dict(prior_land, reused=True)
                    else:
                        land = context.land()
                        land_receipt = dict(
                            directory=str(land),
                            definition_sha256=land_identity,
                            outputs=[
                                pin_file(Path(land) / name)
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
                        pin_file(output / name)
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
                    substitute,
                    (self.grid, ownership, parent_directory, output, merged),
                    [
                        pin_file(selected),
                        *receipt["outputs"],
                        *[
                            pin_file(ownership / name)
                            for name in ("rows.u32le", "runs.u32le")
                        ],
                    ],
                    [merged],
                )
                ownership = merged
        if ownership is None:
            raise ValueError("no geographic division selected")
        for receipt in receipts.values():
            verify_pins(receipt["outputs"])
        report = dict(directory=str(ownership), parents=receipts, grid=vars(self.grid))
        path = self.directory / "report.json"
        if not path.exists():
            write_json(path, report)
        return report
