"""Assemble archived OSM ways and optional source-backed offshore continuations."""

from worldatlas.source_imports.contracts import NonEmptyText, Runtime, SourceId
from worldatlas.source_imports.osm.ways import assemble_archive
from worldatlas.source_imports.atlas_sources.catalog import catalog_source, download_source
from worldatlas.source_imports.features.geometry import geometry_hash, save_features, validate_geometry
from worldatlas.source_imports.traces.geodesic import construct


def osm_way_chain(
    runtime: Runtime, *, source_id: SourceId, feature_id: NonEmptyText,
    source_feature_id: NonEmptyText, basis: NonEmptyText,
    before: list[tuple[float, float]] | None = None,
    after: list[tuple[float, float]] | None = None,
    max_step_metres: float = 1000,
    evidence_source_ids: list[SourceId] | None = None,
):
    """Preserve an archived OSM chain and join selected offshore points geodesically."""
    with runtime.connect() as database:
        source = catalog_source(database, source_id)
        for ident in evidence_source_ids or []:
            catalog_source(database, ident)
        archive = download_source(runtime.storage, source, runtime.work_dir)
        geometry = assemble_archive(archive, source['sha256'])
        points = geometry['coordinates']
        if before:
            prefix = construct([*before, points[0]], max_step_metres)['coordinates']
            points = [*prefix[:-1], *points]
        if after:
            suffix = construct([points[-1], *after], max_step_metres)['coordinates']
            points = [*points, *suffix[1:]]
        geometry = dict(type='LineString', coordinates=points)
        line = validate_geometry(geometry)
        if not line.is_simple or line.is_closed:
            raise ValueError('assembled boundary must be open without crossings or retracing')
        if (runtime.expected_geometry_sha256 is not None
                and geometry_hash(geometry) != runtime.expected_geometry_sha256):
            raise ValueError('assembled boundary differs from the expected geometry checksum')
        with runtime.saving(database):
            hashes = save_features(database, [dict(feature_id=feature_id,
                source_feature_id=source_feature_id, geometry=geometry)],
                dict(recipe_id=runtime.recipe_id))
    return dict(feature_id=feature_id, vertices=len(points), sha256=hashes[feature_id])
