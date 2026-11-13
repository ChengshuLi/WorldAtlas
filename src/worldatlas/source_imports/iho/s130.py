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
    """Check the selections needed by this S-130 construction method."""
    if not isinstance(recipe, dict):
        raise ValueError('invalid S-130 construction record')
    strings = ('source_id', 'source_version', 'gml_member', 'gml_sha256', 'basis')
    fields = set(strings) | {'method', 'max_step_km', 'routes'}
    if set(recipe) - {'recipe_id', 'recipe_version'} != fields:
        raise ValueError('invalid S-130 construction record fields')
    if recipe.get('method') != 's130_rhumb_routes':
        raise ValueError('unsupported S-130 construction method')
    if any(not isinstance(recipe.get(key), str) or not recipe[key].strip() for key in strings):
        raise ValueError('invalid S-130 construction record')
    step = recipe.get('max_step_km')
    if type(step) not in (float, int) or not 0 < step <= 1:
        raise ValueError('max_step_km must be in (0,1]')
    routes = recipe.get('routes')
    if not isinstance(routes, list) or not routes:
        raise ValueError('missing S-130 route selections')
    ids, endpoint_ids = set(), set()
    for route in routes:
        required = {'route_id', 'construction_line_id', 'reverse', 'endpoint_names'}
        if (not isinstance(route, dict)
                or not required <= set(route) <= required | {'extend_to_south_grid_edge', 'endpoint_ids'}
                or any(not isinstance(route.get(key), str) or not route[key].strip()
                       for key in ('route_id', 'construction_line_id'))
                or type(route.get('reverse')) is not bool
                or type(route.get('extend_to_south_grid_edge', False)) is not bool
                or not isinstance(route.get('endpoint_names'), list)
                or len(route['endpoint_names']) != 2
                or any(not isinstance(name, str) or not name.strip() for name in route['endpoint_names'])):
            raise ValueError('invalid S-130 route selection')
        if route['route_id'] in ids:
            raise ValueError('duplicate route selection')
        ids.add(route['route_id'])
        selected_ids = route.get('endpoint_ids',
                                 [f"{route['route_id']}-endpoint-{i}" for i in range(2)])
        if (not isinstance(selected_ids, list) or len(selected_ids) != 2
                or any(not isinstance(ident, str) or not ident.strip() for ident in selected_ids)
                or len(set(selected_ids)) != 2 or endpoint_ids.intersection(selected_ids)):
            raise ValueError('invalid or duplicate endpoint IDs')
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
