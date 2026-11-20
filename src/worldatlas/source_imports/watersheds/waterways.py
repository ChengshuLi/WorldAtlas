"""Read OSM extracts and trace where rivers and streams drain."""
from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise
import math
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import zipfile

import numpy as np
import osmium
from osgeo import gdal, osr
import pyarrow as pa
from pyproj import Transformer
from shapely import line_merge, to_wkb
from shapely.geometry import LineString, MultiLineString, Point, box
from shapely.strtree import STRtree

from worldatlas.geodesy.ogr import geometry_layer
from worldatlas.source_imports.shared.sources import archive_member
from worldatlas.source_imports.watersheds.terrain import wrap_array_as_raster


def _stage_osm_files(paths, directory):
    """Stage archived extracts for Pyosmium's streaming reader."""
    for index, selection in enumerate(paths):
        path, name = selection if isinstance(selection, tuple) else (selection, None)
        path = Path(path)
        if name is None and not zipfile.is_zipfile(path):
            # A standalone input can be opened in place.
            yield osmium.io.File(str(path), 'pbf' if path.suffix.lower() == '.pbf' else 'osm')
            continue
        with zipfile.ZipFile(path) as archive:
            # An explicit member picks one file. Otherwise read every XML response in the archive.
            members = ([archive_member(archive, name)] if name is not None else
                       [item for item in archive.infolist() if item.filename.endswith(('.osm', '.xml'))])
            if not members:
                raise ValueError('OSM archive has no XML responses')
            for member_index, member in enumerate(members):
                kind = 'pbf' if member.filename.lower().endswith('.pbf') else 'osm'
                # Give Pyosmium a temporary file it can open on each pass.
                unpacked = directory / f'{index}-{member_index}.{kind}'
                with archive.open(member) as source, unpacked.open('wb') as output:
                    shutil.copyfileobj(source, output)
                yield osmium.io.File(str(unpacked), kind)


def _intersection_parts(hit):
    """Yield the individual points and lines where two lines meet."""
    if hit.is_empty:
        return
    if hit.geom_type in ('Point', 'LineString'):
        yield hit
    else:
        for part in hit.geoms:
            yield from _intersection_parts(part)


def _shared_segment_ends(start, end, shared_line):
    """Yield the shared stretches of one source segment in flow direction."""
    if start == end:
        return
    parts = _intersection_parts(LineString([start, end]).intersection(shared_line))
    stretches = MultiLineString([part for part in parts if part.geom_type == 'LineString'])
    for stretch in _intersection_parts(line_merge(stretches)):
        first, last = stretch.coords[0], stretch.coords[-1]
        if math.dist(start, first) > math.dist(start, last):
            first, last = last, first
        yield first, last


def _rectangles_from_wgs84_bounds(bounds):
    """Build one rectangle, or split it at 180° longitude if it wraps."""
    west, south, east, north = bounds
    if west <= east:
        return (box(west, south, east, north),)
    # A single Shapely box would cover the long way around through 0° longitude.
    return (box(west, south, 180, north), box(-180, south, east, north))


def _vertices_around_point(line, coordinates, point):
    """Find the vertices immediately before and after an interior line point."""
    matches = np.flatnonzero(np.all(coordinates[1:-1] == point, axis=1))
    if matches.size:
        index = matches[0]
        return coordinates[index], coordinates[index + 2]
    steps = np.diff(coordinates, axis=0)
    # A crossing can lie inside a segment, with no vertex recorded at its position.
    station = line.project(Point(point))
    index = np.searchsorted(np.cumsum(np.hypot(steps[:, 0], steps[:, 1])), station)
    index = min(index, len(coordinates) - 2)
    return coordinates[index], coordinates[index + 1]


