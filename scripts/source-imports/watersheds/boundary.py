"""Join source lines, drainage divides and explicit geodesic connectors once."""
from collections import defaultdict
from dataclasses import dataclass, field
import heapq
import math

import numpy as np
from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import substring
from shapely.strtree import STRtree

from watersheds.drainage import upstream_order

GEOD = Geod(ellps='WGS84')


def distance(first, second):
    value = GEOD.inv(*first, *second)[2]
    if not math.isfinite(value):
        raise ValueError('invalid WGS84 boundary coordinates')
    return value


@dataclass
class Join:
    point: tuple
    edges: dict = field(default_factory=dict)


class Divide:
    """A grid-edge graph; connected pieces may meet at branches or form loops."""
    def __init__(self):
        self.coordinates = {}
        self.edges = set()
        self.origin = None
        self.crs = None

    def add_grid(self, grid, labels, pairs, output_bounds=None):
        labels = np.asarray(labels)
        if labels.shape != grid.elevation.shape:
            raise ValueError('basin labels and terrain grid must match')
        pairs = [tuple(map(int, pair)) for pair in pairs]
        if not pairs or any(len(pair) != 2 or min(pair) < 0 or pair[0] == pair[1] for pair in pairs):
            raise ValueError('distinct known drainage groups are required')
        origin = grid.native_origin or grid.transform
        crs = CRS.from_user_input(grid.crs)
        if self.origin is not None and (self.origin != origin or self.crs != crs):
            raise ValueError('divide domains must share one native grid')
        self.origin, self.crs = origin, crs
        to_geo = Transformer.from_crs(crs, 4326, always_xy=True)
        height, width = labels.shape
        if output_bounds is not None:
            if (len(output_bounds) != 4 or not np.isfinite(output_bounds).all() or
                    not output_bounds[0] < output_bounds[2] or not output_bounds[1] < output_bounds[3]):
                raise ValueError('divide output bounds require a finite geographic rectangle')

        def node(row, column):
            key = (row + grid.window_offset[0], column + grid.window_offset[1])
            if key not in self.coordinates:
                point = to_geo.transform(*grid.coordinates(row, column, center=False), errcheck=True)
                if not np.isfinite(point).all() or not -90 <= point[1] <= 90:
                    raise ValueError('invalid divide coordinates')
                self.coordinates[key] = tuple(map(float, point))
            return key

        for dr, dc in ((0, 1), (1, 0)):
            first, second = labels[:height - dr, :width - dc], labels[dr:, dc:]
            selected = np.zeros(first.shape, dtype=bool)
            for a, b in pairs:
                selected |= ((first == a) & (second == b)) | ((first == b) & (second == a))
            for rr, cc in np.argwhere(selected):
                row, column = int(rr), int(cc)
                if output_bounds is not None:
                    midpoint = grid.coordinates(row + (.5 if dc else 1),
                                                column + (1 if dc else .5), center=False)
                    lon, lat = to_geo.transform(*midpoint, errcheck=True)
                    west, south, east, north = output_bounds
                    if not (west <= lon < east and south <= lat < north):
                        continue
                edge = ((node(row, column + 1), node(row + 1, column + 1)) if dc else
                        (node(row + 1, column), node(row + 1, column + 1)))
                self.edges.add(tuple(sorted(edge)))

    def segments(self):
        edges = sorted(self.edges)
        return edges, [LineString([self.coordinates[a], self.coordinates[b]]) for a, b in edges]

    def geometry(self):
        return MultiLineString([list(line.coords) for line in self.segments()[1]])

    def nearest_vertex(self, point):
        """Select a native divide corner for an explicit geographic connector."""
        if not self.coordinates:
            raise ValueError('selected divide is empty')
        keys = sorted(self.coordinates)
        coordinates = np.asarray([self.coordinates[key] for key in keys])
        lengths = GEOD.inv(coordinates[:, 0], coordinates[:, 1],
                           np.full(len(keys), point[0]), np.full(len(keys), point[1]))[2]
        if not np.isfinite(lengths).all():
            raise ValueError('invalid geographic connector anchor')
        key = keys[int(np.argmin(lengths))]
        edge = min(edge for edge in self.edges if key in edge)
        return Join(self.coordinates[key], {self: edge})

    def route(self, start, end):
        """Find a WGS84 shortest connected path between the chosen intersections."""
        if start.point == end.point:
            raise ValueError('divide joins coincide')
        coordinates = dict(self.coordinates)
        split = {edge: [(0., edge[0]), (1., edge[1])] for edge in self.edges}
        terminals = []
        for index, join in enumerate((start, end)):
            edge = join.edges.get(self)
            if edge not in split:
                raise ValueError('join does not identify a divide edge')
            a, b = edge
            if join.point == coordinates[a]:
                terminal = a
            elif join.point == coordinates[b]:
                terminal = b
            else:
                terminal = ('join', index)
                first, last = coordinates[a], coordinates[b]
                axis = 0 if abs(last[0] - first[0]) >= abs(last[1] - first[1]) else 1
                fraction = (join.point[axis] - first[axis]) / (last[axis] - first[axis])
                if not 0 <= fraction <= 1:
                    raise ValueError('join lies outside its divide edge')
                coordinates[terminal] = join.point
                split[edge].append((fraction, terminal))
            terminals.append(terminal)
        adjacent = defaultdict(list)
        for edge in sorted(split):
            pieces = sorted(split[edge], key=lambda item: item[0])
            for (_, a), (_, b) in zip(pieces, pieces[1:]):
                length = distance(coordinates[a], coordinates[b])
                adjacent[a].append((b, length))
                adjacent[b].append((a, length))
        source, target = terminals
        lengths, parents = {source: 0.}, {}
        queue, order = [(0., 0, source)], 0
        while queue:
            length, _, node = heapq.heappop(queue)
            if length != lengths[node]:
                continue
            if node == target:
                break
            for other, weight in adjacent[node]:
                proposed = length + weight
                if proposed < lengths.get(other, float('inf')):
                    lengths[other], parents[other] = proposed, node
                    order += 1
                    heapq.heappush(queue, (proposed, order, other))
        if target not in lengths:
            raise ValueError('selected joins are on disconnected divide pieces')
        path = [target]
        while path[-1] != source:
            path.append(parents[path[-1]])
        points = [coordinates[node] for node in reversed(path)]
        if len(points) < 2:
            raise ValueError('divide joins coincide')
        return LineString(points)


