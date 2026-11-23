"""Read OSM streams, find where they drain, and check the finished boundary.

An OSM node is a saved point. An OSM way lists the nodes that draw a
line, in order. For drainage, this module follows ways tagged as rivers
or streams and keeps their original points for drawing on the terrain grid.
"""

import math
import shutil
import zipfile
from collections import defaultdict
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

import numpy as np
import osmium
import pyarrow as pa
from osgeo import gdal, osr
from osmium.filter import IdFilter
from osmium.io import File
from osmium.osm import NODE, RELATION, WAY, Node, Relation
from osmium.osm import Way as OsmWay
from osmium.osm.types import OSMEntity
from pyproj import Transformer
from shapely import line_merge, to_wkb
from shapely.geometry import LineString, MultiLineString, Point, Polygon, box
from shapely.geometry.base import BaseGeometry, BaseMultipartGeometry
from shapely.strtree import STRtree

from worldatlas.geodesy.ogr import geometry_layer
from worldatlas.source_assets.archives import archive_member
from worldatlas.source_imports.watersheds.basins import Basins
from worldatlas.source_imports.watersheds.terrain import (
    TerrainGrid,
    wrap_array_as_raster,
)


def _stage_osm_files(
    paths: Iterable[Path | str | tuple[Path | str, str]], directory: Path
) -> Iterator[File]:
    """Open standalone OSM files or unpack archive members for repeated reads.

    Args:
        paths: Files or (archive_path, member_name) selections.
        directory: Temporary directory for extracted members.

    Yields:
        Pyosmium file objects pointing at regular files.

    Raises:
        ValueError: An archive lacks a usable member.
    """
    for index, selection in enumerate(paths):
        path, name = selection if isinstance(selection, tuple) else (selection, None)
        path = Path(path)
        if name is None and not zipfile.is_zipfile(path):
            # Pyosmium can open a standalone file directly from its existing path.
            yield File(str(path), 'pbf' if path.suffix.lower() == '.pbf' else 'osm')
            continue
        with zipfile.ZipFile(path) as archive:
            # A selection like ('rivers.zip', 'north.osm') reads just north.osm.
            # With only the ZIP path, read every .osm and .xml file inside it.
            members = (
                [archive_member(archive, name)]
                if name is not None
                else [
                    item
                    for item in archive.infolist()
                    if item.filename.endswith(('.osm', '.xml'))
                ]
            )
            if not members:
                raise ValueError('OSM archive has no XML responses')
            for member_index, member in enumerate(members):
                kind = 'pbf' if member.filename.lower().endswith('.pbf') else 'osm'
                # Unpack once so the way pass and the node pass can read the same file.
                unpacked = directory / f'{index}-{member_index}.{kind}'
                with archive.open(member) as source, unpacked.open('wb') as output:
                    shutil.copyfileobj(source, output)
                yield File(str(unpacked), kind)


def _intersection_parts(hit: BaseGeometry) -> Iterator[BaseGeometry]:
    """Read the individual point and line pieces of a line intersection.

    Args:
        hit: Intersection result from Shapely.

    Yields:
        Every nonempty Point or LineString, including those in collections.
    """
    if hit.is_empty:
        return
    if hit.geom_type in ('Point', 'LineString'):
        yield hit
    else:
        # One stream can run along the boundary, then cross at a separate spot.
        # Shapely can return both the shared line and the crossing point together.
        assert isinstance(hit, BaseMultipartGeometry)
        for part in hit.geoms:
            yield from _intersection_parts(part)


def _shared_segment_ends(
    start: tuple[float, float], end: tuple[float, float], shared_line: BaseGeometry
) -> Iterator[tuple[tuple[float, ...], tuple[float, ...]]]:
    """Find where a stream joins and leaves the boundary along a segment.

    Args:
        start: Upstream endpoint in longitude and latitude.
        end: Downstream endpoint.
        shared_line: Linework where the stream and boundary coincide.

    Yields:
        Pairs of (entry_point, exit_point) in the direction of flow.
    """
    if start == end:
        return
    parts = _intersection_parts(LineString([start, end]).intersection(shared_line))
    stretches = MultiLineString(
        [part for part in parts if isinstance(part, LineString)]
    )
    # An extra saved point on the boundary can split one shared stretch into
    # two pieces. Join them so we compare the two ends of the whole stretch.
    for stretch in _intersection_parts(line_merge(stretches)):
        # If the water flows A → D and follows the boundary from B to C,
        # return (B, C), even if Shapely gave us the points in reverse order.
        ends = stretch.coords
        first, last = sorted(
            (ends[0], ends[-1]), key=lambda point: math.dist(start, point)
        )
        yield first, last


def _rectangles_from_wgs84_bounds(
    bounds: tuple[float, float, float, float],
) -> tuple[Polygon, ...]:
    """Convert WGS84 bounds to one or two rectangles.

    Args:
        bounds: (west, south, east, north) in degrees.

    Returns:
        A tuple of Shapely polygons. If west exceeds east, split the
        rectangle at the longitude seam.
    """
    west, south, east, north = bounds
    if west <= east:
        return (box(west, south, east, north),)
    # A search from 179°E to 179°W needs two narrow strips next to 180°.
    # One box between those numbers would run through 0° instead.
    return (box(west, south, 180, north), box(-180, south, east, north))


def _line_points_before_and_after(
    line: LineString, coordinates: np.ndarray, point: Sequence[float]
) -> tuple[np.ndarray, np.ndarray]:
    """Find the two vertices around an interior point on a line.

    Args:
        line: Line containing the point.
        coordinates: N-by-2 array of the line's vertices in order.
        point: Coordinates of the interior point.

    Returns:
        Two length-two arrays. At vertex B on A–B–C, return A and C.
    """
    # On A → B → C, a contact at the saved point B needs A and C.
    matches = np.flatnonzero(np.all(coordinates[1:-1] == point, axis=1))
    if matches.size:
        index = matches[0]
        return coordinates[index], coordinates[index + 2]
    # If the contact is between A and B, find its distance along the line
    # and compare it with the distance to each saved point.
    steps = np.diff(coordinates, axis=0)
    distance_along_line = line.project(Point(point))
    index = np.searchsorted(
        np.cumsum(np.hypot(steps[:, 0], steps[:, 1])), distance_along_line
    )
    index = min(index, len(coordinates) - 2)
    return coordinates[index], coordinates[index + 1]