def _boundary_side(point, before, after, neighbor):
    """Return which of the boundary's two local sectors contains a river arm."""
    def angle(vertex):
        return math.atan2(vertex[1] - point[1], vertex[0] - point[0])

    start = angle(before)
    # At a boundary corner, the two rays divide the area into unequal sectors.
    end = (angle(after) - start) % math.tau
    arm = (angle(neighbor) - start) % math.tau
    if arm == 0 or arm == end:
        return 0
    return 1 if arm < end else -1


@dataclass
class Way:
    """Keep the values needed after Pyosmium advances beyond a way.

    Args:
        nodes: Ordered OSM node IDs, normally from upstream to downstream.
        tags: Provider attributes, including the waterway classification.
        version: OSM object version in the archive.
    """

    nodes: tuple
    tags: dict
    version: int

    @property
    def is_river_or_stream(self):
        """Check how OSM classifies this way for drainage tracing.

        Returns:
            Whether the ``waterway`` tag is ``river`` or ``stream``.
        """
        return self.tags.get('waterway') in ('river', 'stream')


class Waterways:
    """Index OSM waterways by shared nodes for drainage and crossing checks."""

    def __init__(self, paths, *, rivers_and_streams_only=False, reverse=()):
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
        with TemporaryDirectory(prefix='watershed-osm-') as directory:
            files = list(_stage_osm_files(paths, Path(directory)))
            # Drainage reads ways first. A general source read takes all OSM object types.
            entities = osmium.osm.WAY if rivers_and_streams_only else osmium.osm.OBJECT
            for file in files:
                self._merge_osm_objects(osmium.FileProcessor(file, entities))
            if rivers_and_streams_only:
                # Merge all way versions before deciding which nodes to read.
                # A selected way can reference nodes in a different extract.
                wanted = {int(node) for way in self.ways.values() for node in way.nodes}
                if wanted:
                    node_filter = osmium.filter.IdFilter(wanted)
                    for file in files:
                        reader = osmium.FileProcessor(file, osmium.osm.NODE).with_filter(node_filter)
                        self._merge_osm_objects(reader)
        # The version lookups have finished merging the extracts. Later code reads the kept objects.
        del self._node_versions, self._way_versions
        # Apply reviewed direction corrections after merging source versions so
        # the corrections apply to the selected version of each way.
        for ident in sorted(set(map(str, reverse))):
            if ident not in self.ways or not self.ways[ident].is_river_or_stream:
                raise ValueError(f'river or stream {ident} is missing from the ways available to reverse')
            way = self.ways[ident]
            # Reversing the node order changes the flow direction while preserving the line's shape.
            self.ways[ident] = Way(tuple(reversed(way.nodes)), way.tags, way.version)
        self.river_and_stream_ids = {
            ident for ident, way in self.ways.items()
            if way.is_river_or_stream
        }
        # Flag an incomplete way if a known point lies in the analysis area
        # or it shares a node with a river or stream that intersects the area.
        self.incomplete = {ident for ident in self.river_and_stream_ids
                           if len(self.ways[ident].nodes) < 2 or
                           any(n not in self.nodes for n in self.ways[ident].nodes)}
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
        # The finished set holds the points we use to trace flow.
        # 1. Keep the first and last point of every complete river or stream way.
        # 2. Keep any point ID used more than once in complete ways.
        # 3. Keep points shared by a complete and an incomplete way so we can
        #    flag the branch with missing data later.
        self.topology_nodes = connection_point_ids
        for ident in complete_way_ids:
            for (start, first), (end, second) in self.iter_way_connection_pairs(ident):
                self.upstream[second].add(first)  # At second, water arrives from first.
                self.downstream[first].add(second)  # At first, water flows next to second.
                # Keep the original way and point positions to recover the full stream shape.
                self.edge_sources[first, second].append((ident, start, end))
        self._lines, self._waterway_index = {}, None

    def _merge_node(self, ident, version, point):
        if not all(map(math.isfinite, point)) or not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
            raise ValueError('invalid OSM node coordinates')
        previous_version = self._node_versions.get(ident)
        if previous_version is not None and version <= previous_version:
            if version == previous_version and self.nodes[ident] != point:
                raise ValueError('conflicting same-version OSM node')
            return
        # Callers that draw a way can read the coordinate pair directly.
        self.nodes[ident], self._node_versions[ident] = point, version

    def _merge_way(self, ident, way):
        is_river_or_stream = way.is_river_or_stream
        previous_version, previous_is_river_or_stream = self._way_versions.get(ident, (None, None))
        if previous_version is not None and way.version <= previous_version:
            if way.version == previous_version and (
                previous_is_river_or_stream != is_river_or_stream
                or (ident in self.ways and self.ways[ident] != way)
            ):
                raise ValueError('conflicting same-version OSM way')
            return
        # Even an excluded way's version prevents older copies from returning.
        self._way_versions[ident] = (way.version, is_river_or_stream)
        if self.rivers_and_streams_only and not is_river_or_stream:
            self.ways.pop(ident, None)
        else:
            self.ways[ident] = way

    def _merge_relation(self, ident, version, members):
        # Relations have no per-record filter, so the kept entry can carry its version.
        previous_version, previous_members = self.relations.get(ident, (None, None))
        if previous_version is not None and version <= previous_version:
            if version == previous_version and previous_members != members:
                raise ValueError('conflicting same-version OSM relation')
            return
        self.relations[ident] = (version, members)

    def _merge_osm_objects(self, objects):
        """Copy the object values needed after Pyosmium advances the reader."""
        member_types = {'n': 'node', 'w': 'way', 'r': 'relation'}
        for obj in objects:
            # Pyosmium's object is valid only until the reader advances.
            ident = str(obj.id)
            if obj.is_node():
                self._merge_node(ident, obj.version, (obj.lon, obj.lat))
            elif obj.is_way():
                self._merge_way(ident, Way(tuple(str(node.ref) for node in obj.nodes),
                                     dict(obj.tags), obj.version))
            else:
                members = tuple((member_types[m.type], str(m.ref), m.role) for m in obj.members)
                self._merge_relation(ident, obj.version, members)

    def iter_way_connection_pairs(self, way_id):
        """Find the consecutive network junctions along an ordered way.

        Args:
            way_id: OSM way ID.

        Returns:
            An iterator of pairs of consecutive connection points in the way.
            For example, ``((0, "10"), (2, "12"))`` spans positions 0 through 2
            of the original way, from OSM node 10 to OSM node 12.
        """
        anchors = [(i, node) for i, node in enumerate(self.ways[str(way_id)].nodes)
                   if node in self.topology_nodes]
        return pairwise(anchors)

    def way_line(self, way_id, start=0, end=None):
        """Read a way or its selected section in original vertex order.

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
        self._lines[key] = LineString([self.nodes[n] for n in way.nodes[start:end + 1]])
        return self._lines[key]

    def way_ids_intersecting_grid_bounds(self, grid):
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
            x, y + height * e, x + width * a, y, densify_pts=21, errcheck=True)
        return self.way_ids_intersecting_bounds(bounds)

    def way_ids_intersecting_bounds(self, bounds):
        """Find complete rivers and streams that intersect a WGS84 rectangle.

        Args:
            bounds: West, south, east, and north limits. If the west limit
                exceeds the east limit, the rectangle crosses the antimeridian.

        Returns:
            Sorted IDs of complete mapped rivers and streams intersecting the rectangle.
        """
        return self._way_ids_intersecting_shapes(_rectangles_from_wgs84_bounds(bounds))

    def _way_ids_intersecting_shapes(self, shapes):
        """Use one index for both rectangle searches and line searches."""
        if self._waterway_index is None:
            self._indexed_way_ids = sorted(self.river_and_stream_ids - self.incomplete)
            self._waterway_index = STRtree([self.way_line(way_id) for way_id in self._indexed_way_ids])
        indices = {
            int(index)
            for shape in shapes
            for index in self._waterway_index.query(shape, predicate='intersects')
        }
        return [self._indexed_way_ids[index] for index in sorted(indices)]

    def require_known_drainage_in_bounds(self, bounds, report):
        """Check that relevant rivers and streams have known downstream routes.

        Args:
            bounds: WGS84 rectangles covered by the terrain calculation.
            report: Downstream tracing report with unresolved sections.

        Raises:
            ValueError: A relevant way has missing geometry or an unresolved route.
        """
        areas = [area for rectangle in bounds for area in _rectangles_from_wgs84_bounds(rectangle)]
        relevant = set(self._way_ids_intersecting_shapes(areas))
        relevant_nodes = {node for ident in relevant for node in self.ways[ident].nodes}
        # An incomplete way can still affect the crop if a known point lies
        # inside it or the way shares a node with a river that touches it.
        for ident in sorted(self.incomplete):
            nodes = self.ways[ident].nodes
            if (relevant_nodes.intersection(nodes) or
                    any(node in self.nodes and any(area.covers(Point(self.nodes[node])) for area in areas)
                        for node in nodes)):
                raise ValueError(f'river or stream {ident} has missing source coordinates; repair the source')
        # A known outlet on one branch does not resolve another branch.
        # Stop only if the uncertainty affects a way that touches a crop.
        for section in report['unresolved_sections']:
            affected = [way for way, _, _ in section['source_segments'] if way in relevant]
            if affected:
                raise ValueError(
                    f'river or stream {affected[0]} has an unresolved downstream route '
                    f'from node {section["nodes"][1]}; known groups={section["groups"]}; '
                    f'first unresolved node={section["unresolved_node"]}; repair the source')

    def fork_outlet_groups(self, node, assigned):
        """Get the known drainage group of each immediate downstream arm.

        Args:
            node: OSM node ID of the selected fork.
            assigned: Known destinations keyed by directed network edge.

        Returns:
            Downstream neighbor IDs and their groups, or an empty mapping if
            any arm lacks one unambiguous group.
        """
        destinations = {}
        for downstream in self.downstream.get(node, ()):
            edge = node, downstream
            groups = assigned.get(edge, ())
            # To allow this boundary contact, we need one known destination
            # for every outgoing branch.
            if len(groups) != 1:
                return {}
            group, = groups
            for way, start, _ in self.edge_sources[edge]:
                # The next network junction may be far away. The crossing
                # check uses the first OSM node after the fork to find which
                # side of the boundary the branch leaves on.
                neighbor = self.ways[way].nodes[start + 1]
                # If two routes share that first node, their groups must agree.
                if destinations.setdefault(neighbor, group) != group:
                    return {}
        return destinations

    def check_boundary_crossings(self, geometry, *, shared_forks=None, followed_source_line=None):
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
        endpoints = {tuple(coordinates[0]), tuple(coordinates[-1])}
        ways = self._way_ids_intersecting_shapes((geometry,))
        # A river can cross at one point or follow the boundary for a while
        # before leaving on the other side. Keep both kinds of intersection.
        hits = defaultdict(set)
        overlaps = defaultdict(list)
        for ident in ways:
            for part in _intersection_parts(geometry.intersection(self.way_line(ident))):
                if part.geom_type == 'LineString':
                    overlaps[ident].append(part)
                else:
                    point = tuple(part.coords[0])
                    if point not in endpoints:
                        hits[point].add(ident)

        crossings, along_boundary_arms = self._crossings_along_boundary(
            geometry, ways, overlaps, followed_source_line)

        # If water flows through nodes 1, 2, and 3 in that order and node 2
        # is on the boundary, record node 1 as incoming and node 3 as outgoing.
        # Group branches from different ways when they share the same OSM node.
        arms = defaultdict(lambda: defaultdict(set))
        vertex_hits = defaultdict(set)
        for ident in ways:
            nodes = self.ways[ident].nodes
            for index, node in enumerate(nodes):
                point = self.nodes[node]
                if point not in hits:
                    continue
                vertex_hits[point].add(ident)
                if index:
                    arms[point][node].add((ident, nodes[index - 1], False))
                if index + 1 < len(nodes):
                    arms[point][node].add((ident, nodes[index + 1], True))

        junctions, river_ends, shared = set(), set(), {}
        for point, hit_ways in sorted(hits.items()):
            # Use the boundary just before and after this point to tell
            # which side each branch is on, even where the boundary bends.
            before, after = _vertices_around_point(geometry, coordinates, point)

            def side(neighbor):
                return _boundary_side(point, before, after, neighbor)

            # The river can also meet the boundary between two saved OSM
            # points. Check the sides of the two points it runs between.
            for ident in hit_ways - vertex_hits[point]:
                river = self.way_line(ident)
                entry, exit = _vertices_around_point(river, np.asarray(river.coords), point)
                if side(entry) * side(exit) == -1:
                    crossings[point].add(ident)

            for node, branches in arms[point].items():
                incoming, outgoing = set(), {}
                neighbors = {neighbor for _, neighbor, _ in branches}
                for ident, neighbor, leaves in branches:
                    arm = ident, node, neighbor, leaves
                    sector = 0 if arm in along_boundary_arms else side(self.nodes[neighbor])
                    if leaves:
                        outgoing[neighbor] = sector
                    else:
                        incoming.add(sector)
                # A crossing needs water arriving from one side and leaving
                # on the other. Side 0 means the branch points along the boundary.
                crosses = any(-sector in incoming for sector in outgoing.values() if sector)
                if crosses:
                    # Allow a selected fork when water arrives from one side
                    # and leaves on both. All branches leaving on a given
                    # side must lead to the same known group, and the two
                    # sides must lead to different groups.
                    groups = shared_forks.get(node, {})
                    if len(incoming) == 1 and set(outgoing.values()) == {-1, 1} and groups.keys() == outgoing.keys():
                        by_side = {sector: {groups[n] for n in outgoing if outgoing[n] == sector}
                                   for sector in (-1, 1)}
                        if all(len(values) == 1 for values in by_side.values()) and by_side[-1] != by_side[1]:
                            shared[node] = sorted(set(groups.values()))
                            junctions.add(node)
                            continue
                    crossings[point].update(ident for ident, _, _ in branches)
                # For contacts without a crossing, report junctions and stream
                # ends. A stream that touches and turns back needs no entry.
                elif len(neighbors) > 2:
                    junctions.add(node)
                elif len(neighbors) == 1:
                    river_ends.add(node)
        result = {'indexed_river_and_stream_ways': len(self._indexed_way_ids),
                  'junction_contacts': sorted(junctions), 'river_endpoint_contacts': sorted(river_ends),
                  'shared_drainage_contacts': [
                      {'node': node, 'groups': shared[node]} for node in sorted(shared)],
                  'crossings': [{'point': list(point), 'ways': sorted(ways)}
                                for point, ways in sorted(crossings.items())]}
        if crossings:
            first = result['crossings'][0]
            raise ValueError(f'boundary crosses a river or stream {first["ways"]} at {first["point"]}')
        return result

    def _crossings_along_boundary(self, boundary, ways, overlaps, followed_source_line):
        """Find routes that enter a shared stretch and leave on the other side."""
        crossings, shared_arms = defaultdict(set), set()
        if not overlaps:
            return crossings, shared_arms

        downstream = defaultdict(set)
        points = {}
        arrivals, departures = defaultdict(set), defaultdict(set)
        coordinates = np.asarray(boundary.coords)
        endpoints = {tuple(coordinates[0]), tuple(coordinates[-1])}
        boundary_neighbors = {}

        def record_branch(branches, contact, neighbor, way):
            point = points[contact]
            # Water can go around the end of the boundary.
            if point in endpoints:
                return
            if point not in boundary_neighbors:
                boundary_neighbors[point] = _vertices_around_point(boundary, coordinates, point)
            side = _boundary_side(point, *boundary_neighbors[point], neighbor)
            if side:
                branches[contact].add((side, way))

        # Keep the direction of each shared stretch. Use OSM node IDs to
        # connect ways. A cut in the middle of a segment belongs to that
        # segment alone, even if another stream passes through the same spot.
        for way, lines in overlaps.items():
            shared_line = MultiLineString(lines)
            # A recipe can explicitly place the border along a river. That
            # reach is a boundary in its own right, even if it has side channels.
            if followed_source_line is not None:
                shared_line = shared_line.difference(followed_source_line)
                if shared_line.is_empty:
                    continue
            for index, (upstream, downstream_node) in enumerate(pairwise(self.ways[way].nodes)):
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

        # At shared OSM nodes, other stream segments can bring water onto the
        # boundary or carry it away. Count only the branches off the boundary.
        for way in ways:
            for upstream, downstream_node in pairwise(self.ways[way].nodes):
                start, end = self.nodes[upstream], self.nodes[downstream_node]
                if start == end:
                    continue
                if upstream in points and (way, upstream, downstream_node, True) not in shared_arms:
                    record_branch(departures, upstream, end, way)
                if downstream_node in points and (way, downstream_node, upstream, False) not in shared_arms:
                    record_branch(arrivals, downstream_node, start, way)

        # Follow water arriving from each side. Report where it leaves on
        # the opposite side, even if it passed through several OSM ways.
        for entry_side in (-1, 1):
            # Take at least one shared stretch. Crossings that occur at a
            # single point are handled by the normal junction check.
            reached = {neighbor for node, branches in arrivals.items()
                       if any(side == entry_side for side, _ in branches)
                       for neighbor in downstream[node]}
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
        return crossings, shared_arms

    def trace_destinations_from_ways(self, groups):
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
                raise ValueError('nonnegative group IDs and downstream ways are required')
            seen = set()
            for ident in map(str, ways):
                if ident not in self.river_and_stream_ids or ident in self.incomplete:
                    raise ValueError(f'selected river or stream {ident} is missing or incomplete')
                # The selected downstream endpoint is the reference. Walking
                # upstream already reaches every earlier node of this way.
                seen.add(self.ways[ident].nodes[-1])
            roots[int(group)] = seen
        return self._trace_upstream_destinations(roots)

    def trace_destinations_from_basins(self, basins):
        """Trace rivers and streams to destinations identified by basin polygons.

        Args:
            basins: Source basin index with the recipe's group mapping.

        Returns:
            Possible group IDs on each directed edge and a report of the traced routes.
        """
        roots = defaultdict(set)
        coastal, seen = [], set()
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
            # Several complete ways can continue through estuary water beyond
            # the basin polygons. Walk upstream only through that uncovered
            # geometry, stopping at the first source-backed basin on each path.
            for parent in sorted(self.upstream[node]):
                for ident, start, end in self.edge_sources[parent, node]:
                    way = self.ways[ident]
                    line = LineString([self.nodes[n] for n in way.nodes[start:end + 1]])
                    group, point = basins.group_at_river_exit(line)
                    if group >= 0:
                        roots[group].add(node)
                        coastal.append({'way': ident, 'group': group, 'point': list(point)})
                    elif point is None:
                        todo.append(parent)
        assigned, report = self._trace_upstream_destinations(roots)
        report['basin_exit_before_way_endpoint'] = coastal
        return assigned, report

    def _trace_upstream_destinations(self, roots):
        """Trace known destinations and unresolved branches upstream separately."""
        reaches = {}
        for group, initial in roots.items():
            seen = set(initial)
            todo = list(sorted(seen))
            while todo:
                for node in sorted(self.upstream[todo.pop()]):
                    if node not in seen:
                        seen.add(node)
                        todo.append(node)
            reaches[int(group)] = seen
        known = set().union(*reaches.values()) if reaches else set()
        supported = set().union(*roots.values()) if roots else set()
        unresolved = {node: node for node in self.topology_nodes - known}
        for ident in self.incomplete:
            unresolved.update((node, node) for node in self.ways[ident].nodes
                              if node in self.topology_nodes)
        todo = list(sorted(unresolved))
        while todo:
            node = todo.pop()
            for parent in sorted(self.upstream[node]):
                # Do not look beyond an established destination reference.
                # Uncovered estuary geometry downstream does not invalidate
                # the basin identity already established by the source.
                if parent in supported:
                    continue
                if parent not in unresolved:
                    unresolved[parent] = unresolved[node]
                    todo.append(parent)
        assigned, ambiguous, unassigned, shared, missing = {}, set(), set(), [], []
        for edge, references in sorted(self.edge_sources.items()):
            matches = tuple(sorted(group for group, nodes in reaches.items() if edge[1] in nodes))
            if matches:
                assigned[edge] = matches
            if edge[1] in unresolved:
                missing.append({'nodes': list(edge), 'groups': list(matches),
                                'source_segments': [list(reference) for reference in references],
                                'unresolved_node': unresolved[edge[1]]})
            if len(matches) > 1:
                ambiguous.update(ident for ident, _, _ in references)
                shared.append({'nodes': list(edge), 'groups': list(matches),
                               'source_segments': [list(reference) for reference in references]})
            elif not matches:
                unassigned.update(ident for ident, _, _ in references)
        return assigned, {'ambiguous': sorted(ambiguous), 'unassigned': sorted(unassigned),
                          'incomplete': sorted(self.incomplete), 'shared_sections': shared,
                          'unresolved_sections': missing}



def rasterize_waterway_lines(lines, grid):
    """Burn WGS84 lines onto a native geographic or projected grid.

    Args:
        lines: Iterable of Shapely lines in longitude and latitude.
        grid: Native terrain grid to receive the river mask.

    Returns:
        A Boolean array marking every cell touched by a line.
    """
    values = np.zeros(grid.elevation.shape, dtype='uint8')
    destination = wrap_array_as_raster(values, grid)
    source_crs = osr.SpatialReference()
    source_crs.ImportFromEPSG(4326)
    source_crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    geometry = pa.array(to_wkb(list(lines)), type=pa.binary())
    if len(geometry):
        vector, layer = geometry_layer(geometry, source_crs)
        gdal.RasterizeLayer(destination, [1], layer, burn_values=[1], options=['ALL_TOUCHED=TRUE'])
    return values.astype(bool)


def rasterize_waterway_destinations(network, assigned, grid):
    """Mark terrain cells touched by mapped rivers with known destinations.

    Args:
        network: Mapped stream network containing the original way coordinates.
        assigned: Known destination group IDs keyed by directed network edge.
        grid: Native terrain to receive the masks.

    Returns:
        A Boolean mask for each destination group and a report of seeded cells.
        A cell may appear in several masks when its mapped river drains to several groups.
    """
    groups = sorted({group for possible in assigned.values() for group in possible})
    way_ids = network.way_ids_intersecting_grid_bounds(grid)
    seeds = {}
    for group in groups:
        lines = [network.way_line(ident, start, end) for ident in way_ids
                 for (start, first), (end, last) in network.iter_way_connection_pairs(ident)
                 if group in assigned.get((first, last), ())]
        seeds[group] = rasterize_waterway_lines(lines, grid)
    count = np.zeros(grid.elevation.shape, dtype='int64')
    for cells in seeds.values():
        count += cells
    return seeds, {'shared_seed_cells': int((count > 1).sum()),
                   'seed_cells': {str(group): int(cells.sum()) for group, cells in seeds.items()},
                   'nearby_ways': len(way_ids)}
