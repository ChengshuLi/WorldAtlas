"""Build selected IHO S-130 routes from a Neon construction record and raw R2 data."""

from psycopg.types.json import Jsonb
from typing import NotRequired, TypedDict

from worldatlas.source_imports.contracts import NonEmptyText, Runtime

from worldatlas.source_imports.iho.s130 import extract_routes
from worldatlas.source_imports.atlas_sources.catalog import (
    catalog_source,
    download_source,
)


def save_routes(database, result, source, recipe):
    """Save the selected endpoints, routes and ordered point links together."""
    common = {
        "basis": recipe["basis"],
        "source_refs": [dict(source_id=source["source_id"])],
    }
    with database.transaction():
        for endpoint in result["endpoints"]:
            database.execute(
                "INSERT INTO atlas.decision_endpoints "
                "(endpoint_id,name,longitude,latitude,derivation,evidence,construction_id) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (endpoint_id) "
                "DO UPDATE SET name=EXCLUDED.name,longitude=EXCLUDED.longitude,"
                "latitude=EXCLUDED.latitude,derivation=EXCLUDED.derivation,"
                "construction_id=EXCLUDED.construction_id,"
                "evidence=(atlas.decision_endpoints.evidence - 'selector' - 'point_id') || EXCLUDED.evidence",
                (
                    endpoint["endpoint_id"],
                    endpoint["name"],
                    endpoint["longitude"],
                    endpoint["latitude"],
                    Jsonb(endpoint["derivation"]),
                    Jsonb(dict(endpoint["evidence"], **common)),
                    recipe["recipe_id"],
                ),
            )
        for route in result["routes"]:
            database.execute(
                "INSERT INTO atlas.decision_routes "
                "(route_id,route_type,parameters,evidence,construction_id) VALUES (%s,%s,%s,%s,%s) "
                "ON CONFLICT (route_id) DO UPDATE SET route_type=EXCLUDED.route_type,"
                "parameters=EXCLUDED.parameters,"
                "construction_id=EXCLUDED.construction_id,"
                "evidence=atlas.decision_routes.evidence || EXCLUDED.evidence",
                (
                    route["route_id"],
                    route["route_type"],
                    Jsonb(route["parameters"]),
                    Jsonb(dict(route["evidence"], **common)),
                    recipe["recipe_id"],
                ),
            )
            database.execute(
                "DELETE FROM atlas.decision_route_points WHERE route_id=%s",
                (route["route_id"],),
            )
            with database.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO atlas.decision_route_points VALUES (%s,%s,%s)",
                    [
                        (route["route_id"], point["ordinal"], point["endpoint_id"])
                        for point in route["points"]
                    ],
                )


class Route(TypedDict):
    route_id: NonEmptyText
    construction_line_id: NonEmptyText
    reverse: bool
    endpoint_names: tuple[NonEmptyText, NonEmptyText]
    endpoint_ids: NotRequired[tuple[NonEmptyText, NonEmptyText]]
    extend_to_south_grid_edge: NotRequired[bool]


def s130_rhumb_routes(
    runtime: Runtime,
    *,
    source_id: NonEmptyText,
    gml_member: NonEmptyText,
    gml_sha256: NonEmptyText,
    basis: NonEmptyText,
    max_step_km: float,
    routes: list[Route],
):
    """Extract selected S-130 rhumb routes in their chosen direction."""
    recipe = runtime.recipe(locals())
    with runtime.connect() as database:
        with database.transaction():
            source = catalog_source(database, source_id)
        archive = download_source(runtime.storage, source, runtime.work_dir)
        result = extract_routes(archive, source["sha256"], recipe)
        with runtime.saving(database):
            save_routes(database, result, source, recipe)
    return dict(
        route_ids=[route["route_id"] for route in result["routes"]],
        endpoint_count=len(result["endpoints"]),
        archive=str(archive),
    )
