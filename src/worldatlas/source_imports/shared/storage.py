"""Validate and save constructed features in Neon."""

import re

from psycopg.types.json import Jsonb
from worldatlas.geodesy.geojson import validate_geometry
from worldatlas.source_imports.shared.recipe_types import NONBLANK_PATTERN


def save_features(runtime, features):
    """Save one construction batch while its recipe is locked for reading.

    PostgreSQL's FOR SHARE row lock prevents edits to the recipe until the
    save transaction ends.

    Args:
        runtime: Connection factory and snapshot of the recipe used.
        features: Feature IDs and their constructed geometries.

    Returns:
        Saved feature IDs in input order.

    Raises:
        ValueError: The recipe changed, the batch is invalid, or a feature
            ID already belongs to another construction.
    """
    with runtime.connect() as database, database.transaction():
        row = database.execute(
            "SELECT method,arguments FROM atlas.construction_records WHERE id=%s FOR SHARE",
            (runtime.recipe_id,),
        ).fetchone()
        if row != (runtime.method, runtime.arguments):
            raise ValueError(
                "construction changed during calculation; rerun its current settings"
            )
        return _write_features(database, features, construction_id=runtime.recipe_id)


def _write_features(database, features, *, construction_id):
    """Write the complete batch atomically on the supplied connection.

    Args:
        database: PostgreSQL connection used for the write.
        features: Feature IDs and their constructed geometries.
        construction_id: Owner of all features in the batch.

    Returns:
        Saved feature IDs in input order.
    """
    identifiers = [feature["feature_id"] for feature in features]
    if (
        not identifiers
        or any(not isinstance(ident, str) or not re.search(NONBLANK_PATTERN, ident)
               for ident in identifiers)
        or len(set(identifiers)) != len(identifiers)
    ):
        raise ValueError("feature IDs must be nonempty and unique")
    records = []
    for feature in features:
        geometry = feature["geometry"]
        validate_geometry(geometry)
        records.append((feature["feature_id"], Jsonb(geometry), construction_id))
    with database.transaction():
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


def feature_result(feature_ids, elapsed, *, download_seconds=0.0, source=None):
    """Summarize the features, files, and timings of an import.

    Args:
        feature_ids: IDs of features saved by the import.
        elapsed: Total elapsed seconds.
        download_seconds: Time spent transferring raw files.
        source: Optional local path of the raw file read by the importer.

    Returns:
        The JSON-serializable result reported by the import command.
    """
    result = {"feature_ids": feature_ids}
    if source is not None:
        result["source"] = str(source)
    result["timing"] = {
        "download_seconds": download_seconds,
        "processing_seconds": elapsed - download_seconds,
    }
    return result
