"""Validate selected geographic operations and imported geometry before processing."""


def selection_feature_ids(selection):
    """Current selections use a list; frozen releases may use one feature ID."""
    return (
        selection["feature_ids"]
        if "feature_ids" in selection
        else [selection["feature_id"]]
    )


def assignment_selection(rule, features):
    """Validate one operation over the union of existing imported features."""
    selection = (
        {"relation": "majority_component", "feature_ids": rule["feature_ids"]}
        if "feature_ids" in rule
        else rule.get("selection")
    )
    # Read the earlier frozen format without mutating the archived selection.
    if isinstance(selection, dict) and set(selection) == {"relation", "feature_id"}:
        selection = {
            "relation": selection["relation"],
            "feature_ids": [selection["feature_id"]],
        }
    if (
        not isinstance(selection, dict)
        or set(selection) != {"relation", "feature_ids"}
        or selection["relation"]
        not in (
            "point_component",
            "intersects_component",
            "contains_component",
            "majority_component",
        )
        or not isinstance(selection["feature_ids"], list)
        or not selection["feature_ids"]
        or any(
            not isinstance(ident, str) or not ident.strip()
            for ident in selection["feature_ids"]
        )
        or len(set(selection["feature_ids"])) != len(selection["feature_ids"])
    ):
        raise ValueError(
            "assignment needs exactly one relation and distinct nonempty feature_ids"
        )
    if missing := set(selection["feature_ids"]) - features:
        raise ValueError(
            "assignment refers to a missing feature: " + str(sorted(missing))
        )
    return selection


def affiliation_selection(rule, features):
    """Read archived affiliation data and check its feature references."""
    selection = rule.get(
        "component_selection", rule.get("evidence", {}).get("component_selection")
    )
    if (
        not isinstance(selection, dict)
        or selection.get("combine") not in ("all", "any")
        or not isinstance(selection.get("conditions"), list)
        or not selection["conditions"]
    ):
        raise ValueError(
            "affiliation needs conditions and an all/any component selection"
        )
    references = set()
    for key in ("conditions", "exclusions"):
        if not isinstance(selection.get(key, []), list):
            raise ValueError("component selection conditions must be lists")
        for condition in selection.get(key, []):
            if (
                not isinstance(condition, dict)
                or condition.get("relation")
                not in ("point_component", "intersects_component", "contains_component")
                or not isinstance(condition.get("feature_id"), str)
            ):
                raise ValueError("invalid component selection condition")
            references.add(condition["feature_id"])
    if references - features:
        raise ValueError(
            "component selection refers to a missing feature: "
            + str(sorted(references - features))
        )
    return selection


def feature_geometry(feature, types, *, coordinate_reference="OGC:CRS84"):
    """Read imported geometry in the declared coordinates."""
    geometry = feature.get("geometry")
    if (
        not isinstance(geometry, dict)
        or geometry.get("type") not in types
        or feature.get("coordinate_reference", "OGC:CRS84") != coordinate_reference
    ):
        raise ValueError(f"feature needs imported geometry in {coordinate_reference}")
    return geometry


def selected_basins(domain):
    """Return basin/feature pairs; reject duplicate active selections."""
    features = {feature["feature_id"]: feature for feature in domain["features"]}
    if len(features) != len(domain["features"]):
        raise ValueError("duplicate geographic feature ID")
    result, identities = [], set()
    for basin in domain["basins"]:
        feature = features.get(basin["feature_id"])
        if feature is None:
            raise ValueError("basin refers to a missing geographic feature")
        feature_geometry(feature, ("Polygon", "MultiPolygon"))
        # Released selections retain their original direct raw-source reference.
        sources = (feature['source_id'],) if 'source_id' in feature else tuple(sorted(
            link['source_id'] for link in domain['construction_sources']
            if link['construction_id'] == feature['construction_id']))
        if not sources:
            raise ValueError('basin construction has no raw source references')
        identity = (sources, feature['source_feature_id'])
        if identity in identities:
            raise ValueError("a provider area is selected more than once")
        identities.add(identity)
        result.append((basin, feature))
    return result
