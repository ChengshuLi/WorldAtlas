"""Read selected provider vertices, ways and river relations from verified files."""
from contextlib import ExitStack
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
import shutil
import zipfile

import numpy as np
from pyproj import CRS, Transformer
import shapefile
from shapely.geometry import LineString

from watersheds.waterways import Waterways


class Sources:
    def __init__(self, files):
        self.files = files
        self.stack = ExitStack()
        self.readers, self.indices, self.networks, self.extracted = {}, {}, {}, {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stack.close()

    def member(self, source, name):
        key = (source, name)
        if key in self.extracted:
            return self.extracted[key]
        if not name or '..' in Path(name).parts or Path(name).is_absolute():
            raise ValueError('invalid source archive member')
        directory = self.files[source].parent / 'extracted'
        directory.mkdir(exist_ok=True)
        with zipfile.ZipFile(self.files[source]) as archive:
            names = [name]
            if name.endswith('.shp'):
                names = [str(Path(name).with_suffix(ext)) for ext in ('.shp', '.shx', '.dbf', '.prj')]
            for member in names:
                destination = directory / member
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = NamedTemporaryFile(dir=directory, prefix='extract-', delete=False)
                try:
                    with temporary, archive.open(member) as stream:
                        shutil.copyfileobj(stream, temporary, 1 << 20)
                    Path(temporary.name).replace(destination)
                finally:
                    Path(temporary.name).unlink(missing_ok=True)
        self.extracted[key] = directory / name
        return self.extracted[key]

    def path(self, specification):
        source = specification['source']
        return self.member(source, specification['member']) if 'member' in specification else self.files[source]

    def network(self, sources, *, natural_only=False):
        paths = [self.path(source) if isinstance(source, dict) else self.files[source]
                 for source in sources]
        key = tuple(paths), natural_only
        if key not in self.networks:
            self.networks[key] = Waterways(paths, natural_only=natural_only)
        return self.networks[key]

    def point(self, specification, lines):
        if 'point' in specification:
            return tuple(map(float, specification['point']))
        if 'node' in specification:
            return self.network([specification['source']]).nodes[str(specification['node'])]
        if 'line' in specification:
            line = lines[specification['line']]
            if specification['endpoint'] not in ('start', 'end'):
                raise ValueError('source endpoint must be start or end')
            return tuple(line.coords[0 if specification['endpoint'] == 'start' else -1])
        if 'intersection' in specification:
            from watersheds.boundary import intersection
            first, second = specification['intersection']
            return intersection(lines[first], lines[second], specification['near']).point
        raise ValueError('unknown source point selection')

    def line(self, parts):
        coordinates = []
        for part in parts:
            breaks = set()
            if 'point' in part:
                coordinates.append(tuple(map(float, part['point'])))
                continue
            if 'way' in part:
                points = list(self.network([part['source']]).line(part['way']).coords)
            elif 'relation' in part:
                points = self.river(part)
            elif 'geojson_feature' in part:
                document = json.loads(self.path(part).read_bytes())
                geometry = document['features'][part['geojson_feature']]['geometry']
                if geometry['type'] != 'LineString':
                    raise ValueError('selected GeoJSON feature must be a line')
                points = geometry['coordinates']
            else:
                path = self.path(part)
                if path not in self.readers:
                    self.readers[path] = self.stack.enter_context(shapefile.Reader(path))
                reader = self.readers[path]
                field = part['feature_field']
                key = (path, field)
                if key not in self.indices:
                    index = {}
                    for row in reader.iterRecords(fields=[field]):
                        if row[field] in index:
                            raise ValueError('source feature identity is not unique')
                        index[row[field]] = row.oid
                    self.indices[key] = index
                feature = reader.shape(self.indices[key][part['feature']])
                breaks = set(feature.parts)
                points = feature.points
                crs = CRS.from_wkt(path.with_suffix('.prj').read_text())
                if not crs.equals(CRS.from_epsg(4326), ignore_axis_order=True):
                    to_geo = Transformer.from_crs(crs, 4326, always_xy=True)
                    points = [to_geo.transform(*point, errcheck=True) for point in points]
            if 'vertices' in part:
                selected = []
                for vertex in part['vertices']:
                    if isinstance(vertex, int):
                        selected.append(points[vertex])
                    else:
                        index, fraction = vertex['edge']
                        if not 0 <= index < len(points) - 1 or index + 1 in breaks or not 0 <= fraction <= 1:
                            raise ValueError('source edge fraction is outside the edge')
                        first, last = points[index], points[index + 1]
                        selected.append(tuple(a + (b - a) * fraction for a, b in zip(first, last)))
                points = selected
            coordinates.extend(tuple(map(float, point)) for point in points)
        if len(coordinates) < 2:
            raise ValueError('source line needs at least two selected points')
        values = np.asarray(coordinates)
        if values.shape != (len(coordinates), 2) or not np.isfinite(values).all() or np.any(np.abs(values[:, 0]) > 180) or np.any(np.abs(values[:, 1]) > 90):
            raise ValueError('source line requires finite WGS84 longitude/latitude pairs')
        return LineString(coordinates)

    def river(self, specification):
        network = self.network([specification['source']])
        _, members = network.relations[str(specification['relation'])]
        adjacent = {}
        for kind, reference, role in members:
            if kind == 'way' and role == specification['role']:
                nodes = network.ways[reference].nodes
                for first, last in zip(nodes, nodes[1:]):
                    adjacent.setdefault(first, set()).add(last)
                    adjacent.setdefault(last, set()).add(first)
        node = str(specification['start_node'])
        if node not in adjacent or len(adjacent[node]) != 1 or any(len(v) > 2 for v in adjacent.values()):
            raise ValueError('selected river members do not form an unbranched chain')
        order, seen = [node], {node}
        while adjacent[order[-1]] - seen:
            following, = adjacent[order[-1]] - seen
            order.append(following)
            seen.add(following)
        if len(seen) != len(adjacent) or len(adjacent[order[-1]]) != 1:
            raise ValueError('selected river chain is disconnected or closed')
        return [network.nodes[node] for node in order]
