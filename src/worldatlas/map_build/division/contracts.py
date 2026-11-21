"""Compile the six geographic operations and their relational input contracts."""

from collections import defaultdict
from typing import Any

OPERATIONS = frozenset(
    (
        "assign_area",
        "divide_area",
        "nearest_land",
        "nearest_coastal_water",
        "nearest_basin_water",
        "nearest_water",
    )
)
ROLE_TYPES = {
    "boundary_line": frozenset(("LineString", "MultiLineString")),
    "scope_area": frozenset(("Polygon", "MultiPolygon")),
    "scope_component": frozenset(("Point",)),
    "distance_reference": frozenset(("Point",)),
    "connected_to": frozenset(("Point",)),
}


def compile_rules(
    geography: dict[str, Any], parent_id: int
) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]]]:
    """Resolve and validate the rules for one geographic parent.

    Args:
        geography: Frozen entities, rules, source features and links.
        parent_id: Entity ID to divide.

    Returns:
        (children_by_id, rules). The rules have their source features and
        target label points attached, in rule-ID order.

    Raises:
        ValueError: A required record is missing, duplicated or invalid.
    """
    entities = {e["id"]: e for e in geography["entities"]}
    features = {f["id"]: f for f in geography["features"]}
    rules = {r["id"]: r for r in geography["rules"]}
    if (
        len(entities) != len(geography["entities"])
        or len(features) != len(geography["features"])
        or len(rules) != len(geography["rules"])
    ):
        raise ValueError("duplicate entity, feature or rule identity")
    if parent_id not in entities:
        raise ValueError("missing geographic parent")
    children = {k: v for k, v in entities.items() if v["parent_id"] == parent_id}
    selected = {ident: r for ident, r in rules.items() if r["parent_id"] == parent_id}
    if not children or not selected:
        raise ValueError("a division needs child entities and rules")
    links, targets = defaultdict(lambda: defaultdict(list)), defaultdict(list)
    seen = set()
    for link in geography["rule_features"]:
        if link["rule_id"] not in selected:
            continue
        role, ident = link["role"], link["feature_id"]
        key = (link["rule_id"], role, ident)
        if key in seen or role not in ROLE_TYPES or ident not in features:
            raise ValueError("duplicate or unresolved rule feature link")
        seen.add(key)
        feature = features[ident]
        if feature["geometry"]["type"] not in ROLE_TYPES[role]:
            raise ValueError(f"rule {link['rule_id']} has invalid {role} geometry")
        links[link["rule_id"]][role].append(feature)
    for target in geography["rule_targets"]:
        if target["rule_id"] not in selected:
            continue
        if target["entity_id"] not in children:
            raise ValueError("rule target is not a direct child")
        label = target["label_point_id"]
        if label is not None and (
            label not in features or features[label]["geometry"]["type"] != "Point"
        ):
            raise ValueError("a divided-face label must reference a Point")
        targets[target["rule_id"]].append(
            dict(target, point=features[label] if label else None)
        )
    result = []
    for ident, rule in sorted(selected.items()):
        operation = rule["operation"]
        inputs = links[ident]
        output = targets[ident]
        if (
            operation not in OPERATIONS
            or type(rule["unassigned_only"]) is not bool
            or rule["unit"] not in ("cell", "component")
            or rule["physical_class"] not in ("land", "water", "mixed")
        ):
            raise ValueError(f"invalid operation settings for {ident}")
        if bool(inputs["boundary_line"]) != (operation == "divide_area"):
            raise ValueError(f"invalid boundary links for {ident}")
        if bool(inputs["distance_reference"]) != (operation == "nearest_land"):
            raise ValueError(f"invalid distance-reference links for {ident}")
        if operation == "nearest_basin_water" and (
            len(inputs["scope_area"]) != 1 or inputs["scope_component"]
        ):
            raise ValueError(
                f"basin {ident} requires exactly one area and no component selector"
            )
        if (
            (operation == "assign_area" and len(output) != 1)
            or (operation == "divide_area" and not output)
            or (operation not in ("assign_area", "divide_area") and output)
            or any(
                (t["point"] is not None) != (operation == "divide_area") for t in output
            )
        ):
            raise ValueError(f"invalid target contract for {ident}")
        if operation == "nearest_land" and (rule["physical_class"], rule["unit"]) != (
            "land",
            "component",
        ):
            raise ValueError("nearest_land requires land components")
        if (
            operation.startswith("nearest_")
            and operation != "nearest_land"
            and (rule["physical_class"], rule["unit"]) != ("water", "cell")
        ):
            raise ValueError("water distance rules require water cells")
        parent = entities[parent_id]["physical_class"]
        if (
            "mixed" not in (parent, rule["physical_class"])
            and parent != rule["physical_class"]
        ):
            raise ValueError("rule physical class is incompatible with its parent")
        if any(
            "mixed"
            not in (children[t["entity_id"]]["physical_class"], rule["physical_class"])
            and children[t["entity_id"]]["physical_class"] != rule["physical_class"]
            for t in output
        ):
            raise ValueError("rule physical class is incompatible with its target")
        result.append(dict(rule, features=dict(inputs), targets=output))
    return children, result
