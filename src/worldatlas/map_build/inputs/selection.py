"""Freeze working geographic decisions in one short, read-only transaction."""

from datetime import datetime, timezone
import json
from pathlib import Path

from worldatlas.map_build.inputs.features import affiliation_selection, selected_basins

HERE = Path(__file__).resolve().parent
DOMAINS = {"mainland", "regional", "water", "ocean"}
QUERY = HERE / "geography.sql"


def validate_bindings(domains):
    """Require every selected stage to give each map code the same meaning.

    Row order and descriptive metadata do not affect a binding. Registry
    revision names may differ when their entity/code meanings are identical.
    """
    expected = None
    for name, domain in domains.items():
        rows = domain.get("category_bindings")
        if not isinstance(rows, list):
            raise ValueError(f"{name} selection needs category bindings")
        bindings, entities = {}, set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"{name} selection has an invalid category binding")
            code, entity, kind = (
                row.get(key) for key in ("code", "entity_id", "physical_class")
            )
            if (
                type(code) is not int
                or not 0 < code < 2**32
                or type(entity) is not int
                or entity <= 0
                or kind not in ("land", "water")
                or code in bindings
                or (entity, kind) in entities
            ):
                raise ValueError(
                    f"{name} selection has invalid or duplicate category bindings"
                )
            bindings[code] = (entity, kind)
            entities.add((entity, kind))
        if expected is not None and bindings != expected:
            raise ValueError(f"{name} category bindings differ from {first}")
        if expected is None:
            first, expected = name, bindings


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


def geographic_domain(selection, name):
    """Expose stage inputs from one working snapshot or an unchanged archived selection."""
    if "geography" not in selection:
        return selection["domains"][name]
    geography = selection["geography"]
    # Ocean barriers and mainland closure lines have different consumers.
    routes = [
        route
        for route in geography["routes"]
        if ("closure_method" in route) == (name == "mainland")
    ]
    return dict(geography, routes=routes)


def selection_domains(selection):
    if "geography" in selection:
        return {name: geographic_domain(selection, name) for name in DOMAINS}
    return selection["domains"]


def entity_colors(selection):
    if "entity_colors" in selection:
        return selection["entity_colors"]
    # Retained archives have registry-keyed colors; never query current Neon.
    snapshot = selection["domains"]["mainland"]
    return selection["registry_colors"][
        snapshot["decision_revision"]["entity_revision"]
    ]


def read_selection(database, *, raw_sources=(), constructions=()):
    """Freeze working records and their catalog in one short read-only transaction."""
    result = {
        "schema": "worldatlas-input-selection-v3",
        "selected_at": datetime.now(timezone.utc).isoformat(),
    }
    with database.transaction():
        database.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        data = json.loads(database.execute(QUERY.read_text()).fetchone()[0])
        features = {feature["feature_id"]: feature for feature in data["features"]}
        with database.cursor(name="selected_features") as cursor:
            cursor.execute(
                "SELECT feature_id,geometry::text FROM atlas.decision_features "
                "WHERE geometry IS NOT NULL ORDER BY feature_id"
            )
            for feature_id, geometry in cursor:
                features[feature_id]["geometry"] = json.loads(geometry)
        selected_basins(data)
        validate_feature_references(data)
        result["geography"] = data
        references = set(raw_sources) | {
            source["source_id"] for source in data["sources"]
        }
        document_refs = set(constructions)
        for key in ("features", "mainland_boundaries", "endpoints", "routes"):
            document_refs.update(
                item["construction_id"]
                for item in data.get(key, [])
                if item.get("construction_id") is not None
            )
        result["regional_partitions"] = []
        for rule_set_id, line_id, definition in database.execute(
            "SELECT rule_set_id,line_id,definition FROM atlas.regional_island_rule_sets "
            "WHERE enabled ORDER BY rule_set_id"
        ).fetchall():
            row = database.execute(
                "SELECT to_jsonb(l)-'created_at' FROM atlas.geographic_line_observations l WHERE line_id=%s",
                (line_id,),
            ).fetchone()
            if row is None:
                raise ValueError("selected geographic line is missing")
            line = row[0]
            result["regional_partitions"].append(
                {"rule_set_id": rule_set_id, "line": line, "policy": definition}
            )
            references.add(line["source_id"])
            if line.get("construction_id") is not None:
                document_refs.add(line["construction_id"])
            references.update(
                source["source_id"] for source in definition.get("sources", [])
            )
        rows = database.execute(
            "SELECT to_jsonb(a)-'created_at' FROM atlas.source_assets a "
            "WHERE source_id=ANY(%s) ORDER BY source_id",
            (sorted(references),),
        ).fetchall()
        result["raw_sources"] = [row[0] for row in rows]
        if missing := references - {row["source_id"] for row in result["raw_sources"]}:
            raise ValueError("selected raw source is missing: " + str(sorted(missing)))
        rows = database.execute(
            "SELECT source_id,document FROM atlas.construction_records "
            "WHERE source_id=ANY(%s) ORDER BY source_id",
            (sorted(document_refs),),
        ).fetchall()
        if missing := document_refs - {row[0] for row in rows}:
            raise ValueError(
                "selected construction is missing: " + str(sorted(missing))
            )
        result["construction_records"] = [
            dict(source_id=ident, document=document) for ident, document in rows
        ]
        result["entity_colors"] = [
            dict(entity_id=ident, color_rgb=color)
            for ident, color in database.execute(
                "SELECT id,color_rgb FROM atlas.geographic_entity_ids ORDER BY id"
            ).fetchall()
        ]
    return result


def validate_feature_references(domain):
    """Check every executable affiliation reference before lengthy processing."""
    features = {feature["feature_id"] for feature in domain.get("features", [])}
    for rule in domain.get("affiliations", []):
        affiliation_selection(rule, features)


def read_saved(path):
    """Read frozen values without rewriting historical archives or consulting Neon."""
    result = json.loads(Path(path).read_bytes())
    if result.get("schema") not in (
        "worldatlas-input-selection-v1",
        "worldatlas-input-selection-v2",
        "worldatlas-input-selection-v3",
    ):
        raise ValueError("unsupported saved input selection")
    domains = selection_domains(result)
    validate_bindings(domains)
    for domain in domains.values():
        validate_feature_references(domain)
    if "water" in domains:
        selected_basins(domains["water"])
    return result
