"""Find the line between drainage groups and join it to other boundary sections."""

import math
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from itertools import pairwise
from typing import Any, TypedDict, cast

import numpy as np
from pyproj import CRS, Transformer
from scipy.sparse import csr_array
from scipy.sparse.csgraph import dijkstra
from shapely import get_coordinates, linestrings, remove_repeated_points
from shapely import intersection as intersect_geometries
from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry, BaseMultipartGeometry
from shapely.ops import substring
from shapely.strtree import STRtree

from worldatlas.geodesy.wgs84 import geodesic, geodesic_distance, geodesic_distances
from worldatlas.source_imports.watersheds.drainage import cells_draining_to
from worldatlas.source_imports.watersheds.terrain import TerrainGrid


@dataclass
class Join:
    """Remember where two boundary sections meet.

    A join in the middle of a terrain edge stores that edge so the route
    can start at the exact meeting point.

    Args:
        point: WGS84 longitude and latitude of the join.
        edges: Optional mapping from each participating divide to its edge ID.
    """

    point: tuple[float, ...]
    edges: dict = field(default_factory=dict)


def _catchment_edge_mask(
    labels: Mapping[int, np.ndarray],
    group_pairs: Sequence[tuple[int, ...]],
    missing: np.ndarray,
    dr: int,
    dc: int,
) -> np.ndarray:
    """Select where two adjacent cells drain to different groups.

    Args:
        labels: Boolean grid for each group, with multiple groups allowed.
        group_pairs: Pairs of groups to separate.
        missing: All-false grid used when a group has no cells in this crop.
        dr: Row step to the neighbor, 1 for the neighbor below.
        dc: Column step to the neighbor, 1 for the neighbor to the right.

    Returns:
        Boolean grid of shape (height - dr, width - dc). True at (r, c)
        means the edge between (r, c) and (r + dr, c + dc) is eligible.
    """
    height, width = missing.shape
    selected_edges = np.zeros((height - dr, width - dc), dtype=bool)
    for a, b in group_pairs:
        group_a_cells, group_b_cells = (
            labels.get(a, missing),
            labels.get(b, missing),
        )
        a_here, a_next = (
            group_a_cells[: height - dr, : width - dc],
            group_a_cells[dr:, dc:],
        )
        b_here, b_next = (
            group_b_cells[: height - dr, : width - dc],
            group_b_cells[dr:, dc:],
        )
        # A cell that drains only to 3 can share an edge with a cell
        # draining to both 3 and 7. Two cells draining to both have
        # the same destinations, so leave their shared edge out.
        selected_edges |= ((a_here & b_next) | (b_here & a_next)) & (
            (a_here != a_next) | (b_here != b_next)
        )
    return selected_edges


