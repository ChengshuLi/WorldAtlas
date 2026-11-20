"""Read pinned OSM objects and assign natural waterways by downstream topology."""
from collections import defaultdict
from dataclasses import dataclass
import math
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import zipfile

import numpy as np
import osmium
from osgeo import gdal, osr
import pyarrow as pa
from pyproj import CRS
from pyproj import Transformer
from shapely import to_wkb
from shapely.geometry import LineString, Point, box
from shapely.strtree import STRtree

from worldatlas.geodesy.ogr import geometry_layer
from worldatlas.source_imports.shared.sources import archive_member


def _osm_files(paths, directory):
    """Stage archived extracts for Pyosmium's streaming reader."""
    for index, selection in enumerate(paths):
        path, name = selection if isinstance(selection, tuple) else (selection, None)
        path = Path(path)
        if name is None and not zipfile.is_zipfile(path):
            yield osmium.io.File(str(path), 'pbf' if path.suffix.lower() == '.pbf' else 'osm')
            continue
        with zipfile.ZipFile(path) as archive:
            members = ([archive_member(archive, name)] if name is not None else
                       [item for item in archive.infolist() if item.filename.endswith(('.osm', '.xml'))])
            if not members:
                raise ValueError('OSM archive has no XML responses')
            for member_index, member in enumerate(members):
                kind = 'pbf' if member.filename.lower().endswith('.pbf') else 'osm'
                unpacked = directory / f'{index}-{member_index}.{kind}'
                with archive.open(member) as source, unpacked.open('wb') as output:
                    shutil.copyfileobj(source, output)
                yield osmium.io.File(str(unpacked), kind)


@dataclass
class Way:
    nodes: tuple
    tags: dict
    version: int


