"""Bounded cell-center Europe/Asia override for the lower Ural boundary.

This is deliberately limited to a small geographic window around the Ural
delta and to the already selected Ural line plus Caspian closure. It does not
change either geometry. The override is applied to land-cell centers only;
water, the physical mask, and all cells outside the window are preserved.
"""
import hashlib
import json
import math


BOUNDS = (51.3, 46.65, 52.2, 47.24)  # west, south, east, north; OGC:CRS84
EUROPE_WITNESS = (51.4, 47.1)
ASIA_WITNESS = (52.1, 47.1)
BOUNDARY_ID = "ural_kara_coast_to_caspian"
ROUTE_ID = "europe_caspian_closure_v1"
SCHEMA = "ural-delta-cell-center-side-v1"


def _geometry_hash(geometry):
    kind = geometry.get("type") if isinstance(geometry, dict) else None
    coords = geometry.get("coordinates") if isinstance(geometry, dict) else None
    if kind != "LineString" or not isinstance(coords, list):
        raise ValueError("expected a LineString geometry")
    canonical = {"type": "LineString", "coordinates": [[float(p[0]), float(p[1])] for p in coords]}
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _near(a, b, eps=1e-11):
    return abs(a[0] - b[0]) <= eps and abs(a[1] - b[1]) <= eps


def _clip_segment(a, b, bounds):
    """Liang–Barsky clip, returning endpoints or None."""
    west, south, east, north = bounds
    dx, dy = b[0] - a[0], b[1] - a[1]
    lo, hi = 0.0, 1.0
    for p, q in ((-dx, a[0] - west), (dx, east - a[0]),
                 (-dy, a[1] - south), (dy, north - a[1])):
        if p == 0:
            if q < 0:
                return None
            continue
        t = q / p
        if p < 0:
            if t > hi:
                return None
            lo = max(lo, t)
        else:
            if t < lo:
                return None
            hi = min(hi, t)
    if lo > hi:
        return None
    return ((a[0] + lo * dx, a[1] + lo * dy),
            (a[0] + hi * dx, a[1] + hi * dy))


def _on_scope_edge(p, bounds, eps=1e-10):
    west, south, east, north = bounds
    return (abs(p[0] - west) <= eps or abs(p[0] - east) <= eps or
            abs(p[1] - south) <= eps or abs(p[1] - north) <= eps)


def clip_line(points, bounds=BOUNDS):
    """Clip a connected input line to the scope; reject disjoint/re-entry paths."""
    if not isinstance(points, list) or len(points) < 2:
        raise ValueError("selected divider needs at least two points")
    p = []
    for xy in points:
        if not isinstance(xy, (list, tuple)) or len(xy) != 2:
            raise ValueError("invalid divider coordinate")
        x, y = float(xy[0]), float(xy[1])
        if not math.isfinite(x) or not math.isfinite(y) or not -180 <= x <= 180 or not -90 <= y <= 90:
            raise ValueError("divider coordinate outside CRS84")
        p.append((x, y))
    path = []
    for a, b in zip(p, p[1:]):
        clipped = _clip_segment(a, b, bounds)
        if clipped is None:
            continue
        u, v = clipped
        if not path:
            path.extend((u, v))
        elif _near(path[-1], u):
            if not _near(path[-1], v):
                path.append(v)
        else:
            raise ValueError("divider exits and re-enters scope")
    if len(path) < 2 or _near(path[0], path[-1]):
        raise ValueError("divider does not cross scope")
    if not _on_scope_edge(path[0], bounds) or not _on_scope_edge(path[-1], bounds):
        raise ValueError("clipped divider endpoints must meet scope edge")
    if any(_near(a, b) for a, b in zip(path, path[1:])):
        raise ValueError("duplicate consecutive clipped divider coordinate")
    return path


def _perimeter_position(p, bounds):
    west, south, east, north = bounds
    width, height = east - west, north - south
    eps = 1e-9
    if abs(p[1] - south) <= eps:
        return p[0] - west
    if abs(p[0] - east) <= eps:
        return width + p[1] - south
    if abs(p[1] - north) <= eps:
        return width + height + east - p[0]
    if abs(p[0] - west) <= eps:
        return 2 * width + height + north - p[1]
    raise ValueError("scope endpoint is not on rectangle perimeter")


def _arc(start, end, bounds):
    """Follow rectangle perimeter counterclockwise from start to end."""
    west, south, east, north = bounds
    width, height = east - west, north - south
    total = 2 * (width + height)
    a, b = _perimeter_position(start, bounds), _perimeter_position(end, bounds)
    if b <= a + 1e-12:
        b += total
    corners = ((east, south, width), (east, north, width + height),
               (west, north, 2 * width + height), (west, south, total))
    middle = []
    for x, y, position in corners:
        for shifted in (position, position + total):
            if a + 1e-12 < shifted < b - 1e-12:
                middle.append((shifted, (x, y)))
    middle.sort(key=lambda item: item[0])
    return [start] + [xy for _, xy in middle] + [end]


def _point_on_segment(p, a, b, eps=1e-11):
    dx, dy = b[0] - a[0], b[1] - a[1]
    cross = (p[0] - a[0]) * dy - (p[1] - a[1]) * dx
    scale = max(1.0, abs(dx), abs(dy))
    if abs(cross) > eps * scale:
        return False
    return (min(a[0], b[0]) - eps <= p[0] <= max(a[0], b[0]) + eps and
            min(a[1], b[1]) - eps <= p[1] <= max(a[1], b[1]) + eps)


