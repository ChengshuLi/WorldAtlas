"""Save source-derived boundaries and validate their assembled regions atomically."""
from worldatlas.source_imports.features.geometry import geometry_hash, storage_geometry, validate_geometry


def save_boundary(database, boundary_id, geometry, provenance, sources, *, construction=None):
    """Save a complete mainland boundary and its raw-input links atomically."""
    from psycopg.types.json import Jsonb

    line = validate_geometry(geometry)
    if line.geom_type != 'LineString' or not line.is_simple:
        raise ValueError('boundary needs a simple LineString')
    geometry = storage_geometry(geometry)
    digest = geometry_hash(geometry)
    construction_id = construction
    selected = {}
    for source in sources:
        key = source['source_id']
        relationship = source.get('relationship', 'construction_input')
        if key not in selected or relationship == 'construction_input':
            selected[key] = relationship
    with database.transaction():
        # Boundaries of one region may be saved by different workers. Serialize
        # their short writes so polygon validation includes every committed edit.
        database.execute(
            'SELECT r.region_id FROM atlas.decision_mainland_seed_regions r '
            'WHERE EXISTS ('
            'SELECT 1 FROM atlas.decision_mainland_region_segments s '
            'WHERE s.region_id=r.region_id AND s.boundary_id=%s) '
            'ORDER BY r.region_id FOR UPDATE',
            (boundary_id,),
        ).fetchall()
        database.execute(
            'INSERT INTO atlas.decision_mainland_boundaries '
            '(boundary_id,geometry,geometry_sha256,'
            'coordinate_reference,provenance,construction_id) '
            "VALUES (%s,%s,%s,'OGC:CRS84',%s,%s) "
            'ON CONFLICT (boundary_id) DO UPDATE SET '
            'geometry=EXCLUDED.geometry,geometry_sha256=EXCLUDED.geometry_sha256,'
            'construction_id=EXCLUDED.construction_id,'
            'provenance=atlas.decision_mainland_boundaries.provenance || EXCLUDED.provenance',
            (boundary_id, Jsonb(geometry), digest, Jsonb(provenance), construction_id),
        )
        database.execute(
            'DELETE FROM atlas.decision_mainland_boundary_sources '
            "WHERE boundary_id=%s AND relationship='construction_input'",
            (boundary_id,),
        )
        for source_id, relationship in sorted(selected.items()):
            database.execute(
                'INSERT INTO atlas.decision_mainland_boundary_sources '
                '(boundary_id,source_id,relationship) '
                'VALUES (%s,%s,%s) '
                'ON CONFLICT (boundary_id,source_id) DO UPDATE SET '
                "relationship=CASE WHEN EXCLUDED.relationship='construction_input' THEN "
                'EXCLUDED.relationship ELSE atlas.decision_mainland_boundary_sources.relationship END',
                (boundary_id, source_id, relationship),
            )
        _validate_regions(database, boundary_id)
    return digest


def _validate_regions(database, boundary_id):
    """Reject edits that break a selected region's joins or polygon validity."""
    from shapely.geometry import Polygon

    regions = database.execute(
        'SELECT DISTINCT region_id FROM atlas.decision_mainland_region_segments '
        'WHERE boundary_id=%s', (boundary_id,),
    ).fetchall()
    for (region_id,) in regions:
        rows = database.execute(
            'SELECT s.reverse,coalesce(b.geometry,r.geometry) '
            'FROM atlas.decision_mainland_region_segments s '
            "LEFT JOIN atlas.decision_mainland_boundaries b ON s.kind='boundary' "
            'AND b.boundary_id=s.boundary_id '
            "LEFT JOIN atlas.decision_mainland_closure_routes r ON s.kind='route' "
            'AND r.route_id=s.route_id '
            'WHERE s.region_id=%s ORDER BY s.ordinal',
            (region_id,),
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
