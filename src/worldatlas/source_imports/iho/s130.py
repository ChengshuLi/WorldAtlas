"""Extract selected rhumb routes and exact endpoints from an IHO S-130 archive."""
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import hashlib
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

NS = {'s130': 'http://www.iho.int/S130/2.0', 'gml': 'http://www.opengis.net/gml/3.2'}
GML_ID = '{http://www.opengis.net/gml/3.2}id'
XLINK_HREF = '{http://www.w3.org/1999/xlink}href'
EPSG_4326 = 'http://www.opengis.net/def/crs/EPSG/0/4326'


def validate_recipe(recipe):
    """Validate shared parameter types, then geographic step and identity relationships."""
    from worldatlas.source_imports.contracts import bind_document
    from worldatlas.source_imports.iho.build_routes import s130_rhumb_routes
    bind_document(s130_rhumb_routes, {key: value for key, value in recipe.items()
                                    if key not in ('recipe_id', 'recipe_version')})
    if not 0 < recipe['max_step_km'] <= 1:
        raise ValueError('max_step_km must be in (0,1]')
    if not recipe['routes']:
        raise ValueError('missing S-130 route selections')
    ids, endpoint_ids = set(), set()
    for route in recipe['routes']:
        if route['route_id'] in ids:
            raise ValueError('duplicate route selection')
        ids.add(route['route_id'])
        selected_ids = route.get('endpoint_ids',
                                 [f"{route['route_id']}-endpoint-{i}" for i in range(2)])
        if len(set(selected_ids)) != 2 or endpoint_ids.intersection(selected_ids):
            raise ValueError('duplicate endpoint IDs')
        endpoint_ids.update(selected_ids)


def coordinate_pair(values):
    """Validate source latitude/longitude decimals without rounding them."""
    try:
        latitude, longitude = (Decimal(value) for value in values)
        if (not latitude.is_finite() or not longitude.is_finite()
                or not -90 < latitude < 90 or not -180 <= longitude <= 180):
            raise ValueError('invalid S-130 coordinate')
        return latitude, longitude
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError('invalid S-130 coordinate') from error


def extract_routes(path, archive_sha256, recipe):
    """Check the source bytes and recover the selected routes in their chosen direction."""
    validate_recipe(recipe)
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
    document = ElementTree.fromstring(data)
    features = {}
    for feature in document.iter():
        ident = feature.get(GML_ID)
        if ident is not None:
            if ident in features:
                raise ValueError('duplicate GML feature ID')
            features[ident] = feature

    endpoints, routes = [], []
    for selected in recipe['routes']:
        source_id, route_id = selected['construction_line_id'], selected['route_id']
        line = features.get(source_id)
        if (line is None or line.tag != f"{{{NS['s130']}}}ConstructionLine"
                or line.findtext('s130:lineType', namespaces=NS) != 'Rhumb Line'):
            raise ValueError(f'{source_id} is not an S-130 rhumb construction line')
        positions = line.findall('.//gml:posList', NS)
        if len(positions) != 1 or positions[0].get('srsName') != EPSG_4326:
            raise ValueError('expected latitude/longitude pairs in EPSG:4326')
        values = (positions[0].text or '').split()
        if len(values) < 4 or len(values) % 2:
            raise ValueError('expected latitude/longitude coordinate pairs')
        coordinates = [values[index:index + 2] for index in range(0, len(values), 2)]
        for pair in coordinates:
            coordinate_pair(pair)
        ends = [coordinates[0], coordinates[-1]]
        if abs(Decimal(ends[0][1]) - Decimal(ends[1][1])) > 180:
            raise ValueError('antimeridian-crossing rhumb unsupported')
        if selected['reverse']:
            ends.reverse()
        extend = selected.get('extend_to_south_grid_edge', False)
        if extend and Decimal(ends[0][1]) != Decimal(ends[1][1]):
            raise ValueError('south-grid extension requires a meridian')
        southern = min(range(2), key=lambda index: Decimal(ends[index][0]))

        # Some source line endpoints have no separate ContributingPoint record.
        # Source point and line coordinates can differ in their final decimal digit.
        contributing = []
        for ref in line.findall('s130:lineContributingLocation', NS):
            point_id = ref.attrib[XLINK_HREF].removeprefix('#')
            point = features.get(point_id)
            position = None if point is None else point.find('.//gml:pos', NS)
            if position is None or position.get('srsName') != EPSG_4326:
                raise ValueError('missing contributing point coordinates')
            contributing.append((point_id, coordinate_pair((position.text or '').split())))

        points = []
        for ordinal, (name, pair) in enumerate(zip(selected['endpoint_names'], ends, strict=True)):
            latitude, longitude = pair
            numeric = coordinate_pair(pair)
            matches = [ident for ident, location in contributing
                       if all(abs(a - b) <= Decimal('1e-12')
                              for a, b in zip(numeric, location, strict=True))]
            if len(matches) > 1:
                raise ValueError('ambiguous contributing endpoint')
            endpoint_id = selected.get('endpoint_ids',
                                       [f'{route_id}-endpoint-{i}' for i in range(2)])[ordinal]
            evidence = {'construction_line_id': source_id, 'gml_sha256': recipe['gml_sha256'],
                        'archive_sha256': archive_sha256, 'source_axis_order': 'latitude longitude'}
            if matches:
                evidence['point_id'] = matches[0]
            fractions = [Fraction(value) for value in pair]
            derivation = dict(method='source_decimal_exact_rational', **{
                axis + '_fraction': [value.numerator, value.denominator]
                for axis, value in zip(('latitude', 'longitude'), fractions, strict=True)})
            if extend and ordinal == southern:
                derivation['method'] = 'grid_south_edge'
            endpoints.append(dict(endpoint_id=endpoint_id, name=name, latitude=latitude,
                                  longitude=longitude, derivation=derivation, evidence=evidence))
            points.append(dict(ordinal=ordinal, endpoint_id=endpoint_id))
        routes.append(dict(route_id=route_id, route_type='spherical_rhumb',
                           parameters={'max_step_km': recipe['max_step_km']}, points=points,
                           evidence={'construction_line_id': source_id,
                                     'gml_sha256': recipe['gml_sha256']}))
    return dict(endpoints=endpoints, routes=routes)
