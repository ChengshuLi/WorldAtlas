"""Execute geographic parent divisions using explicit data dependencies."""

from __future__ import annotations

import hashlib
import os
import threading
import time
from collections.abc import Callable, Iterable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from contextvars import copy_context
from pathlib import Path
from typing import Any, cast

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import write_layer
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.division import policies
from worldatlas.map_build.division.areas import assign_area, divide_area
from worldatlas.map_build.division.connectivity import build_domain
from worldatlas.map_build.division.contracts import CompiledDivision, CompiledRule
from worldatlas.map_build.division.intervals import Eligibility, combine, overlay, spans
from worldatlas.map_build.division.scope import Scope
from worldatlas.map_build.division.shores import ReferenceCells, ShoreGeometry
from worldatlas.map_build.execution.control import check_cancelled, stage
from worldatlas.map_build.execution.runtime import Checkpoints, Timing
from worldatlas.map_build.inputs.selection_types import GeographicSelection
from worldatlas.map_build.land.components import ComponentGrid
from worldatlas.map_build.land.connected import build_components
from worldatlas.shared.files import pin_file


def rule_directory(calculation: Path | str, rule_id: str) -> Path:
    """Derive a stable output path for a rule.

    Args:
        calculation: Parent division directory.
        rule_id: Geographic rule identifier.

    Returns:
        Subdirectory named by a hash of the rule ID.
    """
    key = hashlib.sha256(rule_id.encode()).hexdigest()
    return Path(calculation) / ("rule-" + key)


def land_groups(
    rules: Sequence[CompiledRule],
) -> tuple[tuple[str, list[CompiledRule]], ...]:
    """Group explicit assignments, geographic land fills, and nearest-land rules.

    Args:
        rules: Compiled rules for the parent.

    Returns:
        Ordered (group_name, rule_list) pairs.
    """
    area = lambda r: r["operation"] in ("assign_area", "divide_area")
    return (
        ("explicit", [r for r in rules if area(r) and not r["unassigned_only"]]),
        (
            "geographic-land-fill",
            [
                r
                for r in rules
                if area(r) and r["unassigned_only"] and r["physical_class"] != "water"
            ],
        ),
        ("nearest-land", [r for r in rules if r["operation"] == "nearest_land"]),
    )


def merge_claims(
    grid: Grid,
    physical_directory: Path | str,
    parent_directory: Path | str,
    snapshot_directory: Path | str,
    claims: Sequence[tuple[str, dict[str, Any]]],
    directory: Path | str,
    allowed: Eligibility,
) -> dict[str, Any]:
    """Combine a rule group's output with the previous ownership grid.

    Args:
        grid: Grid used by the inputs and output.
        physical_directory: Physical land and water grid.
        parent_directory: Mask of cells belonging to the parent.
        snapshot_directory: Ownership grid before the group ran.
        claims: Rule IDs and their output layer reports.
        directory: New output directory.
        allowed: Physical classes each child may own.

    Returns:
        Layer report including counts of cells claimed by each rule.

    Raises:
        ValueError: Two rules disagree or a claim is ineligible.
    """
    with ExitStack() as resources:
        physical = resources.enter_context(open_grid(physical_directory, grid))
        parent = resources.enter_context(open_grid(parent_directory, grid))
        snapshot = resources.enter_context(open_grid(snapshot_directory, grid))
        inputs = [
            resources.enter_context(open_grid(result["directory"], grid))
            for _, result in claims
        ]

        def rows() -> Iterator[tuple[int, list[tuple[int, int, int]]]]:
            """Read and combine only the claims that can affect each row.

            Yields:
                (row, spans) with owner IDs.
            """
            for y in range(grid.height):
                check_cancelled()
                active = [
                    i
                    for i, (_, result) in enumerate(claims)
                    if result["assigned_bounds"] is not None
                    and result["assigned_bounds"][2] <= y < result["assigned_bounds"][3]
                ]
                records = combine(
                    row(physical, y, grid.width),
                    row(parent, y, grid.width),
                    row(snapshot, y, grid.width),
                    [row(inputs[i], y, grid.width) for i in active],
                    y=y,
                    rules=[claims[i][0] for i in active],
                    allowed=allowed,
                )
                if records:
                    yield y, records

        result = write_layer(directory, grid, rows())
        result["contributions"] = [
            dict(rule_id=name, counts=r["counts"]) for name, r in claims
        ]
        return result


