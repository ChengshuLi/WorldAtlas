"""Import explicitly interpreted points and scope areas from cataloged sources."""

import time
from typing import Literal, TypedDict

from worldatlas.source_imports.contracts import NonEmptyText, Runtime, SourceId
from worldatlas.source_imports.atlas_sources.catalog import catalog_source
from worldatlas.source_imports.features.geometry import save_features


class Point(TypedDict):
    type: Literal["Point"]
    coordinates: tuple[float, float]


class Polygon(TypedDict):
    type: Literal["Polygon"]
    coordinates: list[list[tuple[float, float]]]


class Selection(TypedDict):
    feature_id: NonEmptyText
    geometry: Point | Polygon


def interpreted_geometry(
    runtime: Runtime,
    *,
    source_ids: list[SourceId],
    basis: NonEmptyText,
    selections: list[Selection],
):
    """Store source-backed interpretations with their complete explicit settings.

    Use provider-feature importers for provider geometry. This method records
    deliberately selected label points and computation scopes whose interpretation
    is explained in basis. It does not read or combine other editable features.
    """
    if not source_ids or len(set(source_ids)) != len(source_ids) or not selections:
        raise ValueError("interpreted geometry needs distinct sources and selections")
    started = time.monotonic()
    with runtime.connect() as database:
        for source_id in source_ids:
            catalog_source(database, source_id)
        with runtime.saving(database):
            hashes = save_features(
                database, selections, construction_id=runtime.recipe_id
            )
    return dict(
        geometry_sha256=hashes,
        timing=dict(
            processing_seconds=time.monotonic() - started,
            download_seconds=0.0,
        ),
    )
