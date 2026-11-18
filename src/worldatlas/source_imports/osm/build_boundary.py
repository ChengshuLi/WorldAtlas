"""Build boundary lines from cataloged OpenStreetMap way responses."""

from worldatlas.source_imports.contracts import NonEmptyText, Runtime, SourceId
from worldatlas.source_imports.osm.ways import assemble
from worldatlas.source_imports.atlas_sources.catalog import catalog_source, download_source
from worldatlas.source_imports.features.geometry import geometry_hash, save_features


def osm_way_chain(
    runtime: Runtime, *, way_source_ids: list[SourceId], start_node_id: int,
    feature_id: NonEmptyText, basis: NonEmptyText,
    evidence_source_ids: list[SourceId] | None = None,
):
    """Join archived OSM ways, preserving their coordinates."""
    if not way_source_ids or len(set(way_source_ids)) != len(way_source_ids):
        raise ValueError('way_source_ids must list distinct OSM way sources')
    with runtime.connect() as database:
        sources = [catalog_source(database, ident) for ident in way_source_ids]
        for ident in evidence_source_ids or []:
            catalog_source(database, ident)
        paths = [download_source(runtime.storage, source, runtime.work_dir) for source in sources]
        geometry = assemble(paths, start_node_id)
        if (runtime.expected_geometry_sha256 is not None
                and geometry_hash(geometry) != runtime.expected_geometry_sha256):
            raise ValueError('assembled boundary differs from the expected geometry checksum')
        with runtime.saving(database):
            hashes = save_features(database, [dict(feature_id=feature_id, geometry=geometry)],
                dict(recipe_id=runtime.recipe_id))
    return dict(feature_id=feature_id, vertices=len(geometry['coordinates']), sha256=hashes[feature_id])
