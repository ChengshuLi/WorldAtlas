"""Resolve geographic selectors independently of ownership and distance policy."""

import math

import numpy as np
from shapely.geometry import mapping, shape
from shapely import union_all

from worldatlas.map_build.core.geometry import PolygonRasterizer
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
    """Fill gaps and coalesce sparse intervals without per-run Python appends."""
    if not len(records):
        return np.array([width], dtype=np.uint32), np.array([0], dtype=np.uint32)
    items = np.asarray(records)
    if (
        items.ndim != 2
        or items.shape[1] != 3
        or not np.issubdtype(items.dtype, np.integer)
    ):
        raise ValueError("scope intervals require integer start, end and value")
    starts, ends, values = items.T
    if (
        np.any(starts < 0)
        or np.any(starts >= ends)
        or np.any(ends > width)
        or np.any(starts[1:] < ends[:-1])
        or np.any(values < 0)
        or np.any(values > np.iinfo(np.uint32).max)
    ):
        raise ValueError("scope intervals overlap or escape the grid")
    stops = np.r_[np.column_stack((starts, ends)).ravel(), width]
    codes = np.r_[
        np.column_stack((np.zeros(len(items), dtype=np.uint32), values)).ravel(), 0
    ]
    nonempty = stops > np.r_[0, stops[:-1]]
    stops, codes = stops[nonempty], codes[nonempty]
    last = np.r_[codes[:-1] != codes[1:], True]
    return stops[last].astype(np.uint32), codes[last].astype(np.uint32)


