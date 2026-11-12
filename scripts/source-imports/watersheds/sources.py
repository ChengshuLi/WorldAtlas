"""Read selected provider vertices, ways and river relations from verified files."""
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
import shutil
import zipfile

import numpy as np
from shapely.geometry import LineString

from watersheds.waterways import Waterways


class Sources:
    def __init__(self, files):
        self.files = files
        self.networks, self.extracted = {}, {}
        self.points = {}

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

    def network(self, sources, *, natural_only=False, reverse=()):
        paths = [self.path(source) if isinstance(source, dict) else self.files[source]
                 for source in sources]
        reverse = tuple(sorted(set(map(str, reverse))))
        key = tuple(paths), natural_only, reverse
        if key not in self.networks:
            self.networks[key] = Waterways(paths, natural_only=natural_only, reverse=reverse)
        return self.networks[key]

    def point(self, specification, lines):
        if 'point' in specification:
            return tuple(map(float, specification['point']))
        if 'node' in specification:
            source, node = specification['source'], str(specification['node'])
            path = self.files[source]
            if path.suffix != '.pbf':
                return self.network([source]).nodes[node]
            key = source, node
            if key not in self.points:
                import osmium

                selected = []

                class Coordinates(osmium.SimpleHandler):
                    def node(self, value):
                        selected.append((value.lon, value.lat))

                Coordinates().apply_file(str(path), filters=[osmium.filter.IdFilter([int(node)])])
                if len(selected) != 1:
                    raise ValueError('selected OSM node is missing or duplicated')
                point = selected[0]
                if not np.isfinite(point).all() or not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
                    raise ValueError('invalid OSM node coordinates')
                self.points[key] = point
            return self.points[key]
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
        """Read one complete source feature; boundary assembly joins sections."""
        if len(parts) != 1:
            raise ValueError('select one source feature per line; join separate sections in boundary assembly')
        part, = parts
        if 'way' in part:
            allowed = {'source', 'way'}
            points = list(self.network([part['source']]).line(part['way']).coords)
        elif 'relation' in part:
            allowed = {'source', 'relation', 'role', 'start_node'}
            points = self.river(part)
        elif 'geojson_feature' in part:
            allowed = {'source', 'member', 'geojson_feature'}
            document = json.loads(self.path(part).read_bytes())
            geometry = document['features'][part['geojson_feature']]['geometry']
            if geometry['type'] != 'LineString':
                raise ValueError('selected GeoJSON feature must be a line')
            points = geometry['coordinates']
        else:
            raise ValueError('unsupported source line selection')
        if set(part) - allowed:
            raise ValueError('unsupported source line options')
        coordinates = [tuple(map(float, point)) for point in points]
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
