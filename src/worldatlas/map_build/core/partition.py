"""Run-interval regions separated by boundary cuts between cell centres."""

from array import array
from bisect import bisect_left
from collections import defaultdict
from fractions import Fraction
import math
from pathlib import Path

from shapely.geometry import LineString, Point
from shapely import contains_xy, get_parts, polygonize, union_all

import numpy as np

from worldatlas.map_build.execution.control import check_cancelled


class CutEdges:
    """Blocked four-neighbor graph edges. H: (row,x)-(row,x+1); V: (row,x)-(row+1,x)."""

    def __init__(self):
        self.horizontal = defaultdict(set)
        self.vertical = defaultdict(set)
        self.wrap = set()  # blocks (x=W-1) <-> (x=0) on this row
        self.paths = []

    def add_h(self, y, x):
        self.horizontal[int(y)].add(int(x))

    def add_v(self, y, x):
        self.vertical[int(y)].add(int(x))

    def add_wrap(self, y):
        self.wrap.add(int(y))


def _scaled_segment(first, last):
    """Express stored coordinates and half-cell centres on one exact scale."""
    coordinates = (*first, *last)
    scale = math.lcm(2, *(value.denominator for value in coordinates))
    x0, y0, x1, y1 = (
        value.numerator * (scale // value.denominator) for value in coordinates
    )
    return x0, y0, x1, y1, scale


def _scan_crossings(x0, y0, x1, y1, scale, row_count, first_edge, last_edge):
    """Find the crossed graph edge on each row of cell centres.

    Return row indices, edge indices, and whether a crossing hits the centre
    at the start of the edge. A line along a row cuts partially covered edges.
    Fully covered edges stay connected along the line.
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


def rasterize_barriers(paths, width, height):
    """Block four-neighbor paths that cross a source line.

    Args:
        paths: Polylines in grid coordinates, with centres at half-integers.
        width: Number of columns.
        height: Number of rows.

    Returns:
        Blocked horizontal, vertical and longitude seam edges. A cell centre
        exactly on a line stays on the left of a canonical line direction.
    """
    cuts = CutEdges()
    tangents = defaultdict(lambda: (0, 0))

    def horizontal(row, edge):
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


def split_eligible(intervals, blocked_edges, width):
    """Split [x0,x1) eligible intervals wherever a horizontal neighbor is cut."""
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
        if start < b:
            out.append((start, b))
    return out


class _DSU:
    def __init__(self):
        self.parent = array("I")
        self.size = array("I")

    def add(self):
        i = len(self.parent)
        if i >= 0xFFFFFFFF:
            raise OverflowError("run-node count exceeds uint32 DSU capacity")
        self.parent.append(i)
        self.size.append(1)
        return i

    def find(self, x):
        p = self.parent
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x

    def union(self, a, b):
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]


def _blocked_count(sorted_x, lo, hi):
    return bisect_left(sorted_x, hi) - bisect_left(sorted_x, lo)


def geographic_cuts(geometries, grid):
    """Use source lines as graph cuts, including periodic longitude neighbours."""
    paths = []
    west, north, step = map(Fraction, (grid.west, grid.north, grid.step))
    for geometry in geometries:
        lines = (
            [geometry["coordinates"]]
            if geometry["type"] == "LineString"
            else geometry["coordinates"]
        )
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


def continuous_face_links(path, offsets, paths, dsu, grid):
    """Preserve continuous face identity where a cell-centre graph fragments it.

    A fine curve can leave a narrow strip between itself and physical water.
    Its cell centres may have no same-face four-neighbour path to a label, even
    though the strip is continuously on that face. Noded source geometry joins
    those graph roots by their actual side, without adding labels or choosing
    a nearest owner. Unlabelled geometric faces remain unlabelled.

    The small envelope is computational context, never an ownership geometry.
    Only its envelope is simplified; the source lines used to separate faces
    retain every supplied coordinate. End rays cut the envelope's caps and do
    not participate in the original scope cuts or assign additional cells.
    """
    if not paths:
        return
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

        def cap(endpoint, direction):
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
        nodes = np.memmap(stream, dtype="<u4", mode="r").reshape(-1, 3)
        try:
            for face in faces:
                xmin, ymin, xmax, ymax = face.bounds
                roots = set()
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
                            roots.add(dsu.find(int(node)))
                if roots:
                    representative = next(iter(roots))
                    for root in roots:
                        dsu.union(representative, root)
        finally:
            nodes._mmap.close()


def divide_regions(eligible_rows, grid, cuts, labels, directory, *, rows=None):
    """Build labelled faces without expanding the domain into individual cells.

    Labels are (entity_id, x, y); several labels may identify the same owner or
    different disconnected faces. Missing labels remain explicit in root_owners
    so the caller can reject faces containing eligible output cells.
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
                    if lo < hi and hi - lo > _blocked_count(blocked, lo, hi):
                        dsu.union(n, m)
                    if b <= d:
                        i += 1
                    if d <= b:
                        j += 1
            if (
                current
                and current[0][0] == 0
                and current[-1][1] == grid.width
                and y not in cuts.wrap
            ):
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
    # Reconcile fragmented faces before considering their labels.
    if len(distinct) > 1:
        continuous_face_links(directory / "nodes.u32le", offsets, cuts.paths, dsu, grid)
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
    # Resolve roots once; later consumers use mapped rows without union-find work.
    with (directory / "nodes.u32le").open("r+b") as stream:
        records = np.memmap(stream, dtype="<u4", mode="r+").reshape(-1, 3)
        records[:, 2] = roots[records[:, 2]]
        records.flush()
        records._mmap.close()
    return owners
