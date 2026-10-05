#!/usr/bin/env python3
"""Rebuild the issue #457 subject ledger from its pinned baseline and sources."""
import hashlib
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
DATA = ROOT / "data"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decompressed_sha(path):
    return hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest()


def canonical_ring(points):
    # Round to six decimal degrees, then remove ring start/direction dependence.
    ring = [(round(float(point[0]), 6), round(float(point[1]), 6)) for point in points[:-1]]
    if not ring:
        return ()

    def rotate_min(values):
        doubled = values + values
        size, left, right, offset = len(values), 0, 1, 0
        while left < size and right < size and offset < size:
            a, b = doubled[left + offset], doubled[right + offset]
            if a == b:
                offset += 1
                continue
            if a > b:
                left += offset + 1
                if left <= right:
                    left = right + 1
            else:
                right += offset + 1
                if right <= left:
                    right = left + 1
            offset = 0
        start = min(left, right)
        return tuple(doubled[start:start + size])

    return min(rotate_min(ring), rotate_min(list(reversed(ring))))


def canonical_polygons(geometry):
    polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    return sorted(tuple(sorted(canonical_ring(ring) for ring in polygon)) for polygon in polygons)


def geometry_inventory(geometry):
    polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    points = []
    for polygon in polygons:
        for ring in polygon:
            points.extend(ring)
    return {
        "component_count": len(polygons),
        "ring_count": sum(len(polygon) for polygon in polygons),
        "hole_ring_count": sum(max(0, len(polygon) - 1) for polygon in polygons),
        "vertex_count": len(points),
        "bbox_degrees": [min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)] if points else None,
    }


