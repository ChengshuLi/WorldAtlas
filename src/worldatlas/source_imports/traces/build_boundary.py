"""Construct a source-figure line and save it through the shared feature importer."""

from typing import Any

from worldatlas.source_imports.contracts import NonEmptyText, Runtime
from worldatlas.source_imports.atlas_sources.catalog import catalog_source
from worldatlas.source_imports.features.geometry import save_features
from worldatlas.source_imports.traces.geodesic import construct


def geodesic_trace(runtime: Runtime, *, source_id: NonEmptyText,
                          source_feature_id: NonEmptyText, feature_id: NonEmptyText,
                          basis: NonEmptyText, points: list[tuple[float, float]],
                          max_step_metres: float,
                          source_location: dict[str, Any] | str | None = None):
    """Join source-figure control points on WGS84, preserving every point."""
    geometry = construct(points, max_step_metres)
    with runtime.connect() as database:
        source = catalog_source(database, source_id)
        with runtime.saving(database):
            hashes = save_features(database, [dict(
                feature_id=feature_id, source_id=source['source_id'],
                source_feature_id=source_feature_id, geometry=geometry,
            )], dict(recipe_id=runtime.recipe_id))
    return dict(feature_id=feature_id, vertices=len(geometry['coordinates']), sha256=hashes[feature_id])
