"""Normalize and save constructed features in Neon."""

import hashlib
import json
import re

from psycopg.types.json import Jsonb
from worldatlas.geodesy.geojson import validate_geometry
from worldatlas.source_imports.shared.contracts import NONBLANK_PATTERN


def geometry_bytes(geometry):
    """Encode geometry using the coordinate representation retained by JSONB.

    Args:
        geometry: GeoJSON geometry to serialize.

    Returns:
        Deterministic UTF-8 JSON bytes.
    """
    return json.dumps(
        storage_geometry(geometry),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def geometry_hash(geometry):
    """Hash the JSONB-compatible representation of a geometry.

    Args:
        geometry: GeoJSON geometry to hash.

    Returns:
        The SHA-256 hex digest.
    """
    return hashlib.sha256(geometry_bytes(geometry)).hexdigest()


def storage_geometry(geometry):
    """Normalize signed zero to match PostgreSQL JSONB storage.

    Args:
        geometry: GeoJSON geometry whose coordinates are ready to save.

    Returns:
        A new geometry dictionary with coordinates copied into arrays.
    """
    # PostgreSQL JSONB stores -0.0 as 0.0. Hash the same coordinates that the
    # database can retain; all other coordinate values remain unchanged.
    def coordinates(value):
        if isinstance(value, (list, tuple)):
            return [coordinates(child) for child in value]
        return 0.0 if type(value) is float and value == 0 else value

    return {
        "type": geometry["type"],
        "coordinates": coordinates(geometry["coordinates"]),
    }


def save_features(runtime, features):
    """Save one construction batch while its recipe is locked for reading.

    Args:
        runtime: Connection factory and snapshot of the recipe used.
        features: Feature IDs and their constructed geometries.

    Returns:
        Geometry checksums keyed by saved feature ID.

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
        Geometry checksums keyed by feature ID.
    """
    identifiers = [feature["feature_id"] for feature in features]
    if (
        not identifiers
        or any(not isinstance(ident, str) or not re.search(NONBLANK_PATTERN, ident)
               for ident in identifiers)
        or len(set(identifiers)) != len(identifiers)
    ):
        raise ValueError("feature IDs must be nonempty and unique")
    records, hashes = [], {}
    for feature in features:
        validate_geometry(feature["geometry"])
        geometry = storage_geometry(feature["geometry"])
        hashes[feature["feature_id"]] = geometry_hash(geometry)
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
    return hashes


def feature_result(hashes, elapsed, *, download_seconds=0.0, source=None):
    """Summarize the files, checksums, and timings of a feature import.

    Args:
        hashes: Saved geometry checksums keyed by feature ID.
        elapsed: Total elapsed seconds.
        download_seconds: Time spent transferring raw files.
        source: Optional local path of the raw file read by the importer.

    Returns:
        The JSON-serializable result reported by the import command.
    """
    result = {"geometry_sha256": hashes}
    if source is not None:
        result["source"] = str(source)
    result["timing"] = {
        "download_seconds": download_seconds,
        "processing_seconds": elapsed - download_seconds,
    }
    return result
