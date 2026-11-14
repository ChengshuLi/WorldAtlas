"""Resolve geographic selection rules against current land components."""

from shapely.geometry import shape

from worldatlas.map_build.inputs.features import (
    assignment_selection,
    affiliation_selection,
    feature_geometry,
)


def resolve_assignments(rules, features, components, bindings, *, protected=()):
    """Return current component claims from source-neutral geographic operations.

    Working rules have one relation and imported feature. Archived inputs retain
    their original compound selections, exclusions and projected-coordinate queries.
    """
    by_id = {f["feature_id"]: f for f in features}
    if len(by_id) != len(features):
        raise ValueError("duplicate geographic feature ID")
    codes = {
        b["entity_id"]: b["code"] for b in bindings if b["physical_class"] == "land"
    }
    protected = set(protected)
    geometries, profiles = {}, {}

    def geometry(ident):
        if ident not in by_id:
            raise ValueError(
                "component selection refers to a missing feature: " + ident
            )
        if ident not in geometries:
            value = feature_geometry(
                by_id[ident],
                ("Point", "Polygon", "MultiPolygon"),
                coordinate_reference=by_id[ident].get(
                    "coordinate_reference", "OGC:CRS84"
                ),
            )
            parsed = shape(value)
            if parsed.is_empty or not parsed.is_valid:
                raise ValueError("component selection needs valid nonempty geometry")
            geometries[ident] = value
        return geometries[ident]

    def condition(record, candidates=None):
        ident, relation = record["feature_id"], record["relation"]
        value = geometry(ident)
        if relation == "point_component":
            if (
                value["type"] != "Point"
                or by_id[ident].get("coordinate_reference", "OGC:CRS84") != "OGC:CRS84"
            ):
                raise ValueError("point-component selection needs a point")
            return {components.point(*value["coordinates"])}
        if relation not in (
            "intersects_component",
            "contains_component",
            "majority_component",
        ):
            raise ValueError("unsupported component selection relation")

        def accepts(count, root):
            if relation == "intersects_component":
                return count > 0
            total = components.totals()[root]
            return (
                count * 2 > total
                if relation == "majority_component"
                else count == total
            )

        if value["type"] not in ("Polygon", "MultiPolygon"):
            raise ValueError("polygon-component selection needs a polygon")
        if by_id[ident].get("coordinate_reference", "OGC:CRS84") != "OGC:CRS84":
            operations = record["coordinate_operations"]
            if operations["source_coordinate_reference"] != by_id[ident].get(
                "coordinate_reference", "OGC:CRS84"
            ):
                raise ValueError(
                    "coordinate operation does not match the imported source coordinates"
                )
            if candidates is None:
                raise ValueError(
                    "projected contact needs a preceding geographic candidate selection"
                )
            counts = components.profile_projected(value, operations, candidates)
            if record.get("unknown_coordinates", "reject") == "reject" and any(
                v["unknown"] for v in counts.values()
            ):
                raise ValueError(
                    "coordinate operations do not cover all candidate component centers"
                )
            if record.get("unknown_coordinates", "reject") not in ("reject", "exclude"):
                raise ValueError("unsupported unknown-coordinate treatment")
            return {
                root
                for root, values in counts.items()
                if not values["unknown"]
                and not values["boundary"]
                and accepts(values["inside"], root)
            }
        if ident not in profiles:
            profiles[ident] = components.profile(value)
        counts = profiles[ident]
        return {root for root, count in counts.items() if accepts(count, root)}

    claims, assigned, identifiers = [], {}, set()
    for rule in rules:
        ident = (
            rule["assignment_id"] if "assignment_id" in rule else rule["affiliation_id"]
        )
        entity = rule["entity_id"]
        if ident in identifiers or entity not in codes:
            raise ValueError("duplicate assignment or unbound target entity")
        identifiers.add(ident)
        if "assignment_id" in rule:
            selection = {
                "combine": "all",
                "conditions": [assignment_selection(rule, by_id.keys())],
            }
        else:
            selection = affiliation_selection(rule, by_id.keys())
        conditions = selection["conditions"]
        selected = None
        for record in conditions:
            found = condition(
                record, selected if selection["combine"] == "all" else None
            )
            selected = (
                found
                if selected is None
                else selected & found
                if selection["combine"] == "all"
                else selected | found
            )
        for exclusion in selection.get("exclusions", []):
            selected -= condition(exclusion)
        included = [
            components.point(w["lon"], w["lat"])
            for w in selection.get("include_witnesses", [])
        ]
        excluded = [
            components.point(w["lon"], w["lat"])
            for w in selection.get("exclude_witnesses", [])
        ]
        if (
            len(set(included)) != len(included)
            or len(set(excluded)) != len(excluded)
            or set(included) & selected
            or not set(excluded) <= selected
        ):
            raise ValueError(
                "component inclusion/exclusion witnesses conflict with selected geometry"
            )
        selected = (selected - set(excluded)) | set(included)
        treatment = selection.get("protected_components", "reject")
        if treatment == "exclude":
            selected -= protected
        elif treatment != "reject":
            raise ValueError("unsupported protected-component treatment")
        elif selected & protected:
            raise ValueError(
                "regional affiliation would change a protected mainland component"
            )
        if not selected:
            raise ValueError(
                "geographic rule selects no current land components: " + ident
            )
        for root in selected:
            if root in assigned and assigned[root] != entity:
                raise ValueError(
                    "geographic rules assign one component to different entities"
                )
            assigned[root] = entity
        claims.append(
            {
                (
                    "assignment_id" if "assignment_id" in rule else "affiliation_id"
                ): ident,
                "entity_id": entity,
                "entity_code": codes[entity],
                "component_ids": sorted(selected),
            }
        )
    return {"claims": claims, "component_entities": assigned}