def _points(geometry):
    if geometry.is_empty:
        return []
    if geometry.geom_type == 'Point':
        return [tuple(geometry.coords[0])]
    if geometry.geom_type == 'LineString':
        return [tuple(geometry.coords[0]), tuple(geometry.coords[-1])]
    return [point for part in geometry.geoms for point in _points(part)]


def intersection(left, right, near):
    """Choose an actual source intersection using its WGS84 distance to an anchor.

    A divide join retains its grid edge identity, so inserting the computed
    intersection needs no rounding or approximate coordinate matching.
    """
    candidates = []
    if isinstance(left, Divide):
        edges, lines = left.segments()
        if isinstance(right, Divide):
            other_edges, other_lines = right.segments()
            tree = STRtree(other_lines)
            for edge, line in zip(edges, lines):
                for index in tree.query(line, predicate='intersects'):
                    for point in _points(line.intersection(other_lines[int(index)])):
                        candidates.append(Join(point, {left: edge, right: other_edges[int(index)]}))
        else:
            tree = STRtree(lines)
            for index in tree.query(right, predicate='intersects'):
                for point in _points(lines[int(index)].intersection(right)):
                    candidates.append(Join(point, {left: edges[int(index)]}))
    elif isinstance(right, Divide):
        return intersection(right, left, near)
    else:
        candidates = [Join(point) for point in _points(left.intersection(right))]
    if not candidates:
        raise ValueError('adjacent sections have no source-supported intersection')
    return min(candidates, key=lambda join: (distance(join.point, near), join.point))


def geodesic(first, last, max_step_m):
    if not math.isfinite(max_step_m) or max_step_m <= 0:
        raise ValueError('positive geodesic spacing is required')
    azimuth, _, length = GEOD.inv(*first, *last)
    if not math.isfinite(length) or length == 0:
        raise ValueError('distinct finite connector endpoints are required')
    count = max(1, math.ceil(length / max_step_m))
    return [tuple(first)] + [GEOD.fwd(*first, azimuth, length * i / count)[:2]
                            for i in range(1, count)] + [tuple(last)]


def assemble(sections, joins, start, end):
    """Cut independent sections at their shared joins and assemble the final line."""
    if not sections or len(joins) != len(sections) - 1:
        raise ValueError('one join is required between each pair of sections')
    ends = [start if isinstance(start, Join) else Join(tuple(start)),
            *joins, end if isinstance(end, Join) else Join(tuple(end))]
    coordinates = []
    for index, section in enumerate(sections):
        first, last = ends[index], ends[index + 1]
        if isinstance(section, Divide):
            cut = section.route(first, last)
        else:
            cut = substring(section, section.project(Point(first.point)), section.project(Point(last.point)))
        if cut.geom_type != 'LineString' or cut.is_empty:
            raise ValueError('boundary section has coincident or invalid joins')
        points = list(cut.coords)
        points[0], points[-1] = first.point, last.point
        coordinates.extend(points if not coordinates else points[1:])
    line = LineString(coordinates)
    if not line.is_simple or not line.is_valid or not np.isfinite(coordinates).all():
        raise ValueError('assembled boundary is not a finite simple line')
    return {'type': 'LineString', 'coordinates': [list(map(float, point)) for point in coordinates]}


