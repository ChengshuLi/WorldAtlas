"""Read pinned OSM objects and assign natural waterways by downstream topology."""
from collections import defaultdict
from contextlib import ExitStack
from dataclasses import dataclass
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
from osgeo import gdal, ogr, osr
from pyproj import CRS
from pyproj import Transformer
import shapefile
from shapely import transform as transform_geometry
from shapely.geometry import LineString, Point, shape
from shapely.strtree import STRtree


@dataclass
class Way:
    nodes: tuple
    tags: dict
    version: int


class Waterways:
    def __init__(self, paths):
        self.nodes, self.ways, self.relations = {}, {}, {}
        node_versions = {}
        for path in paths:
            with ExitStack() as stack:
                if zipfile.is_zipfile(path):
                    archive = stack.enter_context(zipfile.ZipFile(path))
                    names = [name for name in archive.namelist() if name.endswith(('.osm', '.xml'))]
                    if not names:
                        raise ValueError('OSM archive has no XML responses')
                    streams = [stack.enter_context(archive.open(name)) for name in names]
                else:
                    streams = [stack.enter_context(open(path, 'rb'))]
                for stream in streams:
                    for _, element in ET.iterparse(stream, events=('end',)):
                        ident = element.get('id')
                        if element.tag == 'node':
                            version = int(element.get('version', '0'))
                            point = (float(element.get('lon')), float(element.get('lat')))
                            if not np.isfinite(point).all() or not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
                                raise ValueError('invalid OSM node coordinates')
                            old = node_versions.get(ident, -1)
                            if version == old and self.nodes[ident] != point:
                                raise ValueError('conflicting same-version OSM node')
                            if version >= old:
                                self.nodes[ident], node_versions[ident] = point, version
                            element.clear()
                        elif element.tag == 'way':
                            way = Way(tuple(n.get('ref') for n in element.findall('nd')),
                                      {tag.get('k'): tag.get('v') for tag in element.findall('tag')},
                                      int(element.get('version', '0')))
                            old = self.ways.get(ident)
                            if old and old.version == way.version and old != way:
                                raise ValueError('conflicting same-version OSM way')
                            if old is None or way.version >= old.version:
                                self.ways[ident] = way
                            element.clear()
                        elif element.tag == 'relation':
                            relation = (int(element.get('version', '0')),
                                        tuple((m.get('type'), m.get('ref'), m.get('role'))
                                              for m in element.findall('member')))
                            old = self.relations.get(ident)
                            if old and old[0] == relation[0] and old != relation:
                                raise ValueError('conflicting same-version OSM relation')
                            if old is None or relation[0] >= old[0]:
                                self.relations[ident] = relation
                            element.clear()
        self.natural = {ident for ident, way in self.ways.items()
                        if way.tags.get('waterway') in ('river', 'stream')}
        self.incomplete = {ident for ident in self.natural
                           if len(self.ways[ident].nodes) < 2 or
                           any(n not in self.nodes for n in self.ways[ident].nodes)}
        self.upstream = defaultdict(set)
        self.downstream = defaultdict(set)
        for ident in sorted(self.natural - self.incomplete):
            nodes = self.ways[ident].nodes
            for first, second in zip(nodes, nodes[1:]):
                self.upstream[second].add(first)
                self.downstream[first].add(second)

    def line(self, way_id):
        way = self.ways[str(way_id)]
        if len(way.nodes) < 2 or any(n not in self.nodes for n in way.nodes):
            raise ValueError('selected OSM way has missing nodes')
        return LineString([self.nodes[n] for n in way.nodes])

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
                seen.update(self.ways[ident].nodes)
            roots[int(group)] = seen
        return self._assign(roots)

    def basin_groups(self, basins):
        """Trace every mapped natural network to source-backed exit basins."""
        roots = defaultdict(set)
        nodes = {node for ident in self.natural - self.incomplete for node in self.ways[ident].nodes}
        for node in sorted(nodes):
            if not self.downstream[node]:
                group = basins.at(self.nodes[node])
                if group >= 0:
                    roots[group].add(node)
        return self._assign(roots)

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
        assigned, ambiguous, unassigned = {}, [], []
        for ident in sorted(self.natural - self.incomplete):
            destination = self.ways[ident].nodes[-1]
            matches = [group for group, nodes in reaches.items() if destination in nodes]
            if len(matches) == 1:
                assigned[ident] = matches[0]
            elif matches:
                ambiguous.append(ident)
            else:
                unassigned.append(ident)
        return assigned, {'ambiguous': ambiguous, 'unassigned': unassigned,
                          'incomplete': sorted(self.incomplete)}


