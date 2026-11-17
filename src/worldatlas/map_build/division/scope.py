"""Resolve geographic selectors independently of ownership and distance policy."""

import math

import numpy as np
from shapely.geometry import mapping, shape
from shapely import union_all

from worldatlas.map_build.core.geometry import rasterize
from worldatlas.map_build.core.rle import row
from worldatlas.map_build.core.wrapping import wrapped_grid_bounds
from worldatlas.map_build.division.intervals import overlay, prepare


def selected(values, identifiers):
    identifiers = np.asarray(identifiers, dtype=np.uint32)
    if not len(identifiers):
        return np.zeros(len(values), dtype=bool)
    positions = np.searchsorted(identifiers, values)
    safe = np.minimum(positions, len(identifiers) - 1)
    return (positions < len(identifiers)) & (identifiers[safe] == values)


def complete_row(width, records):
    """Convert sparse disjoint spans into a complete canonical RLE row."""
    stops = []
    values = []
    cursor = 0

    def append(end, value):
        if values and values[-1] == value:
            stops[-1] = end
        else:
            stops.append(end)
            values.append(value)

    for a, b, value in records:
        if not cursor <= a < b <= width:
            raise ValueError("scope intervals overlap or escape the grid")
        if a > cursor:
            append(a, 0)
        append(b, value)
        cursor = b
    if cursor < width:
        append(width, 0)
    return np.asarray(stops, dtype=np.uint32), np.asarray(values, dtype=np.uint32)


class Scope:
    """Keep geometric construction context intact while filtering output cells.

    components(kind) returns the parent's physical ComponentGrid for land/water.
    Geometry batches are ordinary streaming rasterization buffers, not resource
    limits. Reference sets and component populations never use the ownership mask.
    """

    def __init__(self, rule, grid, physical, parent, snapshot, components):
        self.rule, self.grid = rule, grid
        self.physical, self.parent, self.snapshot = physical, parent, snapshot
        self.components = components
        self.points = {"land": set(), "water": set()}
        inputs = rule["features"]
        self.restricted = bool(
            inputs.get("scope_area") or inputs.get("scope_component")
        )
        areas = [shape(f["geometry"]) for f in inputs.get("scope_area", ())]
        self.geometry = mapping(union_all(areas)) if areas else None
        self.bounds = (
            wrapped_grid_bounds(self.geometry, grid.width, grid.height, grid.step)[0]
            if areas
            else None
        )
        self.batch = None
        self.area_buffer = None
        self.populations = {}
        for point in inputs.get("scope_component", ()):
            lon, lat = point["geometry"]["coordinates"]
            x = math.floor((lon - grid.west) / grid.step) % grid.width
            y = math.floor((grid.north - lat) / grid.step)
            if not 0 <= y < grid.height:
                raise ValueError("scope component point is outside the grid")
            ends, codes = row(physical, y, grid.width)
            code = int(codes[np.searchsorted(ends, x, side="right")])
            kind = {17: "land", 1: "water"}.get(code)
            if kind is None:
                raise ValueError("scope component point is outside the physical domain")
            if rule["physical_class"] != "mixed" and rule["physical_class"] != kind:
                raise ValueError("scope component has an incompatible physical class")
            root = components(kind).component_at(lon, lat)
            if root is None:
                raise ValueError("scope component point is outside the parent")
            self.points[kind].add(root)
        self.points = {
            kind: np.asarray(sorted(roots), dtype=np.uint32)
            for kind, roots in self.points.items()
        }

    def area_row(self, y):
        if self.geometry is None:
            return complete_row(self.grid.width, ())
        x0, x1, y0, y1 = self.bounds
        if not y0 <= y < y1:
            return complete_row(self.grid.width, ())
        if self.area_buffer is not None:
            values = self.area_buffer[y - y0]
        else:
            first = y0 + (y - y0) // 64 * 64
            last = min(first + 64, y1)
            if self.batch is None or self.batch[0] != first:
                self.batch = (
                    first,
                    rasterize(self.geometry, self.grid, (x0, x1, first, last))[1],
                )
            values = self.batch[1][y - first]
        records = []
        for a, b in ((x0, min(x1, self.grid.width)), (0, max(0, x1 - self.grid.width))):
            if a == b:
                continue
            offset = (a - x0) % self.grid.width
            v = values[offset : offset + b - a]
            cuts = np.r_[0, np.flatnonzero(v[1:] != v[:-1]) + 1, len(v)]
            records.extend(
                (a + int(lo), a + int(hi), 1) for lo, hi in zip(cuts, cuts[1:]) if v[lo]
            )
        return complete_row(self.grid.width, sorted(records))

    def component_row(self, y, roots):
        records = []
        for kind, ids in roots.items():
            if not len(ids):
                continue
            spans = self.components(kind).row(y)
            for a, b, _ in spans[selected(spans[:, 2], ids)]:
                records.append((int(a), int(b), 1))
        return complete_row(self.grid.width, sorted(records))

    def context_row(self, y):
        if not self.restricted:
            return row(self.parent, y, self.grid.width)
        a, b, values = overlay(
            self.area_row(y),
            self.component_row(y, self.points),
            row(self.parent, y, self.grid.width),
        )
        mask = ((values[0] != 0) | (values[1] != 0)) & (values[2] != 0)
        return complete_row(
            self.grid.width,
            [(int(lo), int(hi), 1) for lo, hi, on in zip(a, b, mask) if on],
        )

    def eligible_components(self):
        if self.populations:
            return self.populations
        kinds = (
            ("land", "water")
            if self.rule["physical_class"] == "mixed"
            else (self.rule["physical_class"],)
        )
        for kind in kinds:
            components = self.components(kind)
            totals = components.totals()
            if not self.restricted:
                roots = set(totals)
            else:
                counts = components.profile(self.geometry) if self.geometry else {}
                roots = set(map(int, self.points[kind])) | {
                    root for root, n in counts.items() if 2 * n > totals[root]
                }
            self.populations[kind] = np.asarray(sorted(roots), dtype=np.uint32)
        return self.populations

    def query_row(self, y):
        chosen = (
            self.context_row(y)
            if self.rule["unit"] == "cell"
            else self.component_row(y, self.eligible_components())
        )
        result = prepare(
            row(self.physical, y, self.grid.width),
            row(self.parent, y, self.grid.width),
            chosen,
            row(self.snapshot, y, self.grid.width),
            physical_class=self.rule["physical_class"],
            unassigned_only=self.rule["unassigned_only"],
        )
        return complete_row(self.grid.width, result)

    def has_output(self):
        return any(np.any(self.query_row(y)[1]) for y in range(self.grid.height))

    def context_intervals(self, y):
        ends, values = self.context_row(y)
        starts = np.r_[0, ends[:-1]]
        return [(int(a), int(b)) for a, b, v in zip(starts, ends, values) if v]
