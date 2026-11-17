"""Execute geographic parent divisions using explicit data dependencies."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from contextvars import copy_context
import hashlib
import os
from pathlib import Path
import threading
import time

import numpy as np

from worldatlas.map_build.core.layers import write_layer
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.division.areas import assign_area, divide_area
from worldatlas.map_build.division.contracts import compile_rules
from worldatlas.map_build.division.intervals import Eligibility, combine, overlay, spans
from worldatlas.map_build.division.scope import Scope
from worldatlas.map_build.division.connectivity import build_domain
from worldatlas.map_build.division.shores import ShoreGeometry
from worldatlas.map_build.division import policies
from worldatlas.map_build.execution.control import check_cancelled
from worldatlas.map_build.execution.runtime import pin
from worldatlas.map_build.land.components import ComponentGrid
from worldatlas.map_build.land.connected import build_components


def land_groups(rules):
    """Declare actual land-stage dependencies once for execution and reuse."""
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
    grid,
    physical_directory,
    parent_directory,
    snapshot_directory,
    claims,
    directory,
    allowed,
):
    with ExitStack() as resources:
        physical = resources.enter_context(open_grid(physical_directory, grid))
        parent = resources.enter_context(open_grid(parent_directory, grid))
        snapshot = resources.enter_context(open_grid(snapshot_directory, grid))
        inputs = [
            resources.enter_context(open_grid(result["directory"], grid))
            for _, result in claims
        ]

        def rows():
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


def execute_rule(context, rule, snapshot_directory, directory):
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
                scope, rule["features"]["input_geometry"], rule["targets"], directory
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
    def __init__(
        self,
        geography,
        parent_id,
        grid,
        physical_directory,
        directory,
        configuration,
        *,
        parent_directory=None,
        checkpoints=None,
        timing=None,
        input_pins=(),
        shore_provider=None,
    ):
        self.geography = geography
        self.parent_id = parent_id
        self.grid = grid
        self.children, self.rules = compile_rules(geography, parent_id)
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

    def close(self):
        self.resources.close()

    def pins(self, directory):
        return [pin(Path(directory) / name) for name in ("rows.u32le", "runs.u32le")]

    def task(self, name, function, args, outputs, *, inputs, kwargs=None):
        if self.checkpoints is None:
            return function(*args, **(kwargs or {}))
        return self.checkpoints.run_function(
            f"parent-{self.parent_id}-{name}",
            "division",
            function,
            args,
            inputs=inputs,
            outputs=outputs,
            timing=self.timing,
            kwargs=kwargs,
        )

    def _prepare_physical(self):
        def rows():
            for y in range(self.grid.height):
                starts, ends, (kind, parent) = overlay(
                    row(self.physical, y, self.grid.width),
                    row(self.parent, y, self.grid.width),
                )
                records = spans(starts, ends, np.where(parent != 0, kind, 0))
                if records:
                    yield y, records

        return write_layer(self.parent_physical_directory, self.grid, rows())

    def components(self, kind):
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
    def shore_geometry(self):
        with self.lock:
            if self._shores is None:
                self._shores = (
                    self.shore_provider()
                    if self.shore_provider
                    else ShoreGeometry(self.physical, self.grid)
                )
            return self._shores

    def water_shores(self):
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

    def scope_components(self, snapshot_directory, physical_class, unassigned_only):
        """Share immutable domain connectivity across all rules using a snapshot."""
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

    def calculate(self, rules, snapshot):
        """Calculate independent claims against one immutable ownership snapshot."""
        inputs = (
            self.input_pins + self.pins(snapshot) + self.pins(self.parent_directory)
        )

        def run(rule):
            check_cancelled()
            key = hashlib.sha256(rule["id"].encode()).hexdigest()
            directory = self.directory / ("rule-" + key)
            result = self.task(
                "rule-" + key,
                execute_rule,
                (self, rule, snapshot, directory),
                [directory],
                inputs=inputs,
            )
            return rule["id"], result

        workers = self.configuration.get("division_workers", os.cpu_count() or 1)
        if type(workers) is not int or workers < 1:
            raise ValueError("division_workers must be positive")
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(copy_context().run, run, r) for r in rules]
            return [future.result() for future in futures]

    def consolidate(self, name, snapshot, claims):
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

    def group(self, name, rules):
        if rules:
            snapshot = self.current
            self.consolidate(name, snapshot, self.calculate(rules, snapshot))

    def require_coverage(self, kind=None):
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

    def land(self):
        for name, rules in land_groups(self.rules):
            self.group(name, rules)
        self.require_coverage("land")
        return self.use_land(self.current)

    def use_land(self, directory):
        """Continue from verified complete land ownership on this parent/grid."""
        self.current = Path(directory)
        self.require_coverage("land")
        self.land_directory = self.current
        self.land_ownership = self.resources.enter_context(
            open_grid(self.land_directory, self.grid)
        )
        return self.land_directory

    def water(self):
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