def rasterize(lines, grid):
    """Burn WGS84 line geometries onto a native geographic or projected grid."""
    height, width = grid.elevation.shape
    destination = gdal.GetDriverByName('MEM').Create('', width, height, 1, gdal.GDT_Byte)
    destination.SetGeoTransform(grid.transform)
    destination.SetProjection(CRS.from_user_input(grid.crs).to_wkt())
    vector = ogr.GetDriverByName('Memory').CreateDataSource('')
    source_crs = osr.SpatialReference()
    source_crs.ImportFromEPSG(4326)
    source_crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    layer = vector.CreateLayer('lines', source_crs, ogr.wkbLineString)
    for line in lines:
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetGeometry(ogr.CreateGeometryFromJson(json.dumps(line.__geo_interface__)))
        layer.CreateFeature(feature)
    if layer.GetFeatureCount():
        gdal.RasterizeLayer(destination, [1], layer, burn_values=[1], options=['ALL_TOUCHED=TRUE'])
    return destination.ReadAsArray().astype(bool)


def seed_grid(network, assigned, grid):
    """Rasterize assigned natural ways; conflicting groups remain unassigned."""
    report = {}
    seeds = np.full(grid.elevation.shape, -1, dtype='int64')
    conflicts = np.zeros(seeds.shape, dtype=bool)
    groups = sorted(set(assigned.values()))
    for group in groups:
        lines = [network.line(ident) for ident, value in assigned.items() if value == group]
        cells = rasterize(lines, grid)
        conflicts |= cells & (seeds >= 0) & (seeds != group)
        seeds[cells & ~conflicts] = group
    seeds[conflicts] = -1
    report['conflicting_seed_cells'] = int(conflicts.sum())
    report['seed_cells'] = {str(group): int((seeds == int(group)).sum()) for group in groups}
    return seeds, report


class Basins:
    """Source basin polygons grouped by explicitly selected attribute values."""
    def __init__(self, paths, attribute, groups, bounds):
        self.polygons, self.values = [], []
        self.groups = {int(group): set(values) for group, values in groups.items()}
        if not self.groups or any(group < 0 or not values for group, values in self.groups.items()):
            raise ValueError('known group IDs and source basin values are required')
        if any(a & b for i, a in enumerate(self.groups.values())
               for b in list(self.groups.values())[i + 1:]):
            raise ValueError('a source basin cannot belong to multiple drainage groups')
        for path in paths:
            projection = Path(path).with_suffix('.prj')
            if not projection.exists():
                raise ValueError('basin source requires its coordinate reference file')
            source_crs = CRS.from_wkt(projection.read_text())
            to_geo = Transformer.from_crs(source_crs, 4326, always_xy=True)
            source_bounds = Transformer.from_crs(4326, source_crs, always_xy=True).transform_bounds(
                *bounds, densify_pts=21, errcheck=True)
            with shapefile.Reader(path) as layer:
                for feature in layer.iterShapeRecords(bbox=source_bounds):
                    polygon = shape(feature.shape.__geo_interface__)
                    if not source_crs.equals(CRS.from_epsg(4326), ignore_axis_order=True):
                        polygon = transform_geometry(polygon, to_geo.transform, interleaved=False)
                    self.polygons.append(polygon)
                    self.values.append(feature.record.as_dict()[attribute])
        self.tree = STRtree(self.polygons)
        self.mapped = set().union(*self.groups.values())
        self.unmapped = sorted(set(self.values) - self.mapped)

    def at(self, point):
        location = Point(*point)
        values = {self.values[int(i)] for i in self.tree.query(location)
                  if self.polygons[int(i)].covers(location)}
        matches = {group for group, selected in self.groups.items() if values & selected}
        return next(iter(matches)) if len(matches) == 1 and values <= self.mapped else -1

    def terminals(self, grid, flow):
        """Classify only domain exits; interior depressions do not become outlets."""
        result = np.full(flow.shape, -1, dtype='int64')
        height, width = flow.shape
        to_geo = Transformer.from_crs(grid.crs, 4326, always_xy=True)
        for rr, cc in np.argwhere(flow == -1):
            row, column = int(rr), int(cc)
            if row not in (0, height - 1) and column not in (0, width - 1):
                continue
            point = to_geo.transform(*grid.coordinates(row, column), errcheck=True)
            result[row, column] = self.at(point)
        return result
