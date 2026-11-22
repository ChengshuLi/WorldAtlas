"""Open connections to the Neon database configured for WorldAtlas."""

import os

import psycopg
from psycopg.conninfo import conninfo_to_dict


def neon_connection_url(*, direct: bool = False) -> str:
    """Read the database connection string from the environment.

    Args:
        direct: Require a direct Neon connection for session-level locks.

    Returns:
        The connection string from ``NEON_DATABASE_URL``.

    Raises:
        ValueError: The setting is missing or uses a pooler when direct access
            is required.
    """
    connection = os.environ.get("NEON_DATABASE_URL")
    if not connection:
        raise ValueError("set NEON_DATABASE_URL to the WorldAtlas database")
    if direct and "-pooler." in str(conninfo_to_dict(connection).get("host", "")):
        raise ValueError("use a direct Neon connection for session-level locks")
    return connection


def connect_neon(
    *, url: str | None = None, autocommit: bool = False
) -> psycopg.Connection:
    """Open a Neon connection with a 15-second connection timeout.

    Args:
        url: Previously loaded connection string. Read the environment when omitted.
        autocommit: Commit statements outside an explicit transaction individually.

    Returns:
        A new connection. The caller closes it and manages transactions.
    """
    return psycopg.connect(
        neon_connection_url() if url is None else url,
        autocommit=autocommit,
        connect_timeout=15,
    )
