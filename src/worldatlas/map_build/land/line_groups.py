"""Classify complete current components against selected latitude-monotonic lines."""

from bisect import bisect_left
import math

import numpy as np

from worldatlas.map_build.core.geodesy import MIN_RADIUS, CUSHION_M


def _require(condition, message):
    if not condition:
        raise ValueError(message)


class LatitudeLine:
    """Interpolate the selected source trace; never extrapolate its latitude range."""

    def __init__(self, geometry, tolerance_degrees):
        if (
            geometry.get('type') != 'LineString'
            or type(tolerance_degrees) not in (int, float)
            or not math.isfinite(tolerance_degrees)
            or tolerance_degrees < 0
        ):
            raise ValueError('line selection needs a LineString and nonnegative contact tolerance')
        points = geometry['coordinates']
        if (
            len(points) < 2
            or any(
                len(p) != 2
                or not all(type(v) in (int, float) and math.isfinite(v) for v in p)
                or not -180 <= p[0] <= 180
                or not -90 <= p[1] <= 90
                for p in points
            )
            or any(a[1] <= b[1] or abs(a[0] - b[0]) >= 180 for a, b in zip(points, points[1:]))
        ):
            raise ValueError('line must be continuous and run strictly north to south')
        self.points = list(reversed(points))
        self.latitudes = [p[1] for p in self.points]
        self.tolerance = tolerance_degrees

    def longitude(self, latitude):
        if not self.latitudes[0] <= latitude <= self.latitudes[-1]:
            return None
        index = bisect_left(self.latitudes, latitude)
        if index == 0:
            return self.points[0][0]
        a, b = self.points[index - 1], self.points[index]
        return a[0] + (b[0] - a[0]) * ((latitude - a[1]) / (b[1] - a[1]))


def scan_components(components, bounds, line):
    """Count complete component populations and their in-window line sides."""
    grid = components.grid
    west, south, east, north = bounds
    if (
        not all(math.isfinite(v) for v in bounds)
        or not -180 <= west <= 180
        or not -180 <= east <= 180
        or west == east
        or not -90 <= south < north <= 90
    ):
        raise ValueError('invalid geographic selection bounds')
    longitudes = grid.longitude(np.arange(grid.width))
    windows = [(west, east)] if west < east else [(-180.0, east), (west, 180.0)]
    columns = [
        (
            int(np.searchsorted(longitudes, a, side='left')),
            int(np.searchsorted(longitudes, b, side='right')),
        )
        for a, b in windows
    ]
    latitudes = grid.latitude(np.arange(grid.height))
    records = {}
    for y in map(int, np.flatnonzero((latitudes >= south) & (latitudes <= north))):
        cut = line.longitude(float(latitudes[y]))
        if cut is not None:
            left = int(np.searchsorted(longitudes, cut - line.tolerance, side='left'))
            right = int(np.searchsorted(longitudes, cut + line.tolerance, side='right'))
        for a, b, root in components.row(y):
            for x0, x1 in columns:
                lo, hi, root = max(int(a), x0), min(int(b), x1), int(root)
                if lo >= hi:
                    continue
                item = records.setdefault(
                    root, dict(total=0, in_scope=0, west=0, east=0, boundary=0, outside_latitude=0)
                )
                item['in_scope'] += hi - lo
                if cut is None:
                    item['outside_latitude'] += hi - lo
                else:
                    item['west'] += max(0, min(hi, left) - lo)
                    item['boundary'] += max(0, min(hi, right) - max(lo, left))
                    item['east'] += max(0, hi - max(lo, right))
    totals = components.totals()
    for root, item in records.items():
        item['total'] = totals[root]
    return records


def collect_runs(components, roots):
    """Read complete selected roots from the already-verified mapped streams."""
    roots = set(roots)
    result = {root: [] for root in roots}
    selected = np.flatnonzero(np.isin(components.runs[:, 2], list(roots)))
    ys = np.searchsorted(components.offsets, selected, side='right') - 1
    for index, y in zip(selected, ys):
        a, b, root = map(int, components.runs[index])
        result[root].append((int(y), a, b))
    return result


def buffered_bounds(bounds, distance_metres):
    """Include every nearby competitor using conservative WGS84 metric bounds."""
    west, south, east, north = bounds
    if not math.isfinite(distance_metres) or distance_metres <= 0 or west >= east:
        raise ValueError('expected positive distance and an unwrapped geographic scope')
    theta = (distance_metres + CUSHION_M) / math.floor(MIN_RADIUS)
    latitude = math.degrees(theta)
    extreme = max(abs(south), abs(north)) + latitude
    if extreme >= 90:
        return [-180.0, max(-90.0, south - latitude), 180.0, min(90.0, north + latitude)]
    longitude = math.degrees(theta / math.cos(math.radians(extreme)))
    if east - west + 2 * longitude >= 360:
        return [-180.0, max(-90.0, south - latitude), 180.0, min(90.0, north + latitude)]
    return [
        (west - longitude + 180) % 360 - 180,
        max(-90.0, south - latitude),
        (east + longitude + 180) % 360 - 180,
        min(90.0, north + latitude),
    ]


def resolve_sides(components, selected, side_codes, *, protected=()):
    """Apply selected affiliations first, then whole-component line sides."""
    if set(side_codes) != {'west', 'east'} or any(
        type(v) is not int or v <= 0 for v in side_codes.values()
    ):
        raise ValueError('line sides need explicit entity category bindings')
    proposals, review = {}, {}
    for root, item in components.items():
        if root in protected:
            if root in selected:
                raise ValueError('selected affiliation intersects a protected component')
            review[root] = 'protected_mainland'
        elif root in selected:
            proposals[root] = {'code': selected[root], 'basis': 'selected_affiliation'}
        elif item['in_scope'] != item['total']:
            review[root] = 'partly_outside_region'
        elif item['outside_latitude']:
            review[root] = 'outside_line_latitude'
        elif item['boundary'] or (item['west'] and item['east']):
            review[root] = 'crosses_or_touches_line'
        elif item['west'] or item['east']:
            proposals[root] = {
                'code': side_codes['west' if item['west'] else 'east'],
                'basis': 'whole_component_line_side',
            }
        else:
            raise ValueError('empty geographic component selection')
    return {'proposals': proposals, 'review': review}
