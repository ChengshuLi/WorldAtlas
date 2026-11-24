"""Resolve geographic selectors independently of ownership and distance policy."""

from collections.abc import Callable, Iterator, Sequence

import numpy as np
from shapely import union_all
from shapely.geometry import shape

from worldatlas.map_build.core.geometry import PolygonRasterizer, polygon_grid_bounds
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import column_spans
from worldatlas.map_build.core.rle import crop, row
from worldatlas.map_build.division.contracts import CompiledRule, point_coordinates
from worldatlas.map_build.division.intervals import overlay, prepare
from worldatlas.map_build.execution.control import check_cancelled
from worldatlas.map_build.land.components import ComponentGrid


def selected(values: np.ndarray, identifiers: Sequence[int] | np.ndarray) -> np.ndarray:
    """Check each value against a sorted list of IDs.

    Args:
        values: 1-D array of IDs to check.
        identifiers: Sorted allowed IDs.

    Returns:
        Bool array marking allowed values in input order.
    """
    identifiers = np.asarray(identifiers, dtype=np.uint32)
    if not len(identifiers):
        return np.zeros(len(values), dtype=bool)
    positions = np.searchsorted(identifiers, values)
    safe = np.minimum(positions, len(identifiers) - 1)
    return (positions < len(identifiers)) & (identifiers[safe] == values)


