"""Resolve official releases or numbered candidates from their asset manifests."""

import os


def read_release_streams(version):
    """Resolve the two streams without embedding object paths in a preview."""
    connection = os.environ.get('NEON_DATABASE_URL')
    if not connection:
        raise ValueError('set NEON_DATABASE_URL to the database containing the map release')

    import psycopg

    try:
        with psycopg.connect(connection) as database:
            database.execute('SET TRANSACTION READ ONLY')
            rows = database.execute(
                "SELECT stream,r.r2_bucket,asset->>'r2_key',(asset->>'size_bytes')::bigint,"
                "asset->>'sha256',r.manifest->'decoded_sha256'->>stream "
                'FROM atlas.map_releases r LEFT JOIN atlas.map_publications p USING(release_id) '
                "CROSS JOIN (VALUES ('rows'),('runs')) streams(stream) "
                "CROSS JOIN LATERAL (SELECT r.manifest->'objects'->(stream||'.u32le.gz') asset) a "
                'WHERE p.map_version=%s OR r.release_id=%s ORDER BY stream',
                (version, version),
            ).fetchall()
    except psycopg.Error:
        raise ValueError('Neon release lookup failed; check release database access') from None
    if [row[0] for row in rows] != ['rows', 'runs']:
        raise ValueError(f'missing row or run stream for map release {version}')
    return rows
