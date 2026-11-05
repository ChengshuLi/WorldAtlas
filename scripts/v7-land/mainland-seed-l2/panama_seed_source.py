"""Bind the selected Panama boundary to its archived OSM input."""
from pathlib import Path

from osm_source_handoff import verified_geometry

BOUNDARY = 'panama_colombia_osm_admin_boundary'
SOURCE = ('osm-panama-current-way-full-bundle', 'capture-20261105-04fe1adb295e')


def bind(boundaries, catalog, pin):
    """Return boundary records with a checked source-derived Panama line.

    The caller authenticates the selected Neon export and the source catalog.
    A source pin is mandatory whenever this boundary is selected. No boundary
    hash, route, or region is replaced when a mismatch occurs.
    """
    key = ('boundary', BOUNDARY)
    if key not in boundaries:
        if pin is not None:
            raise ValueError('Panama archive supplied without selected boundary')
        return boundaries, None
    if not isinstance(pin, dict) or set(pin) != {'path', 'sha256'}:
        raise ValueError('selected Panama boundary requires a pinned OSM archive')
    record = boundaries[key]
    source = catalog.get(SOURCE)
    refs = record.get('qualified_source_refs', [])
    if not any((r.get('source_id'), r.get('version')) == SOURCE for r in refs):
        raise ValueError('selected boundary lacks Panama source link')
    if not source or source.get('kind') != 'raw' or source.get('sha256') != pin['sha256']:
        raise ValueError('Panama archive does not match selected source catalog')
    if not isinstance(source.get('size_bytes'), int) or Path(pin['path']).stat().st_size != source['size_bytes']:
        raise ValueError('Panama archive size mismatch')
    geom = verified_geometry(pin['path'], pin['sha256'], record['geometry_sha256'])
    result = dict(boundaries)
    result[key] = {**record, 'geometry': geom}
    trace = {'boundary_id': BOUNDARY, 'source_id': SOURCE[0], 'source_version': SOURCE[1],
             'archive_sha256': pin['sha256'], 'geometry_sha256': record['geometry_sha256'],
             'vertices': len(geom['coordinates']), 'method': 'osm-way-full-chain-v1'}
    return result, trace