def _boundary_side(
    point: Sequence[float],
    before: Sequence[float] | np.ndarray,
    after: Sequence[float] | np.ndarray,
    neighbor: Sequence[float] | np.ndarray,
) -> int:
    """Tell which side of the boundary a stream moves toward.

    Args:
        point: Shared point on the boundary.
        before: Previous boundary vertex.
        after: Next boundary vertex.
        neighbor: Next point along the stream segment.

    Returns:
        1 or -1 for opposite sides of the line, or 0 along it. With a straight
        west-to-east boundary, -1 is north and 1 is south.
    """

    def angle(vertex: Sequence[float] | np.ndarray) -> float:
        """Measure the direction from the contact point to a vertex.

        Args:
            vertex: Coordinates of the vertex.

        Returns:
            Angle in radians measured from the positive x axis.
        """
        return math.atan2(vertex[1] - point[1], vertex[0] - point[0])

    start = angle(before)
    # Look out from the contact toward the two nearby boundary points.
    # Their directions split the full circle in two, even at a sharp bend.
    # Measure the stream direction from the same starting direction.
    end = (angle(after) - start) % math.tau
    arm = (angle(neighbor) - start) % math.tau
    # The signs label the two sides. For a straight boundary drawn from
    # west to east, -1 is north, 1 is south, and 0 points along the line.
    if arm == 0 or arm == end:
        return 0
    return 1 if arm < end else -1


type BoundaryContact = str | tuple[str, int, tuple[float, ...]]


def _follow_shared_stretches(
    points: Mapping[BoundaryContact, tuple[float, ...]],
    downstream: defaultdict[BoundaryContact, set[BoundaryContact]],
    arrivals: Mapping[BoundaryContact, set[tuple[int, str]]],
    departures: Mapping[BoundaryContact, set[tuple[int, str]]],
    endpoints: Collection[tuple[float, ...]],
) -> defaultdict[tuple[float, ...], set[str]]:
    """Find stream routes that enter on one side and leave on the other.

    For A → B → C → D, B → C runs along the boundary. If A and D
    are on different sides, report the crossing at C on the departing way.

    Args:
        points: Coordinates by contact ID.
        downstream: Next contacts along shared stretches.
        arrivals: (side, OSM way ID) pairs arriving at each contact.
        departures: (side, OSM way ID) pairs leaving each contact.
        endpoints: Coordinates at the ends of the whole boundary.

    Returns:
        The crossing coordinates and OSM way IDs that leave there.
    """
    crossings = defaultdict(set)
    # Follow water arriving from each side. For water that joined from
    # above, an exit below counts as crossing and an exit above is fine.
    for entry_side in (-1, 1):
        # Take at least one shared stretch. Crossings that occur at a
        # single point are handled by the normal junction check.
        reached = {
            neighbor
            for node, branches in arrivals.items()
            if any(side == entry_side for side, _ in branches)
            for neighbor in downstream[node]
        }
        pending = list(reached)
        while pending:
            node = pending.pop()
            if points[node] in endpoints:
                continue
            for side, way in departures.get(node, ()):
                if side == -entry_side:
                    crossings[points[node]].add(way)
            for neighbor in downstream[node] - reached:
                reached.add(neighbor)
                pending.append(neighbor)
    return crossings


@dataclass
class Way:
    """Keep the values needed after Pyosmium advances beyond a way.

    Args:
        nodes: Ordered OSM node IDs, normally from upstream to downstream.
        tags: Provider attributes, including the waterway classification.
        version: OSM object version in the archive.
    """

    nodes: tuple[str, ...]
    tags: dict[str, str]
    version: int

    @property
    def is_river_or_stream(self) -> bool:
        """Check how OSM classifies this way for drainage tracing.

        Returns:
            Whether the ``waterway`` tag is ``river`` or ``stream``.
        """
        return self.tags.get('waterway') in ('river', 'stream')