class Divide:
    """Keep the cell edges that the boundary can follow."""

    def __init__(self) -> None:
        """Start an empty graph of eligible terrain edges."""
        self.coordinates = {}
        self.edges = set()
        self.origin = None
        self.crs = None

    def add_catchment_edges(
        self,
        grid: TerrainGrid,
        labels: Mapping[int, np.ndarray],
        pairs: Collection[tuple[int | str, int | str]],
        output_bounds: tuple[float, float, float, float] | None = None,
        *,
        bounds_crs: int | str | CRS = 4326,
    ) -> None:
        """Add the edges between cells that drain to the chosen groups.

        For instance, put an edge between a cell that drains to group 3
        and its neighbor that drains to group 7. Those edges give the
        boundary a set of connected routes to choose from.

        Args:
            grid: Terrain crop, aligned with any previous crops in this divide.
            labels: A True/False grid for each drainage group. A cell may
                drain to two groups when a river splits.
            pairs: The pairs to separate, such as ``[(3, 7)]``.
            output_bounds: Optional west, south, east, and north limits for edge midpoints.
            bounds_crs: Coordinate reference of the output limits.

        Raises:
            ValueError: The crop, group labels, group pairs, or output limits are invalid.
        """
        if any(
            np.asarray(cells).shape != grid.elevation.shape
            or np.asarray(cells).dtype != bool
            for cells in labels.values()
        ):
            raise ValueError('basin labels and terrain grid must match')
        group_pairs = [tuple(map(int, pair)) for pair in pairs]
        if not group_pairs or any(
            len(pair) != 2 or min(pair) < 0 or pair[0] == pair[1]
            for pair in group_pairs
        ):
            raise ValueError('distinct known drainage groups are required')
        origin = grid.native_origin or grid.transform
        crs = CRS.from_user_input(grid.crs)
        if self.origin is not None and (self.origin != origin or self.crs != crs):
            raise ValueError('divide domains must share one native grid')
        self.origin, self.crs = origin, crs
        to_geo = Transformer.from_crs(crs, 4326, always_xy=True)
        to_output = Transformer.from_crs(crs, bounds_crs, always_xy=True)
        missing = np.zeros(grid.elevation.shape, dtype=bool)
        if output_bounds is not None:
            if (
                len(output_bounds) != 4
                or not np.isfinite(output_bounds).all()
                or not output_bounds[0] < output_bounds[2]
                or not output_bounds[1] < output_bounds[3]
            ):
                raise ValueError(
                    'divide output bounds require a finite geographic rectangle'
                )

        def node(row: int, column: int) -> tuple[int, int]:
            # The same corner can have a different local row and column in
            # two crops. Its full-grid position gives both crops the same key.
            """Record a grid corner and remember its WGS84 coordinates.

            Args:
                row: Row of the corner in the elevation crop.
                column: Column of the corner in the crop.

            Returns:
                Corner's (row, column) on the full native grid.
            """
            key = (row + grid.window_offset[0], column + grid.window_offset[1])
            if key not in self.coordinates:
                point = to_geo.transform(
                    *grid.cell_coordinates(row, column, center=False), errcheck=True
                )
                if not np.isfinite(point).all() or not -90 <= point[1] <= 90:
                    raise ValueError('invalid divide coordinates')
                self.coordinates[key] = tuple(map(float, point))
            return key

        for dr, dc in ((0, 1), (1, 0)):
            selected_edges = _catchment_edge_mask(labels, group_pairs, missing, dr, dc)
            for rr, cc in np.argwhere(selected_edges):
                row, column = int(rr), int(cc)
                if output_bounds is not None:
                    midpoint = grid.cell_coordinates(
                        row + (0.5 if dc else 1),
                        column + (1 if dc else 0.5),
                        center=False,
                    )
                    x, y = to_output.transform(*midpoint, errcheck=True)
                    west, south, east, north = output_bounds
                    if not (west <= x < east and south <= y < north):
                        continue
                edge = (
                    (node(row, column + 1), node(row + 1, column + 1))
                    if dc
                    else (node(row + 1, column), node(row + 1, column + 1))
                )
                self.edges.add(tuple(sorted(edge)))

    def edge_ids_and_lines(
        self,
    ) -> tuple[list[tuple[tuple[int, int], tuple[int, int]]], np.ndarray]:
        """Create line geometries in the same order as their grid-edge identifiers.

        Returns:
            The ordered edge identifiers and a parallel array of Shapely lines.
        """
        edges = sorted(self.edges)
        coordinates = np.asarray(
            [(self.coordinates[a], self.coordinates[b]) for a, b in edges]
        )
        return edges, cast(np.ndarray, linestrings(coordinates.reshape(-1, 2, 2)))

    def join_at_nearest_corner(self, point: Sequence[float]) -> Join:
        """Select the closest native divide corner to a geographic reference.

        Args:
            point: Reference longitude and latitude in WGS84 degrees.

        Returns:
            A join at the selected corner with its incident edge ID.

        Raises:
            ValueError: The divide is empty or the reference gives invalid distances.
        """
        if not self.coordinates:
            raise ValueError('selected divide is empty')
        keys = sorted(self.coordinates)
        coordinates = np.asarray([self.coordinates[key] for key in keys])
        lengths = geodesic_distances(
            coordinates[:, 0], coordinates[:, 1], point[0], point[1]
        )
        if not np.isfinite(lengths).all():
            raise ValueError('invalid geographic connector anchor')
        key = keys[int(np.argmin(lengths))]
        edge = min(edge for edge in self.edges if key in edge)
        return Join(self.coordinates[key], {self: edge})

    def shortest_divide_path(self, start: Join, end: Join) -> LineString:
        """Find the shortest route between two joins along the saved cell edges.

        Args:
            start: Join identifying the start point and its divide edge.
            end: Join identifying the end point and its divide edge.

        Returns:
            A WGS84 line from start to end, with distance measured in metres
            along the connected edges.

        Raises:
            ValueError: The joins are invalid, coincide, or lie on disconnected pieces.
        """
        if start.point == end.point:
            raise ValueError('divide joins coincide')
        coordinates = dict(self.coordinates)
        split = {edge: [(0.0, edge[0]), (1.0, edge[1])] for edge in self.edges}
        terminals = []
        for index, join in enumerate((start, end)):
            edge = join.edges.get(self)
            if edge is None or edge not in split:
                raise ValueError('join does not identify a divide edge')
            a, b = edge
            if join.point == coordinates[a]:
                terminal = a
            elif join.point == coordinates[b]:
                terminal = b
            else:
                # If the join lies halfway along A–B, make two edges,
                # A–join and join–B, so the route can start at the join.
                terminal = ('join', index)
                first, last = coordinates[a], coordinates[b]
                axis = 0 if abs(last[0] - first[0]) >= abs(last[1] - first[1]) else 1
                fraction = (join.point[axis] - first[axis]) / (last[axis] - first[axis])
                if not 0 <= fraction <= 1:
                    raise ValueError('join lies outside its divide edge')
                coordinates[terminal] = join.point
                split[edge].append((fraction, terminal))
            terminals.append(terminal)
        nodes = list(coordinates)
        node_ids = {node: index for index, node in enumerate(nodes)}
        rows, columns = [], []
        for edge in sorted(split):
            pieces = sorted(split[edge], key=lambda item: item[0])
            for (_, a), (_, b) in pairwise(pieces):
                rows.append(node_ids[a])
                columns.append(node_ids[b])
        positions = np.asarray(list(coordinates.values()))
        lon1, lat1 = positions[rows].T
        lon2, lat2 = positions[columns].T
        lengths = geodesic_distances(lon1, lat1, lon2, lat2)
        if not np.isfinite(lengths).all():
            raise ValueError('invalid WGS84 boundary coordinates')
        # Each divide edge is traversable in both directions.
        graph = csr_array(
            (np.concatenate((lengths, lengths)), (rows + columns, columns + rows)),
            shape=(len(nodes), len(nodes)),
        )
        source, target = (node_ids[node] for node in terminals)
        distances, previous = dijkstra(graph, indices=source, return_predecessors=True)
        if not np.isfinite(distances[target]):
            raise ValueError('selected joins are on disconnected divide pieces')
        # SciPy tells us how we reached each point. Follow that trail
        # backward from the end, then reverse it to draw from start to end.
        path = [target]
        while path[-1] != source:
            path.append(previous[path[-1]])
        return LineString([coordinates[nodes[index]] for index in reversed(path)])


