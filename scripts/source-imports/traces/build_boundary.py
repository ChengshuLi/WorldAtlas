"""Build and save one final boundary from a construction record in Neon."""

from psycopg.types.json import Jsonb

from atlas_sources.catalog import catalog_source, read_recipe
from features.geometry import geometry_hash, storage_geometry
from traces.curve import construct


def build_boundary(database, recipe_id, recipe_version, expected_geometry_sha256=None):
    """Read the source and chosen points, construct the curve, and save it together."""
    with database.transaction():
        recipe = read_recipe(database, recipe_id, recipe_version)
        if recipe.get('method') != 'smooth_latitude_trace':
            raise ValueError('unsupported traced-boundary method')
        if any(not isinstance(recipe.get(key), str) or not recipe[key].strip()
               for key in ('source_id', 'source_version', 'line_id', 'basis')):
            raise ValueError('invalid traced-boundary construction record')
        source = catalog_source(database, recipe['source_id'], recipe['source_version'])
        geometry = construct(recipe.get('points'), recipe.get('step_latitude_degrees'),
                             recipe.get('smoothing_latitude_degrees'))
        geometry = storage_geometry(geometry)
        digest = geometry_hash(geometry)
        if expected_geometry_sha256 is not None and digest != expected_geometry_sha256:
            raise ValueError('expected geometry SHA-256 mismatch')
        provenance = {
            'basis': recipe['basis'],
            'method': recipe['method'],
            'source_refs': [dict(source_id=source['source_id'], version=source['version'],
                                 sha256=source['sha256'])],
            'construction': dict(processor='traces.curve.construct', recipe_id=recipe_id,
                                 recipe_version=recipe_version),
        }
        database.execute(
            'INSERT INTO atlas.geographic_line_observations '
            '(line_id,source_id,source_version,geometry,geometry_sha256,'
            'coordinate_reference,provenance,status) '
            "VALUES (%s,%s,%s,%s,%s,'OGC:CRS84',%s,'research') ON CONFLICT (line_id) "
            'DO UPDATE SET source_id=EXCLUDED.source_id,source_version=EXCLUDED.source_version,'
            'geometry=EXCLUDED.geometry,geometry_sha256=EXCLUDED.geometry_sha256,'
            'provenance=atlas.geographic_line_observations.provenance || EXCLUDED.provenance',
            (recipe['line_id'], source['source_id'], source['version'], Jsonb(geometry),
             digest, Jsonb(provenance)),
        )

    return dict(line_id=recipe['line_id'], vertices=len(geometry['coordinates']), sha256=digest)