def main():
    scope = json.loads((PACKET / "scope.json").read_text())
    expected_world_index = "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03"
    expected_hierarchy_file = "568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b"
    if sha(DATA / "world-index.json") != expected_world_index or sha(DATA / "hierarchy.json") != expected_hierarchy_file:
        raise SystemExit("Baseline geography pins changed; do not refresh this packet against a different baseline")
    if scope["release"]["hierarchy_sha256"] != "03d23534f87cdd0582bcb228780f00f65090bec2e8a760acbab528383f28549d" or scope["release"]["id"] != "geography:review:df86cbaeaf2e18f16ddf2906ef089768baac22f4428e28ed0a4724296cbb413e":
        raise SystemExit("Pinned scope release mismatch")
    manifest = json.loads((PACKET / "sources-manifest.json").read_text())
    for source in manifest["sources"]:
        if not source.get("path"):
            if not source.get("url") or source.get("sha256") is not None:
                raise SystemExit("A restoration-only source needs a URL and no claimed retained-byte hash")
            continue
        source_path = PACKET / source["path"]
        if sha(source_path) != source["sha256"] or source_path.stat().st_size != source["bytes"]:
            raise SystemExit("Retained source hash/length mismatch: " + source["path"])
        if source.get("uncompressed_sha256"):
            decoded = gzip.decompress(source_path.read_bytes())
            if hashlib.sha256(decoded).hexdigest() != source["uncompressed_sha256"] or len(decoded) != source["uncompressed_bytes"]:
                raise SystemExit("Retained uncompressed source hash/length mismatch: " + source["path"])
    index = json.loads((DATA / "world-index.json").read_text())
    units = {u["id"]: u for u in json.loads((DATA / "hierarchy.json").read_text())}
    features = {}
    part_hashes = {}
    for part in index["parts"]:
        path = DATA / part
        part_hashes[part] = sha(path)
        for feature in json.loads(path.read_text())["features"]:
            features[feature["id"]] = (feature, part)

    aafc_doc = json.loads((PACKET / "sources/aafc-terrestrial-ecoregions-v2.2.geojson").read_text())
    aafc = {str(f["properties"]["ECOREGION_ID"]): f["properties"] for f in aafc_doc["features"]}
    ecoprov_doc = json.loads((PACKET / "sources/aafc-ecoprovinces-baseline-arcgis-layer0.geojson").read_text())
    ecoprov = {round(float(f["properties"]["ECOPROVINCE_ID"]), 1): f["properties"] for f in ecoprov_doc["features"]}
    layer_doc = json.loads((PACKET / "sources/aafc-baseline-arcgis-layer0.geojson").read_text())
    layer_groups, v22_groups = {}, {}
    for feature in layer_doc["features"]:
        layer_groups.setdefault(str(feature["properties"]["ECOREGION_ID"]), []).append(feature)
    for feature in aafc_doc["features"]:
        v22_groups.setdefault(str(feature["properties"]["ECOREGION_ID"]), []).append(feature)
    if set(layer_groups) != set(v22_groups):
        raise SystemExit("AAFC source editions have different ecoregion ID sets")
    if any(any(f["properties"]["ECOREGION_NAME_EN"] != aafc[key]["ECOREGION_NAME_EN"] for f in layer_groups[key] + v22_groups[key]) for key in aafc):
        raise SystemExit("AAFC source editions have different English ecoregion names")
    equivalent_at_screen_precision = sum(
        sorted(canonical_polygons(f["geometry"]) for f in layer_groups[key]) ==
        sorted(canonical_polygons(f["geometry"]) for f in v22_groups[key]) for key in aafc
    )
    if equivalent_at_screen_precision != len(aafc):
        raise SystemExit("AAFC geometries differ at six-decimal-degree ring-normalized screening precision")
    gb_doc = json.loads((PACKET / "sources/geoboundaries-GRL-ADM1-9469f09.geojson").read_text())
    gb_by_id = {f["properties"]["shapeID"]: f for f in gb_doc["features"]}
    resolve_bytes = gzip.decompress((PACKET / "sources/resolve-scoped-ecoregions-0-417-418.geojson.gz").read_bytes())
    resolve_doc = json.loads(resolve_bytes)
    resolve_by_id = {str(f["properties"]["ECO_ID"]): f for f in resolve_doc["features"]}
    if set(resolve_by_id) != {"0", "417", "418"}:
        raise SystemExit("RESOLVE retained source query does not contain the exact three scoped source features")
    resolve_item = json.loads((PACKET / "sources/resolve-item-metadata.json").read_text())
    if resolve_item.get("extent", [None, None])[1][1] != 70:
        raise SystemExit("RESOLVE item extent changed; revisit the high-Arctic coverage finding")
    rows = []
    for location_id in scope["member_location_ids"]:
        if location_id not in features:
            raise SystemExit("Pinned ID missing from baseline: " + location_id)
        feature, part = features[location_id]
        props = feature["properties"]
        metadata = props.get("metadata", {})
        chain, parent = [], props.get("parent_id")
        while parent and parent not in [item["id"] for item in chain]:
            unit = units.get(parent)
            if not unit:
                chain.append({"id": parent, "missing": True})
                break
            chain.append({"id": parent, "name": unit.get("name"), "type": unit.get("type", unit.get("level"))})
            parent = unit.get("parent_id")
        source = metadata.get("source_id")
        source_row = aafc.get(source.rsplit(":", 1)[-1]) if source and source.startswith("aafc:ecoregion:") else None
        ecoprov_row = ecoprov.get(round(float(source_row["ECOPROVINCE_ID"]), 1)) if source_row else None
        gb_row = gb_by_id.get(metadata.get("original_id")) if source == "gb:GRL:ADM1" else None
        resolve_row = resolve_by_id.get(source.rsplit(":", 1)[-1]) if source and source.startswith("resolve:") else None
        member_ids = metadata.get("source_member_ids", [])
        member_crosswalk = {"status": "not-applicable", "source_member_ids": member_ids}
        identity_finding = "source identifier maps to a retained AAFC feature" if source_row else "unverified against a retained named source feature"
        if resolve_row:
            member_features = [gb_by_id.get(member_id.rsplit(":", 1)[-1]) for member_id in member_ids if member_id.startswith("gb:GRL:ADM1:")]
            source_member_id = metadata.get("original_id")
            expected_id = "gb:GRL:ADM1:" + str(source_member_id)
            resolve_name = resolve_row["properties"]["ECO_NAME"]
            member_name = member_features[0]["properties"]["shapeName"] if len(member_features) == 1 and member_features[0] else None
            expected_name = (member_name + " · " + resolve_name) if member_name else None
            member_valid = (len(member_ids) == 1 and member_ids[0] == expected_id and len(member_features) == 1
                            and member_features[0] is not None and props.get("name") == expected_name)
            member_crosswalk = {"status": "verified" if member_valid else "unverified", "source_member_ids": member_ids,
                                "original_id": source_member_id, "retained_geoBoundaries_name": member_name,
                                "expected_derived_name": expected_name, "resolve_source_name": resolve_name}
            identity_finding = "source feature and derived territorial member/name crosswalk verified" if member_valid else "source membership/name crosswalk unverified"
        elif gb_row:
            identity_finding = "retained geoBoundaries original ID and source name verified" if props.get("name") == gb_row["properties"]["shapeName"] else "retained geoBoundaries source name mismatch"
        elif source_row:
            identity_finding = "retained AAFC ecoregion ID and source name verified" if props.get("name", "").endswith(source_row["ECOREGION_NAME_EN"]) else "retained AAFC source name mismatch"
        if source_row:
            parent_matches = bool(ecoprov_row and units.get(props.get("parent_id"), {}).get("name") == ecoprov_row["ECOPROVINCE_NAME_EN"])
            assessment = "Location {} ({}) in parent province {}: AAFC ecoregion {} ({}) has source ecoprovince ID {} ({}); the parent name {} the official ecoprovince name. This supports the child's ecological lineage, while this jurisdiction-assigned portion's exact territorial clipping, island completeness and local granularity remain unverified (follow-up #887).".format(
                location_id, props.get("reference_owner"), props.get("parent_id"),
                source_row["ECOREGION_ID"], source_row["ECOREGION_NAME_EN"], source_row["ECOPROVINCE_ID"],
                ecoprov_row["ECOPROVINCE_NAME_EN"] if ecoprov_row else "unresolved ecoprovince name",
                "matches" if parent_matches else "does not match",
            )
        elif gb_row:
            source_inventory = geometry_inventory(gb_row["geometry"])
            atlas_inventory = geometry_inventory(feature["geometry"])
            assessment = "Greenland location {} ({}) from source {} names {}; the source/atlas component counts are {}/{} and vertex counts are {}/{}. Names {}. Boundary generalization, municipality/park role and physical-tier fit remain unverified (follow-up #888).".format(
                location_id, props.get("reference_owner"), source or "missing", props.get("name"), source_inventory["component_count"], atlas_inventory["component_count"],
                source_inventory["vertex_count"], atlas_inventory["vertex_count"],
                "match" if props.get("name") == gb_row["properties"]["shapeName"] else "differ",
            )
        elif resolve_row:
            source_name = resolve_row["properties"]["ECO_NAME"]
            atlas_piece_count = sum(1 for item in scope["member_location_ids"] if features[item][0]["properties"].get("metadata", {}).get("source_id") == source)
            assessment = "Greenland location {} ({}) is a portion of RESOLVE {} ({}) with {} atlas pieces in this scope; its native source geometry has {} components and {} vertices. This is a physical ecoregion source; the source item ends at 70 degrees north, so it cannot demonstrate this or neighboring Arctic locations' completeness above that latitude (follow-up #888).".format(
                location_id, props.get("reference_owner"), source, source_name, atlas_piece_count,
                geometry_inventory(resolve_row["geometry"])["component_count"], geometry_inventory(resolve_row["geometry"])["vertex_count"],
            )
        else:
            assessment = "Greenland location {} ({}) named {} cites RESOLVE source {}; its retained item metadata describes physical ecoregions but the item extent ends at 70 degrees north. This specific portion's source geometry, class meaning and completeness cannot be checked from that item snapshot (follow-up #888).".format(
                location_id, props.get("reference_owner"), props.get("name"), source
            )
        review_flags = []
        inventory = geometry_inventory(feature["geometry"]) if feature.get("geometry") else None
        if inventory and inventory["component_count"] > 1:
            review_flags.append("{} disconnected geometry components require source-level island/fragment review".format(inventory["component_count"]))
        if inventory and inventory["hole_ring_count"]:
            review_flags.append("{} interior rings require a source-backed explanation".format(inventory["hole_ring_count"]))
        if source_row:
            related = [other for other in scope["member_location_ids"] if features[other][0]["properties"].get("metadata", {}).get("source_id") == source]
            if len(related) > 1:
                review_flags.append("source ecoregion {} is represented by {} jurisdiction/area-specific atlas pieces; split and neighboring-scale correctness are unverified".format(source_row["ECOREGION_ID"], len(related)))
        if not metadata.get("hierarchy_overlap"):
            review_flags.append("no numeric source-to-parent overlap claim is retained on this location")
        geometry_bytes = json.dumps(feature.get("geometry"), sort_keys=True, separators=(",", ":")).encode()
        rows.append({
            "id": location_id,
            "name": props.get("name"),
            "reference_owner": props.get("reference_owner"),
            "geometry_type": feature.get("geometry", {}).get("type"),
            "geometry_inventory": geometry_inventory(feature["geometry"]) if feature.get("geometry") else None,
            "review_flags": review_flags,
            "geometry_sha256": hashlib.sha256(geometry_bytes).hexdigest(),
            "baseline_part": part,
            "baseline_part_sha256": part_hashes[part],
            "source_id": source,
            "source_name": metadata.get("source_name"),
            "source_url": metadata.get("source_url"),
            "license": metadata.get("license"),
            "reference_year": metadata.get("reference_year"),
            "administrative_level": metadata.get("administrative_level"),
            "source_role": metadata.get("source_role"),
            "location_basis": metadata.get("location_basis"),
            "original_id": metadata.get("original_id"),
            "source_member_ids": metadata.get("source_member_ids", []),
            "source_member_crosswalk": member_crosswalk,
            "geoBoundaries_source_name": gb_row["properties"]["shapeName"] if gb_row else None,
            "geoBoundaries_source_geometry_inventory": geometry_inventory(gb_row["geometry"]) if gb_row else None,
            "geoBoundaries_name_matches": props.get("name") == gb_row["properties"]["shapeName"] if gb_row else None,
            "geoBoundaries_geometry_matches_screen": canonical_polygons(feature["geometry"]) == canonical_polygons(gb_row["geometry"]) if gb_row else None,
            "resolve_source_name": resolve_row["properties"]["ECO_NAME"] if resolve_row else None,
            "resolve_source_geometry_inventory": geometry_inventory(resolve_row["geometry"]) if resolve_row else None,
            "resolve_source_license": resolve_row["properties"].get("LICENSE") if resolve_row else None,
            "parent_overlap_claim": metadata.get("hierarchy_overlap"),
            "reference_territory_overlap_claim": metadata.get("geographic_overlap"),
            "parent_chain": chain,
            "aafc_current_name_en": source_row.get("ECOREGION_NAME_EN") if source_row else None,
            "aafc_ecozone_id": source_row.get("ECOZONE_ID") if source_row else None,
            "aafc_ecoprovince_id": source_row.get("ECOPROVINCE_ID") if source_row else None,
            "aafc_ecoprovince_name_en": ecoprov_row.get("ECOPROVINCE_NAME_EN") if ecoprov_row else None,
            "parent_name_matches_official_ecoprovince": props.get("parent_id") and units.get(props.get("parent_id"), {}).get("name") == ecoprov_row.get("ECOPROVINCE_NAME_EN") if ecoprov_row else None,
            "aafc_current_source_feature_present": bool(source_row),
            "classification": "insufficient-evidence",
            "source_identity_finding": identity_finding if source else "missing source identity",
            "assessment": assessment,
            "confidence": "insufficient evidence for geographic correctness",
        })

    ids = scope["member_location_ids"]
    if len(ids) != 125 or len(set(ids)) != 125:
        raise SystemExit("Scope must contain exactly 125 unique IDs")
    if hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest() != scope["member_location_ids_sha256"]:
        raise SystemExit("Pinned member ID digest mismatch")
    if len(rows) != len(ids):
        raise SystemExit("Incomplete subject audit")
    if any(not row["aafc_current_source_feature_present"] for row in rows if row["source_id"].startswith("aafc:")):
        raise SystemExit("AAFC source ID missing from official current dataset")
    gb_rows = [row for row in rows if row["source_id"] == "gb:GRL:ADM1"]
    if len(gb_rows) != 2 or any(not row["geoBoundaries_name_matches"] for row in gb_rows):
        raise SystemExit("The two scoped Greenland geoBoundaries records did not match their pinned source identities")
    resolve_rows = [row for row in rows if row["source_id"].startswith("resolve:")]
    if len(resolve_rows) != 9 or any(row["source_member_crosswalk"]["status"] != "verified" for row in resolve_rows):
        raise SystemExit("Derived Greenland RESOLVE rows do not all map their original IDs, source-member IDs and names to retained geoBoundaries features")

    province_members = {}
    for row in rows:
        for parent in row["parent_chain"]:
            if parent.get("type") == "province" or ":province:" in parent["id"]:
                province_members.setdefault(parent["id"], {"name": parent["name"], "location_ids": []})["location_ids"].append(row["id"])
                break
    province_assessment = []
    for unit_id, entry in sorted(province_members.items()):
        unit = units[unit_id]
        member_rows = [row for row in rows if row["id"] in entry["location_ids"]]
        aa_ids = sorted({str(row["source_id"].rsplit(":", 1)[-1]) for row in member_rows if row["source_id"].startswith("aafc:")}, key=lambda x: int(x))
        aa_names = sorted({row["aafc_ecoprovince_name_en"] for row in member_rows if row["aafc_ecoprovince_name_en"]})
        aa_ep_ids = sorted({str(round(float(row["aafc_ecoprovince_id"]), 1)) for row in member_rows if row["aafc_ecoprovince_id"] is not None})
        source_ids = sorted({row["source_id"] for row in member_rows})
        if aa_names:
            matching = aa_names == [unit["name"]]
            finding = "Province {} ({}), children {}: the {} assigned AAFC ecoregion IDs {} map to official ecoprovince ID(s) {} and name(s) {}. The parent label {} the official source name, supporting source identity and tier naming; exact parent geometry containment, completeness and territory clipping remain unverified (follow-up #887).".format(
                unit_id, unit["name"], ", ".join(sorted(entry["location_ids"])), len(aa_ids), ", ".join(aa_ids), ", ".join(aa_ep_ids), ", ".join(aa_names), "matches" if matching else "does not match"
            )
        else:
            grl_names = sorted({row["geoBoundaries_source_name"] for row in member_rows if row["geoBoundaries_source_name"]})
            physical_names = sorted({row["resolve_source_name"] for row in member_rows if row["resolve_source_name"]})
            grl_sources = sorted({row["source_id"] for row in member_rows})
            finding = "Province {} ({}), children {}: the {} scoped locations trace to Greenland identities {}; geoBoundaries name match(es): {}; RESOLVE physical classes represented: {}. This supports the listed lineage but source/atlas boundary transformation, administrative versus physical tier fit, and coverage completeness remain open (follow-up #888).".format(
                unit_id, unit["name"], ", ".join(sorted(entry["location_ids"])), len(member_rows), ", ".join(grl_sources), ", ".join(grl_names) if grl_names else "none directly represented", ", ".join(physical_names) if physical_names else "none"
            )
        province_assessment.append({
            "id": unit_id, "name": unit["name"], "parent_area_id": unit.get("parent_id"),
            "basis": unit.get("metadata", {}).get("basis"), "framework_status": unit.get("metadata", {}).get("framework_status"),
            "source": unit.get("metadata", {}).get("source"), "scoped_location_count": len(entry["location_ids"]),
            "location_ids": sorted(entry["location_ids"]), "source_ids": source_ids,
            "aafc_ecoregion_ids": aa_ids, "official_ecoprovince_names": aa_names,
            "official_ecoprovince_ids": aa_ep_ids,
            "classification": "insufficient-evidence", "finding": finding,
        })
    area_assessment = [{
        "id": area["id"], "name": area["name"],
        "owned_scope_count": area["owned_member_location_count"],
        "full_current_area_count": area["full_area_location_count"],
        "partial_scope": area["partial"],
        "classification": "insufficient-evidence",
        "finding": "This packet reviews the pinned area portion only; full-area completeness and parent approval remain open. For the partial Greenland scope, do not infer the unowned members from this packet.",
    } for area in scope["area_scopes"]]

    assessment = {
        "scope_member_ids_sha256": scope["member_location_ids_sha256"],
        "baseline_commit": "4215fda0a40697bbdc4f9f0a229fffe7764aac55",
        "baseline_world_index_sha256": sha(DATA / "world-index.json"),
        "baseline_hierarchy_sha256": sha(DATA / "hierarchy.json"),
        "scope_count": len(ids),
        "assessed_count": len(rows),
        "assessment_method": "Pinned-ID join to baseline geography parts and hierarchy; source attributes cross-checked against retained official AAFC 2.2 GeoJSON. Geometry hashes are SHA-256 of compact sorted-key JSON serialization, not canonicalized geometric equivalence hashes.",
        "aafc_source_comparison": {
            "baseline_item_layer_feature_count": len(layer_doc["features"]),
            "official_v2_2_feature_count": len(aafc_doc["features"]),
            "unique_ecoregion_id_count_in_each": len(aafc),
            "source_feature_count_equal_for_each_id": all(len(layer_groups[key]) == len(v22_groups[key]) for key in aafc),
            "id_sets_equal": True,
            "english_names_equal_for_all_ids": True,
            "geometries_equal_after_ring_order_and_direction_normalization_at_1e_6_degree_rounding": equivalent_at_screen_precision,
            "method": "Compare polygon rings after rounding coordinates to six decimal degrees, normalizing ring start vertex and direction, and sorting rings/polygons. This is a source-edition screening comparison only; it is not a geodetic error bound, legal-boundary test, or validation of atlas territory clipping.",
            "baseline_layer_metadata_sha256": decompressed_sha(PACKET / "sources/aafc-arcgis-layer-metadata.json.gz"),
            "baseline_layer_response_sha256": sha(PACKET / "sources/aafc-baseline-arcgis-layer0.geojson"),
            "official_v2_2_sha256": sha(PACKET / "sources/aafc-terrestrial-ecoregions-v2.2.geojson"),
        },
        "areas": area_assessment,
        "provinces": province_assessment,
        "subjects": rows,
    }
    result = json.dumps(assessment, indent=2, ensure_ascii=False) + "\n"
    if "--write" in __import__("sys").argv:
        (PACKET / "subject-assessment.json").write_text(result)
    elif result != (PACKET / "subject-assessment.json").read_text():
        raise SystemExit("subject-assessment.json differs; run with --write to refresh after reviewing input changes")
    print("PASS: reproduced 125/125 subject rows and matched subject-assessment.json")


if __name__ == "__main__":
    main()