def _join_candidate_points(geometry: BaseGeometry) -> list[tuple[float, ...]]:
    """Collect possible meeting points from an intersection.

    Args:
        geometry: Intersection of two boundary lines.

    Returns:
        Coordinate tuples for isolated intersections and both ends of shared stretches.
    """
    if geometry.is_empty:
        return []
    if geometry.geom_type == 'Point':
        return [tuple(geometry.coords[0])]
    if geometry.geom_type == 'LineString':
        return [tuple(geometry.coords[0]), tuple(geometry.coords[-1])]
    return [
        point
        for part in cast(BaseMultipartGeometry, geometry).geoms
        for point in _join_candidate_points(part)
    ]


def choose_intersection_join(
    left: LineString | Divide, right: LineString | Divide, near: Sequence[float]
) -> Join:
    """Pick the meeting point closest to the coordinate given in the recipe.

    A line can cross a divide twice. The nearby coordinate tells us which
    crossing to use. If it lands inside a divide edge, save the exact
    point and the edge so the route can start there.

    Args:
        left: First source line or divide graph.
        right: Second source line or divide graph.
        near: WGS84 point used to choose among the intersections.

    Returns:
        The chosen point and its edge on each participating divide.

    Raises:
        ValueError: The two sections have no intersection.
    """
    if isinstance(left, Divide):
        edges, lines = left.edge_ids_and_lines()
        if isinstance(right, Divide):
            other_edges, other_lines = right.edge_ids_and_lines()
            first, second = STRtree(other_lines).query(lines, predicate='intersects')
            hits = intersect_geometries(lines[first], other_lines[second])
            candidates = [
                Join(point, {left: edges[i], right: other_edges[j]})
                for i, j, hit in zip(first, second, hits, strict=True)
                for point in _join_candidate_points(hit)
            ]
        else:
            indices = STRtree(lines).query(right, predicate='intersects')
            hits = intersect_geometries(lines[indices], right)
            candidates = [
                Join(point, {left: edges[i]})
                for i, hit in zip(indices, hits, strict=True)
                for point in _join_candidate_points(hit)
            ]
    elif isinstance(right, Divide):
        return choose_intersection_join(right, left, near)
    else:
        candidates = [
            Join(point) for point in _join_candidate_points(left.intersection(right))
        ]
    if not candidates:
        raise ValueError('adjacent sections have no source-supported intersection')
    return min(
        candidates, key=lambda join: (geodesic_distance(join.point, near), join.point)
    )


