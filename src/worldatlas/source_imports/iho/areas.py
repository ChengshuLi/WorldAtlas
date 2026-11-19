"""Read complete S-130 sea areas, preserving source surfaces and collection identity."""

import hashlib
import json
import math
import time
from xml.etree import ElementTree
from zipfile import ZipFile

from shapely.affinity import translate
from shapely.geometry import Polygon, box, mapping
from shapely.ops import unary_union

from worldatlas.geodesy.geojson import validate_geometry
from worldatlas.source_imports.shared.contracts import FeatureIdentity, NonEmptyText, SourceId
from worldatlas.source_imports.shared.runtime import Runtime
from worldatlas.source_imports.shared.sources import acquire_sources
from worldatlas.source_imports.shared.storage import feature_result, save_features

NS = {"s130": "http://www.iho.int/S130/2.0", "gml": "http://www.opengis.net/gml/3.2"}
GML_ID = "{http://www.opengis.net/gml/3.2}id"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
EPSG_4326 = "http://www.opengis.net/def/crs/EPSG/0/4326"


def read_document(path, member, gml_sha256):
    """Verify and parse the selected GML member of a verified archive.

    Args:
        path: Local path of the verified S-130 ZIP archive.
        member: Exact GML member name inside the archive.
        gml_sha256: Expected SHA-256 of the member bytes.

    Returns:
        Root element of the parsed XML document.

    Raises:
        ValueError: The member is missing, duplicated, or fails verification.
    """
    with ZipFile(path) as archive:
        if archive.namelist().count(member) != 1:
            raise ValueError("expected one selected IHO GML member")
        raw = archive.read(member)
    if hashlib.sha256(raw).hexdigest() != gml_sha256:
        raise ValueError("IHO GML SHA-256 mismatch")
    return ElementTree.fromstring(raw)


def ring(position):
    """Read a closed S-130 ring as unwrapped longitude and latitude pairs.

    Args:
        position: GML position list declaring EPSG:4326 latitude first.

    Returns:
        Closed ring with continuous longitudes, including across the dateline.

    Raises:
        ValueError: The coordinates are malformed, invalid, or open.
    """
    if position is None or position.get("srsName") != EPSG_4326:
        raise ValueError("expected S-130 latitude/longitude in EPSG:4326")
    values = list(map(float, (position.text or "").split()))
    if len(values) < 8 or len(values) % 2:
        raise ValueError("invalid S-130 ring coordinates")
    points = [(values[i + 1], values[i]) for i in range(0, len(values), 2)]
    if points[0] != points[-1] or any(
        not math.isfinite(x)
        or not math.isfinite(y)
        or not -180 <= x <= 180
        or not -90 <= y <= 90
        for x, y in points
    ):
        raise ValueError("invalid or open S-130 ring")
    # Unwrap antimeridian crossings before constructing the polygon.
    unwrapped = [points[0]]
    for x, y in points[1:]:
        # At a pole every longitude meets. Preserve an explicitly encoded
        # world-edge cap instead of collapsing its two meridians together.
        if abs(y) != 90 and abs(unwrapped[-1][1]) != 90:
            while x - unwrapped[-1][0] > 180:
                x -= 360
            while x - unwrapped[-1][0] < -180:
                x += 360
        unwrapped.append((x, y))
    return unwrapped


