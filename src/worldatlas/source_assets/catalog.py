"""Resolve the R2 locations and checksums of raw sources registered in Neon."""

from collections.abc import Iterable

from psycopg import Connection

from worldatlas.source_assets.pins import R2ObjectPin


def catalog_sources(
    database: Connection, source_ids: Iterable[str]
) -> dict[str, R2ObjectPin]:
    """Resolve raw source IDs in one catalog query.

    Args:
        database: The caller's PostgreSQL connection.
        source_ids: Iterable of raw source IDs to look up.

    Returns:
        A dictionary keyed by source ID. Each entry contains its R2 bucket,
        object key, expected byte size, and SHA-256.

    Raises:
        ValueError: A requested catalog entry is missing.
    """
    ids = list(dict.fromkeys(source_ids))
    rows = database.execute(
        "SELECT id,r2_bucket,r2_key,sha256,size_bytes FROM atlas.source_assets "
        "WHERE id=ANY(%s)",
        (ids,),
    )
    sources: dict[str, R2ObjectPin] = {
        ident: R2ObjectPin(
            source_id=ident,
            r2_bucket=bucket,
            r2_key=key,
            sha256=digest,
            size_bytes=size,
        )
        for ident, bucket, key, digest, size in rows
    }
    missing = next((ident for ident in ids if ident not in sources), None)
    if missing is not None:
        raise ValueError(f'raw source {missing!r} is missing from the Neon catalog')
    return sources
