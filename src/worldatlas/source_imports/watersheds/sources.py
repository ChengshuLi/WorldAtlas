"""Find the files, points, and lines named in a watershed recipe."""

import json
from collections.abc import Iterable, Mapping
from itertools import pairwise
from pathlib import Path
from typing import Annotated, NotRequired, cast
from zipfile import ZipFile

import osmium
from osmium.filter import IdFilter
from osmium.osm import NODE, Node
from pydantic import Field
from shapely.geometry import LineString
from typing_extensions import TypedDict

from worldatlas.geodesy.geojson import Position, validate_geometry
from worldatlas.source_assets.archives import archive_member
from worldatlas.source_imports.shared.recipe_types import NonEmptyText
from worldatlas.source_imports.shared.sources import gdal_dataset_path
from worldatlas.source_imports.watersheds.boundary import choose_intersection_join
from worldatlas.source_imports.watersheds.waterways import Waterways


class FileSelection(TypedDict):
    """Name a source file and optionally a file inside its ZIP.

    For example, ``{"source": "dem", "member": "north.tif"}`` selects
    north.tif inside the file named dem in the recipe.
    """

    source: NonEmptyText
    member: NotRequired[NonEmptyText]


class GeoJSONLine(FileSelection):
    """Pick a line from a GeoJSON file by its position.

    For example, ``{"source": "author", "geojson_feature": 2}`` picks the
    third feature in the file. The first feature is at position 0.
    """

    geojson_feature: Annotated[int, Field(ge=0)]


class OsmWayLine(TypedDict):
    """Pick one OSM way, such as ``{"source": "coast", "way": 42}``.

    A way is an ordered list of saved points. Together they draw the line.
    """

    source: NonEmptyText
    way: NonEmptyText | int


class OsmRiverLine(TypedDict):
    """Pick the pieces of a river that share a role in an OSM relation.

    A relation groups related OSM objects. A recipe can select the ways
    marked ``main_stream`` to draw the main river channel.
    """

    source: NonEmptyText
    relation: NonEmptyText | int
    role: str


SourceLine = GeoJSONLine | OsmWayLine | OsmRiverLine


class CoordinatePoint(TypedDict, closed=True):
    """Supply an explicit WGS84 longitude and latitude."""

    point: Position


class OsmNodePoint(TypedDict, closed=True):
    """Select a node in one OSM source."""

    source: NonEmptyText
    node: NonEmptyText | int


class IntersectionPoint(TypedDict, closed=True):
    """Select the meeting point of two lines closest to a known location."""

    intersection: tuple[NonEmptyText, NonEmptyText]
    near: Position


type SourcePoint = CoordinatePoint | OsmNodePoint | IntersectionPoint


def _read_pbf_node(path: Path, node_id: int) -> tuple[float, float]:
    """Read one node from a PBF file, including a node that no way uses.

    Args:
        path: Local OSM PBF file.
        node_id: Numeric OSM ID of the point to read.

    Returns:
        Longitude and latitude in WGS84 degrees.

    Raises:
        ValueError: The file has no matching node, has duplicates, or has
            invalid coordinates for the node.
    """
    reader = osmium.FileProcessor(path, NODE).with_filter(IdFilter([node_id]))
    selected = []
    for entry in reader:
        # Only nodes were requested. Copy the coordinates before the reader
        # advances because the OSM object is valid only during this iteration.
        location = cast(Node, entry).location
        if not location.valid():
            raise ValueError('invalid OSM node coordinates')
        selected.append((location.lon, location.lat))
    if len(selected) != 1:
        raise ValueError('selected OSM node is missing or duplicated')
    return selected[0]