def _point_in_ring(p, ring):
    inside = False
    x, y = p
    for a, b in zip(ring, ring[1:]):
        if _point_on_segment(p, a, b):
            return None
        if (a[1] > y) != (b[1] > y):
            cross_x = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if x < cross_x:
                inside = not inside
    return inside


def split_scope(points, bounds=BOUNDS, europe_witness=EUROPE_WITNESS, asia_witness=ASIA_WITNESS):
    """Construct the two scope faces from a boundary crossing the rectangle."""
    line = clip_line(points, bounds)
    west, south, east, north = bounds
    ring_e = line + _arc(line[-1], line[0], bounds)[1:]
    reverse = list(reversed(line))
    ring_a = reverse + _arc(reverse[-1], reverse[0], bounds)[1:]
    if ring_e[0] != ring_e[-1] or ring_a[0] != ring_a[-1]:
        raise ValueError("scope side rings must close")
    e = _point_in_ring(europe_witness, ring_e)
    a = _point_in_ring(asia_witness, ring_e)
    if e is None or a is None or e == a:
        raise ValueError("Europe and Asia witnesses do not lie on opposite sides")
    if e:
        return line, ring_e, ring_a
    return line, ring_a, ring_e


def compile_rule(snapshot, categories, grid):
    """Bind a bounded divider rule to the snapshot's selected Ural + closure."""
    rev = snapshot.get("decision_revision", {}).get("id")
    if not isinstance(rev, str) or not rev:
        raise ValueError("decision revision missing")
    policy = snapshot.get("land_baseline_policy")
    if not isinstance(policy, dict) or policy.get("decision_revision") != rev:
        raise ValueError("land policy revision mismatch")
    if BOUNDARY_ID not in policy.get("boundary_ids", []) or ROUTE_ID not in policy.get("route_ids", []):
        raise ValueError("selected Ural boundary or closure route missing from land policy")
    names = {int(code): str(name).lower() for code, name in categories.items()}
    europe = [c for c, name in names.items() if name == "europe"]
    asia = [c for c, name in names.items() if name == "asia"]
    if len(europe) != 1 or len(asia) != 1:
        raise ValueError("Europe/Asia category codes are ambiguous")
    boundaries = snapshot.get("mainland_boundaries")
    routes = snapshot.get("routes")
    if not isinstance(boundaries, list) or not isinstance(routes, list):
        raise ValueError("selected boundary/route records missing")
    b = [x for x in boundaries if x.get("boundary_id") == BOUNDARY_ID]
    r = [x for x in routes if x.get("route_id") == ROUTE_ID]
    if len(b) != 1 or len(r) != 1:
        raise ValueError("selected Ural boundary or route is ambiguous")
    boundary, route = b[0], r[0]
    for item in (boundary, route):
        if item.get("decision_revision") != rev or item.get("execution_status") != "selected_for_research":
            raise ValueError("Ural geometry is not selected in the current snapshot")
        if _geometry_hash(item.get("geometry")) != item.get("geometry_sha256"):
            raise ValueError("selected Ural geometry hash mismatch")
    pts = boundary["geometry"]["coordinates"]
    route_pts = route["geometry"]["coordinates"]
    terminal = route.get("start_terminal")
    if terminal != {"boundary_id": BOUNDARY_ID, "endpoint": "end"}:
        raise ValueError("Caspian closure does not start at the selected Ural endpoint")
    if not route_pts or [float(x) for x in pts[-1]] != [float(x) for x in route_pts[0]]:
        raise ValueError("Ural boundary and Caspian closure do not join")
    full = [[float(x), float(y)] for x, y in pts]
    full.extend([[float(x), float(y)] for x, y in route_pts[1:]])
    clipped, europe_ring, asia_ring = split_scope(full)
    return {
        "schema": SCHEMA,
        "revision": rev,
        "boundary_id": BOUNDARY_ID,
        "boundary_sha256": boundary["geometry_sha256"],
        "route_id": ROUTE_ID,
        "route_sha256": route["geometry_sha256"],
        "scope_bounds": list(BOUNDS),
        "europe_witness": list(EUROPE_WITNESS),
        "asia_witness": list(ASIA_WITNESS),
        "europe_code": europe[0],
        "asia_code": asia[0],
        "grid": grid,
        "line_scope_vertices": clipped,
        "europe_ring": europe_ring,
        "asia_ring": asia_ring,
    }


def classify_cell(rule, lon, lat):
    """Return 19/18-side code within scope; return None outside; reject edges."""
    west, south, east, north = rule["scope_bounds"]
    eps = 1e-10
    if lon < west - eps or lon > east + eps or lat < south - eps or lat > north + eps:
        return None
    if (abs(lon - west) <= eps or abs(lon - east) <= eps or
            abs(lat - south) <= eps or abs(lat - north) <= eps):
        raise ValueError("land cell center on Ural delta scope edge")
    point = (lon, lat)
    e = _point_in_ring(point, rule["europe_ring"])
    if e is None:
        raise ValueError("land cell center on Ural divider or scope edge")
    return rule["europe_code"] if e else rule["asia_code"]
