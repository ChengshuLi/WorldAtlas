"""Run a working construction record through its typed source importer."""

import argparse
import hashlib
import json
import logging
import os
from contextlib import ExitStack, closing
from pathlib import Path

from worldatlas.source_imports.atlas_sources.catalog import read_recipe
from worldatlas.source_imports.contracts import Runtime, validate_arguments
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


def selected_constructions(database):
    """Find constructions referenced by working geometry."""
    return [
        row[0]
        for row in database.execute(
            "SELECT DISTINCT construction_id FROM atlas.source_features ORDER BY construction_id"
        ).fetchall()
    ]


def run_import(
    connect, recipe_id, *, storage=None, work_dir=None, expected_geometry_sha256=None
):
    with connect() as database:
        method, arguments = read_recipe(database, recipe_id)
    importer = IMPORTERS.get(method) if isinstance(method, str) else None
    if importer is None:
        raise ValueError(f"unsupported source construction method: {method!r}")
    if method not in ("geodesic_trace", "interpreted_geometry") and (
        storage is None or work_dir is None
    ):
        raise ValueError("this method requires --r2-endpoint and --work-dir")
    if expected_geometry_sha256 is not None and method != "osm_way_chain":
        raise ValueError(
            "an expected geometry checksum applies to OSM way-chain boundaries"
        )
    validate_arguments(importer, arguments)
    return importer(
        Runtime(
            connect,
            storage,
            recipe_id,
            method,
            work_dir,
            expected_geometry_sha256,
            arguments=arguments,
        ),
        **arguments,
    )


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--recipe", metavar="ID")
    selection.add_argument(
        "--all",
        action="store_true",
        help="regenerate all constructions referenced by working records",
    )
    parser.add_argument("--r2-endpoint")
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--expected-geometry-sha256")
    args = parser.parse_args()
    if not (connection := os.environ.get("NEON_DATABASE_URL")):
        parser.error("set NEON_DATABASE_URL to the working database")
    if args.all and args.expected_geometry_sha256:
        parser.error("an expected checksum applies to a single construction")
    import psycopg

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
        if args.all:
            with connect() as database:
                identities = selected_constructions(database)
        else:
            identities = [args.recipe]
        results = []
        for ident in identities:
            result = run_import(
                connect,
                ident,
                storage=storage,
                work_dir=args.work_dir,
                expected_geometry_sha256=args.expected_geometry_sha256,
            )
            results.append(result)
            if args.work_dir is not None:
                name = hashlib.sha256(ident.encode()).hexdigest()
                receipt = args.work_dir / "receipts" / (name + ".json")
                receipt.parent.mkdir(parents=True, exist_ok=True)
                receipt.write_text(
                    json.dumps(dict(construction_id=ident, result=result), indent=2)
                    + "\n"
                )
    print(json.dumps(results if args.all else results[0]))