class Sources:
    """Look up the local files and map features a recipe names.

    Args:
        files: Verified local files by recipe name. For example, the name
            ``dem`` might refer to the local file ``elevation.tif``.
    """

    def __init__(self, files: Mapping[str, Path]) -> None:
        """Store the verified local files and prepare the lookup caches.

        Args:
            files: Recipe file names mapped to local paths.
        """
        self.files = files
        # Reuse an OSM network or a PBF point if another step asks for it again.
        self.networks = {}
        self.points = {}

    def resolve_raster_path(self, specification: str | FileSelection) -> str | Path:
        """Tell GDAL where to open an elevation file.

        Args:
            specification: A recipe file name, or a ``source`` and ``member``
                selecting one file inside a ZIP.

        Returns:
            The local path or an address GDAL uses to open a file inside a ZIP.
            For example, ``/vsizip/{/data/dem.zip}/north.tif`` names north.tif
            inside dem.zip.

        Raises:
            ValueError: The selected file inside the archive is invalid or missing.
        """
        if isinstance(specification, str):
            return self.files[specification]
        path = self.files[specification['source']]
        return (
            gdal_dataset_path(path, specification['member'])
            if 'member' in specification
            else path
        )

    def resolve_vector_path(self, selection: str | FileSelection) -> str:
        """Tell GDAL where to open the file that contains the basin shapes.

        Args:
            selection: A recipe file name such as ``"basins"``, or a selection
                like ``{"source": "basins", "member": "north.shp"}``.

        Returns:
            The local path or an address GDAL can open inside a ZIP. Given
            only the ZIP source, select its sole Shapefile.

        Raises:
            ValueError: The requested archive file is invalid, missing, or ambiguous.
        """
        if isinstance(selection, str):
            return gdal_dataset_path(self.files[selection])
        return gdal_dataset_path(
            self.files[selection['source']], selection.get('member')
        )

    def read_osm_network(
        self,
        sources: Iterable[str | FileSelection],
        *,
        rivers_and_streams_only: bool = False,
        reverse: Iterable[int | str] = (),
    ) -> Waterways:
        """Read the OSM files and remember the result for later lookups.

        Args:
            sources: Recipe file names or selections of files inside ZIPs.
            rivers_and_streams_only: Whether to retain only ways tagged as rivers or streams.
            reverse: IDs of streams whose saved point order needs reversing
                so it follows the known direction of flow.

        Returns:
            A Waterways object for the selected files and options. Repeated
            requests with those same settings reuse the object.

        Raises:
            ValueError: The OSM data is inconsistent or a stream to reverse is missing.
        """
        paths = []
        for selection in sources:
            if isinstance(selection, str):
                paths.append(self.files[selection])
            else:
                path = self.files[selection['source']]
                paths.append(
                    (path, selection['member']) if 'member' in selection else path
                )
        # Way 42 and way "42" refer to the same stream. Sort and remove
        # duplicates so lists with the same corrections share one read.
        reverse = tuple(sorted(set(map(str, reverse))))
        # A coastline lookup may need every way. A drainage lookup may keep
        # only rivers and streams and reverse some. Cache those reads separately.
        key = tuple(paths), rivers_and_streams_only, reverse
        if key not in self.networks:
            self.networks[key] = Waterways(
                paths, rivers_and_streams_only=rivers_and_streams_only, reverse=reverse
            )
        return self.networks[key]

    def resolve_recipe_point(
        self, specification: SourcePoint, lines: Mapping[str, LineString]
    ) -> tuple[float, float]:
        """Find the longitude and latitude of a point named in the recipe.

        Args:
            specification: Coordinates such as ``{"point": [51.5, 46.8]}``,
                an OSM point such as ``{"source": "river", "node": 42}``, or
                two line names in ``intersection`` and a coordinate pair in ``near``.
            lines: The drawn lines by recipe name, used for intersections.

        Returns:
            The selected longitude and latitude in degrees.

        Raises:
            ValueError: The selection is unsupported, the PBF point is missing,
                duplicated, or invalid, or the selected lines never meet.
        """
        if 'point' in specification:
            longitude, latitude = specification['point']
            return longitude, latitude
        if 'node' in specification:
            source, node = specification['source'], str(specification['node'])
            path = self.files[source]
            # The general OSM reader handles standalone files and archives.
            # For a .pbf file, scan for just this node to avoid storing a whole network.
            if path.suffix != '.pbf':
                return self.read_osm_network([source]).nodes[node]
            key = source, node
            if key not in self.points:
                self.points[key] = _read_pbf_node(path, int(node))
            return self.points[key]
        if 'intersection' in specification:
            first, second = specification['intersection']
            # When a river meets a coastline twice, near tells us which
            # of the two meeting points the recipe intends to use.
            longitude, latitude = choose_intersection_join(
                lines[first], lines[second], specification['near']
            ).point
            return longitude, latitude
        raise ValueError('unknown source point selection')

    def read_source_line(self, part: SourceLine) -> LineString:
        """Read one complete source line for boundary assembly.

        Args:
            part: A GeoJSON feature, OSM way, or OSM river relation selection.

        Returns:
            A Shapely line with the selected longitude and latitude pairs.

        Raises:
            ValueError: The selector is unsupported or the line has invalid coordinates.
        """
        if 'way' in part:  # An OsmWayLine selects one OSM way.
            # A recipe can draw the boundary along a coastline, so keep ways
            # with any tag for this lookup.
            points = list(
                self.read_osm_network([part['source']]).way_line(part['way']).coords
            )
        elif 'relation' in part:  # An OsmRiverLine joins selected relation members.
            points = self.join_river_relation_ways(part)
        elif 'geojson_feature' in part:  # A GeoJSONLine selects a feature by position.
            path = self.files[part['source']]
            if 'member' in part:
                with (
                    ZipFile(path) as archive,
                    archive.open(archive_member(archive, part['member'])) as stream,
                ):
                    document = json.load(stream)
            else:
                with path.open('rb') as stream:
                    document = json.load(stream)
            index = part['geojson_feature']
            if not 0 <= index < len(document['features']):
                raise ValueError('GeoJSON feature position is outside the source')
            geometry = document['features'][index]['geometry']
            if geometry['type'] != 'LineString':
                raise ValueError('selected GeoJSON feature must be a line')
            points = geometry['coordinates']
        else:
            raise ValueError('unsupported source line selection')
        if len(points) < 2:
            raise ValueError('source line needs at least two selected points')
        # All three readers must give us one longitude and one latitude per
        # point. For example, [10, 95] fails because latitude stops at 90°.
        try:
            line = validate_geometry({'type': 'LineString', 'coordinates': points})
        except ValueError as error:
            raise ValueError(
                'source line requires finite WGS84 longitude/latitude pairs'
            ) from error
        return cast(LineString, line)

    def join_river_relation_ways(
        self, specification: OsmRiverLine
    ) -> list[tuple[float, float]]:
        """Join the selected pieces of a river at their shared OSM points.

        Args:
            specification: The recipe file name, OSM relation ID, and role
                of the pieces to keep, such as ``main_stream``.

        Returns:
            Longitude and latitude pairs in line order. Start at the end
            with the smaller OSM node ID so the result is repeatable. The
            boundary recipe supplies the locations where its own line stops.

        Raises:
            ValueError: The selected members do not form one open, connected chain.
        """
        network = self.read_osm_network([specification['source']])
        _, members = network.relations[str(specification['relation'])]
        # If the pieces are 20–30 and 10–20, node 20 has neighbors 10 and 30.
        # Save both directions so we can walk the same line from either end.
        adjacent = {}
        for kind, reference, role in members:
            if kind == 'way' and role == specification['role']:
                nodes = network.ways[reference].nodes
                for first, last in pairwise(nodes):
                    adjacent.setdefault(first, set()).add(last)
                    adjacent.setdefault(last, set()).add(first)
        # In 10–20–30, nodes 10 and 30 each have one neighbor, so they
        # are the ends. A node with three neighbors would be a fork.
        endpoints = [
            node for node, neighbors in adjacent.items() if len(neighbors) == 1
        ]
        if len(endpoints) != 2 or any(
            len(neighbors) > 2 for neighbors in adjacent.values()
        ):
            raise ValueError('selected river members do not form an unbranched chain')
        node = min(endpoints, key=int)
        order, seen = [node], {node}
        # After walking from 10 to 20, skip the point we came from and go to 30.
        while adjacent[order[-1]] - seen:
            (following,) = adjacent[order[-1]] - seen
            order.append(following)
            seen.add(following)
        # A separate loop can leave us with two ends but still leave points unvisited.
        if len(seen) != len(adjacent):
            raise ValueError('selected river chain is disconnected or closed')
        return [network.nodes[node] for node in order]