class Waterways:
    """Connect streams at shared OSM nodes and keep their shapes for map checks."""

    def __init__(
        self,
        paths: Iterable[Path | str | tuple[Path | str, str]],
        *,
        rivers_and_streams_only: bool = False,
        reverse: Iterable[int | str] = (),
    ) -> None:
        """Read OSM extracts and connect rivers and streams downstream.

        Args:
            paths: Local OSM XML, XML archives, PBF files, or ``(archive, member)`` selections.
            rivers_and_streams_only: Whether to retain only rivers and streams and their nodes.
            reverse: IDs of rivers and streams with reviewed direction corrections.
        """
        # The same numeric ID can name a node, a way, and a relation.
        self.nodes, self.ways, self.relations = {}, {}, {}
        self.rivers_and_streams_only = rivers_and_streams_only
        self._node_versions, self._way_versions = {}, {}
        self._read_osm_files(paths)
        # The recipe can correct a mapped flow direction. Wait until we know
        # which version of the way we kept.
        for ident in sorted(set(map(str, reverse))):
            if ident not in self.ways or not self.ways[ident].is_river_or_stream:
                raise ValueError(
                    f'river or stream {ident} is missing from the ways available to reverse'
                )
            way = self.ways[ident]
            # Reversing A → B → C to C → B → A draws the same line.
            self.ways[ident] = Way(tuple(reversed(way.nodes)), way.tags, way.version)
        self.river_and_stream_ids = {
            ident for ident, way in self.ways.items() if way.is_river_or_stream
        }
        # Find ways we cannot draw. A later check decides whether the missing
        # points are close enough to the area we are studying to stop the build.
        self.incomplete = {
            ident
            for ident in self.river_and_stream_ids
            if len(self.ways[ident].nodes) < 2
            or any(n not in self.nodes for n in self.ways[ident].nodes)
        }
        self._connect_streams()
        self._lines, self._waterway_index = {}, None

    def _read_osm_files(
        self, paths: Iterable[Path | str | tuple[Path | str, str]]
    ) -> None:
        """Load and merge the OSM objects needed for this network.

        Args:
            paths: Local OSM files or (ZIP path, member name) selections.
        """
        with TemporaryDirectory(prefix='watershed-osm-') as directory:
            files = list(_stage_osm_files(paths, Path(directory)))
            # For drainage, first find the rivers and streams. Then read only
            # the points they use. Reading a source line can need all object types.
            entities = WAY if self.rivers_and_streams_only else NODE | WAY | RELATION
            for file in files:
                self._merge_osm_objects(osmium.FileProcessor(file, entities))
            if self.rivers_and_streams_only:
                # Merge all way versions before deciding which nodes to read.
                # A selected way can reference nodes in a different extract.
                wanted = {int(node) for way in self.ways.values() for node in way.nodes}
                if wanted:
                    node_filter = IdFilter(wanted)
                    for file in files:
                        reader = osmium.FileProcessor(file, NODE).with_filter(
                            node_filter
                        )
                        self._merge_osm_objects(reader)
        # Version tracking is only needed while merging the input files.
        del self._node_versions, self._way_versions

    def _connect_streams(self) -> None:
        """Join streams at shared OSM nodes and retain the points between them.

        For A → B → C, the routing graph needs only A → C if B just draws
        a bend. An edge keeps the source way and positions of A and C so
        the renderer can still draw all three points.
        """
        self.upstream, self.downstream = defaultdict(set), defaultdict(set)
        self.edge_sources = defaultdict(list)
        complete_way_ids = sorted(self.river_and_stream_ids - self.incomplete)
        complete_point_ids, connection_point_ids = set(), set()
        for way_id in complete_way_ids:
            point_ids = self.ways[way_id].nodes
            connection_point_ids.update((point_ids[0], point_ids[-1]))
            for point_id in point_ids:
                if point_id in complete_point_ids:
                    connection_point_ids.add(point_id)
                complete_point_ids.add(point_id)
        for way_id in self.incomplete:
            shared_point_ids = complete_point_ids.intersection(self.ways[way_id].nodes)
            connection_point_ids.update(shared_point_ids)
        # If a stream runs A → B → C, the flow lookup can go straight from A
        # to C when B only draws a bend. Keep B as a stop when it appears
        # more than once, including when a way with missing points uses it.
        self.topology_nodes = connection_point_ids
        for ident in complete_way_ids:
            for (start, first), (end, second) in self.iter_way_connection_pairs(ident):
                self.upstream[second].add(first)  # At second, water arrives from first.
                self.downstream[first].add(
                    second
                )  # At first, water flows next to second.
                # Keep the source positions so we can draw A → B → C when
                # the flow lookup only stores A → C.
                self.edge_sources[first, second].append((ident, start, end))

    def _merge_node(self, ident: str, version: int, point: tuple[float, float]) -> None:
        """Keep the latest saved version of an OSM node.

        Args:
            ident: Node ID.
            version: Version in the archive.
            point: Longitude and latitude of the node.

        Raises:
            ValueError: Matching versions have different coordinates.
        """
        previous_version = self._node_versions.get(ident)
        if previous_version is not None and version <= previous_version:
            if version == previous_version and self.nodes[ident] != point:
                raise ValueError('conflicting same-version OSM node')
            return
        self.nodes[ident], self._node_versions[ident] = point, version

    def _merge_way(self, ident: str, way: OsmWay) -> None:
        """Keep the latest version of a way and apply the stream filter.

        Args:
            ident: OSM way ID.
            way: Pyosmium way, valid until the reader advances.

        Raises:
            ValueError: Matching versions disagree about the retained way.
        """
        previous_version, previous_is_river_or_stream = self._way_versions.get(
            ident, (None, None)
        )
        version = way.version
        if previous_version is not None and version < previous_version:
            return
        is_river_or_stream = way.tags.get('waterway') in ('river', 'stream')
        # Track a newer version even when its new tag excludes it. That keeps
        # an older stream from returning after the source retags it as a canal.
        # We only need to copy node IDs and tags for ways we keep.
        selected = None
        if not self.rivers_and_streams_only or is_river_or_stream:
            selected = Way(
                tuple(str(node.ref) for node in way.nodes), dict(way.tags), version
            )
        if version == previous_version:
            if (
                previous_is_river_or_stream != is_river_or_stream
                or self.ways.get(ident) != selected
            ):
                raise ValueError('conflicting same-version OSM way')
            return
        self._way_versions[ident] = (version, is_river_or_stream)
        if selected is None:
            self.ways.pop(ident, None)
        else:
            self.ways[ident] = selected

    def _merge_relation(
        self, ident: str, version: int, members: tuple[tuple[str, str, str], ...]
    ) -> None:
        # We keep all relations we read, so each saved relation can hold its own version.
        """Keep the latest version of a relation.

        Args:
            ident: OSM relation ID.
            version: Version in the archive.
            members: Ordered (type, ID, role) records.

        Raises:
            ValueError: Matching versions have different members.
        """
        previous_version, previous_members = self.relations.get(ident, (None, None))
        if previous_version is not None and version <= previous_version:
            if version == previous_version and previous_members != members:
                raise ValueError('conflicting same-version OSM relation')
            return
        self.relations[ident] = (version, members)

    def _merge_osm_objects(self, objects: Iterable[OSMEntity]) -> None:
        """Copy values from transient Pyosmium objects into the network.

        Args:
            objects: Nodes, ways or relations from the reader.
        """
        member_types = {'n': 'node', 'w': 'way', 'r': 'relation'}
        for obj in objects:
            # Pyosmium's object is valid only until the reader advances.
            ident = str(obj.id)
            if isinstance(obj, Node):
                location = obj.location
                if not location.valid():
                    raise ValueError('invalid OSM node coordinates')
                self._merge_node(ident, obj.version, (location.lon, location.lat))
            elif isinstance(obj, OsmWay):
                self._merge_way(ident, obj)
            else:
                # The reader is configured to yield only nodes, ways, and relations.
                assert isinstance(obj, Relation)
                members = tuple(
                    (member_types[m.type], str(m.ref), m.role) for m in obj.members
                )
                self._merge_relation(ident, obj.version, members)

    def iter_way_connection_pairs(
        self, way_id: str
    ) -> Iterator[tuple[tuple[int, str], tuple[int, str]]]:
        """Find the stretches between points where we stop to trace flow.

        Args:
            way_id: OSM way ID.

        Returns:
            Pairs of ``(position, OSM node ID)`` values. For a way with nodes
            10, 11, and 12, ``((0, "10"), (2, "12"))`` describes one stretch
            from node 10 to node 12. Node 11 still draws the bend in the line.
        """
        anchors = [
            (i, node)
            for i, node in enumerate(self.ways[str(way_id)].nodes)
            if node in self.topology_nodes
        ]
        return pairwise(anchors)

    def way_line(
        self, way_id: str | int, start: int = 0, end: int | None = None
    ) -> LineString:
        """Draw a way or a selected stretch in the order we store its points.

        Args:
            way_id: OSM way ID.
            start: Index of the first included node.
            end: Index of the last included node, or None to include the way's end.

        Returns:
            A Shapely LineString with the source coordinates.

        Raises:
            ValueError: The way is too short or its archive lacks referenced nodes.
        """
        way_id = str(way_id)
        way = self.ways[way_id]
        end = len(way.nodes) - 1 if end is None else end
        key = way_id, start, end
        if key in self._lines:
            return self._lines[key]
        if len(way.nodes) < 2 or any(n not in self.nodes for n in way.nodes):
            raise ValueError('selected OSM way has missing nodes')
        self._lines[key] = LineString(
            [self.nodes[n] for n in way.nodes[start : end + 1]]
        )
        return self._lines[key]

    def way_ids_intersecting_grid_bounds(self, grid: TerrainGrid) -> list[str]:
        """Find complete rivers and streams that intersect the grid's bounding rectangle.

        Args:
            grid: Terrain crop and coordinate reference.

        Returns:
            The matching way IDs. Downstream geometry outside the crop is retained.
        """
        x, a, _, y, _, e = grid.transform
        height, width = grid.elevation.shape
        # (x, y) is the top-left corner. Each column moves right by a, and each
        # row moves down by e, which is negative. Pass left, bottom, right, top.
        # Convert to longitude and latitude so we can look up OSM streams.
        # Use pyproj's default of 21 extra points per side because an edge can
        # curve past its corners during conversion. Raise if conversion fails.
        bounds = Transformer.from_crs(grid.crs, 4326, always_xy=True).transform_bounds(
            x, y + height * e, x + width * a, y, densify_pts=21, errcheck=True
        )
        return self.way_ids_intersecting_bounds(bounds)

    def way_ids_intersecting_bounds(
        self, bounds: tuple[float, float, float, float]
    ) -> list[str]:
        """Find complete rivers and streams that intersect a WGS84 rectangle.

        Args:
            bounds: West, south, east, and north limits. For example,
                ``(179, -1, -179, 1)`` spans the two degrees around 180°.

        Returns:
            Sorted IDs of complete mapped rivers and streams intersecting the rectangle.
        """
        return self._way_ids_intersecting_shapes(_rectangles_from_wgs84_bounds(bounds))

    def _way_ids_intersecting_shapes(self, shapes: Sequence[BaseGeometry]) -> list[str]:
        """Find indexed stream ways that intersect any supplied shape.

        Args:
            shapes: Rectangles or other search geometries.

        Returns:
            Unique OSM way IDs in spatial index order.
        """
        # Build the lookup on the first search. Later searches reuse it.
        # The tree returns line positions, so keep their OSM IDs in that order.
        if self._waterway_index is None:
            self._indexed_way_ids = sorted(self.river_and_stream_ids - self.incomplete)
            self._waterway_index = STRtree(
                [self.way_line(way_id) for way_id in self._indexed_way_ids]
            )
        indices = {
            int(index)
            for shape in shapes
            for index in self._waterway_index.query(shape, predicate='intersects')
        }
        return [self._indexed_way_ids[index] for index in sorted(indices)]

    def require_known_drainage_in_bounds(
        self,
        bounds: Iterable[tuple[float, float, float, float]],
        report: dict[str, Any],
    ) -> None:
        """Stop if missing stream data could change the divide in a crop.

        Args:
            bounds: WGS84 rectangles covered by the terrain calculation.
            report: Downstream tracing report with unresolved sections.

        Raises:
            ValueError: A relevant way has missing geometry or an unresolved route.
        """
        areas = [
            area
            for rectangle in bounds
            for area in _rectangles_from_wgs84_bounds(rectangle)
        ]
        relevant = set(self._way_ids_intersecting_shapes(areas))
        relevant_nodes = {node for ident in relevant for node in self.ways[ident].nodes}
        # Say a stream uses A → B but B is missing. Stop if A lies in the
        # crop or joins a complete stream that reaches the crop.
        for ident in sorted(self.incomplete):
            nodes = self.ways[ident].nodes
            if relevant_nodes.intersection(nodes) or any(
                node in self.nodes
                and any(area.covers(Point(self.nodes[node])) for area in areas)
                for node in nodes
            ):
                raise ValueError(
                    f'river or stream {ident} has missing source coordinates; repair the source'
                )
        # A known outlet on one branch does not resolve another branch.
        # Stop only if the uncertainty affects a way that touches a crop.
        for section in report['unresolved_sections']:
            affected = [
                way for way, _, _ in section['source_segments'] if way in relevant
            ]
            if affected:
                raise ValueError(
                    f'river or stream {affected[0]} has an unresolved downstream route '
                    f'from node {section["nodes"][1]}; known groups={section["groups"]}; '
                    f'first unresolved node={section["unresolved_node"]}; repair the source'
                )

    def drainage_groups_by_outgoing_node(
        self, node: str, assigned: Mapping[tuple[str, str], tuple[int, ...]]
    ) -> dict[str, int]:
        """Find the destination of each branch leaving the fork.

        Args:
            node: OSM node ID of the selected fork.
            assigned: Known groups for each ``(upstream node, downstream node)`` stretch.

        Returns:
            A map like ``{'3': 1, '4': 2}``. Water leaving toward node 3
            drains to group 1 and water leaving toward node 4 drains to group 2.
            Return an empty map if any branch lacks exactly one known group.
        """
        destinations = {}
        for downstream in self.downstream.get(node, ()):
            edge = node, downstream
            groups = assigned.get(edge, ())
            # To allow this boundary contact, we need one known destination
            # for every outgoing branch.
            if len(groups) != 1:
                return {}
            (group,) = groups
            for way, start, _ in self.edge_sources[edge]:
                # The next network junction may be far away. The crossing
                # check uses the first OSM node after the fork to find which
                # side of the boundary the branch leaves on.
                neighbor = self.ways[way].nodes[start + 1]
                # A node used by several routes is itself a network stop.
                # Those routes therefore share this edge and its group.
                destinations[neighbor] = group
        return destinations

    def check_boundary_crossings(
        self,
        geometry: LineString,
        *,
        shared_forks: Mapping[str, dict[str, int]] | None = None,
        followed_source_line: BaseGeometry | None = None,
    ) -> dict[str, Any]:
        """Check whether water crosses the finished boundary.

        A river can touch the boundary and turn back to the same side. A
        selected fork can also sit on the boundary if water arrives from
        one side and the outgoing branches on opposite sides lead to two
        different known drainage groups.

        Args:
            geometry: The finished boundary line in WGS84 longitude and latitude.
            shared_forks: Map from each selected fork's OSM node ID to the
                drainage group of each immediate downstream OSM node.
            followed_source_line: Assembled portions that deliberately follow
                a mapped source line. A river can receive and release water
                on both sides of a reach chosen as the boundary.

        Returns:
            A report of stream ends and junctions that touch the boundary,
            including any selected forks that passed the check.

        Raises:
            ValueError: Water crosses at an unapproved point or follows the
                boundary and leaves on the opposite side. The error gives the
                coordinates and OSM way IDs of the first crossing.
        """
        shared_forks = shared_forks or {}
        coordinates = np.asarray(geometry.coords)
        ways = self._way_ids_intersecting_shapes((geometry,))
        point_hits, overlaps = self._boundary_intersections(geometry, coordinates, ways)
        crossings, along_boundary_arms = self._crossings_along_boundary(
            geometry, ways, overlaps, followed_source_line
        )

        junctions, river_ends, shared = self._crossings_at_contacts(
            geometry,
            coordinates,
            ways,
            point_hits,
            along_boundary_arms,
            shared_forks,
            crossings,
        )
        result = {
            'indexed_river_and_stream_ways': len(self._indexed_way_ids),
            'junction_contacts': sorted(junctions),
            'river_endpoint_contacts': sorted(river_ends),
            'shared_drainage_contacts': [
                {'node': node, 'groups': shared[node]} for node in sorted(shared)
            ],
            'crossings': [
                {'point': list(cast(tuple[float, ...], point)), 'ways': sorted(ways)}
                for point, ways in sorted(crossings.items())
            ],
        }
        if crossings:
            first = result['crossings'][0]
            raise ValueError(
                f'boundary crosses a river or stream {first["ways"]} at {first["point"]}'
            )
        return result

    def _boundary_intersections(
        self, geometry: LineString, coordinates: np.ndarray, ways: Collection[str]
    ) -> tuple[dict[tuple[float, ...], set[str]], dict[str, list[LineString]]]:
        """Separate individual meeting points from stretches shared with the boundary.

        Args:
            geometry: Finished boundary line.
            coordinates: Longitude and latitude pairs of the boundary vertices.
            ways: OSM way IDs whose lines meet the boundary.

        Returns:
            Ways by isolated contact coordinate and shared stretches by way ID.
        """
        endpoints = {tuple(coordinates[0]), tuple(coordinates[-1])}
        # Keep isolated meeting points in point_hits and shared lines in overlaps.
        # A stream can change sides at one spot or after following the boundary.
        # At a boundary endpoint, water can go around the end.
        point_hits = defaultdict(set)
        overlaps = defaultdict(list)
        for ident in ways:
            for part in _intersection_parts(
                geometry.intersection(self.way_line(ident))
            ):
                if part.geom_type == 'LineString':
                    overlaps[ident].append(part)
                else:
                    point = tuple(part.coords[0])
                    if point not in endpoints:
                        point_hits[point].add(ident)

        return point_hits, overlaps

    def _branches_at_contacts(
        self,
        ways: Collection[str],
        point_hits: Mapping[tuple[float, ...], set[str]],
    ) -> tuple[
        Mapping[tuple[float, ...], Mapping[str, set[tuple[str, str, bool]]]],
        dict[tuple[float, ...], set[str]],
    ]:
        """Find which branches meet at each OSM node on the boundary.

        Args:
            ways: OSM way IDs whose lines meet the boundary.
            point_hits: Ways by contact coordinate.

        Returns:
            Branches by contact coordinate and node ID. Each branch is
            (way ID, neighboring node ID, whether water leaves the contact).
            Also returns which ways have a saved node at each contact.
        """
        # For 1 → 2 → 3 with node 2 on the boundary, record the branch toward
        # node 1 as incoming (False) and the branch toward node 3 as outgoing
        # (True). Ways that share node 2 are part of the same junction.
        arms = defaultdict(lambda: defaultdict(set))
        ways_with_saved_points = defaultdict(set)
        for ident in ways:
            nodes = self.ways[ident].nodes
            for index, node in enumerate(nodes):
                point = self.nodes[node]
                if point not in point_hits:
                    continue
                ways_with_saved_points[point].add(ident)
                if index:
                    arms[point][node].add((ident, nodes[index - 1], False))
                if index + 1 < len(nodes):
                    arms[point][node].add((ident, nodes[index + 1], True))

        return arms, ways_with_saved_points

    def _crossings_at_contacts(
        self,
        geometry: LineString,
        coordinates: np.ndarray,
        ways: Collection[str],
        point_hits: Mapping[tuple[float, ...], set[str]],
        along_boundary_arms: set[tuple[str, str, str, bool]],
        shared_forks: Mapping[str, dict[str, int]],
        crossings: dict[tuple[float, ...], set[str]],
    ) -> tuple[set[str], set[str], dict[str, list[int]]]:
        """Check whether water changes sides at an individual contact point.

        An OSM segment can cross between its saved nodes. At a saved node,
        follow the actual incoming and outgoing branches to see which way
        the water moves. The reviewed fork exception is checked here.

        Args:
            geometry: Finished boundary in WGS84.
            coordinates: Boundary vertices in line order.
            ways: IDs of all intersecting OSM ways.
            point_hits: Way IDs by point where they meet the boundary.
            along_boundary_arms: Branches covered by the shared-stretch check.
            shared_forks: Reviewed outgoing destinations keyed by fork node ID.
            crossings: Crossings by coordinate, updated in place.

        Returns:
            Junction node IDs, stream-end node IDs, and accepted fork node
            IDs with their sorted destination group IDs.
        """
        arms, ways_with_saved_points = self._branches_at_contacts(ways, point_hits)

        junctions, river_ends, shared = set(), set(), {}
        for point, hit_ways in sorted(point_hits.items()):
            # Use the boundary just before and after this point to tell
            # which side each branch is on, even where the boundary bends.
            before, after = _line_points_before_and_after(geometry, coordinates, point)

            def side(neighbor: Sequence[float] | np.ndarray) -> int:
                """Tell which side the stream moves toward from this contact.

                Args:
                    neighbor: Coordinates of the next stream point.

                Returns:
                    Side code -1 or 1, or 0 if the segment follows the boundary.
                """
                return _boundary_side(point, before, after, neighbor)

            # Water can flow straight from A above the boundary to B below,
            # with no saved river point on the boundary. Opposite sides
            # multiply to -1.
            for ident in hit_ways - ways_with_saved_points[point]:
                river = self.way_line(ident)
                entry, exit = _line_points_before_and_after(
                    river, np.asarray(river.coords), point
                )
                if side(entry) * side(exit) == -1:
                    crossings[point].add(ident)

            for node, branches in arms[point].items():
                incoming, outgoing = set(), {}
                neighbors = {neighbor for _, neighbor, _ in branches}
                for ident, neighbor, leaves in branches:
                    arm = ident, node, neighbor, leaves
                    branch_side = (
                        0 if arm in along_boundary_arms else side(self.nodes[neighbor])
                    )
                    if leaves:
                        outgoing[neighbor] = branch_side
                    else:
                        incoming.add(branch_side)
                # A crossing needs water arriving from one side and leaving
                # on the other. Side 0 means the branch points along the boundary.
                crosses = any(
                    -branch_side in incoming
                    for branch_side in outgoing.values()
                    if branch_side
                )
                if crosses:
                    # Allow a selected fork when water arrives from one side
                    # and leaves on both. All branches leaving on a given
                    # side must lead to the same known group, and the two
                    # sides must lead to different groups.
                    groups = shared_forks.get(node, {})
                    if (
                        len(incoming) == 1
                        and set(outgoing.values()) == {-1, 1}
                        and groups.keys() == outgoing.keys()
                    ):
                        by_side = {
                            branch_side: {
                                groups[n]
                                for n in outgoing
                                if outgoing[n] == branch_side
                            }
                            for branch_side in (-1, 1)
                        }
                        if (
                            all(len(values) == 1 for values in by_side.values())
                            and by_side[-1] != by_side[1]
                        ):
                            shared[node] = sorted(set(groups.values()))
                            junctions.add(node)
                            continue
                    crossings[point].update(ident for ident, _, _ in branches)
                # Three or more neighbors make a junction. One means the
                # stream starts or ends here. Skip an ordinary touch with two.
                elif len(neighbors) > 2:
                    junctions.add(node)
                elif len(neighbors) == 1:
                    river_ends.add(node)
        return junctions, river_ends, shared

    def _crossings_along_boundary(
        self,
        boundary: LineString,
        ways: Collection[str],
        overlaps: Mapping[str, list[LineString]],
        followed_source_line: BaseGeometry | None,
    ) -> tuple[dict[tuple[float, ...], set[str]], set[tuple[str, str, str, bool]]]:
        """Find routes that cross while following a shared boundary stretch.

        Args:
            boundary: Completed boundary to check.
            ways: OSM way IDs involved in the check.
            overlaps: Boundary stretches that each way follows.
            followed_source_line: Optional stretches intentionally chosen as the
                boundary.

        Returns:
            Crossings keyed by contact coordinates, and stream branches already
            counted along a shared stretch.
        """
        crossings, shared_arms = defaultdict(set), set()
        if not overlaps:
            return crossings, shared_arms

        # If a stream joins the boundary at B, follows it to C, and leaves
        # at C, record B → C here. Other branches may join or leave at either end.
        downstream = defaultdict(set)
        points = {}
        arrivals, departures = defaultdict(set), defaultdict(set)
        coordinates = np.asarray(boundary.coords)
        endpoints = {tuple(coordinates[0]), tuple(coordinates[-1])}
        boundary_neighbors = {}

        def record_branch(
            branches: dict[BoundaryContact, set[tuple[int, str]]],
            contact: BoundaryContact,
            neighbor: Sequence[float],
            way: str,
        ) -> None:
            """Record the side of an incoming or outgoing stream branch at one contact.

            Args:
                branches: Contacts mapped to (side, way_id) pairs.
                contact: Saved node ID or an interior point on a way segment.
                neighbor: Next coordinates away from the boundary.
                way: OSM way ID.
            """
            point = points[contact]
            # Water can go around the end of the boundary.
            if point in endpoints:
                return
            if point not in boundary_neighbors:
                boundary_neighbors[point] = _line_points_before_and_after(
                    boundary, coordinates, point
                )
            before, after = boundary_neighbors[point]
            side = _boundary_side(point, before, after, neighbor)
            if side:
                branches[contact].add((side, way))

        # Connect shared stretches by saved OSM node ID. If the stream joins
        # in the middle of an OSM segment, identify that spot by the way,
        # segment position, and coordinates so it only connects to its own way.
        for way, lines in overlaps.items():
            shared_line = MultiLineString(lines)
            # The Ural recipe uses the main river as the boundary. A side
            # channel can leave that river, so skip the stretches the recipe
            # chose here. The check for crossings at individual points still runs.
            if followed_source_line is not None:
                shared_line = shared_line.difference(followed_source_line)
                if shared_line.is_empty:
                    continue
            for index, (upstream, downstream_node) in enumerate(
                pairwise(self.ways[way].nodes)
            ):
                start, end = self.nodes[upstream], self.nodes[downstream_node]
                for first, last in _shared_segment_ends(start, end, shared_line):
                    entry = upstream if first == start else (way, index, first)
                    exit = downstream_node if last == end else (way, index, last)
                    points[entry], points[exit] = first, last
                    downstream[entry].add(exit)
                    if first == start:
                        shared_arms.add((way, upstream, downstream_node, True))
                    else:
                        record_branch(arrivals, entry, start, way)
                    if last == end:
                        shared_arms.add((way, downstream_node, upstream, False))
                    else:
                        record_branch(departures, exit, end, way)

        # An incoming branch may be in a different way from the shared line.
        # If A → B reaches the boundary and B → C follows it, record A → B
        # as an arrival. B → C is already stored in downstream.
        for way in ways:
            for upstream, downstream_node in pairwise(self.ways[way].nodes):
                start, end = self.nodes[upstream], self.nodes[downstream_node]
                if start == end:
                    continue
                if (
                    upstream in points
                    and (way, upstream, downstream_node, True) not in shared_arms
                ):
                    record_branch(departures, upstream, end, way)
                if (
                    downstream_node in points
                    and (way, downstream_node, upstream, False) not in shared_arms
                ):
                    record_branch(arrivals, downstream_node, start, way)

        crossings = _follow_shared_stretches(
            points, downstream, arrivals, departures, endpoints
        )
        return crossings, shared_arms

    def trace_destinations_from_ways(
        self,
        groups: Mapping[int, Collection[int | str]]
        | Mapping[str, Collection[int | str]],
    ) -> tuple[dict[tuple[str, str], tuple[int, ...]], dict[str, Any]]:
        """Find which streams flow to the ends of the selected OSM ways.

        Args:
            groups: Map from drainage group IDs to lists of OSM way IDs.
                For example, ``{3: ['10']}`` uses the end of way 10 as a
                known destination for group 3.

        Returns:
            The pair ``(assigned, report)``. In ``assigned``, an entry like
            ``{('101', '103'): (3,)}`` says water flowing from node 101 to
            node 103 can reach group 3. A stretch can reach several groups.
            Stretches with no known group are absent from ``assigned``.
            The ``report`` lists ways with missing coordinates and stretches
            that reach multiple groups or have an unresolved downstream route,
            including stretches with no known group.

        Raises:
            ValueError: A group ID is invalid or a selected way is missing or incomplete.
        """
        roots = {}
        for group, ways in groups.items():
            if int(group) < 0 or not ways:
                raise ValueError(
                    'nonnegative group IDs and downstream ways are required'
                )
            seen = set()
            for ident in map(str, ways):
                if ident not in self.river_and_stream_ids or ident in self.incomplete:
                    raise ValueError(
                        f'selected river or stream {ident} is missing or incomplete'
                    )
                # The selected downstream endpoint is the reference. Walking
                # upstream already reaches every earlier node of this way.
                seen.add(self.ways[ident].nodes[-1])
            roots[int(group)] = seen
        return self._trace_upstream_destinations(roots)

    def trace_destinations_from_basins(
        self, basins: Basins
    ) -> tuple[dict[tuple[str, str], tuple[int, ...]], dict[str, Any]]:
        """Find each stream's drainage group using the basin map at its end.

        Args:
            basins: Source basin polygons and the drainage groups assigned by the recipe.

        Returns:
            ``(assigned, report)``, with the same stretch-to-group map as
            ``trace_destinations_from_ways``. The report also records where
            a stream left a basin before its mapped line ended.
        """
        roots = defaultdict(set)
        coastal, seen = [], set()
        # Start where an OSM stream ends. The basin covering the end point
        # can tell us where all connected streams upstream drain.
        todo = sorted(node for node in self.topology_nodes if not self.downstream[node])
        while todo:
            node = todo.pop()
            if node in seen:
                continue
            seen.add(node)
            values = basins.basin_ids_at_point(self.nodes[node])
            if values:
                group = basins.group_for_basin_ids(values)
                if group >= 0:
                    roots[group].add(node)
                continue
            # Say the river flows A → B → C. The basin ends at B, but the
            # mapped river reaches C in the estuary. Walk backward until we
            # find B and use the basin there. If that basin has no known
            # group, stop there instead of looking for a different basin.
            for parent in sorted(self.upstream[node]):
                for ident, start, end in self.edge_sources[parent, node]:
                    way = self.ways[ident]
                    line = LineString(
                        [self.nodes[n] for n in way.nodes[start : end + 1]]
                    )
                    group, point = basins.river_exit_group_and_point(line)
                    if group >= 0:
                        roots[group].add(node)
                        coastal.append(
                            {
                                'way': ident,
                                'group': group,
                                'point': list(cast(tuple[float, ...], point)),
                            }
                        )
                    elif point is None:
                        todo.append(parent)
        assigned, report = self._trace_upstream_destinations(roots)
        report['basin_exit_before_way_endpoint'] = coastal
        return assigned, report

    def _trace_upstream_destinations(
        self, roots: Mapping[int, set[str]]
    ) -> tuple[dict[tuple[str, str], tuple[int, ...]], dict[str, Any]]:
        """Find which known and unknown outlets can be reached from each stream segment.

        Args:
            roots: Known drainage group IDs mapped to outlet node IDs.

        Returns:
            Segment endpoints mapped to tuples of known groups, plus a report
            of shared destinations, missing coordinates and unresolved branches.
        """
        reaches = {}
        # If A → B → C and C drains to group 3, work backward from C.
        # Both B and A can reach group 3. Repeat separately for each group.
        for group, initial in roots.items():
            seen = set(initial)
            todo = list(sorted(seen))
            while todo:
                for node in sorted(self.upstream[todo.pop()]):
                    if node not in seen:
                        seen.add(node)
                        todo.append(node)
            reaches[int(group)] = seen
        # Now work backward from the unknown ends. If B also flows to D and
        # we do not know where D drains, A → B has an unresolved route even
        # though it can also reach group 3.
        known = set().union(*reaches.values()) if reaches else set()
        supported = set().union(*roots.values()) if roots else set()
        unresolved = {node: node for node in self.topology_nodes - known}
        # A way with missing coordinates may hide a route from a junction.
        # Start the same backward search at the junction where it connects.
        for ident in self.incomplete:
            unresolved.update(
                (node, node)
                for node in self.ways[ident].nodes
                if node in self.topology_nodes
            )
        todo = list(sorted(unresolved))
        while todo:
            node = todo.pop()
            for parent in sorted(self.upstream[node]):
                # Once a point is an accepted destination, uncertainty
                # farther downstream does not undo the known group there.
                if parent in supported:
                    continue
                if parent not in unresolved:
                    unresolved[parent] = unresolved[node]
                    todo.append(parent)
        assigned, ambiguous, unassigned, shared, missing = {}, set(), set(), [], []
        # For A → B, read B's destinations. Record both group 3 and the
        # unresolved branch when B can reach C and D in the example above.
        for edge, references in sorted(self.edge_sources.items()):
            matches = tuple(
                sorted(group for group, nodes in reaches.items() if edge[1] in nodes)
            )
            if matches:
                assigned[edge] = matches
            if edge[1] in unresolved:
                missing.append(
                    {
                        'nodes': list(edge),
                        'groups': list(matches),
                        'source_segments': [
                            list(reference) for reference in references
                        ],
                        'unresolved_node': unresolved[edge[1]],
                    }
                )
            if len(matches) > 1:
                ambiguous.update(ident for ident, _, _ in references)
                shared.append(
                    {
                        'nodes': list(edge),
                        'groups': list(matches),
                        'source_segments': [
                            list(reference) for reference in references
                        ],
                    }
                )
            elif not matches:
                unassigned.update(ident for ident, _, _ in references)
        return assigned, {
            'ambiguous': sorted(ambiguous),
            'unassigned': sorted(unassigned),
            'incomplete': sorted(self.incomplete),
            'shared_sections': shared,
            'unresolved_sections': missing,
        }


