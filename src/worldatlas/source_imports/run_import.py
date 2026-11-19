"""Run a saved construction through its registered source importer.

Set ``NEON_DATABASE_URL`` and run ``worldatlas-import --recipe ID``.
For methods that read raw files, also supply ``--r2-endpoint`` and
``--work-dir``.
"""

import argparse
import json
import logging
import os
from contextlib import ExitStack, closing
from pathlib import Path

import psycopg

from worldatlas.source_imports.atlas_sources.catalog import read_recipe
from worldatlas.source_imports.contracts import Runtime
from worldatlas.source_imports.features.build_features import (
    s130_areas,
    selected_osm_features,
    selected_vector_features,
)
from worldatlas.source_imports.features.interpreted import interpreted_geometry
from worldatlas.source_imports.osm.build_boundary import osm_way_chain
from worldatlas.source_imports.traces.build_boundary import geodesic_trace
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


def run_import(connect, recipe_id, *, storage=None, work_dir=None):
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
    if method not in ("geodesic_trace", "interpreted_geometry") and (
        storage is None or work_dir is None
    ):
        raise ValueError("this method requires --r2-endpoint and --work-dir")
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


def main():
    """Run the requested import and print its result as JSON."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--recipe", metavar="ID", required=True, help="construction ID in Neon"
    )
    parser.add_argument("--r2-endpoint")
    parser.add_argument("--work-dir", type=Path, help="local cache for raw source files")
    args = parser.parse_args()
    if not (connection := os.environ.get("NEON_DATABASE_URL")):
        parser.error("set NEON_DATABASE_URL to the working database")
    connect = lambda: psycopg.connect(connection, connect_timeout=15)
    with ExitStack() as stack:
        storage = None
        if args.r2_endpoint:
            import boto3

            storage = stack.enter_context(
                closing(
                    boto3.client(
                        "s3", endpoint_url=args.r2_endpoint, region_name="auto"
                    )
                )
            )
        result = run_import(
            connect,
            args.recipe,
            storage=storage,
            work_dir=args.work_dir,
        )
    print(json.dumps(result))
