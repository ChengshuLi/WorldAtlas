"""Read source coordinates and declared rhumb interpolation from an S-130 archive."""
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

from worldatlas.source_imports.geodesy import spherical_rhumb_points

NS = {'s130': 'http://www.iho.int/S130/2.0', 'gml': 'http://www.opengis.net/gml/3.2'}
GML_ID = '{http://www.opengis.net/gml/3.2}id'
EPSG_4326 = 'http://www.opengis.net/def/crs/EPSG/0/4326'


def coordinate_pair(values):
    """Read provider latitude/longitude decimals without imposing coordinate rounding."""
    try:
        latitude, longitude = (Decimal(value) for value in values)
        if (not latitude.is_finite() or not longitude.is_finite()
                or not -90 < latitude < 90 or not -180 <= longitude <= 180):
            raise ValueError('invalid S-130 coordinate')
        return latitude, longitude
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError('invalid S-130 coordinate') from error


def extract_routes(path, archive_sha256, recipe):
    """Return selected line features; source interpolation belongs in import, not map building."""
    from worldatlas.source_imports.contracts import bind_document
    from worldatlas.source_imports.iho.build_routes import s130_rhumb_routes
    bind_document(s130_rhumb_routes, {k:v for k,v in recipe.items() if k != 'recipe_id'})
    if not recipe['routes'] or len({r['feature_id'] for r in recipe['routes']}) != len(recipe['routes']):
        raise ValueError('selected S-130 feature IDs must be nonempty and distinct')
    with Path(path).open('rb') as archive:
        if hashlib.file_digest(archive, 'sha256').hexdigest() != archive_sha256:
            raise ValueError('IHO archive SHA-256 mismatch')
        with ZipFile(archive) as source:
            members = [entry for entry in source.infolist() if entry.filename == recipe['gml_member']]
            if len(members) != 1 or members[0].is_dir():
                raise ValueError('expected one GML archive member')
            data = source.read(members[0])
    if hashlib.sha256(data).hexdigest() != recipe['gml_sha256']:
        raise ValueError('IHO GML SHA-256 mismatch')
    features = {}
    for feature in ElementTree.fromstring(data).iter():
        ident = feature.get(GML_ID)
        if ident is not None:
            if ident in features:
                raise ValueError('duplicate GML feature ID')
            features[ident] = feature
    result = []
    for selected in recipe['routes']:
        ident = selected['construction_line_id']
        line = features.get(ident)
        if (line is None or line.tag != f"{{{NS['s130']}}}ConstructionLine"
                or line.findtext('s130:lineType', namespaces=NS) != 'Rhumb Line'):
            raise ValueError(f'{ident} is not an S-130 rhumb construction line')
        positions = line.findall('.//gml:posList', NS)
        if len(positions) != 1 or positions[0].get('srsName') != EPSG_4326:
            raise ValueError('expected latitude/longitude pairs in EPSG:4326')
        values = (positions[0].text or '').split()
        if len(values) < 4 or len(values) % 2:
            raise ValueError('expected latitude/longitude coordinate pairs')
        coordinates = [coordinate_pair(values[i:i+2]) for i in range(0,len(values),2)]
        # Preserve every provider vertex and its declared interpolation.
        ends = [[float(lon),float(lat)] for lat,lon in coordinates]
        if selected['reverse']:
            ends.reverse()
        sampled = spherical_rhumb_points(ends, recipe['max_step_km'])
        result.append(dict(feature_id=selected['feature_id'], source_feature_id=ident,
                           geometry=dict(type='LineString', coordinates=[list(p) for p in sampled])))
    return result