def cell_at(grid, point):
    x, y = Transformer.from_crs(4326, grid.crs, always_xy=True).transform(*point, errcheck=True)
    left, a, _, top, _, e = grid.transform
    row, column = math.floor((y - top) / e), math.floor((x - left) / a)
    if not (0 <= row < grid.elevation.shape[0] and 0 <= column < grid.elevation.shape[1]):
        raise ValueError('selected source point is outside the terrain domain')
    return row, column


def flow_to_point(grid, flow, labels, point, inside_group, outside_groups, max_step_m):
    """Connect a divide to a known stream head using its actual upstream flow.

    Find the closest cell reached by flow from the selected divide, follow its
    actual upstream route and connect its center to the exact source point.
    A vector point need not fall in the cell traversed by raster drainage.
    No pixel search radius or modified elevation is needed.
    """
    row, column = cell_at(grid, point)
    if labels[row, column] != inside_group:
        raise ValueError('source stream head is not assigned to its declared drainage group')
    height, width = labels.shape
    to_geo = Transformer.from_crs(grid.crs, 4326, always_xy=True)

    def center(index):
        rr, cc = divmod(int(index), width)
        return tuple(to_geo.transform(*grid.coordinates(rr, cc), errcheck=True))

    interface = np.zeros(labels.shape, dtype=bool)
    for dr, dc in ((-1, 0), (0, -1), (0, 1), (1, 0)):
        source = (slice(max(0, -dr), min(height, height - dr)),
                  slice(max(0, -dc), min(width, width - dc)))
        neighbor = (slice(max(0, dr), min(height, height + dr)),
                    slice(max(0, dc), min(width, width + dc)))
        interface[source] |= ((labels[source] == inside_group) &
                              np.isin(labels[neighbor], outside_groups))
    reached = interface.ravel().copy()
    todo = list(map(int, np.flatnonzero(reached)))
    while todo:
        following = int(flow.ravel()[todo.pop()])
        if following >= 0 and not reached[following] and labels.ravel()[following] == inside_group:
            reached[following] = True
            todo.append(following)
    eligible = np.flatnonzero(reached)
    if not len(eligible):
        raise ValueError('no source-backed divide flows to the selected drainage group')
    rows, columns = np.divmod(eligible, width)
    lon, lat = to_geo.transform(*grid.coordinates(rows, columns), errcheck=True)
    lengths_to_point = GEOD.inv(lon, lat, np.full(lon.shape, point[0]),
                              np.full(lat.shape, point[1]))[2]
    terminal = int(eligible[np.argmin(lengths_to_point)])
    lengths = {terminal: 0.}
    candidates = []
    for value in upstream_order(flow, terminal):
        index = int(value)
        rr, cc = divmod(index, width)
        if index != terminal:
            parent = int(flow.ravel()[index])
            lengths[index] = lengths[parent] + distance(center(index), center(parent))
        if labels[rr, cc] != inside_group:
            continue
        for dr, dc in ((-1, 0), (0, -1), (0, 1), (1, 0)):
            nr, nc = rr + dr, cc + dc
            if 0 <= nr < height and 0 <= nc < width and labels[nr, nc] in outside_groups:
                neighbor = nr * width + nc
                cost = lengths[index] + .5 * distance(center(neighbor), center(index))
                candidates.append((cost, index, neighbor))
    if not candidates:
        raise ValueError('no source-backed divide flows to the selected stream head')
    _, index, neighbor = min(candidates)
    cells = [index]
    while cells[-1] != terminal:
        cells.append(int(flow.ravel()[cells[-1]]))
    centers = [center(value) for value in cells]
    snap = distance(centers[-1], point)
    connector = geodesic(centers[-1], point, max_step_m) if snap else [tuple(point)]
    coordinates = [center(neighbor), *centers, *connector[1:]]
    return LineString(coordinates), {'flow_cells': len(cells), 'point_snap_m': snap,
                                      'interface_cells': [list(divmod(index, width)),
                                                          list(divmod(neighbor, width))]}
