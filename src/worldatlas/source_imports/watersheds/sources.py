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
from worldatlas.source_imports.watersheds.boundary import choose_intersection_join
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
        # Cache reads by file and selection so separate steps can share results.
        # The constructor separately keeps the names the recipe gives its lines.
        self.networks = {}
        self.points = {}

    def resolve_raster_path(self, specification):
        """Resolve a terrain file or explicitly selected ZIP member for GDAL.

        Args:
            specification: A source alias in ``source`` and an optional ZIP member.

        Returns:
            The local file or GDAL virtual path.
        """
        path = self.files[specification['source']]
        return gdal_dataset_path(path, specification['member']) if 'member' in specification else path

    def resolve_vector_path(self, selection):
        """Resolve a vector file or a Shapefile inside its ZIP for GDAL.

        Args:
            selection: A source alias or a mapping with ``source`` and an optional ``member``.

        Returns:
            The GDAL dataset path.
        """
        if isinstance(selection, str):
            return gdal_dataset_path(self.files[selection])
        return gdal_dataset_path(self.files[selection['source']], selection.get('member'))

    def read_osm_network(self, sources, *, rivers_and_streams_only=False, reverse=()):
        """Read and reuse an OSM network for these source files and directions.

        Args:
            sources: Source aliases or selections of specific archive members.
            rivers_and_streams_only: Whether to retain only ways tagged as rivers or streams.
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
        # Normalize the IDs so equivalent reversal lists reuse the same network.
        reverse = tuple(sorted(set(map(str, reverse))))
        # One set of files can support both raw source lines and corrected drainage.
        key = tuple(paths), rivers_and_streams_only, reverse
        if key not in self.networks:
            self.networks[key] = Waterways(paths, rivers_and_streams_only=rivers_and_streams_only, reverse=reverse)
        return self.networks[key]

    def read_selected_point(self, specification, lines):
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
                return self.read_osm_network([source]).nodes[node]
            key = source, node
            if key not in self.points:
                # An isolated PBF node may belong to no river or stream way.
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
            return choose_intersection_join(lines[first], lines[second], specification['near']).point
        raise ValueError('unknown source point selection')

    def read_selected_line(self, part: SourceLine):
        """Read one complete source line for boundary assembly.

        Args:
            part: A GeoJSON feature, OSM way, or OSM river relation selection.

        Returns:
            The selected Shapely line in WGS84.

        Raises:
            ValueError: The selector is unsupported or the line has invalid coordinates.
        """
        if 'way' in part:  # An OsmWayLine selects one OSM way.
            # Allow all way types here because a source line can be a coastline.
            points = list(self.read_osm_network([part['source']]).way_line(part['way']).coords)
        elif 'relation' in part:  # An OsmRiverLine joins selected relation members.
            points = self.assemble_river_relation(part)
        elif 'geojson_feature' in part:  # A GeoJSONLine selects a feature by position.
            path = self.files[part['source']]
            if 'member' in part:
                with ZipFile(path) as archive, archive.open(archive_member(archive, part['member'])) as stream:
                    document = json.load(stream)
            else:
                with path.open('rb') as stream:
                    document = json.load(stream)
            # geojson_feature is the zero-based position in the feature list.
            geometry = document['features'][part['geojson_feature']]['geometry']
            if geometry['type'] != 'LineString':
                raise ValueError('selected GeoJSON feature must be a line')
            points = geometry['coordinates']
        else:
            raise ValueError('unsupported source line selection')
        if len(points) < 2:
            raise ValueError('source line needs at least two selected points')
        # Validate one longitude/latitude pair per vertex, then use the same array in Shapely.
        coordinates = np.asarray(points, dtype=float)
        if (coordinates.shape != (len(points), 2) or not np.isfinite(coordinates).all()
                or np.any(np.abs(coordinates[:, 0]) > 180)
                or np.any(np.abs(coordinates[:, 1]) > 90)):
            raise ValueError('source line requires finite WGS84 longitude/latitude pairs')
        return LineString(coordinates)

    def assemble_river_relation(self, specification):
        """Order a river relation's selected member ways from a known end.

        Args:
            specification: The source alias, relation ID, member role, and start node ID.

        Returns:
            Ordered WGS84 coordinates from the selected ways.

        Raises:
            ValueError: The selected members do not form one open, connected chain.
        """
        network = self.read_osm_network([specification['source']])
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