class _WaypointAttachments(TypedDict):
    """Record the part of the old divide replaced by an ordered set of points."""

    first: int
    last: int
    points: list[tuple[float, ...]]


def _nearest_waypoint_attachments(
    coordinates: np.ndarray, points: Sequence[Sequence[float]]
) -> list[_WaypointAttachments]:
    """Find the initial span of the divide to replace for each waypoint.

    Args:
        coordinates: Original (longitude, latitude) pairs in line order.
        points: Reviewed points in their intended order along that line.

    Returns:
        One span per waypoint, with inclusive indices into the original
        coordinate array. A waypoint on a vertex can use that vertex twice.

    Raises:
        ValueError: A waypoint is invalid or goes backward along the line.
    """
    groups: list[_WaypointAttachments] = []
    previous = -1
    for point in points:
        point = tuple(map(float, point))
        if (
            len(point) != 2
            or not np.isfinite(point).all()
            or abs(point[0]) > 180
            or abs(point[1]) > 90
        ):
            raise ValueError('waypoints require finite WGS84 coordinates')
        lengths = geodesic_distances(
            coordinates[:, 0], coordinates[:, 1], point[0], point[1]
        )
        index = int(np.argmin(lengths))
        if index < previous:
            raise ValueError('waypoints must follow the ordered divide')
        previous = index
        # A waypoint already on a saved corner can use that corner for
        # both attachments. Otherwise start with the neighboring corners.
        first, last = (
            (index, index)
            if tuple(coordinates[index]) == point
            else (max(0, index - 1), min(len(coordinates) - 1, index + 1))
        )
        groups.append({'first': first, 'last': last, 'points': [point]})
    return groups