def complete_row(
    width: int, records: Sequence[tuple[int, int, int]] | np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Fill the gaps between sparse intervals with zero.

    Args:
        width: Number of cells in the row.
        records: Ordered (first_column, end_column, code) records.

    Returns:
        Two uint32 arrays of exclusive end columns and codes. Adjacent
        runs with the same code share one entry.

    Raises:
        ValueError: Records are malformed, overlap, or extend past the row.
    """
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
    """Prepare the geographic scope and eligible cells of one rule.

    The geographic scope is where lines can divide the grid. A rule's class,
    component selection, and previous owners determine which cells can receive
    its assignment.
    """

    def __init__(
        self,
        rule: CompiledRule,
        grid: Grid,
        physical: tuple[np.ndarray, np.ndarray],
        parent: tuple[np.ndarray, np.ndarray],
        snapshot: tuple[np.ndarray, np.ndarray],
        components: Callable[[str], ComponentGrid],
        *,
        connectivity: Callable[[str, bool], ComponentGrid] | None = None,
    ) -> None:
        """Resolve a rule's polygon and component selectors.

        Args:
            rule: Compiled rule with its scope features and output filters.
            grid: Dimensions and coordinates of the build grid.
            physical: Physical row offsets and run data.
            parent: Row-run mask of the parent's cells.
            snapshot: Ownership streams from before this rule group.
            components: Look up the parent's land or water components by class.
            connectivity: Optional lookup for the connected components in the rule's
                eligible domain.

        Raises:
            ValueError: A scope point does not identify a compatible component.
        """
        self.rule, self.grid = rule, grid
        self.physical, self.parent, self.snapshot = physical, parent, snapshot
        self.components = components
        self.connectivity = connectivity
        self.connectivity_domain = None
        self.connected = None
        self.connectivity_receipt = []
        point_roots: dict[str, set[int]] = {"land": set(), "water": set()}
        inputs = rule["features"]
        self.restricted = bool(
            inputs.get("scope_area") or inputs.get("scope_component")
        )
        areas = [shape(dict(f["geometry"])) for f in inputs.get("scope_area", ())]
        self.geometry = union_all(areas) if areas else None
        self.bounds = (
            polygon_grid_bounds(self.geometry, grid)
            if self.geometry is not None
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
        self._context_rows: tuple[int, int] | None = None
        self._query_rows: tuple[int, int] | None = None
        for point in inputs.get("scope_component", ()):
            lon, lat = point_coordinates(point)
            cell = grid.cell_at(lon, lat)
            if cell is None:
                raise ValueError("scope component point is outside the grid")
            x, y = cell
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
            point_roots[kind].add(root)
        self.points = {
            kind: np.asarray(sorted(roots), dtype=np.uint32)
            for kind, roots in point_roots.items()
        }
        self._query_roots: set[int]

    def context_rows(self) -> range:
        """Find rows that can contain the rule's unfiltered geographic scope.

        Returns:
            Range of row indices, before filtering by class or current owner.
        """
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

    def query_rows(self) -> range:
        """Find which rows may receive the rule's assignment.

        Returns:
            Range of row indices to check for eligible cells.
        """
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

    def area_row(self, y: int) -> tuple[np.ndarray, np.ndarray]:
        """Read the polygon coverage in one row, rasterizing a batch as needed.

        Args:
            y: Zero-based row index.

        Returns:
            Run ends and values as uint32 arrays. Value 1 marks a covered cell.
        """
        if self.geometry is None or self.bounds is None:
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

    def set_eligible_area(
        self, values: np.ndarray, bounds: tuple[int, int, int, int]
    ) -> None:
        """Reuse an already rasterized scope, such as the water part of a basin.

        Args:
            values: Two-dimensional bool mask.
            bounds: Grid window represented by the mask.

        Raises:
            ValueError: The supplied mask does not match this rule's area.
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

    def mask_row(self, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Convert a row of the scope mask to full-width runs.

        Args:
            values: Bool values in the polygon's window, which may wrap.

        Returns:
            Run ends and values as uint32 arrays, with zero beyond the mask.
        """
        assert self.bounds is not None
        x0, x1 = self.bounds[:2]
        return complete_row(
            self.grid.width, column_spans(values, x0, x1, self.grid.width)
        )

    def component_row(
        self, y: int, roots: dict[str, np.ndarray]
    ) -> tuple[np.ndarray, np.ndarray]:
        """Mark cells in the selected physical components in one row.

        Args:
            y: Row index.
            roots: Sorted component IDs for each physical class.

        Returns:
            Run ends and values as uint32 arrays. Selected cells have value 1.
        """
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

    def context_row(self, y: int) -> tuple[np.ndarray, np.ndarray]:
        """Combine polygon and point-selected scope inside the parent.

        Args:
            y: Row index.

        Returns:
            Run ends and values as uint32 arrays. Value 1 marks the scope.
        """
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

    def eligible_components(self) -> dict[str, np.ndarray]:
        """Select whole components by point or majority polygon coverage.

        Returns:
            Physical classes mapped to sorted uint32 arrays of component IDs.
            A polygon selects a component when it covers over half of its cells.
        """
        if self.populations:
            return self.populations
        kinds = (
            ("land", "water")
            if self.rule["physical_class"] == "mixed"
            else (self.rule["physical_class"],)
        )
        if not self.context_rows():
            self.populations = {kind: np.empty(0, dtype=np.uint32) for kind in kinds}
            return self.populations
        for kind in kinds:
            components = self.components(kind)
            totals = components.totals()
            if not self.restricted:
                roots = set(totals)
            else:
                counts = (
                    components.profile(self.geometry)
                    if self.geometry is not None
                    else {}
                )
                roots = set(map(int, self.points[kind])) | {
                    root for root, n in counts.items() if 2 * n > totals[root]
                }
            self.populations[kind] = np.asarray(sorted(roots), dtype=np.uint32)
        return self.populations

    def query_row(self, y: int) -> tuple[np.ndarray, np.ndarray]:
        """Find the cells a rule can assign on a row.

        Args:
            y: Row index.

        Returns:
            Run ends and values as uint32 arrays. Value 1 marks eligible cells
            after applying physical class, existing ownership, and connectivity.
        """
        check_cancelled()
        if self.eligible_area is not None:
            assert self.bounds is not None
            chosen = self.mask_row(self.eligible_area[y - self.bounds[2]])
        elif self.rule["unit"] == "cell" or not self.restricted:
            chosen = self.context_row(y)
        else:
            chosen = self.component_row(y, self.eligible_components())
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
        # The domain already contains only cells this rule can claim. Keep
        # the cells that also lie within the selected polygon or component.
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
                lon, lat = point_coordinates(feature)
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

    def query_windows(
        self, rows_per_batch: int = 64
    ) -> Iterator[tuple[int, int, list[tuple[int, int, np.ndarray]]]]:
        """Read eligible cells in batches for nearest-shore calculations.

        Args:
            rows_per_batch: Number of rows to process together.

        Yields:
            (first_row, end_row, windows). Each window has its first column,
            exclusive end column, and a 2-D bool mask.
        """
        rows = self.query_rows()
        for first in range(rows.start, rows.stop, rows_per_batch):
            check_cancelled()
            last = min(first + rows_per_batch, rows.stop)
            if self.eligible_area is not None and not self.rule["features"].get(
                "connected_to"
            ):
                assert self.bounds is not None
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

    def has_output(self) -> bool:
        """Check whether a rule can claim any cell.

        Returns:
            True if any row contains eligible cells.
        """
        return any(np.any(self.query_row(y)[1]) for y in self.query_rows())

    def context_intervals(self, y: int) -> list[tuple[int, int]]:
        """Read the parts of a row available for boundary division.

        Args:
            y: Row index.

        Returns:
            (first_column, end_column) spans in the geographic scope.
        """
        ends, values = self.context_row(y)
        starts = np.r_[0, ends[:-1]]
        return [(int(a), int(b)) for a, b, v in zip(starts, ends, values) if v]
