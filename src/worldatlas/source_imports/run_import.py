"""Run a saved construction through its registered source importer.

Set ``NEON_DATABASE_URL`` and run ``worldatlas-import --recipe ID``.
For methods that read raw files, also supply ``--r2-endpoint`` and
``--work-dir``.
"""

import argparse
import json
import logging
from collections.abc import Callable
from contextlib import closing, nullcontext
from functools import partial
from pathlib import Path
from typing import Any

import psycopg

from worldatlas.shared.database import connect_neon, neon_connection_url
from worldatlas.shared.r2 import R2Client, make_r2_client
from worldatlas.source_imports.iho.areas import s130_areas
from worldatlas.source_imports.interpreted.geometry import interpreted_geometry
from worldatlas.source_imports.osm.features import selected_osm_features
from worldatlas.source_imports.osm.ways import osm_way_chain
from worldatlas.source_imports.shared.runtime import Runtime
from worldatlas.source_imports.traces.geodesic import geodesic_trace
from worldatlas.source_imports.vector.features import selected_vector_features
from worldatlas.source_imports.watersheds.build_boundary import watershed_boundary

IMPORTERS = {
    constructor.__name__: constructor
    for constructor in (
        geodesic_trace,
        osm_way_chain,
        watershed_boundary,
        selected_vector_features,
        selected_osm_features,
        s130_areas,
        interpreted_geometry,
    )
}


def read_recipe(
    database: psycopg.Connection, recipe_id: str
) -> tuple[str, dict[str, Any]]:
    """Return the stored method and arguments for a construction ID.

    Args:
        database: The caller's PostgreSQL connection.
        recipe_id: Construction ID to look up.

    Returns:
        A pair containing the method name and its argument dictionary.

    Raises:
        ValueError: The construction record is missing.
    """
    row = database.execute(
        'SELECT method,arguments FROM atlas.construction_records WHERE id=%s',
        (recipe_id,),
    ).fetchone()
    if row is None:
        raise ValueError('construction record is missing from Neon')
    return row


def run_import(
    connect: Callable[[], psycopg.Connection],
    recipe_id: str,
    *,
    storage: R2Client | None = None,
    work_dir: Path | None = None,
) -> dict[str, Any]:
    """Run a construction validated when it was saved in Neon.

    Pass the saved keyword arguments and a separate ``Runtime`` object
    to the registered importer. The importer writes the resulting geometry.

    Args:
        connect: Callable that opens a PostgreSQL connection.
        recipe_id: Construction ID to read from Neon.
        storage: R2 client, required for methods that read raw files.
        work_dir: Local cache directory, required when ``storage`` is needed.

    Returns:
        The result reported by the selected importer.

    Raises:
        ValueError: The construction is missing, the method is unsupported,
            or required download settings are absent.
    """
    with connect() as database:
        method, arguments = read_recipe(database, recipe_id)
    importer = IMPORTERS.get(method) if isinstance(method, str) else None
    if importer is None:
        raise ValueError(f"unsupported source construction method: {method!r}")
    return importer(
        Runtime(
            connect=connect,
            storage=storage,
            recipe_id=recipe_id,
            method=method,
            arguments=arguments,
            work_dir=work_dir,
        ),
        **arguments,
    )


def main() -> None:
    """Run the requested import and print its result as JSON."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--recipe", metavar="ID", required=True, help="construction ID in Neon"
    )
    parser.add_argument("--r2-endpoint")
    parser.add_argument(
        "--work-dir", type=Path, help="local cache for raw source files"
    )
    args = parser.parse_args()
    try:
        url = neon_connection_url()
    except ValueError as exc:
        parser.error(str(exc))
    connect = partial(connect_neon, url=url)
    r2 = (
        closing(make_r2_client(args.r2_endpoint)) if args.r2_endpoint else nullcontext()
    )
    with r2 as storage:
        result = run_import(
            connect,
            args.recipe,
            storage=storage,
            work_dir=args.work_dir,
        )
    print(json.dumps(result))