class Scope:
    """Keep geometric construction context intact while filtering output cells.

    components(kind) returns the parent's physical ComponentGrid for land/water.
    Geometry batches are ordinary streaming rasterization buffers, not resource
    limits. Reference sets and component populations never use the ownership mask.
    """

    def __init__(
        self, rule, grid, physical, parent, snapshot, components, *, connectivity=None
    ):
        self.rule, self.grid = rule, grid
        self.physical, self.parent, self.snapshot = physical, parent, snapshot
        self.components = components
        self.connectivity = connectivity
        self.connectivity_domain = None
        self.connected = None
        self.connectivity_receipt = []
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
        self.eligible_area = None
        self.rasterizer = None
        self.populations = {}
        positions = np.flatnonzero(parent[1][1::2])
        if len(positions):
            first, last = (
                np.searchsorted(parent[0], positions[[0, -1]], side="right") - 1
            )
            self.parent_rows = int(first), int(last) + 1
        else:
            self.parent_rows = 0, 0
        self._context_rows = self._query_rows = None
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

    def context_rows(self):
        """Bound geometric context without applying ownership or physical filters."""
        if self._context_rows is None:
            ranges = []
            if not self.restricted:
                ranges.append(self.parent_rows)
            if self.bounds:
                ranges.append(self.bounds[2:])
            ranges.extend(
                self.components(kind).row_bounds(ids)
                for kind, ids in self.points.items()
                if len(ids)
            )
            ranges = [(a, b) for a, b in ranges if a < b]
            self._context_rows = (
                (
                    max(self.parent_rows[0], min(a for a, _ in ranges)),
                    min(self.parent_rows[1], max(b for _, b in ranges)),
                )
                if ranges
                else (0, 0)
            )
        return range(*self._context_rows)

    def query_rows(self):
        """Skip empty rows; majority-selected components keep their full extent."""
        if self._query_rows is None:
            if self.rule["unit"] == "cell" or not self.restricted:
                rows = self.context_rows()
                self._query_rows = rows.start, rows.stop
            else:
                bounds = [
                    self.components(kind).row_bounds(ids)
                    for kind, ids in self.eligible_components().items()
                    if len(ids)
                ]
                self._query_rows = (
                    (min(a for a, _ in bounds), max(b for _, b in bounds))
                    if bounds
                    else (0, 0)
                )
        return range(*self._query_rows)

    def area_row(self, y):
        if self.geometry is None:
            return complete_row(self.grid.width, ())
        x0, x1, y0, y1 = self.bounds
        if not y0 <= y < y1:
            return complete_row(self.grid.width, ())
        first = y0 + (y - y0) // 64 * 64
        last = min(first + 64, y1)
        if self.batch is None or self.batch[0] != first:
            if self.rasterizer is None:
                self.rasterizer = PolygonRasterizer(self.geometry, self.grid)
            self.batch = (
                first,
                self.rasterizer.rasterize((x0, x1, first, last))[1],
            )
        return self.mask_row(self.batch[1][y - first])

    def set_eligible_area(self, values, bounds):
        """Reuse a complete area already clipped to physical class and parent.

        This is an output-query representation, not geometric construction
        context. Ownership filtering and connectivity remain separate.
        """
        if (
            self.rule["unit"] != "cell"
            or self.rule["features"].get("scope_component")
            or tuple(bounds) != self.bounds
            or values.dtype != np.bool_
            or values.shape != (bounds[3] - bounds[2], bounds[1] - bounds[0])
        ):
            raise ValueError("prepared area does not represent this cell scope")
        self.eligible_area = values

    def mask_row(self, values):
        x0, x1 = self.bounds[:2]
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
            parts = self.components(kind).row(y)
            parts = parts[selected(parts[:, 2], ids)]
            if len(parts):
                records.append(
                    np.column_stack(
                        (parts[:, :2], np.ones(len(parts), dtype=np.uint32))
                    )
                )
        if not records:
            return complete_row(self.grid.width, ())
        parts = np.concatenate(records)
        return complete_row(
            self.grid.width, parts[np.argsort(parts[:, 0], kind="stable")]
        )

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
            self.mask_row(self.eligible_area[y - self.bounds[2]])
            if self.eligible_area is not None
            else (
                self.context_row(y)
                if self.rule["unit"] == "cell" or not self.restricted
                else self.component_row(y, self.eligible_components())
            )
        )
        references = self.rule["features"].get("connected_to")
        if not references:
            if self.eligible_area is not None:
                if not self.rule["unassigned_only"]:
                    return chosen
                a, b, (mask, owners) = overlay(
                    chosen, row(self.snapshot, y, self.grid.width)
                )
                return complete_row(
                    self.grid.width,
                    np.column_stack((a, b, (mask != 0) & (owners == 0))),
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
        if self.connectivity_domain is None:
            if self.connectivity is None:
                raise ValueError("connected_to requires eligible parent connectivity")
            self.connectivity_domain = self.connectivity(
                self.rule["physical_class"], self.rule["unassigned_only"]
            )
        data = self.connectivity_domain
        # The shared domain already applies parent, physical and ownership
        # eligibility. Intersect with geometry without filtering ownership again.
        a, b, (selected_scope, domain) = overlay(
            chosen, row(data.physical, y, self.grid.width)
        )
        eligible = complete_row(
            self.grid.width, np.column_stack((a, b, selected_scope & domain))
        )
        if not np.any(eligible[1]):
            return eligible
        if self.connected is None:
            roots = set()
            for feature in references:
                lon, lat = feature["geometry"]["coordinates"]
                root = data.component_at(lon, lat)
                if root is None:
                    raise ValueError(
                        f"rule {self.rule['id']}: connectivity reference {lon},{lat} is not eligible parent territory"
                    )
                roots.add(root)
                self.connectivity_receipt.append(
                    dict(
                        longitude=lon,
                        latitude=lat,
                        component=root,
                        component_cells=data.totals()[root],
                    )
                )
            self.connected = data, np.asarray(sorted(roots), dtype=np.uint32)
        data, roots = self.connected
        parts = data.row(y)
        parts = parts[selected(parts[:, 2], roots)]
        connected = complete_row(
            self.grid.width,
            np.column_stack((parts[:, :2], np.ones(len(parts), dtype=np.uint32))),
        )
        a, b, (chosen, within) = overlay(eligible, connected)
        return complete_row(self.grid.width, np.column_stack((a, b, chosen & within)))

    def query_windows(self, rows_per_batch=64):
        """Yield row batches and disjoint dense windows without needless recoding."""
        rows = self.query_rows()
        for first in range(rows.start, rows.stop, rows_per_batch):
            last = min(first + rows_per_batch, rows.stop)
            if self.eligible_area is not None and not self.rule["features"].get(
                "connected_to"
            ):
                x0, x1, y0, _ = self.bounds
                windows = []
                for left, right in (
                    (x0, min(x1, self.grid.width)),
                    (0, max(0, x1 - self.grid.width)),
                ):
                    if left == right:
                        continue
                    offset = (left - x0) % self.grid.width
                    mask = self.eligible_area[
                        first - y0 : last - y0, offset : offset + right - left
                    ]
                    if self.rule["unassigned_only"]:
                        from worldatlas.map_build.water.shared_nearest import crop

                        owners = np.stack(
                            [
                                crop(*self.snapshot, y, left, right, self.grid.width)
                                for y in range(first, last)
                            ]
                        )
                        mask = mask & (owners == 0)
                    if mask.any():
                        windows.append((left, right, mask))
                if windows:
                    yield first, last, windows
                continue
            queries = [self.query_row(y) for y in range(first, last)]
            active = [
                (np.r_[0, ends[:-1]][values != 0], ends[values != 0])
                for ends, values in queries
            ]
            if not any(len(a) for a, _ in active):
                continue
            left = min(int(a[0]) for a, _ in active if len(a))
            right = max(int(b[-1]) for a, b in active if len(a))
            masks = []
            for ends, values in queries:
                cuts = np.r_[left, ends[(ends > left) & (ends < right)], right]
                chosen = values[np.searchsorted(ends, cuts[:-1], side="right")]
                masks.append(np.repeat(chosen != 0, np.diff(cuts)))
            yield first, last, [(left, right, np.asarray(masks, dtype=bool))]

    def has_output(self):
        return any(np.any(self.query_row(y)[1]) for y in self.query_rows())

    def context_intervals(self, y):
        ends, values = self.context_row(y)
        starts = np.r_[0, ends[:-1]]
        return [(int(a), int(b)) for a, b, v in zip(starts, ends, values) if v]
