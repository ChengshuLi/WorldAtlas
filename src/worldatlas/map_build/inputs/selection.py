"""Freeze working geographic decisions in one short, read-only transaction."""

from datetime import datetime, timezone
import json
from pathlib import Path

from worldatlas.map_build.division.contracts import compile_rules
from worldatlas.geodesy.geojson import validate_geometry

HERE = Path(__file__).resolve().parent

QUERY = HERE / "geography.sql"


def validate_bindings(geography):
    """Require unique code meanings compatible with existing geographic entities."""
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


def canonical_bytes(value):
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode()


def entity_colors(selection):
    return [
        {"entity_id": e["id"], "color_rgb": e.get("color_rgb")}
        for e in selection["geography"]["entities"]
    ]


def read_selection(database, *, raw_sources=(), parents=None):
    """Freeze working records and their catalog in one short read-only transaction."""
    result = {
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
        data = json.loads(
            database.execute(QUERY.read_text(), (parents, parents)).fetchone()[0]
        )
        features = {feature["id"]: feature for feature in data["features"]}
        with database.cursor(name="selected_features") as cursor:
            cursor.execute(
                "SELECT id,geometry::text FROM atlas.source_features "
                "WHERE id=ANY(%s) ORDER BY id",
                (sorted(features),),
            )
            for feature_id, geometry in cursor:
                features[feature_id]["geometry"] = json.loads(geometry)
        validate_feature_references(data)
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
        if missing := document_refs - {row[0] for row in rows}:
            raise ValueError(
                "selected construction is missing: " + str(sorted(missing))
            )
        result["construction_records"] = [
            dict(id=ident, method=method, arguments=arguments, basis=basis)
            for ident, method, arguments, basis in rows
        ]
    return result


def validate_feature_references(domain):
    """Validate frozen geometry and every declared operation before processing."""
    if domain.get("schema") != "worldatlas-geographic-division-v2":
        raise ValueError(
            "unsupported geographic selection; restore the release's captured code"
        )
    for feature in domain["features"]:
        validate_geometry(feature["geometry"])
    parents = {r["parent_id"] for r in domain["rules"]}
    for parent in parents:
        compile_rules(domain, parent)
    validate_bindings(domain)


def read_saved(path):
    """Use exact frozen values without consulting or modifying today's Neon."""
    result = json.loads(Path(path).read_bytes())
    if result.get("schema") != "worldatlas-input-selection-v4":
        raise ValueError(
            "this selection requires its release archive's captured implementation"
        )
    validate_feature_references(result["geography"])
    return result