def route_line_through_waypoints(
    line: LineString, points: Sequence[Sequence[float]], max_step_m: float
) -> tuple[LineString, list[dict[str, Any]]]:
    """Make the divide pass through the points named in the recipe.

    Say the divide runs A–B–C–D and we want to pass through P near B.
    Choose two points on the divide and draw a new stretch through P.
    If that stretch cuts the old divide farther away, move the
    attachments outward until the cut falls inside the part being replaced.

    Args:
        line: The ordered divide line to modify.
        points: WGS84 waypoints in their intended order along the divide.
        max_step_m: Maximum spacing between samples on the added geodesics.

    Returns:
        The connected line and a report of chosen attachments and connector lengths.

    Raises:
        ValueError: The waypoints are invalid, out of order, or produce a self-crossing line.
    """
    if not math.isfinite(max_step_m) or max_step_m <= 0:
        raise ValueError('positive geodesic spacing is required')
    coordinates = np.asarray(line.coords)
    groups = _nearest_waypoint_attachments(coordinates, points)
    edges = cast(
        np.ndarray, linestrings(np.stack((coordinates[:-1], coordinates[1:]), axis=1))
    )
    tree = STRtree(edges)

    def connector(group: _WaypointAttachments) -> list[tuple[float, ...]]:
        """Join a group of waypoints to their attachments on the divide.

        Args:
            group: Attachment indices and intermediate points.

        Returns:
            Longitude and latitude pairs along the sampled connections.
        """
        chain = [
            tuple(coordinates[group['first']]),
            *group['points'],
            tuple(coordinates[group['last']]),
        ]
        result = [chain[0]]
        for first, last in pairwise(chain):
            if first != last:
                result.extend(geodesic(first, last, max_step_m)[1:])
        return result

    changed = True
    while changed:
        changed = False
        for group in groups:
            curve = connector(group)
            geometry = LineString(curve) if len(curve) > 1 else Point(curve[0])
            first, last = group['first'], group['last']
            for index in tree.query(geometry, predicate='intersects'):
                index = int(index)
                if first <= index < last:
                    continue
                allowed = Point(coordinates[first if index < first else last])
                if edges[index].intersection(geometry).difference(allowed).is_empty:
                    continue
                # Replace the old edge we crossed as well. Leaving it in
                # place could make the finished line cross itself.
                group['first'] = min(group['first'], index)
                group['last'] = max(group['last'], index + 1)
            changed |= (first, last) != (group['first'], group['last'])
        merged = []
        for group in groups:
            # If two replacements touch or overlap, use one connector
            # through both sets of waypoints in recipe order.
            if merged and merged[-1]['last'] >= group['first']:
                merged[-1]['first'] = min(merged[-1]['first'], group['first'])
                merged[-1]['last'] = max(merged[-1]['last'], group['last'])
                merged[-1]['points'].extend(group['points'])
                changed = True
            else:
                merged.append(group)
        groups = merged
    result, receipts, position = [], [], 0
    for group in groups:
        curve = connector(group)
        result.extend(map(tuple, coordinates[position : group['first'] + 1]))
        result.extend(curve[1:])
        position = group['last'] + 1
        receipts.append(
            {
                'points': [list(p) for p in group['points']],
                'start': list(curve[0]),
                'end': list(curve[-1]),
                'length_m': sum(geodesic_distance(a, b) for a, b in pairwise(curve)),
            }
        )
    result.extend(map(tuple, coordinates[position:]))
    connected = LineString(result)
    if not connected.is_simple:
        raise ValueError(
            'geographic waypoint connections do not form a simple ordered line'
        )
    return connected, receipts


def assemble_boundary_line(
    sections: Sequence[LineString | Divide],
    joins: Sequence[Join],
    start: Sequence[float] | Join,
    end: Sequence[float] | Join,
    *,
    waypoints: dict[int, dict[str, Any]] | None = None,
    connections: dict[str, Any] | None = None,
    source_sections: Collection[int] = (),
) -> tuple[dict[str, Any], list[LineString]]:
    """Trim each section at its joins and put the pieces together.

    If the source line is A–B–C–D and the joins are B and C, keep B–C.
    A calculated divide may offer several routes between those points,
    so use its shortest connected route.

    Args:
        sections: Ordered source lines, connectors, or divide graphs.
        joins: One resolved join for each consecutive pair of sections.
        start: First point, supplied as coordinates or a resolved join.
        end: Last point, supplied as coordinates or a resolved join.
        waypoints: Points to include and connector spacing for each selected section.
        connections: Optional report. Add the waypoint attachment points and lengths.
        source_sections: Indices of sections that deliberately follow a source line.

    Returns:
        The completed WGS84 GeoJSON LineString and the trimmed source sections.

    Raises:
        ValueError: Sections cannot meet at the declared joins or form an invalid line.
    """
    if not sections or len(joins) != len(sections) - 1:
        raise ValueError('one join is required between each pair of sections')
    ends = [
        start if isinstance(start, Join) else Join(tuple(start)),
        *joins,
        end if isinstance(end, Join) else Join(tuple(end)),
    ]
    coordinates, followed_sources = [], []
    for index, section in enumerate(sections):
        first, last = ends[index], ends[index + 1]
        if isinstance(section, Divide):
            cut = section.shortest_divide_path(first, last)
        else:
            cut = substring(
                section,
                section.project(Point(first.point)),
                section.project(Point(last.point)),
            )
        if cut.geom_type != 'LineString' or cut.is_empty:
            raise ValueError('boundary section has coincident or invalid joins')
        if waypoints and index in waypoints:
            choice = waypoints[index]
            cut, receipts = route_line_through_waypoints(
                cast(LineString, cut), choice['points'], choice['max_step_m']
            )
            if connections is not None:
                connections[str(index)] = {'waypoints': receipts}
        points = list(cut.coords)
        points[0], points[-1] = first.point, last.point
        coordinates.extend(points)
        if index in source_sections:
            followed_sources.append(LineString(points))
    # Both sections contribute the same shared point. Keep it once.
    line = remove_repeated_points(LineString(coordinates), tolerance=0)
    values = get_coordinates(line)
    if (
        not line.is_simple
        or not line.is_valid
        or not np.isfinite(values).all()
        or np.any(np.abs(values[:, 0]) > 180)
        or np.any(np.abs(values[:, 1]) > 90)
        or np.any(np.abs(np.diff(values[:, 0])) > 180)
    ):
        raise ValueError(
            'assembled boundary is not a finite simple WGS84 line without a longitude discontinuity'
        )
    return {'type': 'LineString', 'coordinates': values.tolist()}, followed_sources