class Waterways:
    """Index OSM waterways by shared nodes for drainage and crossing checks."""

    def __init__(self, paths, *, natural_only=False, reverse=()):
        """Read OSM extracts and connect rivers and streams downstream.

        Args:
            paths: Local OSM XML, XML archives, PBF files, or ``(archive, member)`` selections.
            natural_only: Whether to retain only rivers and streams and their nodes.
            reverse: IDs of natural waterways with reviewed direction corrections.
        """
        self.nodes, self.ways, self.relations = {}, {}, {}
        self.natural_only = natural_only
        self._node_versions, self._way_versions = {}, {}
        with TemporaryDirectory(prefix='watershed-osm-') as directory:
            files = list(_osm_files(paths, Path(directory)))
            entities = osmium.osm.WAY if natural_only else osmium.osm.OBJECT
            for file in files:
                self._read_objects(osmium.FileProcessor(file, entities))
            if natural_only:
                # Merge all way versions before deciding which nodes to read.
                # A selected way can reference nodes in a different extract.
                wanted = {int(node) for way in self.ways.values() for node in way.nodes}
                if wanted:
                    node_filter = osmium.filter.IdFilter(wanted)
                    for file in files:
                        reader = osmium.FileProcessor(file, osmium.osm.NODE).with_filter(node_filter)
                        self._read_objects(reader)
        del self._node_versions, self._way_versions
        # Apply reviewed direction corrections after merging source versions so
        # the corrections apply to the selected version of each way.
        for ident in sorted(set(map(str, reverse))):
            if ident not in self.ways or self.ways[ident].tags.get('waterway') not in ('river', 'stream'):
                raise ValueError(f'reversed natural waterway {ident} is missing')
            way = self.ways[ident]
            self.ways[ident] = Way(tuple(reversed(way.nodes)), way.tags, way.version)
        self.natural = {ident for ident, way in self.ways.items()
                        if way.tags.get('waterway') in ('river', 'stream')}
        self.incomplete = {ident for ident in self.natural
                           if len(self.ways[ident].nodes) < 2 or
                           any(n not in self.nodes for n in self.ways[ident].nodes)}
        self.upstream, self.downstream = defaultdict(set), defaultdict(set)
        self.edge_sources = defaultdict(list)
        seen, junctions = set(), set()
        for ident in sorted(self.natural - self.incomplete):
            nodes = self.ways[ident].nodes
            junctions.update((nodes[0], nodes[-1]))
            for node in nodes:
                if node in seen:
                    junctions.add(node)
                seen.add(node)
        for ident in self.incomplete:
            junctions.update(node for node in self.ways[ident].nodes if node in seen)
        self.topology_nodes = junctions
        for ident in sorted(self.natural - self.incomplete):
            for (start, first), (end, second) in self.segments(ident):
                self.upstream[second].add(first)
                self.downstream[first].add(second)
                self.edge_sources[first, second].append((ident, start, end))
        self._lines, self._spatial = {}, None

    def _node(self, ident, version, point):
        if not all(map(math.isfinite, point)) or not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
            raise ValueError('invalid OSM node coordinates')
        old = self._node_versions.get(ident, -1)
        if version == old and self.nodes[ident] != point:
            raise ValueError('conflicting same-version OSM node')
        if version >= old:
            self.nodes[ident], self._node_versions[ident] = point, version

    def _way(self, ident, way):
        natural = way.tags.get('waterway') in ('river', 'stream')
        old = self._way_versions.get(ident)
        if old and old[0] == way.version:
            if old[1] != natural or (ident in self.ways and self.ways[ident] != way):
                raise ValueError('conflicting same-version OSM way')
        if old is None or way.version >= old[0]:
            self._way_versions[ident] = (way.version, natural)
            if not self.natural_only or natural:
                self.ways[ident] = way
            else:
                self.ways.pop(ident, None)

    def _relation(self, ident, relation):
        if self.natural_only:
            return
        old = self.relations.get(ident)
        if old and old[0] == relation[0] and old != relation:
            raise ValueError('conflicting same-version OSM relation')
        if old is None or relation[0] >= old[0]:
            self.relations[ident] = relation

    def _read_objects(self, objects):
        """Copy the object values needed after Pyosmium advances the reader."""
        member_types = {'n': 'node', 'w': 'way', 'r': 'relation'}
        for obj in objects:
            ident = str(obj.id)
            if obj.is_node():
                self._node(ident, obj.version, (obj.lon, obj.lat))
            elif obj.is_way():
                self._way(ident, Way(tuple(str(node.ref) for node in obj.nodes),
                                     dict(obj.tags), obj.version))
            else:
                members = tuple((member_types[m.type], str(m.ref), m.role) for m in obj.members)
                self._relation(ident, (obj.version, members))

    def segments(self, way_id):
        """Source index/node pairs delimiting each directed topology segment."""
        anchors = [(i, node) for i, node in enumerate(self.ways[str(way_id)].nodes)
                   if node in self.topology_nodes]
        return zip(anchors, anchors[1:])

    def line(self, way_id, start=0, end=None):
        """Keep original coordinates from start through end, including both indices."""
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

    def nearby(self, grid):
        """Select ways intersecting the grid, preserving each complete geometry."""
        x, a, _, y, _, e = grid.transform
        height, width = grid.elevation.shape
        bounds = Transformer.from_crs(grid.crs, 4326, always_xy=True).transform_bounds(
            x, y + height * e, x + width * a, y, densify_pts=21, errcheck=True)
        return self.in_bounds(bounds)

    def in_bounds(self, bounds):
        """Find complete natural ways in a WGS84 rectangle, including wrapping."""
        if self._spatial is None:
            self._spatial_ids = sorted(self.natural - self.incomplete)
            self._spatial = STRtree([self.line(ident) for ident in self._spatial_ids])
        west, south, east, north = bounds
        areas = [box(west, south, east, north)] if west <= east else [
            box(west, south, 180, north), box(-180, south, east, north)]
        indices = {int(index) for area in areas for index in self._spatial.query(area, predicate='intersects')}
        return [self._spatial_ids[index] for index in sorted(indices)]

    def require_destinations(self, bounds, report):
        """Reject unresolved relevant rivers before calculating terrain drainage."""
        relevant = set().union(*(self.in_bounds(rectangle) for rectangle in bounds))
        relevant_nodes = {node for ident in relevant for node in self.ways[ident].nodes}
        areas = [area for w, s, e, n in bounds
                 for area in ([box(w, s, e, n)] if w <= e else
                              [box(w, s, 180, n), box(-180, s, e, n)])]
        for ident in sorted(self.incomplete):
            nodes = self.ways[ident].nodes
            if (relevant_nodes.intersection(nodes) or
                    any(node in self.nodes and any(area.covers(Point(self.nodes[node])) for area in areas)
                        for node in nodes)):
                raise ValueError(f'natural waterway {ident} has missing source coordinates; repair the source')
        for section in report['unresolved_sections']:
            affected = [way for way, _, _ in section['source_segments'] if way in relevant]
            if affected:
                raise ValueError(
                    f'natural waterway {affected[0]} has an unresolved downstream route '
                    f'from node {section["nodes"][1]}; known groups={section["groups"]}; '
                    f'first unresolved node={section["unresolved_node"]}; repair the source')

    def check_crossings(self, geometry):
        """Check the final line against river interiors, allowing real endpoints.

        A natural fork or confluence ends a river section. An arbitrary OSM way
        split with two incident neighbours does not. No locations are exempted.
        """
        ports = defaultdict(set)
        for references in self.edge_sources.values():
            for ident, first, last in references:
                nodes = self.ways[ident].nodes
                ports[nodes[first]].add(nodes[first + 1])
                ports[nodes[last]].add(nodes[last - 1])
        contacts = defaultdict(list)
        for node, neighbors in ports.items():
            if len(neighbors) != 2:
                contacts[self.nodes[node]].append((node, len(neighbors)))
        endpoints = {tuple(geometry.coords[0]), tuple(geometry.coords[-1])}
        self.in_bounds(geometry.bounds)
        crossings, junctions, river_ends = {}, set(), set()

        def intersection_points(hit):
            if hit.geom_type == 'Point':
                yield tuple(hit.coords[0])
            elif hit.geom_type in ('MultiPoint', 'GeometryCollection'):
                for part in hit.geoms:
                    yield from intersection_points(part)
            # Following a river along a line is not a transverse crossing.

        for index in self._spatial.query(geometry, predicate='intersects'):
            ident = self._spatial_ids[int(index)]
            for point in intersection_points(geometry.intersection(self.line(ident))):
                if point in endpoints:
                    continue
                matching = [(node, degree) for node, degree in contacts.get(point, [])
                            if node in self.ways[ident].nodes]
                if matching:
                    for node, degree in matching:
                        (junctions if degree > 2 else river_ends).add(node)
                else:
                    crossings.setdefault(point, set()).add(ident)
        result = {'checked_natural_ways': len(self._spatial_ids),
                  'junction_contacts': sorted(junctions), 'river_endpoint_contacts': sorted(river_ends),
                  'crossings': [{'point': list(point), 'ways': sorted(ways)}
                                for point, ways in sorted(crossings.items())]}
        if crossings:
            first = result['crossings'][0]
            raise ValueError(f'boundary crosses natural waterway {first["ways"]} at {first["point"]}')
        return result

    def groups(self, groups):
        """Include all mapped natural tributaries reaching the selected ways.

        Keys are actual construction group IDs; values are selected downstream
        way IDs. Ways reaching multiple groups are reported as ambiguous.
        """
        roots = {}
        for group, ways in groups.items():
            if int(group) < 0 or not ways:
                raise ValueError('nonnegative group IDs and downstream ways are required')
            seen = set()
            for ident in map(str, ways):
                if ident not in self.natural or ident in self.incomplete:
                    raise ValueError(f'selected natural waterway {ident} is missing or incomplete')
                # The selected downstream endpoint is the reference. Walking
                # upstream already reaches every earlier node of this way.
                seen.add(self.ways[ident].nodes[-1])
            roots[int(group)] = seen
        return self._assign(roots)

    def basin_groups(self, basins):
        """Trace every mapped natural network to source-backed exit basins."""
        roots = defaultdict(set)
        coastal, seen = [], set()
        todo = sorted(node for node in self.topology_nodes if not self.downstream[node])
        while todo:
            node = todo.pop()
            if node in seen:
                continue
            seen.add(node)
            values = basins.values_at(self.nodes[node])
            if values:
                group = basins.group(values)
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
                    group, point = basins.exit_group(line)
                    if group >= 0:
                        roots[group].add(node)
                        coastal.append({'way': ident, 'group': group, 'point': list(point)})
                    elif point is None:
                        todo.append(parent)
        assigned, report = self._assign(roots)
        report['basin_exit_before_way_endpoint'] = coastal
        return assigned, report

    def _assign(self, roots):
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



