"""Read selected provider vertices, ways and river relations from verified files."""
from itertools import pairwise
import json
from typing import NotRequired, TypedDict
from zipfile import ZipFile

import numpy as np
import osmium
from shapely.geometry import LineString

from worldatlas.source_imports.shared.recipe_types import NonEmptyText
from worldatlas.source_imports.shared.sources import archive_member, gdal_dataset_path
from worldatlas.source_imports.watersheds.boundary import intersection
from worldatlas.source_imports.watersheds.waterways import Waterways


class FileSelection(TypedDict):
    """Select a recipe source and optionally one of its ZIP members."""

    source: NonEmptyText
    member: NotRequired[NonEmptyText]


class GeoJSONLine(FileSelection):
    """Select a line by its position in a GeoJSON feature collection."""

    geojson_feature: int


class OsmWayLine(TypedDict):
    """Select a complete way from an OSM extract."""

    source: NonEmptyText
    way: NonEmptyText | int


class OsmRiverLine(TypedDict):
    """Select and orient a river relation's member ways."""

    source: NonEmptyText
    relation: NonEmptyText | int
    role: str
    start_node: NonEmptyText | int


SourceLine = GeoJSONLine | OsmWayLine | OsmRiverLine


class Sources:
    """Resolve source aliases and reuse the geometry read from their files.

    Args:
        files: Verified local paths keyed by the recipe's source aliases.
    """

    def __init__(self, files):
        self.files = files
        self.networks = {}
        self.points = {}

    def path(self, specification):
        """Resolve a terrain file or explicitly selected ZIP member for GDAL.

        Args:
            specification: A source alias in ``source`` and an optional ZIP member.

        Returns:
            The local file or GDAL virtual path.
        """
        path = self.files[specification['source']]
        return gdal_dataset_path(path, specification['member']) if 'member' in specification else path

    def vector_path(self, selection):
        """Resolve a vector file or a Shapefile inside its ZIP for GDAL.

        Args:
            selection: A source alias or a mapping with ``source`` and an optional ``member``.

        Returns:
            The GDAL dataset path.
        """
        if isinstance(selection, str):
            return gdal_dataset_path(self.files[selection])
        return gdal_dataset_path(self.files[selection['source']], selection.get('member'))

    def network(self, sources, *, natural_only=False, reverse=()):
        """Read and reuse an OSM network for these source files and directions.

        Args:
            sources: Source aliases or selections of specific archive members.
            natural_only: Whether to retain only natural rivers and streams.
            reverse: IDs of ways whose source-backed downstream direction is reversed.

        Returns:
            A Waterways instance cached for the requested files and options.
        """
        paths = []
        for selection in sources:
            if isinstance(selection, str):
                paths.append(self.files[selection])
            else:
                path = self.files[selection['source']]
                paths.append((path, selection['member']) if 'member' in selection else path)
        reverse = tuple(sorted(set(map(str, reverse))))
        # One set of files can support both raw source lines and corrected drainage.
        key = tuple(paths), natural_only, reverse
        if key not in self.networks:
            self.networks[key] = Waterways(paths, natural_only=natural_only, reverse=reverse)
        return self.networks[key]

    def point(self, specification, lines):
        """Resolve a recipe point to WGS84 longitude and latitude.

        Args:
            specification: A coordinate pair, OSM node, named line endpoint, or
                intersection of two named lines with a point near the intended join.
            lines: Parsed source lines keyed by the names used in the recipe.

        Returns:
            The selected longitude and latitude in degrees.

        Raises:
            ValueError: The selector is unsupported or the selected point is invalid.
        """
        if 'point' in specification:
            return tuple(map(float, specification['point']))
        if 'node' in specification:
            source, node = specification['source'], str(specification['node'])
            path = self.files[source]
            if path.suffix != '.pbf':
                return self.network([source]).nodes[node]
            key = source, node
            if key not in self.points:
                # An isolated node in a PBF may have no natural river referencing it.
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
            first, second = specification['intersection']
            return intersection(lines[first], lines[second], specification['near']).point
        raise ValueError('unknown source point selection')

    def line(self, part: SourceLine):
        """Read one complete source line for boundary assembly.

        Args:
            part: A GeoJSON feature, OSM way, or OSM river relation selection.

        Returns:
            The selected Shapely line in WGS84.

        Raises:
            ValueError: The selector is unsupported or the line has invalid coordinates.
        """
        if 'way' in part:
            points = list(self.network([part['source']]).line(part['way']).coords)
        elif 'relation' in part:
            points = self.river(part)
        elif 'geojson_feature' in part:
            path = self.files[part['source']]
            if 'member' in part:
                with ZipFile(path) as archive, archive.open(archive_member(archive, part['member'])) as stream:
                    document = json.load(stream)
            else:
                with path.open('rb') as stream:
                    document = json.load(stream)
            geometry = document['features'][part['geojson_feature']]['geometry']
            if geometry['type'] != 'LineString':
                raise ValueError('selected GeoJSON feature must be a line')
            points = geometry['coordinates']
        else:
            raise ValueError('unsupported source line selection')
        coordinates = [tuple(map(float, point)) for point in points]
        if len(coordinates) < 2:
            raise ValueError('source line needs at least two selected points')
        values = np.asarray(coordinates)
        if values.shape != (len(coordinates), 2) or not np.isfinite(values).all() or np.any(np.abs(values[:, 0]) > 180) or np.any(np.abs(values[:, 1]) > 90):
            raise ValueError('source line requires finite WGS84 longitude/latitude pairs')
        return LineString(coordinates)

    def river(self, specification):
        """Order a river relation's selected member ways from a known end.

        Args:
            specification: The source alias, relation ID, member role, and start node ID.

        Returns:
            Ordered WGS84 coordinates from the selected ways.

        Raises:
            ValueError: The selected members do not form one open, connected chain.
        """
        network = self.network([specification['source']])
        _, members = network.relations[str(specification['relation'])]
        adjacent = {}
        for kind, reference, role in members:
            if kind == 'way' and role == specification['role']:
                nodes = network.ways[reference].nodes
                for first, last in pairwise(nodes):
                    adjacent.setdefault(first, set()).add(last)
                    adjacent.setdefault(last, set()).add(first)
        node = str(specification['start_node'])
        # A valid start has one neighbor. Interior nodes have two.
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