def cell_containing_point(
    grid: TerrainGrid, point: Sequence[float], *, required: bool = True
) -> tuple[int, int] | None:
    """Find the grid cell containing a geographic point.

    Args:
        grid: Terrain crop and coordinate reference.
        point: Longitude and latitude in WGS84 degrees.
        required: Whether a point outside the crop should raise an error.

    Returns:
        The row and column, or None for an optional point outside the crop.

    Raises:
        ValueError: A required point is outside the crop.
    """
    longitude, latitude = point
    x, y = Transformer.from_crs(4326, grid.crs, always_xy=True).transform(
        longitude, latitude, errcheck=True
    )
    left, a, _, top, _, e = grid.transform
    row, column = math.floor((y - top) / e), math.floor((x - left) / a)
    if not (
        0 <= row < grid.elevation.shape[0] and 0 <= column < grid.elevation.shape[1]
    ):
        if required:
            raise ValueError('selected source point is outside the terrain domain')
        return None
    return row, column


def _cells_reachable_from_divide(
    flow: np.ndarray,
    labels: np.ndarray,
    inside_group: int,
    outside_groups: Sequence[int],
) -> np.ndarray:
    """List cells reached by flowing downhill from the inside edge of the divide.

    Args:
        flow: Two-dimensional array of downstream cell indices.
        labels: Same-sized array with a group ID at every cell (-1 if unknown).
        inside_group: Only visit cells with this label.
        outside_groups: Labels across an edge that can start the path.

    Returns:
        Flat row-major cell indices in ascending order, including the starts.

    Raises:
        ValueError: No inside cell touches the chosen opposing groups.
    """
    height, width = labels.shape
    interface = np.zeros(labels.shape, dtype=bool)
    for dr, dc in ((-1, 0), (0, -1), (0, 1), (1, 0)):
        source = (
            slice(max(0, -dr), min(height, height - dr)),
            slice(max(0, -dc), min(width, width - dc)),
        )
        neighbor = (
            slice(max(0, dr), min(height, height + dr)),
            slice(max(0, dc), min(width, width + dc)),
        )
        interface[source] |= (labels[source] == inside_group) & np.isin(
            labels[neighbor], outside_groups
        )
    # This mask is local, so grow it in place to include the cells it reaches.
    reached = interface.ravel()
    downstream = flow.ravel()
    groups = labels.ravel()
    # Start on the inside cells touching the divide, then follow their water
    # downhill. Only reached cells are candidates near the mapped point.
    todo = list(map(int, np.flatnonzero(reached)))
    while todo:
        following = int(downstream[todo.pop()])
        if (
            following >= 0
            and not reached[following]
            and groups[following] == inside_group
        ):
            reached[following] = True
            todo.append(following)
    eligible = np.flatnonzero(reached)
    if not len(eligible):
        raise ValueError('no source-backed divide flows to the selected drainage group')
    return eligible