def rasterize_waterway_lines(
    lines: Sequence[LineString], grid: TerrainGrid
) -> np.ndarray:
    """Mark the elevation cells that a stream line touches.

    Args:
        lines: Stream lines in longitude and latitude.
        grid: Elevation grid that supplies cell positions and sizes.

    Returns:
        A grid with the same shape as the elevation grid. True means a line
        touches that cell.
    """
    values = np.zeros(grid.elevation.shape, dtype='uint8')
    destination = wrap_array_as_raster(values, grid)
    source_crs = osr.SpatialReference()
    source_crs.ImportFromEPSG(4326)
    source_crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    geometry = pa.array(to_wkb(list(lines)), type=pa.binary())
    if len(geometry):
        vector, layer = geometry_layer(geometry, source_crs)
        # A line that clips a cell's corner still touches that cell.
        gdal.RasterizeLayer(
            destination, [1], layer, burn_values=[1], options=['ALL_TOUCHED=TRUE']
        )
    return values.astype(bool)


def rasterize_waterway_destinations(
    network: Waterways,
    assigned: Mapping[tuple[str, str], tuple[int, ...]],
    grid: TerrainGrid,
) -> tuple[dict[int, np.ndarray], dict[str, Any], list[str]]:
    """Mark terrain cells touched by mapped rivers with known destinations.

    Args:
        network: Mapped stream network containing the original way coordinates.
        assigned: Known destination groups for each ``(upstream node, downstream node)`` pair.
        grid: Elevation grid on which to mark those stretches.

    Returns:
        Group masks, the cell-count report and the source way IDs in this crop.
        If a stream reaches groups 3 and 7, each cell it touches is True in
        both masks.
    """
    groups = sorted({group for possible in assigned.values() for group in possible})
    way_ids = network.way_ids_intersecting_grid_bounds(grid)
    seeds = {}
    # Draw a separate grid for each group so one cell can belong to both.
    for group in groups:
        lines = [
            network.way_line(ident, start, end)
            for ident in way_ids
            for (start, first), (end, last) in network.iter_way_connection_pairs(ident)
            if group in assigned.get((first, last), ())
        ]
        seeds[group] = rasterize_waterway_lines(lines, grid)
    # A cell marked for groups 3 and 7 adds one to each group's total
    # and counts once as a shared cell.
    count = np.zeros(grid.elevation.shape, dtype='int64')
    for cells in seeds.values():
        count += cells
    report = {
        'shared_seed_cells': int((count > 1).sum()),
        'seed_cells': {str(group): int(cells.sum()) for group, cells in seeds.items()},
        'nearby_ways': len(way_ids),
    }
    return seeds, report, way_ids