def execute_rule(
    context: ParentDivision,
    rule: CompiledRule,
    snapshot_directory: Path | str,
    directory: Path | str,
) -> dict[str, Any]:
    """Prepare one rule's scope and write its proposed assignments.

    Args:
        context: Shared parent grid, components and shores.
        rule: Resolved method, scope, references and targets.
        snapshot_directory: Ownership grid before the rule group.
        directory: New directory for the calculation and output.

    Returns:
        Rule report with the output layer, timing, and any connectivity references.
    """
    started = time.monotonic()
    with open_grid(snapshot_directory, context.grid) as snapshot:
        scope = Scope(
            rule,
            context.grid,
            context.physical,
            context.parent,
            snapshot,
            context.components,
            connectivity=lambda kind, unassigned: context.scope_components(
                snapshot_directory, kind, unassigned
            ),
        )
        operation = rule["operation"]
        if operation == "assign_area":
            result = assign_area(scope, rule["targets"][0]["entity_id"], directory)
        elif operation == "divide_area":
            result = divide_area(
                scope, rule["features"]["boundary_line"], rule["targets"], directory
            )
        elif (
            operation not in ("nearest_land", "nearest_basin_water")
            and not scope.has_output()
        ):
            result = write_layer(directory, context.grid, ())
        else:
            result = {
                "nearest_land": policies.nearest_land,
                "nearest_coastal_water": policies.nearest_coastal_water,
                "nearest_basin_water": policies.nearest_basin_water,
                "nearest_water": policies.nearest_water,
            }[operation](context, scope, directory)
    return dict(
        result,
        rule_id=rule["id"],
        operation=operation,
        processing_seconds=time.monotonic() - started,
        download_seconds=0.0,
        **(
            {"connectivity_references": scope.connectivity_receipt}
            if scope.connectivity_receipt
            else {}
        ),
    )


