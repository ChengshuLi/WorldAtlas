"""Freeze working geographic decisions in one short, read-only transaction."""

import json
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, LiteralString, cast

from psycopg import Connection

from worldatlas.geodesy.geojson import validate_geometry
from worldatlas.map_build.division.contracts import CompiledRules, compile_rules

HERE = Path(__file__).resolve().parent

QUERY = HERE / "geography.sql"


def validate_map_code_bindings(geography: dict[str, Any]) -> None:
    """Check the mappings between map codes and (entity, land or water) pairs.

    Args:
        geography: Geographic entities and their code bindings.

    Raises:
        ValueError: A code or (entity, physical class) pair is invalid or duplicated.
    """
    entities = {entity["id"]: entity for entity in geography["entities"]}
    codes, pairs = set(), set()
    for binding in geography["category_bindings"]:
        code, entity, kind = (
            binding.get(k) for k in ("code", "entity_id", "physical_class")
        )
        if (
            type(code) is not int
            or not 0 < code < 2**32
            or type(entity) is not int
            or entity not in entities
            or entity == 0
            or kind not in ("land", "water")
            or code in codes
            or (entity, kind) in pairs
            or entities[entity]["physical_class"] not in ("mixed", kind)
        ):
            raise ValueError("invalid or duplicate category binding")
        codes.add(code)
        pairs.add((entity, kind))


def canonical_bytes(selection: dict[str, Any]) -> bytes:
    """Encode a frozen selection as compact, sorted JSON for comparisons.

    Args:
        selection: Frozen input selection to encode.

    Returns:
        UTF-8 bytes with sorted keys and one trailing newline.

    Raises:
        TypeError: A value cannot be encoded as JSON.
        ValueError: A number is nonfinite or a container refers to itself.
    """
    return (
        json.dumps(
            selection,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode()


def entity_colors(selection: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect the configured colors of entities in a selection.

    Args:
        selection: Frozen build inputs containing geographic entities.

    Returns:
        Dictionaries with an "entity_id" and "color_rgb" in entity order.
    """
    return [
        {"entity_id": e["id"], "color_rgb": e.get("color_rgb")}
        for e in selection["geography"]["entities"]
    ]


def read_selection(
    database: Connection,
    *,
    raw_sources: Iterable[str] = (),
    parents: list[int] | None = None,
) -> dict[str, Any]:
    """Read the working build inputs from one consistent database snapshot.

    Args:
        database: Open PostgreSQL connection for a read-only transaction.
        raw_sources: Additional raw source IDs used for physical rasterization.
        parents: Parent IDs to load with their ancestors, or None for all
            divisions.

    Returns:
        Selection dictionary with geographic rules, coordinates, construction
        records and source catalog entries.

    Raises:
        ValueError: A requested parent or raw source record is missing.
    """
    result: dict[str, Any] = {
        "schema": "worldatlas-input-selection-v4",
        "selected_at": datetime.now(timezone.utc).isoformat(),
    }
    with database.transaction():
        database.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        if parents is not None:
            found = database.execute(
                """
                WITH RECURSIVE required AS (
                  SELECT id,parent_id FROM atlas.geographic_entities WHERE id=ANY(%s)
                  UNION SELECT e.id,e.parent_id FROM atlas.geographic_entities e
                    JOIN required r ON e.id=r.parent_id
                ) SELECT id FROM required
            """,
                (parents,),
            ).fetchall()
            ancestors = {r[0] for r in found}
            if set(parents) - ancestors:
                raise ValueError("requested parent does not exist")
            parents = sorted(ancestors)
        # The query returns one row with one JSON text column. It includes rules
        # for the requested parents and their ancestors, or all rules if parents
        # is None. The object contains lists of levels, entities, map codes, rules
        # and their links, features (ID and construction ID), and source references.
        # Feature coordinates are fetched separately below.
        result_row = database.execute(
            cast(LiteralString, QUERY.read_text()), (parents, parents)
        ).fetchone()
        assert result_row is not None
        data = json.loads(result_row[0])
        features = {feature["id"]: feature for feature in data["features"]}
        with database.cursor(name="selected_features") as cursor:
            cursor.execute(
                "SELECT id,geometry::text FROM atlas.source_features "
                "WHERE id=ANY(%s) ORDER BY id",
                (sorted(features),),
            )
            for feature_id, geometry in cursor:
                features[feature_id]["geometry"] = json.loads(geometry)
        result["geography"] = data
        references = set(raw_sources) | {
            source["source_id"] for source in data["sources"]
        }
        document_refs = {feature["construction_id"] for feature in features.values()}
        rows = database.execute(
            "SELECT (to_jsonb(a)-'created_at'-'id') || jsonb_build_object('source_id',a.id) "
            "FROM atlas.source_assets a WHERE id=ANY(%s) ORDER BY id",
            (sorted(references),),
        ).fetchall()
        result["raw_sources"] = [row[0] for row in rows]
        if missing := references - {row["source_id"] for row in result["raw_sources"]}:
            raise ValueError("selected raw source is missing: " + str(sorted(missing)))
        rows = database.execute(
            "SELECT id,method,arguments,basis FROM atlas.construction_records "
            "WHERE id=ANY(%s) ORDER BY id",
            (sorted(document_refs),),
        ).fetchall()
        # The source_features foreign key guarantees these recipes in this snapshot.
        result["construction_records"] = [
            dict(id=ident, method=method, arguments=arguments, basis=basis)
            for ident, method, arguments, basis in rows
        ]
    return result


def prepare_geography(domain: dict[str, Any]) -> dict[int, CompiledRules]:
    """Check frozen geometry and map codes and assemble the rules for each parent.

    Args:
        domain: Geographic part of a frozen selection.

    Returns:
        Child entities and assembled rules keyed by parent entity ID.

    Raises:
        ValueError: The schema, geometry, rules, or bindings are invalid.
    """
    if domain.get("schema") != "worldatlas-geographic-division-v2":
        raise ValueError(
            "unsupported geographic selection; restore the release's captured code"
        )
    for feature in domain["features"]:
        validate_geometry(feature["geometry"])
    parents = {r["parent_id"] for r in domain["rules"]}
    compiled = {parent: compile_rules(domain, parent) for parent in parents}
    validate_map_code_bindings(domain)
    return compiled


def read_saved(path: Path | str) -> dict[str, Any]:
    """Load an earlier frozen selection from disk.

    Args:
        path: Path to the selection JSON file.

    Returns:
        Selection dictionary containing the saved coordinates and rules.

    Raises:
        ValueError: The file has an incompatible schema.
    """
    result = json.loads(Path(path).read_bytes())
    if result.get("schema") != "worldatlas-input-selection-v4":
        raise ValueError(
            "this selection requires its release archive's captured implementation"
        )
    return result
