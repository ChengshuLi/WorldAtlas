"""Apply the same parent division recursively, reusing verified unchanged outputs."""

from contextlib import ExitStack
import hashlib
import json
from pathlib import Path

import numpy as np

from worldatlas.map_build.core.layers import write_layer
from worldatlas.map_build.core.rle import open_grid, row
from worldatlas.map_build.division.contracts import compile_rules
from worldatlas.map_build.division.engine import ParentDivision, land_groups
from worldatlas.map_build.division.intervals import overlay, spans
from worldatlas.map_build.division.shores import ShoreGeometry
from worldatlas.map_build.execution.runtime import json_bytes, pin, verify_pins, write


def selected_parents(geography, requested):
    """Select requested divisions and the ancestors needed to establish their cells."""
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

    def depth(ident):
        seen = set()
        while ident is not None:
            if ident in seen:
                raise ValueError("geographic hierarchy contains a cycle")
            seen.add(ident)
            ident = entities[ident]["parent_id"]
        return len(seen)

    return sorted(selected, key=lambda ident: (depth(ident), ident))


def definition(
    geography, parent, grid, physical, membership, configuration, *, land_only=False
):
    """Only operative inputs determine reuse; notes, colors and sibling edits do not."""
    children, rules = compile_rules(geography, parent)
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
            name: pin(Path(physical) / name)["sha256"]
            for name in ("rows.u32le", "runs.u32le")
        },
        membership=None
        if membership is None
        else {
            name: pin(Path(membership) / name)["sha256"]
            for name in ("rows.u32le", "runs.u32le")
        },
    )
    if any(r["operation"] == "nearest_coastal_water" for r in rules):
        result["coastal_band_metres"] = configuration["coastal_band_metres"]
    return result


def membership(grid, ownership_directory, parent, directory):
    with open_grid(ownership_directory, grid) as owners:

        def rows():
            for y in range(grid.height):
                ends, values = row(owners, y, grid.width)
                records = spans(
                    np.r_[0, ends[:-1]], ends, (values == parent).astype(np.uint32)
                )
                if records:
                    yield y, records

        return write_layer(directory, grid, rows())


def substitute(grid, prior_directory, parent_directory, child_directory, directory):
    with ExitStack() as stack:
        prior = stack.enter_context(open_grid(prior_directory, grid))
        parent = stack.enter_context(open_grid(parent_directory, grid))
        children = stack.enter_context(open_grid(child_directory, grid))

        def rows():
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
    def __init__(
        self,
        geography,
        grid,
        physical,
        directory,
        configuration,
        *,
        requested=None,
        reuse=None,
        checkpoints=None,
        timing=None,
    ):
        self.geography, self.grid, self.physical = geography, grid, Path(physical)
        self.directory = Path(directory)
        self.directory.mkdir(exist_ok=True)
        self.configuration = configuration
        self.checkpoints, self.timing = checkpoints, timing
        self.parents = selected_parents(geography, requested)
        self.reuse = (
            {}
            if reuse is None
            else json.loads((Path(reuse) / "report.json").read_text())["parents"]
        )
        self._shores = None

    def shores(self):
        if self._shores is None:
            with open_grid(self.physical, self.grid) as physical:
                self._shores = ShoreGeometry(physical, self.grid)
        return self._shores

    def task(self, name, function, args, inputs, outputs):
        if self.checkpoints is None:
            return function(*args)
        return self.checkpoints.run_function(
            name,
            "division",
            function,
            args,
            inputs=inputs,
            outputs=outputs,
            timing=self.timing,
        )

    def run(self):
        ownership = None
        receipts = {}
        for parent in self.parents:
            directory = self.directory / ("parent-" + str(parent))
            directory.mkdir(exist_ok=True)
            parent_directory = None
            if ownership is not None:
                parent_directory = directory / "membership"
                self.task(
                    "membership-" + str(parent),
                    membership,
                    (self.grid, ownership, parent, parent_directory),
                    [pin(ownership / name) for name in ("rows.u32le", "runs.u32le")],
                    [parent_directory],
                )
            settings = definition(
                self.geography,
                parent,
                self.grid,
                self.physical,
                parent_directory,
                self.configuration,
            )
            data = json_bytes(settings)
            identity = hashlib.sha256(data).hexdigest()
            selected = directory / "definition.json"
            if selected.exists():
                if selected.read_bytes() != data:
                    raise ValueError("parent definition changed on resume")
            else:
                write(selected, settings)
            receipt_path = directory / "result.json"
            saved = (
                json.loads(receipt_path.read_text())
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
                    parent_directory=parent_directory,
                    checkpoints=self.checkpoints,
                    timing=self.timing,
                    input_pins=[pin(selected)],
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
                                pin(Path(land) / name)
                                for name in ("rows.u32le", "runs.u32le", "report.json")
                            ],
                            reused=False,
                        )
                    output = context.water()
                finally:
                    context.close()
                receipt = dict(
                    directory=str(output),
                    definition_sha256=identity,
                    reused=False,
                    land=land_receipt,
                    outputs=[
                        pin(output / name)
                        for name in ("rows.u32le", "runs.u32le", "report.json")
                    ],
                )
            if not receipt_path.exists():
                write(receipt_path, receipt)
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
                        pin(selected),
                        *receipt["outputs"],
                        *[
                            pin(ownership / name)
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
            write(path, report)
        return report