def rasterize(lines, grid):
    """Burn WGS84 lines onto a native geographic or projected grid.

    Args:
        lines: Iterable of Shapely lines in longitude and latitude.
        grid: Native terrain grid to receive the river mask.

    Returns:
        A Boolean array marking every cell touched by a line.
    """
    height, width = grid.elevation.shape
    destination = gdal.GetDriverByName('MEM').Create('', width, height, 1, gdal.GDT_Byte)
    destination.SetGeoTransform(grid.transform)
    destination.SetProjection(CRS.from_user_input(grid.crs).to_wkt())
    source_crs = osr.SpatialReference()
    source_crs.ImportFromEPSG(4326)
    source_crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    geometry = pa.array(to_wkb(list(lines)), type=pa.binary())
    if len(geometry):
        vector, layer = geometry_layer(geometry, source_crs)
        gdal.RasterizeLayer(destination, [1], layer, burn_values=[1], options=['ALL_TOUCHED=TRUE'])
    return destination.ReadAsArray().astype(bool)


def seed_grid(network, assigned, grid):
    """Retain every known destination when burning natural river sections."""
    groups = sorted({group for possible in assigned.values() for group in possible})
    nearby = network.nearby(grid)
    seeds = {}
    for group in groups:
        lines = [network.line(ident, start, end) for ident in nearby
                 for (start, first), (end, last) in network.segments(ident)
                 if group in assigned.get((first, last), ())]
        seeds[group] = rasterize(lines, grid)
    count = np.zeros(grid.elevation.shape, dtype='int64')
    for cells in seeds.values():
        count += cells
    return seeds, {'shared_seed_cells': int((count > 1).sum()),
                   'seed_cells': {str(group): int(cells.sum()) for group, cells in seeds.items()},
                   'nearby_ways': len(nearby)}
