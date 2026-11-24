"""Validate and save constructed features in Neon."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NotRequired, TypedDict

from psycopg.types.json import Jsonb

from worldatlas.geodesy.geojson import validate_geometry
from worldatlas.shared.files import JSONValue
from worldatlas.shared.text import is_nonblank
from worldatlas.source_imports.shared.runtime import Runtime


class Feature(TypedDict):
    """One construction output and its WGS84 GeoJSON."""

    feature_id: str
    geometry: Mapping[str, JSONValue]


class ImportTiming(TypedDict):
    """Transfer and processing durations in seconds."""

    download_seconds: float
    processing_seconds: float


class FeatureResult(TypedDict):
    """Files, saved IDs and timings reported by a feature importer."""

    feature_ids: list[str]
    source: NotRequired[str]
    timing: ImportTiming


def save_features(runtime: Runtime, features: Sequence[Feature]) -> list[str]:
    """Save one construction batch while its recipe is locked for reading.

    PostgreSQL's FOR SHARE row lock prevents edits to the recipe until the
    save transaction ends. Features omitted from this batch are retained.

    Args:
        runtime: Connection factory and snapshot of the recipe used.
        features: Feature IDs and their constructed geometries.

    Returns:
        Saved feature IDs in input order.

    Raises:
        ValueError: The recipe changed, the batch is invalid, or a feature
            ID already belongs to another construction.
    """
    identifiers = [feature["feature_id"] for feature in features]
    if (
        not identifiers
        or any(not is_nonblank(ident) for ident in identifiers)
        or len(set(identifiers)) != len(identifiers)
    ):
        raise ValueError("feature IDs must be nonempty and unique")
    records = []
    for feature in features:
        geometry = feature["geometry"]
        validate_geometry(geometry)
        records.append(
            (feature["feature_id"], Jsonb(dict(geometry)), runtime.recipe_id)
        )
    with runtime.connect() as database, database.transaction():
        row = database.execute(
            "SELECT method,arguments FROM atlas.construction_records WHERE id=%s FOR SHARE",
            (runtime.recipe_id,),
        ).fetchone()
        if row != (runtime.method, runtime.arguments):
            raise ValueError(
                "construction changed during calculation; rerun its current settings"
            )
        with database.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO atlas.source_features (id,geometry,construction_id) VALUES (%s,%s,%s) "
                "ON CONFLICT (id) DO UPDATE SET geometry=EXCLUDED.geometry "
                "WHERE atlas.source_features.construction_id=EXCLUDED.construction_id",
                records,
            )
            if cursor.rowcount != len(records):
                raise ValueError("feature ID already belongs to another construction")
    return identifiers


def feature_result(
    feature_ids: list[str],
    elapsed: float,
    *,
    download_seconds: float = 0.0,
    source: Path | str | None = None,
) -> FeatureResult:
    """Summarize the features, files, and timings of an import.

    Args:
        feature_ids: IDs of features saved by the import.
        elapsed: Total elapsed seconds.
        download_seconds: Time spent transferring raw files.
        source: Optional local path of the raw file read by the importer.

    Returns:
        The JSON-serializable result reported by the import command.
    """
    result: FeatureResult = {
        "feature_ids": feature_ids,
        "timing": {
            "download_seconds": download_seconds,
            "processing_seconds": elapsed - download_seconds,
        },
    }
    if source is not None:
        result["source"] = str(source)
    return result
