"""Run-interval regions separated by boundary cuts between cell centres."""

from array import array
from bisect import bisect_left
from collections import defaultdict
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


def _cross(ax, ay, bx, by):
    return ax * by - ay * bx


def _point_on_segment(p, a, b, eps=1e-10):
    px, py = p
    ax, ay = a
    bx, by = b
    dx = bx - ax
    dy = by - ay
    if abs(_cross(dx, dy, px - ax, py - ay)) > eps * max(1.0, abs(dx) + abs(dy)):
        return False
    dot = (px - ax) * dx + (py - ay) * dy
    ll = dx * dx + dy * dy
    return -eps <= dot <= ll + eps


def _intersection_nonvertex(p, q, a, b, eps=1e-10):
    """True iff line segment pq intersects edge ab away from a/b graph vertices.

    Intersections at cell-center graph vertices are handled by the deterministic
    tie rule in rasterize_barriers. A source edge overlapping an entire graph
    edge is also assigned by those endpoint ties, so it is not cut here.
    """
    px, py = p
    qx, qy = q
    ax, ay = a
    bx, by = b
    rx, ry = qx - px, qy - py
    sx, sy = bx - ax, by - ay
    den = _cross(rx, ry, sx, sy)
    apx, apy = ax - px, ay - py
    if abs(den) <= eps:
        if abs(_cross(apx, apy, rx, ry)) > eps * max(1.0, abs(rx) + abs(ry)):
            return False
        rr = rx * rx + ry * ry
        if rr == 0:
            return False
        t0 = (apx * rx + apy * ry) / rr
        t1 = ((bx - px) * rx + (by - py) * ry) / rr
        lo = max(0.0, min(t0, t1))
        hi = min(1.0, max(t0, t1))
        if hi < lo - eps:
            return False
        # If both edge endpoints are on the source route, use the vertex tie.
        if _point_on_segment(a, p, q, eps) and _point_on_segment(b, p, q, eps):
            return False
        # Any positive-length partial overlap or a touch of edge interior is a cut.
        return hi - lo > eps or (
            lo >= -eps
            and lo <= 1 + eps
            and (
                eps < min(abs(lo), abs(1 - lo))
                or _point_on_segment(p, a, b, eps)
                or _point_on_segment(q, a, b, eps)
            )
        )
    t = _cross(apx, apy, sx, sy) / den
    u = _cross(apx, apy, rx, ry) / den
    if t < -eps or t > 1 + eps or u < -eps or u > 1 + eps:
        return False
    ix = px + t * rx
    iy = py + t * ry
    # A graph-center endpoint hit is deferred to the tie handler.
    if math.hypot(ix - ax, iy - ay) <= eps or math.hypot(ix - bx, iy - by) <= eps:
        return False
    return True


