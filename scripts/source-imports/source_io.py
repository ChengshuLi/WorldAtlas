"""Save source-derived mainland boundaries and refresh their assembled regions."""
import hashlib
import json

from features.geometry import storage_geometry


def save_boundary(database, revision, boundary_id, geometry, provenance, sources):
    """Save a complete mainland boundary and its raw-input links atomically."""
    from psycopg.types.json import Jsonb

    geometry = storage_geometry(geometry)
    raw = json.dumps(geometry, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    digest = hashlib.sha256(raw).hexdigest()
    selected = {}
    for source in sources:
        key = (source['source_id'], source['version'])
        relationship = source.get('relationship', 'construction_input')
        if key not in selected or relationship == 'construction_input':
            selected[key] = relationship
    with database.transaction():
        # Boundaries of one region may be saved by different workers. Serialize
        # their short writes so each polygon hash includes every committed edit.
        database.execute(
            'SELECT r.region_id FROM atlas.decision_mainland_seed_regions r '
            'WHERE r.revision=%s AND EXISTS ('
            'SELECT 1 FROM atlas.decision_mainland_region_segments s '
            'WHERE s.revision=r.revision AND s.region_id=r.region_id AND s.boundary_id=%s) '
            'ORDER BY r.region_id FOR UPDATE',
            (revision, boundary_id),
        ).fetchall()
        old = database.execute(
            "SELECT jsonb_array_length(geometry->'coordinates') "
            'FROM atlas.decision_mainland_boundaries WHERE revision=%s AND boundary_id=%s',
            (revision, boundary_id),
        ).fetchone()
        count = len(geometry['coordinates'])
        if old and old[0] != count:
            slices = database.execute(
                'SELECT start_index,end_index FROM atlas.decision_mainland_region_segments '
                "WHERE revision=%s AND boundary_id=%s AND kind='boundary'",
                (revision, boundary_id),
            ).fetchall()
            if any(first != 0 or last != old[0] for first, last in slices):
                raise ValueError('partial region slices need source-backed joins before changing boundary vertices')
            database.execute(
                'UPDATE atlas.decision_mainland_region_segments SET end_index=%s '
                "WHERE revision=%s AND boundary_id=%s AND kind='boundary'",
                (count, revision, boundary_id),
            )
        database.execute(
            'INSERT INTO atlas.decision_mainland_boundaries '
            '(revision,boundary_id,method,execution_status,geometry,geometry_sha256,'
            'geometry_hash_method,coordinate_reference,provenance) '
            "VALUES (%s,%s,'stored_linestring_v1','selected_for_research',%s,%s,"
            "'binary64-sorted-compact-geojson-v1','OGC:CRS84',%s) "
            'ON CONFLICT (revision,boundary_id) DO UPDATE SET '
            'geometry=EXCLUDED.geometry,geometry_sha256=EXCLUDED.geometry_sha256,'
            'provenance=atlas.decision_mainland_boundaries.provenance || EXCLUDED.provenance',
            (revision, boundary_id, Jsonb(geometry), digest, Jsonb(provenance)),
        )
        database.execute(
            'DELETE FROM atlas.decision_mainland_boundary_sources '
            "WHERE revision=%s AND boundary_id=%s AND relationship='construction_input'",
            (revision, boundary_id),
        )
        for (source_id, version), relationship in sorted(selected.items()):
            database.execute(
                'INSERT INTO atlas.decision_mainland_boundary_sources '
                '(revision,boundary_id,source_id,source_version,relationship) '
                'VALUES (%s,%s,%s,%s,%s) '
                'ON CONFLICT (revision,boundary_id,source_id,source_version) DO UPDATE SET '
                "relationship=CASE WHEN EXCLUDED.relationship='construction_input' THEN "
                'EXCLUDED.relationship ELSE atlas.decision_mainland_boundary_sources.relationship END',
                (revision, boundary_id, source_id, version, relationship),
            )
        _refresh_regions(database, revision, boundary_id)
    return digest


def _refresh_regions(database, revision, boundary_id):
    """Keep existing derived region hashes consistent with the newly saved line."""
    from shapely.geometry import Polygon

    regions = database.execute(
        'SELECT DISTINCT region_id FROM atlas.decision_mainland_region_segments '
        'WHERE revision=%s AND boundary_id=%s', (revision, boundary_id),
    ).fetchall()
    for (region_id,) in regions:
        rows = database.execute(
            'SELECT s.start_index,s.end_index,s.reverse,coalesce(b.geometry,r.geometry) '
            'FROM atlas.decision_mainland_region_segments s '
            "LEFT JOIN atlas.decision_mainland_boundaries b ON s.kind='boundary' "
            'AND (b.revision,b.boundary_id)=(s.revision,s.boundary_id) '
            "LEFT JOIN atlas.decision_mainland_closure_routes r ON s.kind='route' "
            'AND (r.revision,r.route_id)=(s.revision,s.route_id) '
            'WHERE s.revision=%s AND s.region_id=%s ORDER BY s.ordinal',
            (revision, region_id),
        ).fetchall()
        ring = []
        for first, last, reverse, geometry in rows:
            if geometry is None or not 0 <= first < last <= len(geometry['coordinates']):
                raise ValueError('region references a missing line or invalid slice')
            points = [[float(x), float(y)] for x, y in geometry['coordinates'][first:last]]
            if reverse:
                points.reverse()
            if len(points) < 2 or (ring and ring[-1] != points[0]):
                raise ValueError('updated boundary does not join its region exactly')
            ring.extend(points if not ring else points[1:])
        if len(ring) < 4 or ring[0] != ring[-1]:
            raise ValueError('updated boundary does not form a closed region')
        if not Polygon(ring).is_valid:
            raise ValueError('updated boundary creates an invalid region polygon')
        polygon = {'type': 'Polygon', 'coordinates': [ring]}
        raw = json.dumps(polygon, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        database.execute(
            'UPDATE atlas.decision_mainland_seed_regions SET geometry_sha256=%s '
            'WHERE revision=%s AND region_id=%s',
            (hashlib.sha256(raw).hexdigest(), revision, region_id),
        )
