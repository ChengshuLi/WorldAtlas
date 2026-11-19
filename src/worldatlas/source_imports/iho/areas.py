"""Import complete sea areas from IHO's S-130 XML archive.

Recipes select areas by IHO area ID. The XML uses a separate record ID to
link the records that hold the polygons for one area.
"""

import math
import time
from xml.etree import ElementTree
from zipfile import ZipFile

from shapely import union_all
from shapely.affinity import translate
from shapely.geometry import Polygon, box, mapping

from worldatlas.source_imports.shared.contracts import FeatureIdentity, NonEmptyText, SourceId
from worldatlas.source_imports.shared.runtime import Runtime
from worldatlas.source_imports.shared.sources import acquire_sources
from worldatlas.source_imports.shared.storage import feature_result, save_features

NS = {"s130": "http://www.iho.int/S130/2.0", "gml": "http://www.opengis.net/gml/3.2"}
GML_ID = "{http://www.opengis.net/gml/3.2}id"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
EPSG_4326 = "http://www.opengis.net/def/crs/EPSG/0/4326"

# These are the XML names used by the S-130 file format.
SEA_AREA_ELEMENT = f"{{{NS['s130']}}}GlobalSeaArea"
LINK_TO_CONTAINING_AREA = "s130:theComponent"
LINKS_TO_AREA_PIECES = "s130:theCollection"
RING_COORDINATES = "gml:LinearRing/gml:posList"


def s130_areas(
    runtime: Runtime,
    *,
    source_id: SourceId,
    gml_member: NonEmptyText,
    selections: list[FeatureIdentity],
):
    """Import complete S-130 sea areas with linked surfaces and holes.

    Args:
        runtime: Import resources and saved recipe snapshot.
        source_id: Catalog ID of the S-130 archive.
        gml_member: Exact GML member name inside the archive.
        selections: Provider MRNs and their output IDs in Neon.

    Returns:
        Saved feature IDs, the local source path, and timings.
    """
    started, timing = time.monotonic(), {}
    path, = acquire_sources(runtime, [source_id], timing=timing)
    features = read_areas(path, gml_member=gml_member, selections=selections)
    feature_ids = save_features(runtime, features)
    return feature_result(feature_ids, time.monotonic() - started, source=path,
                          download_seconds=timing.get("download_seconds", 0.0))


def read_areas(path, *, gml_member, selections):
    """Read complete S-130 areas from a verified archive.

    Args:
        path: Local path of the verified S-130 archive.
        gml_member: Exact GML member name inside the archive.
        selections: Provider MRNs paired with output feature IDs.

    Returns:
        Features containing the selected areas and their output IDs.
    """
    document = read_document(path, gml_member)
    reader = SeaAreas(document)
    return [
        {
            "feature_id": selection["feature_id"],
            "geometry": reader.geometry(selection["source_feature_id"]),
        }
        for selection in selections
    ]


def read_document(path, member):
    """Parse the selected GML file from a verified archive.

    Args:
        path: Local path of the verified S-130 ZIP archive.
        member: Exact GML member name inside the archive.

    Returns:
        Root element of the parsed XML document.

    Raises:
        ValueError: The member is missing or duplicated.
        ElementTree.ParseError: The selected member is invalid XML.
    """
    with ZipFile(path) as archive:
        if archive.namelist().count(member) != 1:
            raise ValueError(f"expected exactly one IHO GML member named {member!r}")
        with archive.open(member) as source:
            return ElementTree.parse(source).getroot()


class SeaAreas:
    """Find sea areas by IHO ID and assemble the polygons for each area."""

    def __init__(self, document):
        """Index XML records and find the record for each whole sea area.

        A Maritime Resource Name (MRN) identifies the sea area. The record
        for the whole area and its individual polygon records can share it.
        Each XML record also has its own ID, which other records link to.

        Args:
            document: Root element of the parsed S-130 GML.

        Raises:
            ValueError: An XML ID is repeated or a sea area has no IHO ID.
        """
        seen_xml_ids = set()
        self._records = {}
        self._provider_ids = {}
        for element in document.iter():
            xml_id = element.get(GML_ID)
            if not xml_id:
                continue
            if xml_id in seen_xml_ids:
                raise ValueError("duplicate GML feature ID")
            seen_xml_ids.add(xml_id)
            if element.tag != SEA_AREA_ELEMENT:
                continue
            provider_id = element.findtext("s130:featureIdentifier", namespaces=NS)
            if not provider_id:
                raise ValueError(f"S-130 area has no provider area ID: {xml_id!r}")
            self._records[xml_id] = element
            self._provider_ids[xml_id] = provider_id

        self._whole_record_ids = {}
        for xml_id, record in self._records.items():
            provider_id = self._provider_ids[xml_id]
            containing_ids = _linked_record_ids(record, LINK_TO_CONTAINING_AREA)
            # Only a link to the same provider ID makes this record a piece.
            is_piece = any(
                self._provider_ids.get(container_id) == provider_id
                for container_id in containing_ids
            )
            if not is_piece:
                self._whole_record_ids.setdefault(provider_id, []).append(xml_id)

    def geometry(self, provider_id):
        """Assemble the complete geometry of one sea area.

        Args:
            provider_id: IHO's Maritime Resource Name (MRN) for the area.

        Returns:
            Complete GeoJSON geometry.

        Raises:
            ValueError: The ID is missing or ambiguous, or its polygons
                are missing or invalid.
        """
        whole_area_ids = self._whole_record_ids.get(provider_id, ())
        if len(whole_area_ids) != 1:
            raise ValueError(f"IHO area ID must identify one complete area: {provider_id!r}")
        polygons = self._read_record_polygons(whole_area_ids[0], ())
        return mapping(union_all(polygons))

    def _read_record_polygons(self, xml_id, link_path):
        """Read polygons from a record, following links when it stores only pieces.

        Args:
            xml_id: ID of the XML record to read.
            link_path: Records already visited along this chain of links.

        Returns:
            Shapely polygons or multipolygons for this record and its pieces.

        Raises:
            ValueError: A link loops back or a piece is missing or invalid.
        """
        if xml_id in link_path:
            raise ValueError(f"S-130 area links back to itself: {xml_id!r}")
        record = self._records[xml_id]
        patches = record.findall(".//gml:PolygonPatch", NS)
        if patches:
            return [read_polygon_patch(patch) for patch in patches]

        piece_ids = _linked_record_ids(record, LINKS_TO_AREA_PIECES)
        if not piece_ids:
            raise ValueError(f"S-130 record {xml_id!r} has no polygons or links to pieces")
        provider_id = self._provider_ids[xml_id]
        path = (*link_path, xml_id)
        polygons = []
        for piece_id in piece_ids:
            if self._provider_ids.get(piece_id) != provider_id:
                raise ValueError(f"missing or mismatched S-130 piece {piece_id!r} in {xml_id!r}")
            polygons.extend(self._read_record_polygons(piece_id, path))
        return polygons


