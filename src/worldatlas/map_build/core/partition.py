"""Run-interval regions separated by boundary cuts between cell centres."""

import math
from bisect import bisect_left
from collections import defaultdict
from collections.abc import Callable, Collection, Iterable, Iterator, Sequence
from fractions import Fraction
from itertools import groupby, pairwise
from pathlib import Path

import numpy as np
from shapely import (
    contains_xy,
    get_parts,
    line_merge,
    polygonize,
    remove_repeated_points,
    union_all,
)
from shapely.geometry import LineString, MultiLineString, Point, Polygon
from shapely.geometry.base import BaseGeometry

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.rle import open_mapped_array
from worldatlas.map_build.core.run_components import RunComponents
from worldatlas.map_build.execution.control import check_cancelled


class CutEdges:
    """Store which adjacent cells a source line separates.

    Horizontal cuts separate columns on one row. Vertical cuts separate
    rows in one column. A seam cut separates the last and first columns.
    """

    def __init__(self) -> None:
        """Start with no cuts or source paths."""
        self.horizontal = defaultdict(set)
        self.vertical = defaultdict(set)
        self.wrap = set()  # blocks (x=W-1) <-> (x=0) on this row
        self.paths = []

    def add_h(self, y: int, x: int) -> None:
        """Block the move between neighbouring columns.

        Args:
            y: Row of the blocked move.
            x: Column on the left of the cut.
        """
        self.horizontal[int(y)].add(int(x))

    def add_v(self, y: int, x: int) -> None:
        """Block the move between neighbouring rows.

        Args:
            y: Row above the cut.
            x: Column of the blocked move.
        """
        self.vertical[int(y)].add(int(x))

    def add_wrap(self, y: int) -> None:
        """Block the move between the last and first columns.

        Args:
            y: Row of the blocked move.
        """
        self.wrap.add(int(y))


