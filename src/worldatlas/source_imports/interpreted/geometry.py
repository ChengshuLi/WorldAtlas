"""Import explicitly interpreted points and scope areas from cataloged sources."""

import time
from typing import Literal, TypedDict

from worldatlas.source_imports.shared.contracts import NonEmptyText, SourceId
from worldatlas.source_imports.shared.runtime import Runtime
from worldatlas.source_imports.shared.sources import acquire_sources
from worldatlas.source_imports.shared.storage import feature_result, save_features


class Point(TypedDict):
    """An explicitly selected WGS84 point."""

    type: Literal["Point"]
    coordinates: tuple[float, float]


class Polygon(TypedDict):
    """An explicit WGS84 polygon with exterior and interior rings."""

    type: Literal["Polygon"]
    coordinates: list[list[tuple[float, float]]]


class Selection(TypedDict):
    """Name an output feature and supply its reviewed geometry."""

    feature_id: NonEmptyText
    geometry: Point | Polygon


def interpreted_geometry(
    runtime: Runtime,
    *,
    source_ids: list[SourceId],
    basis: NonEmptyText,
    selections: list[Selection],
):
    """Store reviewed label points and computation scopes from the recipe.

    Args:
        runtime: Import resources and saved recipe snapshot.
        source_ids: Distinct catalog IDs for the supporting evidence.
        basis: Human-readable explanation retained in the recipe.
        selections: Output IDs and their explicit WGS84 geometry.

    Returns:
        Saved feature IDs and timings.
    """
    if not source_ids or len(set(source_ids)) != len(source_ids) or not selections:
        raise ValueError("interpreted geometry needs distinct sources and selections")
    started = time.monotonic()
    acquire_sources(runtime, [], evidence_source_ids=source_ids)
    feature_ids = save_features(runtime, selections)
    return feature_result(feature_ids, time.monotonic() - started)
