"""Save source-derived boundaries and validate their assembled regions atomically."""
from features.geometry import geometry_hash, storage_geometry, validate_geometry


def save_boundary(database, revision, boundary_id, geometry, provenance, sources, *, construction=None):
    """Save a complete mainland boundary and its raw-input links atomically."""
    from psycopg.types.json import Jsonb

    line = validate_geometry(geometry)
    if line.geom_type != 'LineString' or not line.is_simple:
        raise ValueError('boundary needs a simple LineString')
    geometry = storage_geometry(geometry)
    digest = geometry_hash(geometry)
    construction_id, construction_version = construction or (None, None)
    selected = {}
    for source in sources:
        key = (source['source_id'], source['version'])
        relationship = source.get('relationship', 'construction_input')
        if key not in selected or relationship == 'construction_input':
            selected[key] = relationship
    with database.transaction():
        # Boundaries of one region may be saved by different workers. Serialize
        # their short writes so polygon validation includes every committed edit.
        database.execute(
            'SELECT r.region_id FROM atlas.decision_mainland_seed_regions r '
            'WHERE r.revision=%s AND EXISTS ('
            'SELECT 1 FROM atlas.decision_mainland_region_segments s '
            'WHERE s.revision=r.revision AND s.region_id=r.region_id AND s.boundary_id=%s) '
            'ORDER BY r.region_id FOR UPDATE',
            (revision, boundary_id),
        ).fetchall()
        database.execute(
            'INSERT INTO atlas.decision_mainland_boundaries '
            '(revision,boundary_id,geometry,geometry_sha256,'
            'coordinate_reference,provenance,construction_id,construction_version) '
            "VALUES (%s,%s,%s,%s,'OGC:CRS84',%s,%s,%s) "
            'ON CONFLICT (revision,boundary_id) DO UPDATE SET '
            'geometry=EXCLUDED.geometry,geometry_sha256=EXCLUDED.geometry_sha256,'
            'construction_id=EXCLUDED.construction_id,construction_version=EXCLUDED.construction_version,'
            'provenance=atlas.decision_mainland_boundaries.provenance || EXCLUDED.provenance',
            (revision, boundary_id, Jsonb(geometry), digest, Jsonb(provenance),
             construction_id, construction_version),
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
        _validate_regions(database, revision, boundary_id)
    return digest


def _validate_regions(database, revision, boundary_id):
    """Reject edits that break a selected region's joins or polygon validity."""
    from shapely.geometry import Polygon

    regions = database.execute(
        'SELECT DISTINCT region_id FROM atlas.decision_mainland_region_segments '
        'WHERE revision=%s AND boundary_id=%s', (revision, boundary_id),
    ).fetchall()
    for (region_id,) in regions:
        rows = database.execute(
            'SELECT s.reverse,coalesce(b.geometry,r.geometry) '
            'FROM atlas.decision_mainland_region_segments s '
            "LEFT JOIN atlas.decision_mainland_boundaries b ON s.kind='boundary' "
            'AND (b.revision,b.boundary_id)=(s.revision,s.boundary_id) '
            "LEFT JOIN atlas.decision_mainland_closure_routes r ON s.kind='route' "
            'AND (r.revision,r.route_id)=(s.revision,s.route_id) '
            'WHERE s.revision=%s AND s.region_id=%s ORDER BY s.ordinal',
            (revision, region_id),
        ).fetchall()
        ring = []
        for reverse, geometry in rows:
            if geometry is None:
                raise ValueError('region references a missing line')
            points = [[float(x), float(y)] for x, y in geometry['coordinates']]
            if reverse:
                points.reverse()
            if len(points) < 2 or (ring and ring[-1] != points[0]):
                raise ValueError('updated boundary does not join its region exactly')
            ring.extend(points if not ring else points[1:])
        if len(ring) < 4 or ring[0] != ring[-1]:
            raise ValueError('updated boundary does not form a closed region')
        if not Polygon(ring).is_valid:
            raise ValueError('updated boundary creates an invalid region polygon')
