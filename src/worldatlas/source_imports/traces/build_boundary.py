"""Build and save one final boundary from a construction record in Neon."""

from psycopg.types.json import Jsonb
from typing import Any

from worldatlas.source_imports.contracts import NonEmptyText, Runtime

from worldatlas.source_imports.atlas_sources.catalog import catalog_source
from worldatlas.source_imports.features.geometry import geometry_hash, storage_geometry
from worldatlas.source_imports.traces.curve import construct


def smooth_latitude_trace(runtime: Runtime, *, source_id: NonEmptyText, source_version: NonEmptyText,
                          line_id: NonEmptyText, basis: NonEmptyText,
                          points: list[tuple[float, float]], step_latitude_degrees: float,
                          smoothing_latitude_degrees: float,
                          source_location: dict[str, Any] | str | None = None):
    """Interpolate and smooth ordered source-figure points, retaining endpoints."""
    with runtime.connect() as database, database.transaction():
        source = catalog_source(database, source_id, source_version)
        geometry = construct(points, step_latitude_degrees, smoothing_latitude_degrees)
        geometry = storage_geometry(geometry)
        digest = geometry_hash(geometry)
        if runtime.expected_geometry_sha256 is not None and digest != runtime.expected_geometry_sha256:
            raise ValueError('expected geometry SHA-256 mismatch')
        provenance = {
            'basis': basis,
        }
        database.execute(
            'INSERT INTO atlas.geographic_line_observations '
            '(line_id,source_id,source_version,geometry,geometry_sha256,'
            'coordinate_reference,provenance,construction_id,construction_version) '
            "VALUES (%s,%s,%s,%s,%s,'OGC:CRS84',%s,%s,%s) ON CONFLICT (line_id) "
            'DO UPDATE SET source_id=EXCLUDED.source_id,source_version=EXCLUDED.source_version,'
            'geometry=EXCLUDED.geometry,geometry_sha256=EXCLUDED.geometry_sha256,'
            'construction_id=EXCLUDED.construction_id,construction_version=EXCLUDED.construction_version,'
            'provenance=atlas.geographic_line_observations.provenance || EXCLUDED.provenance',
            (line_id, source['source_id'], source['version'], Jsonb(geometry),
             digest, Jsonb(provenance), runtime.recipe_id, runtime.version),
        )

    return dict(line_id=line_id, vertices=len(geometry['coordinates']), sha256=digest)