class ParentDivision:
    """Assign one parent's cells to its direct children."""

    def __init__(
        self,
        geography: GeographicSelection,
        parent_id: int,
        grid: Grid,
        physical_directory: Path | str,
        directory: Path | str,
        configuration: dict[str, Any],
        *,
        compiled: CompiledDivision,
        parent_directory: Path | str | None = None,
        checkpoints: Checkpoints | None = None,
        timing: Timing | None = None,
        input_pins: Iterable[dict[str, str]] = (),
        shore_provider: Callable[[], ShoreGeometry] | None = None,
    ) -> None:
        """Open the physical grid and prepare the parent's initial ownership.

        Args:
            geography: Saved rules and geographic entities.
            parent_id: Entity to divide.
            grid: Physical dimensions and coordinates.
            physical_directory: Physical row-run grid directory.
            directory: Directory for this division's outputs.
            configuration: Build settings used by the rules.
            compiled: This parent's child entities and assembled rules.
            parent_directory: Inherited mask of the parent's cells. Omit only for
                the root.
            checkpoints: Optional store for completed work.
            timing: Optional timing log used by the checkpoint runner.
            input_pins: Paths and SHA-256 digests for this division's inputs.
            shore_provider: Optional shared physical shore calculation.

        Raises:
            ValueError: A non-root division is missing its parent mask.
        """
        self.geography = geography
        self.parent_id = parent_id
        self.grid = grid
        self.children = compiled.children_by_id
        self.rules = compiled.rules
        self.allowed = Eligibility(
            {e: v["physical_class"] for e, v in self.children.items()}
        )
        self.configuration = configuration
        self.directory = Path(directory)
        self.directory.mkdir(exist_ok=True)
        self.physical_directory = Path(physical_directory)
        self.checkpoints, self.timing = checkpoints, timing
        self.input_pins = list(input_pins)
        self.resources = ExitStack()
        self.lock = threading.RLock()
        self.component_grids = {}
        self.scope_component_grids = {}
        self._shores = None
        self._water_shores = None
        self.shore_provider = shore_provider
        self.land_ownership = None
        self.land_directory = None
        self.shore_order = [
            b["entity_id"]
            for b in sorted(geography["category_bindings"], key=lambda b: b["code"])
            if b["physical_class"] == "land" and b["entity_id"] in self.children
        ]
        try:
            if parent_directory is None:
                parent = next(e for e in geography["entities"] if e["id"] == parent_id)
                if parent["parent_id"] is not None:
                    raise ValueError(
                        "a non-root division requires inherited parent membership"
                    )
                parent_directory = self.directory / "parent-membership"
                self.task(
                    "parent-membership",
                    write_layer,
                    (
                        parent_directory,
                        grid,
                        ((y, [(0, grid.width, 1)]) for y in range(grid.height)),
                    ),
                    [parent_directory],
                    inputs=self.input_pins,
                )
                self.parent_physical_directory = self.physical_directory
            else:
                self.parent_physical_directory = self.directory / "parent-physical"
            self.parent_directory = Path(parent_directory)
            self.physical = self.resources.enter_context(
                open_grid(self.physical_directory, grid)
            )
            self.parent = self.resources.enter_context(
                open_grid(self.parent_directory, grid)
            )
            if self.parent_physical_directory != self.physical_directory:
                self.task(
                    "parent-physical",
                    self._prepare_physical,
                    (),
                    [self.parent_physical_directory],
                    inputs=self.input_pins + self.pins(self.parent_directory),
                )
            self.parent_physical = self.resources.enter_context(
                open_grid(self.parent_physical_directory, grid)
            )
            empty = self.directory / "empty"
            self.empty_directory = empty
            self.task(
                "empty",
                write_layer,
                (empty, grid, ()),
                [empty],
                inputs=self.input_pins,
            )
            self.current = empty
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        """Close the division's open maps and other resources."""
        self.resources.close()

    def pins(self, directory: Path | str) -> list[dict[str, str]]:
        """Hash a layer's two row-run files.

        Args:
            directory: Layer directory.

        Returns:
            File pins for rows.u32le and runs.u32le in that order.
        """
        return [
            pin_file(Path(directory) / name) for name in ("rows.u32le", "runs.u32le")
        ]

    def task(
        self,
        name: str,
        function: Callable[..., Any],
        args: tuple[Any, ...],
        outputs: Iterable[Path | str],
        *,
        inputs: list[dict[str, str]],
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        """Run a calculation or reuse its verified checkpoint.

        Args:
            name: Name of the task within this parent.
            function: Calculation to perform.
            args: Positional arguments to the function.
            outputs: Paths the calculation writes.
            inputs: File pins to verify before reuse.
            kwargs: Additional keyword arguments.

        Returns:
            The calculation's result, or the equivalent saved JSON value.
        """
        if self.checkpoints is None:
            return function(*args, **(kwargs or {}))
        return self.checkpoints.run_function(
            f"parent-{self.parent_id}-{name}",
            "division",
            function,
            args,
            inputs=inputs,
            outputs=outputs,
            timing=cast(Timing, self.timing),
            kwargs=kwargs,
        )

    def _prepare_physical(self) -> dict[str, Any]:
        """Write land and water runs limited to the parent's cells.

        Returns:
            Layer report for the clipped physical grid.
        """

        def rows() -> Iterator[tuple[int, list[tuple[int, int, int]]]]:
            """Find the physical runs inside the parent for each row.

            Yields:
                (row, spans) with land or water codes.
            """
            for y in range(self.grid.height):
                starts, ends, (kind, parent) = overlay(
                    row(self.physical, y, self.grid.width),
                    row(self.parent, y, self.grid.width),
                )
                records = spans(starts, ends, np.where(parent != 0, kind, 0))
                if records:
                    yield y, records

        return write_layer(self.parent_physical_directory, self.grid, rows())

    def components(self, kind: str) -> ComponentGrid:
        """Find or build the parent's physical components of one class.

        Args:
            kind: "land" or "water".

        Returns:
            Open component grid owned by this division.
        """
        with self.lock:
            if kind not in self.component_grids:
                code = {"land": 17, "water": 1}[kind]
                directory = self.directory / (kind + "-components")
                self.task(
                    kind + "-components",
                    build_components,
                    (self.grid, self.parent_physical_directory, directory),
                    [directory],
                    inputs=self.input_pins + self.pins(self.parent_physical_directory),
                    kwargs=dict(physical_code=code),
                )
                data = ComponentGrid(
                    self.parent_physical_directory,
                    directory,
                    self.grid,
                    physical_code=code,
                )
                self.resources.callback(data.close)
                data.totals()
                self.component_grids[kind] = data
            return self.component_grids[kind]

    @property
    def shore_geometry(self) -> ShoreGeometry:
        """Find or build the physical shore geometry for the grid.

        Returns:
            Cached geometry without ownership labels.
        """
        with self.lock:
            if self._shores is None:
                self._shores = (
                    self.shore_provider()
                    if self.shore_provider
                    else ShoreGeometry(self.physical, self.grid)
                )
            return self._shores

    def water_shores(self) -> ReferenceCells:
        """Attach land owners to shores that can assign water.

        Returns:
            Labelled shore runs for children that can own water.

        Raises:
            ValueError: Land ownership is not ready.
        """
        with self.lock:
            if self.land_ownership is None:
                raise ValueError(
                    "land ownership must be complete before using its shores"
                )
            if self._water_shores is None:
                self._water_shores = self.shore_geometry.attach(
                    self.land_ownership,
                    self.shore_order,
                    reference_owners={
                        e
                        for e, child in self.children.items()
                        if child["physical_class"] != "land"
                    },
                )
            return self._water_shores

    def scope_components(
        self, snapshot_directory: Path | str, physical_class: str, unassigned_only: bool
    ) -> ComponentGrid:
        """Find connected pieces of the parent's eligible domain.

        Args:
            snapshot_directory: Owners at the start of the rule group.
            physical_class: Eligible class, or "mixed" for both.
            unassigned_only: Whether to exclude cells already assigned.

        Returns:
            Cached component grid shared by rules that use the same domain.
        """
        key = (str(snapshot_directory), physical_class, unassigned_only)
        with self.lock:
            if key not in self.scope_component_grids:
                name = "connectivity-" + hashlib.sha256(repr(key).encode()).hexdigest()
                directory = self.directory / name
                with open_grid(snapshot_directory, self.grid) as snapshot:
                    self.task(
                        name,
                        build_domain,
                        (
                            self.grid,
                            self.physical,
                            self.parent,
                            snapshot,
                            physical_class,
                            unassigned_only,
                            directory,
                        ),
                        [directory],
                        inputs=self.input_pins
                        + self.pins(snapshot_directory)
                        + self.pins(self.parent_directory)
                        + self.pins(self.physical_directory),
                    )
                data = self.resources.enter_context(
                    ComponentGrid(
                        directory / "domain",
                        directory / "components",
                        self.grid,
                        physical_code=1,
                    )
                )
                data.totals()
                self.scope_component_grids[key] = data
            return self.scope_component_grids[key]

    def calculate(
        self, rules: Sequence[CompiledRule], snapshot: Path
    ) -> list[tuple[str, dict[str, Any]]]:
        """Calculate a group of rules against the same ownership grid.

        Args:
            rules: Rules that can run independently.
            snapshot: Ownership layer before this group.

        Returns:
            (rule_id, report) pairs in rule order.

        Raises:
            ValueError: The worker count is invalid.
        """
        inputs = (
            self.input_pins + self.pins(snapshot) + self.pins(self.parent_directory)
        )

        workers = self.configuration.get("division_workers", os.cpu_count() or 1)
        if type(workers) is not int or workers < 1:
            raise ValueError("division_workers must be positive")
        failure = None
        failure_lock = threading.Lock()
        with stage() as cancelled, ThreadPoolExecutor(max_workers=workers) as executor:

            def run(rule: CompiledRule) -> tuple[str, dict[str, Any]]:
                """Calculate one rule and request cancellation if it fails.

                Args:
                    rule: Compiled geographic rule.

                Returns:
                    Rule ID and its output report.
                """
                nonlocal failure
                check_cancelled()
                directory = rule_directory(self.directory, rule["id"])
                try:
                    result = self.task(
                        directory.name,
                        execute_rule,
                        (self, rule, snapshot, directory),
                        [directory],
                        inputs=inputs,
                    )
                except Exception as error:
                    with failure_lock:
                        if failure is None:
                            failure = error
                            cancelled.set()
                    raise
                return rule["id"], result

            futures = [executor.submit(copy_context().run, run, r) for r in rules]
            try:
                return [future.result() for future in futures]
            except BaseException as error:
                cancelled.set()
                for future in futures:
                    future.cancel()
                if (
                    isinstance(error, InterruptedError)
                    and failure is not None
                    and error is not failure
                ):
                    raise failure from None
                raise

    def consolidate(
        self, name: str, snapshot: Path, claims: Sequence[tuple[str, dict[str, Any]]]
    ) -> None:
        """Check a group's claims and advance the current ownership grid.

        Args:
            name: Name of the rule group.
            snapshot: Ownership layer before the group ran.
            claims: Rule IDs and their layer reports.
        """
        if not claims:
            return
        inputs = (
            self.input_pins + self.pins(snapshot) + self.pins(self.parent_directory)
        )
        directory = self.directory / name
        claim_pins = [p for _, r in claims for p in self.pins(r["directory"])]
        result = self.task(
            name,
            merge_claims,
            (
                self.grid,
                self.physical_directory,
                self.parent_directory,
                snapshot,
                claims,
                directory,
                self.allowed,
            ),
            [directory],
            inputs=inputs + claim_pins,
        )
        self.current = Path(result["directory"])

    def group(self, name: str, rules: Sequence[CompiledRule]) -> None:
        """Calculate and merge one group of rules.

        Args:
            name: Name of the rule group.
            rules: Rules sharing one starting ownership layer.
        """
        if rules:
            snapshot = self.current
            self.consolidate(name, snapshot, self.calculate(rules, snapshot))

    def require_coverage(self, kind: str | None = None) -> None:
        """Check for unassigned cells inside the parent.

        Args:
            kind: Optional "land" or "water" filter. None checks both.

        Raises:
            ValueError: An eligible cell is missing its owner.
        """
        with open_grid(self.current, self.grid) as owners:
            for y in range(self.grid.height):
                starts, _, (physical, parent, assigned) = overlay(
                    row(self.physical, y, self.grid.width),
                    row(self.parent, y, self.grid.width),
                    row(owners, y, self.grid.width),
                )
                eligible = parent != 0
                if kind is not None:
                    eligible &= physical == {"land": 17, "water": 1}[kind]
                missing = eligible & (assigned == 0)
                if missing.any():
                    x = int(starts[np.flatnonzero(missing)[0]])
                    raise ValueError(
                        f"parent {self.parent_id}: unassigned {kind or 'geographic'} cell {x},{y}"
                    )

    def land(self) -> Path:
        """Run the land rule groups and check land coverage.

        Returns:
            Directory containing the ownership grid after the land groups.
        """
        for name, rules in land_groups(self.rules):
            self.group(name, rules)
        return self.use_land(self.current)

    def use_land(self, directory: Path | str) -> Path:
        """Use a completed ownership layer as the source of land labels.

        Args:
            directory: Directory containing the saved layer.

        Returns:
            Path to the layer, which stays open during water assignment.

        Raises:
            ValueError: A land cell lacks an owner.
        """
        self.current = Path(directory)
        self.require_coverage("land")
        self.land_directory = self.current
        self.land_ownership = self.resources.enter_context(
            open_grid(self.land_directory, self.grid)
        )
        return self.land_directory

    def water(self) -> Path:
        """Run the water rule groups and check coverage of the entire parent.

        Returns:
            Directory containing the completed ownership grid.

        Raises:
            ValueError: Land ownership is missing or a cell still lacks an owner.
        """
        if self.land_ownership is None:
            raise ValueError("prepare land ownership before water calculations")
        self.group(
            "shore-water",
            [
                r
                for r in self.rules
                if r["operation"] in ("nearest_coastal_water", "nearest_basin_water")
            ],
        )
        self.group(
            "geographic-water-fill",
            [
                r
                for r in self.rules
                if r["operation"] in ("assign_area", "divide_area")
                and r["unassigned_only"]
                and r["physical_class"] == "water"
            ],
        )
        self.group(
            "nearest-water",
            [r for r in self.rules if r["operation"] == "nearest_water"],
        )
        self.require_coverage()
        return self.current