def connect_divide_to_stream_head(
    grid: TerrainGrid,
    flow: np.ndarray,
    labels: np.ndarray,
    point: Sequence[float],
    inside_group: int,
    outside_groups: Sequence[int],
    max_step_m: float,
) -> tuple[LineString, dict[str, Any]]:
    """Find a route from the divide to the mapped start of a stream.

    A nearby cell may drain somewhere else. First find the cells water can
    reach from the chosen divide, then pick the one closest to the mapped
    stream start. Follow the terrain flow to that cell and connect its center
    to the exact mapped point.

    Args:
        grid: Terrain crop and coordinate reference.
        flow: Grid of downstream cell indices, with -1 at terminals.
        labels: Grid giving each cell its unique drainage group or -1.
        point: WGS84 coordinate of the source stream head.
        inside_group: Destination associated with the stream head.
        outside_groups: Opposing destinations whose interfaces can start the path.
        max_step_m: Maximum spacing of points in the geodesic connector, in metres.

    Returns:
        The path from the divide through the selected flow cells to the stream head,
        and a report containing the interface cells and connector length.

    Raises:
        ValueError: Available flow and labels do not establish a path from the divide.
    """
    row, column = cast(tuple[int, int], cell_containing_point(grid, point))
    if labels[row, column] != inside_group:
        raise ValueError(
            'source stream head is not assigned to its declared drainage group'
        )
    height, width = labels.shape
    to_geo = Transformer.from_crs(grid.crs, 4326, always_xy=True)

    def center(index: int) -> tuple[float, ...]:
        """Find a terrain cell centre using a flat index.

        Args:
            index: Row-major cell index.

        Returns:
            (longitude, latitude) in degrees.
        """
        rr, cc = divmod(int(index), width)
        return tuple(to_geo.transform(*grid.cell_coordinates(rr, cc), errcheck=True))

    eligible = _cells_reachable_from_divide(flow, labels, inside_group, outside_groups)
    downstream, groups = flow.ravel(), labels.ravel()
    rows, columns = np.divmod(eligible, width)
    lon, lat = to_geo.transform(*grid.cell_coordinates(rows, columns), errcheck=True)
    lengths_to_point = geodesic_distances(lon, lat, point[0], point[1])
    terminal = int(eligible[np.argmin(lengths_to_point)])
    lengths = {terminal: 0.0}
    candidates = []
    # Work back from the chosen cell. Measure each path back to a cell
    # touching the divide. Continue only through cells in the same group.
    for value in cells_draining_to(flow, terminal):
        index = int(value)
        rr, cc = divmod(index, width)
        if index != terminal:
            parent = int(downstream[index])
            if groups[index] != inside_group or parent not in lengths:
                continue
            lengths[index] = lengths[parent] + geodesic_distance(
                center(index), center(parent)
            )
        for dr, dc in ((-1, 0), (0, -1), (0, 1), (1, 0)):
            nr, nc = rr + dr, cc + dc
            if (
                0 <= nr < height
                and 0 <= nc < width
                and labels[nr, nc] in outside_groups
            ):
                neighbor = nr * width + nc
                cost = lengths[index] + 0.5 * geodesic_distance(
                    center(neighbor), center(index)
                )
                candidates.append((cost, index, neighbor))
    # The terminal can be reached from at least one inside cell on the divide.
    _, index, neighbor = min(candidates)
    cells = [index]
    while cells[-1] != terminal:
        cells.append(int(downstream[cells[-1]]))
    centers = [center(value) for value in cells]
    snap = geodesic_distance(centers[-1], point)
    connector = geodesic(centers[-1], point, max_step_m) if snap else [tuple(point)]
    # Start at the center across the divide so this line meets the divide
    # edge. Boundary assembly trims the line at that meeting point.
    coordinates = [center(neighbor), *centers, *connector[1:]]
    return LineString(coordinates), {
        'flow_cells': len(cells),
        'point_snap_m': snap,
        'interface_cells': [list(divmod(index, width)), list(divmod(neighbor, width))],
    }