def rasterize_barriers(paths, width, height, eps=1e-10):
    """Convert polyline paths in grid-edge (x,y) coordinates into blocked graph edges.

    At a source-line hit on a cell-center graph vertex, the tie cell is assigned
    to the left side of the oriented route; only edges to its right-side
    neighbors are blocked. This prevents diagonal leakage without dropping any
    cell. Shared boundary-aligned cell-center edges stay connected on that same
    tie side. Paths use longitude-unwrapped grid coordinates. The wrapper adds periodic
    copies and explicit seam cuts for longitude wrapping.
    """
    cuts = CutEdges()
    tie_vectors = defaultdict(lambda: [0.0, 0.0])
    for path in paths:
        check_cancelled()
        pts = [(float(x), float(y)) for x, y in path]
        for p, q in zip(pts, pts[1:]):
            x0, y0 = p
            x1, y1 = q
            dx = x1 - x0
            dy = y1 - y0
            if abs(dx) + abs(dy) <= eps:
                continue
            # Collect graph-center vertices on the route; store oriented tangents.
            ix0 = math.ceil(min(x0, x1) - 0.5 - eps)
            ix1 = math.floor(max(x0, x1) - 0.5 + eps)
            iy0 = math.ceil(min(y0, y1) - 0.5 - eps)
            iy1 = math.floor(max(y0, y1) - 0.5 + eps)
            for iy in range(iy0, iy1 + 1):
                cy = iy + 0.5
                for ix in range(ix0, ix1 + 1):
                    cx = ix + 0.5
                    if _point_on_segment((cx, cy), p, q, eps):
                        v = tie_vectors[(ix, iy)]
                        v[0] += dx
                        v[1] += dy
            # Candidate east/west graph edges, endpoints at cell centers.
            j0 = max(0, math.ceil(min(y0, y1) - 0.5 - eps))
            j1 = min(height - 1, math.floor(max(y0, y1) - 0.5 + eps))
            i0 = max(0, math.floor(min(x0, x1) - 1.5))
            i1 = min(width - 2, math.ceil(max(x0, x1) - 0.5))
            for j in range(j0, j1 + 1):
                yy = j + 0.5
                for i in range(i0, i1 + 1):
                    a = (i + 0.5, yy)
                    b = (i + 1.5, yy)
                    if _intersection_nonvertex(p, q, a, b, eps):
                        cuts.add_h(j, i)
            # Candidate north/south graph edges.
            i0 = max(0, math.ceil(min(x0, x1) - 0.5 - eps))
            i1 = min(width - 1, math.floor(max(x0, x1) - 0.5 + eps))
            j0 = max(0, math.floor(min(y0, y1) - 1.5))
            j1 = min(height - 2, math.ceil(max(y0, y1) - 0.5))
            for i in range(i0, i1 + 1):
                xx = i + 0.5
                for j in range(j0, j1 + 1):
                    a = (xx, j + 0.5)
                    b = (xx, j + 1.5)
                    if _intersection_nonvertex(p, q, a, b, eps):
                        cuts.add_v(j, i)
    # Deterministic graph-vertex tie handling after tangents have been combined.
    for (ix, iy), (dx, dy) in tie_vectors.items():
        if abs(dx) + abs(dy) <= eps:
            continue
        cx, cy = ix + 0.5, iy + 0.5
        for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = cx + ox, cy + oy
            side = _cross(dx, dy, nx - cx, ny - cy)
            if side >= -eps:
                continue  # keep left/on-line neighbors in same tie class
            if ox == 1 and 0 <= ix < width - 1:
                cuts.add_h(iy, ix)
            elif ox == -1 and 0 <= ix - 1 < width - 1:
                cuts.add_h(iy, ix - 1)
            elif oy == 1 and 0 <= iy < height - 1:
                cuts.add_v(iy, ix)
            elif oy == -1 and 0 <= iy - 1 < height - 1:
                cuts.add_v(iy - 1, ix)
    cuts.paths = paths
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
    for geometry in geometries:
        lines = (
            [geometry["coordinates"]]
            if geometry["type"] == "LineString"
            else geometry["coordinates"]
        )
        for line in lines:
            longitude = np.rad2deg(np.unwrap(np.deg2rad(np.asarray(line)[:, 0])))
            x = (longitude - grid.west) / grid.step
            y = (grid.north - np.asarray(line)[:, 1]) / grid.step
            paths.append(list(zip(x, y)))
    copies = [
        [(x + shift, y) for x, y in path]
        for path in paths
        for shift in (-grid.width, 0, grid.width)
        if any(-1 <= x + shift <= grid.width + 1 for x, _ in path)
    ]
    cuts = rasterize_barriers(copies, grid.width, grid.height)
    for path in copies:
        for a, b in zip(path, path[1:]):
            if min(a[0], b[0]) > 0.5 or max(a[0], b[0]) < -0.5:
                continue
            first = max(0, math.ceil(min(a[1], b[1]) - 0.5))
            last = min(grid.height - 1, math.floor(max(a[1], b[1]) - 0.5))
            for row in range(first, last + 1):
                if _intersection_nonvertex(a, b, (-0.5, row + 0.5), (0.5, row + 0.5)):
                    cuts.add_wrap(row)
    return cuts


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
