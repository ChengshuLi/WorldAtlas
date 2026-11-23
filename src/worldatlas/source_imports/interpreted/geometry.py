"""Import explicitly interpreted points and scope areas from cataloged sources."""

import time
from collections.abc import Mapping
from typing import Literal, TypedDict, cast

from worldatlas.shared.files import JSONValue
from worldatlas.source_imports.shared.recipe_types import NonEmptyText, SourceId
from worldatlas.source_imports.shared.runtime import Runtime
from worldatlas.source_imports.shared.storage import (
    Feature,
    FeatureResult,
    feature_result,
    save_features,
)


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
    selections: list[Selection],
) -> FeatureResult:
    """Store reviewed label points and computation scopes from the recipe.

    Args:
        runtime: Import resources and saved recipe snapshot.
        source_ids: Distinct catalog IDs for the supporting evidence.
        selections: Output IDs and their explicit WGS84 geometry.

    Returns:
        Saved feature IDs and timings.

    Raises:
        ValueError: The recipe has invalid sources or selections, or its
            features cannot be saved for the current recipe.
    """
    if not source_ids or len(set(source_ids)) != len(source_ids):
        raise ValueError(
            "interpreted geometry needs a nonempty list of distinct source IDs"
        )
    if not selections:
        raise ValueError("interpreted geometry needs at least one selection")

    started = time.monotonic()
    features: list[Feature] = [
        {
            "feature_id": selection["feature_id"],
            "geometry": cast(Mapping[str, JSONValue], selection["geometry"]),
        }
        for selection in selections
    ]
    feature_ids = save_features(runtime, features)
    return feature_result(feature_ids, time.monotonic() - started)
