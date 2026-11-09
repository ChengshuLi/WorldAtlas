#!/usr/bin/env python3
"""Recover the two selected Iceland routes from the pinned IHO S-130 ZIP."""
import argparse
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

ARCHIVE_SHA256 = '44997a24a4fe83256cce1ef2b28588f46c9c2b7f1036a78bdb39283c5c0a76de'
GML_SHA256 = '6812d76e9eed51a21732cf9aa34da1f1ff44e05e8dbd28d63589f3d875c14924'
GML_MEMBER = 'S-130/DATASET_FILES/01AA/13001AA_GLOBAL01.gml'
NS = {'s130': 'http://www.iho.int/S130/2.0', 'gml': 'http://www.opengis.net/gml/3.2'}
GML_ID = '{http://www.opengis.net/gml/3.2}id'
XLINK_HREF = '{http://www.w3.org/1999/xlink}href'
EPSG_4326 = 'http://www.opengis.net/def/crs/EPSG/0/4326'
SELECTION = (
    ('local-atlantic-arctic-2', 'M.1505', ('Cape Nansen', 'Straumnes')),
    ('local-atlantic-arctic-3', 'M.1504', ('Gerpir', 'Jan Mayen South Cape')),
)


def extract_routes(path):
    with path.open('rb') as archive:
        if hashlib.file_digest(archive, 'sha256').hexdigest() != ARCHIVE_SHA256:
            raise ValueError('IHO archive SHA-256 mismatch')
        with ZipFile(archive) as source:
            data = source.read(GML_MEMBER)
    if hashlib.sha256(data).hexdigest() != GML_SHA256:
        raise ValueError('IHO GML SHA-256 mismatch')

    document = ElementTree.fromstring(data)
    lines = {line.attrib[GML_ID]: line for line in document.findall('.//s130:ConstructionLine', NS)}
    endpoints, routes = [], []
    for route_id, source_id, names in SELECTION:
        line = lines[source_id]
        if line.findtext('s130:lineType', namespaces=NS) != 'Rhumb Line':
            raise ValueError(f'{source_id} is not a rhumb line')
        positions, = line.findall('.//gml:posList', NS)
        coordinates = positions.text.split()
        if positions.get('srsName') != EPSG_4326 or len(coordinates) < 4 or len(coordinates) % 2:
            raise ValueError(f'{source_id} does not contain latitude/longitude pairs in EPSG:4326')

        # The selected routes run in the reverse direction of their source lines.
        point_ids = [point.attrib[XLINK_HREF].removeprefix('#')
                     for point in line.findall('s130:lineContributingLocation', NS)]
        points = []
        for ordinal, (name, point_id, coordinate) in enumerate(
            zip(names, reversed(point_ids), (coordinates[-2:], coordinates[:2]), strict=True)
        ):
            endpoint_id = f'{route_id}-endpoint-{ordinal}'
            latitude, longitude = coordinate
            endpoints.append({'endpoint_id': endpoint_id, 'name': name, 'latitude': latitude,
                              'longitude': longitude, 'evidence': {'point_id': point_id,
                              'construction_line_id': source_id, 'gml_sha256': GML_SHA256,
                              'archive_sha256': ARCHIVE_SHA256, 'source_axis_order': 'latitude longitude'}})
            points.append({'ordinal': ordinal, 'endpoint_id': endpoint_id})
        routes.append({'route_id': route_id, 'route_type': 'spherical_rhumb',
                       'parameters': {'max_step_km': 0.05}, 'points': points,
                       'evidence': {'construction_line_id': source_id, 'gml_sha256': GML_SHA256}})
    return {'endpoints': endpoints, 'routes': routes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path, help='pinned S-130 ZIP')
    parser.add_argument('--output', required=True, type=Path, help='output JSON for the selected routes')
    args = parser.parse_args()
    args.output.write_text(json.dumps(extract_routes(args.archive), indent=2) + '\n')


if __name__ == '__main__':
    main()