def _linked_record_ids(record, link_tag):
    """Read the target XML IDs for links of one kind.

    Args:
        record: XML record containing the links.
        link_tag: Tag that points to the containing record or its pieces.

    Returns:
        Target IDs in source order. A link such as "#M.0120" becomes "M.0120".
    """
    return [
        link.get(XLINK_HREF, "").removeprefix("#")
        for link in record.findall(link_tag, NS)
    ]


def read_polygon_patch(patch):
    """Read one source polygon with its holes and split it at the dateline.

    Args:
        patch: GML element containing an outer ring and any holes.

    Returns:
        A Shapely polygon or multipolygon within the WGS84 longitude range.

    Raises:
        ValueError: An outline or hole is malformed, or the polygon is invalid.
    """
    exterior = read_ring_coordinates(patch.find(f"gml:exterior/{RING_COORDINATES}", NS))
    outer_mean_longitude = sum(longitude for longitude, _ in exterior) / len(exterior)
    holes = []
    for interior in patch.findall("gml:interior", NS):
        hole = read_ring_coordinates(interior.find(RING_COORDINATES, NS))
        hole_mean_longitude = sum(longitude for longitude, _ in hole) / len(hole)
        # The outline and hole were unwrapped independently. Bring them into
        # the same longitude range before building the polygon.
        shift = 360 * round((outer_mean_longitude - hole_mean_longitude) / 360)
        holes.append([(x + shift, y) for x, y in hole])
    polygon = Polygon(exterior, holes)
    if polygon.is_empty or not polygon.is_valid:
        raise ValueError("S-130 source surface is empty or invalid")
    west, _, east, _ = polygon.bounds
    if west >= -180 and east <= 180:
        return polygon

    # Clip every shifted copy that intersects the standard longitude range.
    world = box(-180, -90, 180, 90)
    first_turn = math.ceil((-180 - east) / 360)
    last_turn = math.floor((180 - west) / 360)
    pieces = []
    for turn in range(first_turn, last_turn + 1):
        shifted = translate(polygon, xoff=360 * turn)
        pieces.extend(polygon_parts(shifted.intersection(world)))
    return union_all(pieces)


def read_ring_coordinates(position):
    """Read an outline or hole and keep its longitudes continuous.

    Args:
        position: GML coordinate list in WGS84, with latitude first.

    Returns:
        Longitude and latitude pairs in boundary order. Longitudes may extend
        past 180 degrees so a short crossing stays short when building a polygon.

    Raises:
        ValueError: The coordinates are malformed, invalid, or open.
    """
    if position is None or position.get("srsName") != EPSG_4326:
        raise ValueError("expected S-130 latitude/longitude in EPSG:4326")
    values = list(map(float, (position.text or "").split()))
    if len(values) < 8 or len(values) % 2:
        raise ValueError("invalid S-130 ring coordinates")
    # GML lists latitude first. Shapely uses longitude as its x coordinate.
    points = [(values[i + 1], values[i]) for i in range(0, len(values), 2)]
    if points[0] != points[-1] or any(
        not (-180 <= longitude <= 180 and -90 <= latitude <= 90)
        for longitude, latitude in points
    ):
        raise ValueError("invalid or open S-130 ring")
    unwrapped = [points[0]]
    for longitude, latitude in points[1:]:
        previous_longitude, previous_latitude = unwrapped[-1]
        # A polar outline can use both map edges to close across the pole.
        # Leave those edges in place even though all longitudes meet at the pole.
        if abs(latitude) != 90 and abs(previous_latitude) != 90:
            while longitude - previous_longitude > 180:
                longitude -= 360
            while longitude - previous_longitude < -180:
                longitude += 360
        unwrapped.append((longitude, latitude))
    # Shapely would close an open ring by adding a straight edge. For a ring
    # that winds around a pole, that edge would cross the whole longitude grid.
    if unwrapped[0] != unwrapped[-1]:
        raise ValueError("S-130 ring does not close after unwrapping; check the pole edge")
    return unwrapped


def polygon_parts(geometry):
    """Collect the polygon pieces of a geometry after longitude clipping.

    Args:
        geometry: Shapely result that may include lines where a polygon
            only touches a clipping edge.

    Returns:
        A list of nonempty polygons.
    """
    if geometry.is_empty:
        return []
    if geometry.geom_type == "Polygon":
        return [geometry]
    if hasattr(geometry, "geoms"):
        return [part for child in geometry.geoms for part in polygon_parts(child)]
    return []