def _scaled_segment(
    first: tuple[Fraction, Fraction], last: tuple[Fraction, Fraction]
) -> tuple[int, int, int, int, int]:
    """Put both endpoints and half-cell centres on one exact integer scale.

    Args:
        first: First endpoint in grid coordinates.
        last: Last endpoint in grid coordinates.

    Returns:
        (x0, y0, x1, y1, scale). Divide by scale to recover a coordinate.
    """
    coordinates = (*first, *last)
    scale = math.lcm(2, *(value.denominator for value in coordinates))
    x0, y0, x1, y1 = (
        value.numerator * (scale // value.denominator) for value in coordinates
    )
    return x0, y0, x1, y1, scale


def _scan_crossings(
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    scale: int,
    row_count: int,
    first_edge: int,
    last_edge: int,
    *,
    scan_rows: bool,
) -> Iterator[tuple[int, int]]:
    """Find which centre-to-centre edges a segment crosses.

    Resolve exact hits as if each centre moved south by t and west by t²
    as t tends to zero from above. The scan uses integers, including the
    exact sign of the segment's slope. It never moves the coordinates.

    Args:
        x0: Scaled first endpoint along the scanline.
        y0: Scaled first endpoint across scanlines.
        x1: Scaled last endpoint along the scanline.
        y1: Scaled last endpoint across scanlines.
        scale: Integer units in one cell.
        row_count: Number of scanlines.
        first_edge: Smallest edge index to consider.
        last_edge: Largest edge index to consider.
        scan_rows: True for east-west edges, false for north-south edges
            with the input axes swapped.

    Yields:
        (scanline index, edge index). An edge index is the column to its
        west on a row scan or the row to its north on a column scan.
    """
    if y0 == y1:
        # A parallel segment cannot intersect the shifted scanline.
        return
    if y0 > y1:
        x0, y0, x1, y1 = x1, y1, x0, y0

    # At an endpoint exactly on a scanline, looking south includes the
    # northern end. Looking west includes the eastern end instead.
    half = scale // 2
    endpoint_adjustment = int(scan_rows)
    first_row = max(0, (y0 + half - endpoint_adjustment) // scale)
    last_row = min(row_count - 1, (y1 - half - endpoint_adjustment) // scale)
    dx, dy = x1 - x0, y1 - y0
    denominator = scale * dy
    # When the crossing is exactly at a centre, the south step dominates.
    # On a row scan the crossing moves west only if the line slopes west as
    # it goes south. On a column scan the shifted centre is always farther
    # south than an exact centre crossing.
    use_previous_edge = not scan_rows or dx < 0
    for row in range(first_row, last_row + 1):
        # x at the crossing is (x0 * dy + offset * dx) / dy.
        # Subtract half a cell before division to index centre-to-centre edges.
        offset = row * scale + half - y0
        edge, remainder = divmod((x0 - half) * dy + offset * dx, denominator)
        if remainder == 0 and use_previous_edge:
            edge -= 1
        if first_edge <= edge <= last_edge:
            yield row, edge


def rasterize_barriers(
    paths: Iterable[Iterable[tuple[Fraction | float, Fraction | float]]],
    width: int,
    height: int,
) -> CutEdges:
    """Block moves between adjacent cell centres that cross a source line.

    Args:
        paths: Polylines in grid coordinates, where each cell centre is at a
            half-integer.
        width: Number of grid columns.
        height: Number of grid rows.

    Returns:
        Horizontal, vertical and seam cuts using the south-then-west
        convention for exact hits.
    """
    cuts = CutEdges()

    for path in paths:
        check_cancelled()
        # Keep the intersection math exact, including when two points would
        # round to the same float. Only consecutive identical points disappear.
        points = tuple(
            point for point, _ in groupby((Fraction(x), Fraction(y)) for x, y in path)
        )
        if len(points) < 2:
            continue
        # Keep the path passed to the geometric face builder in a stable order.
        points = min(points, points[::-1])
        cuts.paths.append(points)
        for first, last in pairwise(points):
            x0, y0, x1, y1, scale = _scaled_segment(first, last)
            # Crossings on a row block moves between columns. Swap the axes
            # to find crossings on a column that block moves between rows.
            for y, x in _scan_crossings(
                x0, y0, x1, y1, scale, height, -1, width - 2, scan_rows=True
            ):
                if x == -1:
                    cuts.add_wrap(y)
                else:
                    cuts.add_h(y, x)
            for x, y in _scan_crossings(
                y0, x0, y1, x1, scale, width, 0, height - 2, scan_rows=False
            ):
                cuts.add_v(y, x)
    return cuts


def split_eligible(
    intervals: Iterable[tuple[int, int]], blocked_edges: list[int], width: int
) -> list[tuple[int, int]]:
    """Cut open intervals into pieces at blocked horizontal connections.

    Args:
        intervals: Eligible (start, end) column pairs.
        blocked_edges: Sorted list of columns to the left of a cut.
        width: Number of grid columns.

    Returns:
        Smaller (start, end) pairs. For example, (0, 5) cut after column 2
        gives (0, 3) and (3, 5).

    Raises:
        ValueError: An input interval is outside the grid or empty.
    """
    out = []
    for a, b in intervals:
        if not (0 <= a < b <= width):
            raise ValueError(f"invalid eligible interval {(a, b)}")
        i = bisect_left(blocked_edges, a)
        j = bisect_left(blocked_edges, b - 1)
        start = a
        for edge in blocked_edges[i:j]:
            out.append((start, edge + 1))
            start = edge + 1
        out.append((start, b))
    return out


def _blocked_count(sorted_x: Sequence[int], lo: int, hi: int) -> int:
    """Count blocked columns within an interval.

    Args:
        sorted_x: Sorted columns with a blocked vertical edge.
        lo: First column in the interval.
        hi: Exclusive end column.

    Returns:
        Number of blocked columns in [lo, hi).
    """
    return bisect_left(sorted_x, hi) - bisect_left(sorted_x, lo)


def geographic_cuts(geometries: Iterable[dict], grid: Grid) -> CutEdges:
    """Translate WGS84 lines into cuts in the cell grid.

    Args:
        geometries: GeoJSON LineString and MultiLineString objects.
        grid: Grid on which to block connections.

    Returns:
        Cuts between cells, including across the longitude seam.
    """
    lines = []
    for geometry in geometries:
        if geometry["type"] == "LineString":
            lines.append(geometry["coordinates"])
        else:
            lines.extend(geometry["coordinates"])
    if len(lines) > 1:
        # A bend split between files must supply the same tangent as an
        # interior vertex. Join exact endpoints and leave branches at junctions.
        joined = line_merge(MultiLineString(lines))
        lines = [part.coords for part in get_parts(joined)]

    copies = []
    west, north, step = map(Fraction, (grid.west, grid.north, grid.step))
    for line in lines:
        coordinates = tuple(map(tuple, line))
        coordinates = min(coordinates, coordinates[::-1])
        path = []
        previous = None
        offset = 0
        for lon, lat in coordinates:
            longitude = Fraction(lon)
            if previous is not None:
                difference = longitude - previous
                if difference > 180:
                    offset -= 360
                elif difference < -180:
                    offset += 360
            path.append(
                (
                    (longitude + offset - west) / step,
                    (north - Fraction(lat)) / step,
                )
            )
            previous = longitude
        # A path can wrap around the globe more than once. Keep every copy
        # that reaches the grid or its one-column margin at the longitude seam.
        west_column = min(x for x, _ in path)
        east_column = max(x for x, _ in path)
        first_turn = math.ceil((-1 - east_column) / grid.width)
        last_turn = math.floor((grid.width + 1 - west_column) / grid.width)
        for turn in range(first_turn, last_turn + 1):
            shift = turn * grid.width
            copies.append([(x + shift, y) for x, y in path])
    return rasterize_barriers(copies, grid.width, grid.height)


def _extend_past_corridor(
    endpoint: np.ndarray,
    outward: np.ndarray,
    corridor: BaseGeometry,
    ray_length: float,
) -> np.ndarray:
    """Find a point beyond the first corridor exit from a line endpoint.

    Args:
        endpoint: Length-two array of endpoint grid coordinates.
        outward: Length-two array pointing away from the adjacent vertex.
        corridor: Area around the original boundary lines.
        ray_length: Length in cells sufficient to cross the whole corridor.

    Returns:
        Length-two array of grid coordinates one cell past the exit.
    """
    length = np.linalg.norm(outward)
    ray = LineString([endpoint, endpoint + ray_length * outward / length])
    endpoint_point = Point(endpoint)
    for part in get_parts(ray.intersection(corridor)):
        if part.geom_type == "LineString" and part.distance(endpoint_point) == 0:
            # The ray can re-enter the corridor. Use the part that starts at
            # the boundary endpoint and runs to the first exit.
            exit_point = max(
                part.coords,
                key=lambda point: np.linalg.norm(np.asarray(point) - endpoint),
            )
            return np.asarray(exit_point) + outward / length
    # The endpoint is already at the edge when the ray leaves immediately.
    return endpoint + outward / length


def _boundary_corridor_faces(
    paths: Iterable[Sequence[tuple[Fraction, Fraction]]],
) -> list[Polygon]:
    """Build the continuous faces near the boundary lines.

    Args:
        paths: Lines in grid coordinates, with consecutive duplicates removed.

    Returns:
        Shapely polygons inside the corridor on each side of the source lines.
    """
    # Shapely uses floats. Distinct fractions can become identical upon
    # conversion. Drop exact duplicates in this representation as well.
    lines = [remove_repeated_points(LineString(path), tolerance=0) for path in paths]
    lines = [line for line in lines if line.length > 0]
    if not lines:
        return []
    # Simplify only the shape used to find nearby cells. Draw the actual
    # divisions inside that shape using the full source lines.
    corridor = union_all(
        [line.simplify(0.25).buffer(2, cap_style="flat", quad_segs=1) for line in lines]
    )
    west, north, east, south = corridor.bounds
    ray_length = 2 * math.hypot(east - west, south - north)
    # Close faces against the corridor edge so a line that stops within
    # the corridor can still separate the cells on its two sides.
    extended = []
    for line in lines:
        points = np.asarray(line.coords)
        first = _extend_past_corridor(
            points[0], points[0] - points[1], corridor, ray_length
        )
        last = _extend_past_corridor(
            points[-1], points[-1] - points[-2], corridor, ray_length
        )
        extended.append(LineString([first, *points, last]))
    network = union_all([corridor.boundary, *extended])
    return [
        face
        for face in get_parts(polygonize(get_parts(network)))
        if corridor.covers(face.representative_point())
    ]


def continuous_face_links(
    path: Path,
    offsets: Sequence[int],
    paths: Iterable[Sequence[tuple[Fraction, Fraction]]],
    dsu: RunComponents,
    uncut: RunComponents,
    grid: Grid,
) -> None:
    """Rejoin pieces of the same geometric face through a narrow passage.

    A passage may be too narrow to contain a path through neighbouring cell
    centres. Rejoin runs that touch the same face and belonged to the same
    connected part of the scope before applying the boundary.

    Args:
        path: Binary file of (first_column, end_column, node_id) records.
        offsets: Run-record offsets for each row, with an ending offset.
        paths: Boundary paths in grid coordinates.
        dsu: Sets of connected runs to update.
        uncut: Sets of connected scope runs before applying the boundary.
        grid: Grid occupied by the runs.
    """
    faces = _boundary_corridor_faces(paths)
    with open_mapped_array(path, "<u4") as node_values:
        nodes = node_values.reshape(-1, 3)
        for face in faces:
            xmin, ymin, xmax, ymax = face.bounds
            scope_nodes = {}
            for y in range(
                max(0, math.floor(ymin)), min(grid.height, math.floor(ymax) + 1)
            ):
                check_cancelled()
                current = nodes[offsets[y] : offsets[y + 1]]
                first = np.searchsorted(current[:, 1], xmin, side="right")
                last = np.searchsorted(current[:, 0], xmax, side="left")
                for left, right, node in current[first:last]:
                    left, right = (
                        max(int(left), math.floor(xmin)),
                        min(int(right), math.floor(xmax) + 1),
                    )
                    centre_columns = np.arange(left, right, dtype=float) + 0.5
                    if contains_xy(face, centre_columns, y + 0.5).any():
                        node = int(node)
                        scope_root = uncut.find(node)
                        dsu.union(scope_nodes.setdefault(scope_root, node), node)


def divide_regions(
    eligible_rows: Callable[[int], Iterable[tuple[int, int]]],
    grid: Grid,
    cuts: CutEdges,
    labels: Sequence[tuple[int, int, int]],
    directory: Path | str,
    *,
    rows: Collection[int] | None = None,
) -> dict[int, int]:
    """Build and label connected regions without expanding runs into cells.

    Args:
        eligible_rows: For each row, gives the sorted eligible column intervals.
        grid: Grid to divide.
        cuts: Connections blocked by boundaries.
        labels: (entity_id, column, row) for each label cell.
        directory: New directory for node records and row offsets.
        rows: Optional subset of grid rows to consider.

    Returns:
        Dictionary that maps a connected region's root ID to its owner ID.
        Unlabelled regions are absent from the dictionary.

    Raises:
        ValueError: A label falls outside the scope, labels disagree within
            a region, or an interval is invalid.
    """
    directory = Path(directory)
    directory.mkdir()
    labels_by_row = defaultdict(list)
    for index, (entity, x, y) in enumerate(labels):
        if (
            not 0 < entity < 2**32
            or not 0 <= x < grid.width
            or not 0 <= y < grid.height
        ):
            raise ValueError("invalid divided-face label")
        labels_by_row[y].append((index, entity, x))
    dsu = RunComponents()
    uncut = RunComponents() if cuts.paths else None
    offsets = [0]
    previous = []
    label_nodes = {}
    rows = range(grid.height) if rows is None else rows
    with (directory / "nodes.u32le").open("xb") as output:
        for y in range(grid.height):
            check_cancelled()
            if y not in rows:
                offsets.append(len(dsu))
                previous = []
                continue
            raw = list(eligible_rows(y))
            if raw != sorted(raw) or any(a[1] > b[0] for a, b in zip(raw, raw[1:])):
                raise ValueError("partition scope intervals overlap or are unordered")
            current = []
            horizontal_cuts = cuts.horizontal.get(y, ())
            for a, b in split_eligible(raw, sorted(horizontal_cuts), grid.width):
                node = dsu.add()
                if uncut is not None:
                    uncut.add()
                # Adjacent input spans can share a face even when supplied
                # separately. A cut between them is the only barrier here.
                if current and current[-1][1] == a:
                    left_node = current[-1][2]
                    if uncut is not None:
                        uncut.union(left_node, node)
                    if a - 1 not in horizontal_cuts:
                        dsu.union(left_node, node)
                current.append((a, b, node))
                for index, entity, x in labels_by_row.get(y, ()):
                    if a <= x < b:
                        label_nodes[index] = (entity, node)
            if previous and current:
                blocked = sorted(cuts.vertical.get(y - 1, ()))
                i = j = 0
                while i < len(previous) and j < len(current):
                    a, b, n = previous[i]
                    c, d, m = current[j]
                    lo, hi = max(a, c), min(b, d)
                    if lo < hi:
                        if uncut is not None:
                            uncut.union(n, m)
                        if hi - lo > _blocked_count(blocked, lo, hi):
                            dsu.union(n, m)
                    if b <= d:
                        i += 1
                    if d <= b:
                        j += 1
            if current and current[0][0] == 0 and current[-1][1] == grid.width:
                if uncut is not None:
                    uncut.union(current[0][2], current[-1][2])
                if y not in cuts.wrap:
                    dsu.union(current[0][2], current[-1][2])
            np.asarray(current, dtype="<u4").tofile(output)
            offsets.append(len(dsu))
            previous = current
    if len(label_nodes) != len(labels):
        raise ValueError("a divided-face label lies outside the computational scope")
    initial_roots = np.fromiter((dsu.find(i) for i in range(len(dsu))), dtype=np.uint32)
    distinct, inverse = np.unique(initial_roots, return_inverse=True)
    # Join pieces in the same geometric face before checking its labels.
    if len(distinct) > 1 and uncut is not None:
        continuous_face_links(
            directory / "nodes.u32le", offsets, cuts.paths, dsu, uncut, grid
        )
    roots = np.fromiter((dsu.find(int(root)) for root in distinct), dtype=np.uint32)[
        inverse
    ]
    owners = {}
    for entity, node in label_nodes.values():
        root = dsu.find(node)
        if root in owners and owners[root] != entity:
            raise ValueError(
                f"conflicting labels {owners[root]} and {entity} share a face"
            )
        owners[root] = entity
    np.asarray(offsets, dtype="<u8").tofile(directory / "rows.u64le")
    # Save the final component ID in each run so readers can use it directly.
    with open_mapped_array(directory / "nodes.u32le", "<u4", writable=True) as nodes:
        records = nodes.reshape(-1, 3)
        records[:, 2] = roots[records[:, 2]]
    return owners
