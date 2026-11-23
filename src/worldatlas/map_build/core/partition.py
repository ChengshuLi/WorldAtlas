"""Run-interval regions separated by boundary cuts between cell centres."""

import math
from array import array
from bisect import bisect_left
from collections import defaultdict
from collections.abc import Callable, Collection, Iterable, Iterator, Sequence
from fractions import Fraction
from pathlib import Path

import numpy as np
from shapely import contains_xy, get_parts, line_merge, polygonize, union_all
from shapely.geometry import LineString, MultiLineString, Point

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.rle import close_memmap
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
) -> Iterator[tuple[int, int, bool]]:
    """Find where a segment cuts between cell centres on each row.

    If a segment lies along a row, it blocks only the partially covered
    connections at its ends. Connections fully on the line stay open.

    Args:
        x0: Scaled first endpoint column.
        y0: Scaled first endpoint row.
        x1: Scaled last endpoint column.
        y1: Scaled last endpoint row.
        scale: Integer units in one cell.
        row_count: Number of grid rows.
        first_edge: Smallest edge index to consider.
        last_edge: Largest edge index to consider.

    Yields:
        (row, edge, hits_centre). Edge is the column on the left of the cut.
    """
    half = scale // 2
    if y0 == y1:
        row, remainder = divmod(y0 - half, scale)
        if remainder == 0 and 0 <= row < row_count:
            for endpoint in sorted({x0, x1}):
                edge, remainder = divmod(endpoint - half, scale)
                if remainder and first_edge <= edge <= last_edge:
                    yield row, edge, False
        return
    if y0 > y1:
        x0, y0, x1, y1 = x1, y1, x0, y0

    first_row = max(0, (y0 + half - 1) // scale)
    last_row = min(row_count - 1, (y1 - half) // scale)
    dx, dy = x1 - x0, y1 - y0
    denominator = scale * dy
    for row in range(first_row, last_row + 1):
        # x at the crossing is (x0 * dy + offset * dx) / dy.
        # Subtract half a cell before division to index centre-to-centre edges.
        offset = row * scale + half - y0
        edge, remainder = divmod((x0 - half) * dy + offset * dx, denominator)
        if first_edge <= edge <= last_edge:
            yield row, edge, remainder == 0


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
        Horizontal, vertical and seam cuts. When a line hits a centre
        exactly, its canonical direction makes the result independent of
        the order of the supplied points.
    """
    cuts = CutEdges()
    tangents: defaultdict[tuple[int, int], tuple[Fraction | int, Fraction | int]] = (
        defaultdict(lambda: (0, 0))
    )

    def horizontal(row: int, edge: int) -> None:
        """Record a horizontal cut or a cut across the date line.

        Args:
            row: Row of the cut.
            edge: Column left of the cut. -1 marks the date-line seam.
        """
        if edge == -1:
            cuts.add_wrap(row)
        elif edge < width - 1:
            cuts.add_h(row, edge)

    for path in paths:
        check_cancelled()
        points = tuple((Fraction(x), Fraction(y)) for x, y in path)
        points = min(points, points[::-1])
        cuts.paths.append(points)
        for first, last in zip(points, points[1:]):
            if first == last:
                continue
            x0, y0, x1, y1, scale = _scaled_segment(first, last)
            dx, dy = x1 - x0, y1 - y0
            for y, x, on_centre in _scan_crossings(
                x0, y0, x1, y1, scale, height, -1, width - 1
            ):
                if on_centre:
                    if x >= 0:
                        vx, vy = tangents[x, y]
                        tangents[x, y] = (
                            vx + Fraction(dx, scale),
                            vy + Fraction(dy, scale),
                        )
                else:
                    horizontal(y, x)
            for x, y, on_centre in _scan_crossings(
                y0, x0, y1, x1, scale, width, 0, height - 1
            ):
                if on_centre:
                    # A sloping segment has already supplied this tangent.
                    if dy == 0:
                        vx, vy = tangents[x, y]
                        tangents[x, y] = (vx + Fraction(dx, scale), vy)
                elif y < height - 1:
                    cuts.add_v(y, x)

    for (x, y), (dx, dy) in tangents.items():
        if dy > 0:
            horizontal(y, x if x < width - 1 else -1)
        elif dy < 0:
            horizontal(y, x - 1)
        if dx < 0 and y < height - 1:
            cuts.add_v(y, x)
        elif dx > 0 and y > 0:
            cuts.add_v(y - 1, x)
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


class _DSU:
    """Group connected runs by a common root ID."""

    def __init__(self) -> None:
        """Start without any runs to connect."""
        self.parent = array("I")
        self.size = array("I")

    def add(self) -> int:
        """Add a run as its own connected set.

        Returns:
            New run ID.
        """
        i = len(self.parent)
        # Reaching this limit requires materializing over four billion nodes.
        if i >= 0xFFFFFFFF:  # pragma: no cover
            raise OverflowError("run-node count exceeds uint32 DSU capacity")
        self.parent.append(i)
        self.size.append(1)
        return i

    def find(self, x: int) -> int:
        """Find the root of a run's connected set.

        Args:
            x: Run ID.

        Returns:
            Current root ID. Shorten the parent chain along the way.
        """
        p = self.parent
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x

    def union(self, a: int, b: int) -> None:
        """Join the connected sets of two runs if they are distinct.

        Args:
            a: ID of the first run.
            b: ID of the second run.
        """
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]


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

    paths = []
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
        paths.append(path)
    copies = [
        [(x + shift, y) for x, y in path]
        for path in paths
        for shift in (-grid.width, 0, grid.width)
        if min(x for x, _ in path) + shift <= grid.width + 1
        and max(x for x, _ in path) + shift >= -1
    ]
    return rasterize_barriers(copies, grid.width, grid.height)


def continuous_face_links(
    path: Path,
    offsets: Sequence[int],
    paths: Iterable[Sequence[tuple[Fraction, Fraction]]],
    dsu: _DSU,
    uncut: _DSU,
    grid: Grid,
) -> None:
    """Join parts of the same geometric face separated by a narrow grid gap.

    A narrow passage can contain too few cell centres to link two pieces.
    Only runs connected within the scope before the boundary cuts can be
    repaired. The source lines determine which face they share.

    Args:
        path: Binary file of (first_column, end_column, node_id) records.
        offsets: Run-record offsets for each row.
        paths: Boundary paths in grid coordinates.
        dsu: Sets of connected runs to update.
        uncut: Sets of connected scope runs before applying the boundary.
        grid: Grid occupied by the runs.
    """
    lines = [LineString(p) for p in paths if len(p) > 1]
    # Douglas-Peucker changes only the supporting envelope by <= .25 grid cells;
    # the two-cell buffer contains the original line and neighbouring centres.
    envelope = union_all(
        [line.simplify(0.25).buffer(2, cap_style="flat", quad_segs=1) for line in lines]
    )
    extended = []
    for line in lines:
        points = np.asarray(line.coords)
        first = points[0] - points[1]
        last = points[-1] - points[-2]
        if not np.linalg.norm(first) or not np.linalg.norm(last):
            raise ValueError("boundary endpoint has a repeated coordinate")

        def cap(endpoint: np.ndarray, direction: np.ndarray) -> np.ndarray:
            """Extend a line endpoint past the first edge of the local envelope.

            Args:
                endpoint: Two coordinates for the endpoint.
                direction: Two components of the outward direction.

            Returns:
                Length-two array of grid coordinates outside the first envelope edge.
            """
            x0, y0, x1, y1 = envelope.bounds
            extent = 2 * math.hypot(x1 - x0, y1 - y0)
            ray = LineString(
                [endpoint, endpoint + extent * direction / np.linalg.norm(direction)]
            )
            clipped = ray.intersection(envelope)
            for part in get_parts(clipped):
                if (
                    part.geom_type == "LineString"
                    and part.distance(Point(endpoint)) == 0
                ):
                    # This is the first interval from the source endpoint, not
                    # another part of the corridor farther along the same ray.
                    exit_point = max(
                        part.coords,
                        key=lambda q: np.linalg.norm(np.asarray(q) - endpoint),
                    )
                    return np.asarray(exit_point) + direction / np.linalg.norm(
                        direction
                    )
            return endpoint + direction / np.linalg.norm(direction)

        extended.append(
            LineString([cap(points[0], first), *points, cap(points[-1], last)])
        )
    network = union_all([envelope.boundary, *extended])
    faces = [
        face
        for face in get_parts(polygonize(get_parts(network)))
        if envelope.covers(face.representative_point())
    ]
    with path.open("rb") as stream:
        mapping = np.memmap(stream, dtype="<u4", mode="r")
        nodes = mapping.reshape(-1, 3)
        try:
            for face in faces:
                xmin, ymin, xmax, ymax = face.bounds
                roots = {}
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
                        centers = np.arange(left, right, dtype=float) + 0.5
                        if contains_xy(
                            face, centers, np.full(len(centers), y + 0.5)
                        ).any():
                            node = int(node)
                            scope_root = uncut.find(node)
                            dsu.union(roots.setdefault(scope_root, node), node)
        finally:
            close_memmap(mapping)


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
    dsu = _DSU()
    uncut = _DSU() if cuts.paths else None
    offsets = [0]
    previous = []
    label_nodes = {}
    rows = range(grid.height) if rows is None else rows
    with (directory / "nodes.u32le").open("xb") as output:
        for y in range(grid.height):
            check_cancelled()
            if y not in rows:
                offsets.append(len(dsu.parent))
                previous = []
                continue
            raw = list(eligible_rows(y))
            if raw != sorted(raw) or any(a[1] > b[0] for a, b in zip(raw, raw[1:])):
                raise ValueError("partition scope intervals overlap or are unordered")
            current = []
            for a, b in split_eligible(
                raw, sorted(cuts.horizontal.get(y, ())), grid.width
            ):
                node = dsu.add()
                if uncut is not None:
                    uncut.add()
                    if current and current[-1][1] == a:
                        uncut.union(current[-1][2], node)
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
            offsets.append(len(dsu.parent))
            previous = current
    if len(label_nodes) != len(labels):
        raise ValueError("a divided-face label lies outside the computational scope")
    initial_roots = np.fromiter(
        (dsu.find(i) for i in range(len(dsu.parent))), dtype=np.uint32
    )
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
    with (directory / "nodes.u32le").open("r+b") as stream:
        mapping = np.memmap(stream, dtype="<u4", mode="r+")
        records = mapping.reshape(-1, 3)
        records[:, 2] = roots[records[:, 2]]
        mapping.flush()
        close_memmap(mapping)
    return owners
