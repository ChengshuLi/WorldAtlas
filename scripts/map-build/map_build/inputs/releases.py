"""Resolve published map streams from their separate release catalog."""
import os

def read_release_streams(version):
    """Resolve the two published streams without embedding object paths in a preview."""
    connection = os.environ.get('NEON_DATABASE_URL')
    if not connection:
        raise ValueError('set NEON_DATABASE_URL to the database containing the map release')

    import psycopg

    try:
        with psycopg.connect(connection) as database:
            database.execute('SET TRANSACTION READ ONLY')
            rows = database.execute(
                'SELECT stream,r2_bucket,r2_key,size_bytes,stored_sha256,decoded_sha256 '
                'FROM atlas.map_release_objects WHERE map_version=%s ORDER BY stream',
                (version,),
            ).fetchall()
    except psycopg.Error:
        raise ValueError('Neon release lookup failed; check release database access') from None
    if [row[0] for row in rows] != ['rows', 'runs']:
        raise ValueError(f'missing row or run stream for map release {version}')
    return rows


