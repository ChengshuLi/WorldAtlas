"""Import selected S-130 construction lines as ordinary geographic features."""
from typing import TypedDict

from worldatlas.source_imports.contracts import NonEmptyText, Runtime, SourceId
from worldatlas.source_imports.atlas_sources.catalog import catalog_source, download_source
from worldatlas.source_imports.features.geometry import save_features
from worldatlas.source_imports.iho.s130 import extract_routes


class Route(TypedDict):
    feature_id: NonEmptyText
    construction_line_id: NonEmptyText
    reverse: bool


def s130_rhumb_routes(
    runtime: Runtime, *, source_id: SourceId, gml_member: NonEmptyText,
    gml_sha256: NonEmptyText, basis: NonEmptyText, max_step_km: float,
    routes: list[Route],
):
    """Preserve selected source endpoints and sample their declared rhumb lines."""
    recipe = runtime.recipe(locals())
    with runtime.connect() as database:
        source = catalog_source(database, source_id)
        archive = download_source(runtime.storage, source, runtime.work_dir)
        features = extract_routes(archive, source['sha256'], recipe)
        with runtime.saving(database):
            hashes = save_features(database, features, recipe)
    return dict(feature_ids=list(hashes), geometry_sha256=hashes, archive=str(archive))
