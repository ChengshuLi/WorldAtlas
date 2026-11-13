"""Read complete S-130 sea areas, preserving source surfaces and collection identity."""
import hashlib
import json
import math
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

from shapely.affinity import translate
from shapely.geometry import Polygon, box, mapping
from shapely.ops import unary_union

from worldatlas.source_imports.features.geometry import validate_geometry
from worldatlas.source_imports.iho.s130 import NS, GML_ID, XLINK_HREF, EPSG_4326


def read_document(path, archive_sha256, member, gml_sha256):
    with Path(path).open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != archive_sha256:
            raise ValueError('IHO archive SHA-256 mismatch')
    with ZipFile(path) as archive:
        if archive.namelist().count(member) != 1:
            raise ValueError('expected one selected IHO GML member')
        raw = archive.read(member)
    if hashlib.sha256(raw).hexdigest() != gml_sha256:
        raise ValueError('IHO GML SHA-256 mismatch')
    return ElementTree.fromstring(raw)


def ring(position):
    if position is None or position.get('srsName') != EPSG_4326:
        raise ValueError('expected S-130 latitude/longitude in EPSG:4326')
    values = list(map(float, (position.text or '').split()))
    if len(values) < 8 or len(values) % 2:
        raise ValueError('invalid S-130 ring coordinates')
    points = [(values[i + 1], values[i]) for i in range(0, len(values), 2)]
    if (points[0] != points[-1] or any(not math.isfinite(x) or not math.isfinite(y)
            or not -180 <= x <= 180 or not -90 <= y <= 90 for x, y in points)):
        raise ValueError('invalid or open S-130 ring')
    # Add complete turns only when the source crosses the antimeridian.
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
    if geometry.is_empty:
        return []
    if geometry.geom_type == 'Polygon':
        return [geometry]
    if hasattr(geometry, 'geoms'):
        return [part for child in geometry.geoms for part in polygon_parts(child)]
    return []


def surface(patch):
    exterior = ring(patch.find('gml:exterior/gml:LinearRing/gml:posList', NS))
    holes = []
    middle = sum(p[0] for p in exterior) / len(exterior)
    interiors = patch.findall('gml:interior', NS)
    for interior in interiors:
        position = interior.find('gml:LinearRing/gml:posList', NS)
        hole = ring(position)
        shift = 360 * round((middle - sum(p[0] for p in hole) / len(hole)) / 360)
        holes.append([(x + shift, y) for x, y in hole])
    polygon = Polygon(exterior, holes)
    if polygon.is_empty or not polygon.is_valid:
        raise ValueError('S-130 source surface is empty or invalid')
    if polygon.bounds[0] >= -180 and polygon.bounds[2] <= 180:
        return polygon
    low, _, high, _ = polygon.bounds
    pieces = []
    for turn in range(math.ceil((-180 - high) / 360), math.floor((180 - low) / 360) + 1):
        pieces.extend(polygon_parts(translate(polygon, xoff=360 * turn)
                                   .intersection(box(-180, -90, 180, 90))))
    return unary_union(pieces)


class SeaAreas:
    def __init__(self, document):
        self.features = {}
        for element in document.iter():
            ident = element.get(GML_ID)
            if ident:
                if ident in self.features:
                    raise ValueError('duplicate GML feature ID')
                self.features[ident] = element
        self.areas = {key: element for key, element in self.features.items()
                      if element.tag == '{' + NS['s130'] + '}GlobalSeaArea'}
        self.mrns = {key: element.findtext('s130:featureIdentifier', namespaces=NS)
                     for key, element in self.areas.items()}
        if any(not value for value in self.mrns.values()):
            raise ValueError('S-130 area has no provider identity')

    def references(self, ident, role):
        return [ref.get(XLINK_HREF, '').removeprefix('#')
                for ref in self.areas[ident].findall('s130:' + role, NS)]

    def roots(self):
        return {ident: self.mrns[ident] for ident in self.areas if not any(
            self.mrns.get(parent) == self.mrns[ident]
            for parent in self.references(ident, 'theComponent'))}

    def parents(self, mrn):
        """Return provider parent MRNs, including ancestors through multipart areas."""
        roots = [ident for ident, value in self.roots().items() if value == mrn]
        if len(roots) != 1:
            raise ValueError('MRN must identify one complete S-130 area')

        def visit(ident, ancestors=()):
            if ident not in self.areas or ident in ancestors:
                raise ValueError('cyclic or missing S-130 parent')
            result = set()
            for parent in self.references(ident, 'theComponent'):
                if parent not in self.areas:
                    raise ValueError('missing S-130 parent')
                result.add(self.mrns[parent])
                result.update(visit(parent, (*ancestors, ident)))
            return result

        return sorted(visit(roots[0]) - {mrn})

    def geometry(self, mrn):
        roots = [ident for ident, value in self.roots().items() if value == mrn]
        if len(roots) != 1:
            raise ValueError('MRN must identify one complete S-130 area')
        def collect(ident, ancestors=()):
            if ident in ancestors or ident not in self.areas:
                raise ValueError('cyclic or missing S-130 area component')
            patches = self.areas[ident].findall('.//gml:PolygonPatch', NS)
            if patches:
                return [surface(patch) for patch in patches]
            children = self.references(ident, 'theCollection')
            if not children or any(self.mrns.get(child) != mrn for child in children):
                raise ValueError('S-130 collection lacks its complete surface components')
            return [part for child in children for part in collect(child, (*ancestors, ident))]
        result = unary_union(collect(roots[0]))
        value = json.loads(json.dumps(mapping(result), allow_nan=False))
        validate_geometry(value)
        return value, roots[0]


def read_areas(path, source, recipe):
    document = read_document(path, source['sha256'], recipe['gml_member'], recipe['gml_sha256'])
    reader = SeaAreas(document)
    result = []
    for selection in recipe['selections']:
        geometry, ident = reader.geometry(selection['source_feature_id'])
        result.append({'feature_id': selection['feature_id'],
                       'source_feature_id': selection['source_feature_id'], 'geometry': geometry,
                       'evidence': {'gml_feature_id': ident, 'gml_sha256': recipe['gml_sha256'],
                                    'source_parent_feature_ids': reader.parents(selection['source_feature_id']),
                                    'representation': 'provider_encoded_surface'}})
    return result