def polygon_parts(geometry):
    """Collect the polygon pieces of a geometry after longitude clipping.

    Args:
        geometry: Shapely result that may include lower-dimensional pieces.

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


def surface(patch):
    """Build an S-130 surface with its interior rings and dateline splits.

    Args:
        patch: Provider GML polygon patch.

    Returns:
        A Shapely polygon or multipolygon within the WGS84 longitude range.
    """
    exterior = ring(patch.find("gml:exterior/gml:LinearRing/gml:posList", NS))
    holes = []
    middle = sum(p[0] for p in exterior) / len(exterior)
    interiors = patch.findall("gml:interior", NS)
    for interior in interiors:
        position = interior.find("gml:LinearRing/gml:posList", NS)
        hole = ring(position)
        shift = 360 * round((middle - sum(p[0] for p in hole) / len(hole)) / 360)
        holes.append([(x + shift, y) for x, y in hole])
    polygon = Polygon(exterior, holes)
    if polygon.is_empty or not polygon.is_valid:
        raise ValueError("S-130 source surface is empty or invalid")
    if polygon.bounds[0] >= -180 and polygon.bounds[2] <= 180:
        return polygon
    low, _, high, _ = polygon.bounds
    pieces = []
    for turn in range(
        math.ceil((-180 - high) / 360), math.floor((180 - low) / 360) + 1
    ):
        pieces.extend(
            polygon_parts(
                translate(polygon, xoff=360 * turn).intersection(
                    box(-180, -90, 180, 90)
                )
            )
        )
    return unary_union(pieces)


class SeaAreas:
    """Index one S-130 document and reconstruct areas from linked surfaces."""

    def __init__(self, document):
        """Index all identified features and their provider area names.

        Args:
            document: Root element of the parsed S-130 GML.
        """
        self.features = {}
        for element in document.iter():
            ident = element.get(GML_ID)
            if ident:
                if ident in self.features:
                    raise ValueError("duplicate GML feature ID")
                self.features[ident] = element
        self.areas = {
            key: element
            for key, element in self.features.items()
            if element.tag == "{" + NS["s130"] + "}GlobalSeaArea"
        }
        self.mrns = {
            key: element.findtext("s130:featureIdentifier", namespaces=NS)
            for key, element in self.areas.items()
        }
        if any(not value for value in self.mrns.values()):
            raise ValueError("S-130 area has no provider identity")

    def references(self, ident, role):
        """Read the GML IDs linked under an area relation.

        Args:
            ident: ID of the area to inspect.
            role: S-130 relation name such as ``theCollection``.

        Returns:
            Linked IDs in document order.
        """
        return [
            ref.get(XLINK_HREF, "").removeprefix("#")
            for ref in self.areas[ident].findall("s130:" + role, NS)
        ]

    def roots(self):
        """Return area IDs and MRNs for roots of complete provider areas."""
        return {
            ident: self.mrns[ident]
            for ident in self.areas
            if not any(
                self.mrns.get(parent) == self.mrns[ident]
                for parent in self.references(ident, "theComponent")
            )
        }

    def geometry(self, mrn):
        """Reconstruct all surfaces belonging to one provider area.

        Args:
            mrn: Provider identity of the selected area.

        Returns:
            Complete GeoJSON geometry and its root GML ID.

        Raises:
            ValueError: The MRN lacks one complete and valid area.
        """
        roots = [ident for ident, value in self.roots().items() if value == mrn]
        if len(roots) != 1:
            raise ValueError("MRN must identify one complete S-130 area")

        def collect(ident, ancestors=()):
            if ident in ancestors or ident not in self.areas:
                raise ValueError("cyclic or missing S-130 area component")
            patches = self.areas[ident].findall(".//gml:PolygonPatch", NS)
            if patches:
                return [surface(patch) for patch in patches]
            children = self.references(ident, "theCollection")
            if not children or any(self.mrns.get(child) != mrn for child in children):
                raise ValueError(
                    "S-130 collection lacks its complete surface components"
                )
            return [
                part
                for child in children
                for part in collect(child, (*ancestors, ident))
            ]

        result = unary_union(collect(roots[0]))
        value = json.loads(json.dumps(mapping(result), allow_nan=False))
        validate_geometry(value)
        return value, roots[0]


def read_areas(path, *, gml_member, gml_sha256, selections):
    """Read complete S-130 areas from a verified archive.

    Args:
        path: Local path of the verified S-130 archive.
        gml_member: Exact GML member name inside the archive.
        gml_sha256: Expected SHA-256 of the GML member.
        selections: Provider MRNs paired with output feature IDs.

    Returns:
        Features containing the selected areas and their output IDs.
    """
    document = read_document(path, gml_member, gml_sha256)
    reader = SeaAreas(document)
    result = []
    for selection in selections:
        geometry, _ = reader.geometry(selection["source_feature_id"])
        result.append(
            {
                "feature_id": selection["feature_id"],
                "source_feature_id": selection["source_feature_id"],
                "geometry": geometry,
            }
        )
    return result


def s130_areas(
    runtime: Runtime,
    *,
    source_id: SourceId,
    gml_member: NonEmptyText,
    gml_sha256: NonEmptyText,
    selections: list[FeatureIdentity],
):
    """Import complete S-130 sea areas with linked surfaces and holes.

    Args:
        runtime: Import resources and saved recipe snapshot.
        source_id: Catalog ID of the S-130 archive.
        gml_member: Exact GML member name inside the archive.
        gml_sha256: Expected SHA-256 of the GML member.
        selections: Provider MRNs and their output IDs in Neon.

    Returns:
        Saved feature IDs, the local source path, and timings.
    """
    started, timing = time.monotonic(), {}
    path, = acquire_sources(runtime, [source_id], timing=timing)
    features = read_areas(path, gml_member=gml_member, gml_sha256=gml_sha256,
                          selections=selections)
    feature_ids = save_features(runtime, features)
    return feature_result(feature_ids, time.monotonic() - started, source=path,
                          download_seconds=timing.get("download_seconds", 0.0))
