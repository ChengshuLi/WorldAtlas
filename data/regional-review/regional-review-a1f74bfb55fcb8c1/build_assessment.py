#!/usr/bin/env python3
"""Rebuild the issue 496 evidence inventory from pinned issue/source inputs.

Inputs are downloaded to /tmp by the README restoration commands. Output is
confined to this owned packet. No baseline files are written.
"""
import csv, gzip, hashlib, json, math, pathlib, re, sys, unicodedata, subprocess
import release_pin_audit

ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
SCOPE = json.loads((HERE / "scope.json").read_text())
IDS = set(SCOPE["member_location_ids"])
def pinned(path):
    return subprocess.check_output(["git", "show", f"{release_pin_audit.V5_COMMIT}:data/{path}"], cwd=ROOT)

world_index = json.loads(pinned("world-index.json"))
features = {}
for filename in world_index["parts"]:
    part = json.loads(pinned(filename))
    for f in part["features"]:
        if f["properties"]["id"] in IDS:
            features[f["properties"]["id"]] = f
if set(features) != IDS:
    raise SystemExit(f"world-index mismatch: missing={sorted(IDS-set(features))}; extra={sorted(set(features)-IDS)}")

hierarchy = {x["id"]: x for x in json.loads(pinned("hierarchy.json"))}
all_locations = {}
for filename in world_index["parts"]:
    part = json.loads(pinned(filename))
    all_locations.update({f["properties"]["id"]:f["properties"] for f in part["features"]})

source_specs = {
 "gb:ECU:ADM2": {"url":"https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/ECU/ADM2/geoBoundaries-ECU-ADM2.geojson", "path":"sources/geoboundaries-ECU-ADM2-2019.geojson.gz", "compressed_sha256":"afda62cc58aae797b8152c19d8307cbd21b1fbd6e9ac9ede23856896711693d2", "vintage":"2019", "license":"Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)", "expected_sha256":"3bec5261a078ec78ef1d24d175fa1ec8f619dc887e59f1cfe39fefba65cd4c76", "metadata_path":"sources/geoboundaries-ECU-ADM2-2019-metadata.json", "metadata_sha256":"969a57b7298d7e71205963b33b8aa3222b4bab26c24481e7de286f3a0681acb0", "metadata_url":"https://github.com/wmgeolab/geoBoundaries/blob/9469f09/releaseData/gbOpen/ECU/ADM2/geoBoundaries-ECU-ADM2-metaData.json", "canonical_role":"Cantons, with a separately coded Zona No Delimitada record", "official_producer":"INEC — Instituto Nacional de Estadística y Censos, Ecuador; OCHA ROLAC", "official_source_dataset":"https://data.humdata.org/dataset/ecuador-admin-level-2-boundaries", "source_update_date":"2023-01-19", "declared_admin_unit_count":224},
 "gb:PER:ADM2": {"url":"https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/PER/ADM2/geoBoundaries-PER-ADM2.geojson", "path":"../regional-review-d2dae235991eaa49/sources/geoboundaries-PER-ADM2-2020.geojson.gz", "compressed_sha256":"047541aa4fe6d33e2d2246b8ea2a518eaf6fc6f9e2bbc241147cb4587b67e44e", "vintage":"2020", "license":"Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)", "expected_sha256":"58d0720bc01abd27bd02fb73d2ee8443fc6067352d97b752d100a18e3b97bb58", "metadata_path":"../regional-review-d2dae235991eaa49/sources/geoboundaries-PER-ADM2-metadata.json.gz", "metadata_sha256":"d6f5b546a17b37172d5e818051c3bc79dedd522d337698381ec2a23f768539ba", "metadata_url":"https://github.com/wmgeolab/geoBoundaries/blob/9469f09/releaseData/gbOpen/PER/ADM2/geoBoundaries-PER-ADM2-metaData.json", "canonical_role":"Provinces", "official_producer":"Instituto Geográfico Nacional, Peru; OCHA ROLAC", "official_source_dataset":"https://data.humdata.org/dataset/limites-de-peru", "source_update_date":"2023-01-19", "declared_admin_unit_count":196},
}
upstream = {}
for source_id, spec in source_specs.items():
    source_path = (HERE / spec["path"]).resolve()
    stored = source_path.read_bytes()
    if hashlib.sha256(stored).hexdigest()!=spec["compressed_sha256"]:
        raise SystemExit(f"stored source hash mismatch for {source_id}")
    raw = gzip.decompress(stored)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != spec["expected_sha256"]:
        raise SystemExit(f"source hash mismatch for {source_id}: {digest}")
    doc = json.loads(raw)
    meta_stored=(HERE/spec["metadata_path"]).resolve().read_bytes()
    meta_raw=gzip.decompress(meta_stored) if spec["metadata_path"].endswith(".gz") else meta_stored
    if hashlib.sha256(meta_raw).hexdigest()!=spec["metadata_sha256"]:
        raise SystemExit(f"metadata hash mismatch for {source_id}")
    spec["metadata_bytes"]=len(meta_raw)
    spec["upstream_metadata"]=json.loads(meta_raw)
    upstream[source_id] = {f["properties"]["shapeID"]:f for f in doc["features"]}
    spec["bytes"] = len(raw)
    spec["sha256"] = digest
    spec["upstream_feature_count"] = len(doc["features"])
    spec["crs"] = "WGS 84 (EPSG:4326; GeoJSON default)"

def norm(s):
    s=unicodedata.normalize("NFKD",str(s or "")).casefold()
    return "".join(c for c in s if not unicodedata.combining(c) and c.isalnum())

ecu_json=json.loads((HERE/"sources/ecu-admin2-official-roster.json").read_text())
if len(ecu_json["rows"])!=224 or len({r["ADM2_PCODE"] for r in ecu_json["rows"]})!=224:
    raise SystemExit("INEC Ecuador ADM2 roster count/code uniqueness changed")
ecu_rows=ecu_json["rows"]
ecu_latest_json=json.loads((HERE/"sources/ecu-admin2-gazetteer-2024.json").read_text())
if len(ecu_latest_json["rows"])!=223 or len({r["ADM2_PCODE"] for r in ecu_latest_json["rows"]})!=223:
    raise SystemExit("2024 Ecuador COD-AB ADM2 gazetteer count/code uniqueness changed")
ecu_latest_rows=ecu_latest_json["rows"]
inei_rows=list(csv.DictReader((HERE/"sources/inei-2019-province-roster-pp45-49.csv").open(encoding="utf-8")))
if len(inei_rows)!=196:
    raise SystemExit("INEI Peru province roster must have 196 rows, including combined Callao province/dept entry")

def positions(geom):
    t, c = geom["type"], geom["coordinates"]
    if t == "Polygon": return [c]
    if t == "MultiPolygon": return c
    raise ValueError(t)

def geom_summary(geom):
    polys=positions(geom); coords=[p for poly in polys for ring in poly for p in ring]
    return {"geometry_type":geom["type"], "polygon_components":len(polys),
            "rings":sum(len(poly) for poly in polys),
            "interior_rings":sum(max(0,len(poly)-1) for poly in polys),
            "coordinate_count":sum(len(r) for p in polys for r in p),
            "bbox":[min(p[0] for p in coords),min(p[1] for p in coords),max(p[0] for p in coords),max(p[1] for p in coords)]}

def area_and_bbox(geom):
    # Lon/lat shoelace is a screening value only; do not present as surveyed area.
    total=0.0
    for poly in positions(geom):
        for ring in poly:
            total += abs(sum(ring[i][0]*ring[(i+1)%len(ring)][1]-ring[(i+1)%len(ring)][0]*ring[i][1] for i in range(len(ring)))/2)
    return total

def parent_chain(feature):
    p=feature["properties"]; chain=[]; pid=p["parent_id"]; seen=set()
    while pid:
        if pid in seen: raise SystemExit(f"parent cycle from {p['id']}")
        seen.add(pid)
        q=all_locations.get(pid) or hierarchy.get(pid)
        if q is None:
            chain.append({"id":pid,"missing_from_pinned_records":True}); break
        chain.append({"id":pid,"name":q.get("name"),"level":q.get("level","location" if pid in all_locations else None),"parent_id":q.get("parent_id"),"metadata":q.get("metadata",{})})
        pid=q.get("parent_id")
    return chain

physical_screen_path=HERE/"gshhg-scope-screen.json"
physical_screen=json.loads(physical_screen_path.read_text()) if physical_screen_path.exists() else None
decisions=[]; parent_ids=set(); counts={}
for id in sorted(IDS):
    f=features[id]; p=f["properties"]; m=p["metadata"]; sid=m["source_id"]
    src=source_specs[sid]; sf=upstream[sid].get(m["original_id"])
    if sf is None: raise SystemExit(f"upstream source feature missing for {id} / {m['original_id']}")
    chain=parent_chain(f)
    for anc in chain:
        if anc["level"] in ("province","area"): parent_ids.add(anc["id"])
    counts[sid]=counts.get(sid,0)+1
    current=geom_summary(f["geometry"]); source=geom_summary(sf["geometry"])
    source_names=sf["properties"].get("shapeName")
    parent_obj=all_locations.get(p.get("parent_id")) or hierarchy.get(p.get("parent_id")) or {}
    atlas_parent_name=parent_obj.get("name")
    official_crosswalk=None
    if sid=="gb:ECU:ADM2":
        candidates=[r for r in ecu_rows if norm(p["name"]) in {norm(r.get(k)) for k in ("ADM2_ES","ADM2_REF","ADM2ALT1_ES","ADM2ALT2_ES")}]
        parent_matches=[r for r in candidates if norm(atlas_parent_name)==norm(r.get("ADM1_ES"))]
        chosen=parent_matches[0] if len(parent_matches)==1 else candidates[0] if len(candidates)==1 else None
        if chosen:
            latest_candidates=[r for r in ecu_latest_rows if norm(p["name"])==norm(r.get("ADM2_ES")) and norm(atlas_parent_name)==norm(r.get("ADM1_ES"))]
            official_crosswalk={"authority":"INEC Ecuador / OCHA ROLAC COD-AB tabular ADM2 sources (2023 and latest gazetteer resource, 2024)","official_code":chosen.get("ADM2_PCODE"),"official_unit_name":chosen.get("ADM2_ES"),"official_reference_name":chosen.get("ADM2_REF"),"official_parent_name":chosen.get("ADM1_ES"),"official_parent_code":chosen.get("ADM1_PCODE"),"candidate_count_by_name":len(candidates),"candidate_selected_by_current_parent":len(parent_matches)==1,"current_atlas_parent":atlas_parent_name,"parent_matches_2023_official":norm(atlas_parent_name)==norm(chosen.get("ADM1_ES")),"latest_2024_gazetteer_match_count_by_name_and_parent":len(latest_candidates),"latest_2024_gazetteer_code":latest_candidates[0].get("ADM2_PCODE") if len(latest_candidates)==1 else None,"latest_2024_gazetteer_admin1":latest_candidates[0].get("ADM1_ES") if len(latest_candidates)==1 else None,"method":"Match 2023 ADM2_ES/ADM2_REF/alternate names; disambiguate duplicated names (Bolívar) with parent code/name. Compare independently against exact 2024 ADM2_ES and ADM1_ES. Absence from the newer table is reported as a source-vintage discrepancy, not as proof the physical territory disappeared."}
    elif sid=="gb:PER:ADM2":
        candidates=[r for r in inei_rows if norm(p["name"])==norm(r["province"])]
        if len(candidates)==1:
            chosen=candidates[0]
            special=norm(atlas_parent_name)=="elcallao" and norm(chosen["department"])=="provconstdelcallao"
            official_crosswalk={"authority":"INEI Bulletin 26 (2020), official province/dept roster updated through 2019-12-31, printed pp.45–49; source bytes in sibling #497 packet","official_code":chosen["ubigeo"],"official_unit_name":chosen["province"],"official_parent_name":chosen["department"],"current_atlas_parent":atlas_parent_name,"candidate_count_by_name":1,"parent_matches_official":norm(atlas_parent_name)==norm(chosen["department"]),"special_parent_alias_candidate":special,"method":"NFKD/casefold exact province-name match against all 196 official province records. Callao is the combined constitutional-province/department record."}
    decisions.append({
      "location_id":id,"name":p["name"],"source_country":sid[3:6],
      "current_source_role":m.get("source_role"),"original_source_id":m.get("original_id"),
      "source_name":source_names,"source_admin_type":sf["properties"].get("shapeType"),
      "source_shape_group":sf["properties"].get("shapeGroup"),
      "source_url":src["url"],"source_vintage":src["vintage"],"source_license":src["license"],
      "source_geometry":source,"current_atlas_geometry":current,
      "longitude_degree_area_screen_only":round(area_and_bbox(f["geometry"]),8),
      "full_parent_chain":chain,
      "official_administrative_crosswalk":official_crosswalk,
      "administrative_role_assessment":f"Current reference maps to an ADM2 source feature whose publisher metadata names the official underlying producer(s) and canonical administrative role {src['canonical_role']}. It supports administrative identity only; it does not independently establish Atlas location granularity, complete settlement/land coverage, or the semantic suitability of the area/province tiers.",
      "source_display_name_match":{"exact":p["name"]==source_names,"atlas_name":p["name"],"source_name":source_names,"note":"Non-exact source strings include likely UTF-8 mojibake; current-name accuracy requires official gazetteer verification." if p["name"]!=source_names else None},
      "settlement_review":"unresolved: no authoritative settlement inventory, urban-area overlay, or explicit non-settlement territory source was inspected for this unit in this tranche.",
      "island_and_disconnected_land_review":"unresolved: source component/ring counts are inventoried, but no national authoritative coastline/island gazetteer was cross-matched. Components may be enclaves, detached administrative islands, or source topology artifacts.",
      "physical_source_screen":physical_screen["per_location"][id] if physical_screen else {"status":"not_run"},
      "decision":"correction_needed" if id=="gb:ECU:ADM2:8360857B1829680752404" else "insufficient_evidence",
      "unresolved":"Independent official administrative boundary source/vintage and its license; named settlement and built-up-area completeness; national/island/coastal physical-geography comparison; source-to-current geometry/topology differences and neighboring consistency. Political reference-owner metadata is not treated as physical geography or historical sovereignty evidence."
    })

all_descendants={}
for location_id,q in all_locations.items():
    pid=q.get("parent_id"); seen=set()
    while pid and pid not in seen:
        seen.add(pid); all_descendants.setdefault(pid,[]).append(location_id)
        anc=all_locations.get(pid) or hierarchy.get(pid)
        pid=anc.get("parent_id") if anc else None
parents=[]
for pid in sorted(parent_ids):
    p=all_locations.get(pid) or hierarchy.get(pid)
    chain=[]; curr=p
    while curr and curr.get("parent_id"):
        q=all_locations.get(curr["parent_id"]) or hierarchy.get(curr["parent_id"])
        if not q: chain.append({"id":curr["parent_id"],"missing":True}); break
        chain.append({"id":q["id"],"name":q.get("name"),"level":q.get("level"),"parent_id":q.get("parent_id"),"metadata":q.get("metadata",{})})
        curr=q
    parents.append({"id":pid,"name":p.get("name"),"level":p.get("level"),"declared_child_count":p.get("metadata",{}).get("child_count"),"current_descendant_location_count":len(all_descendants.get(pid,[])),"member_location_count_in_scope":sum(1 for loc in features if loc in all_descendants.get(pid,[])),"metadata":p.get("metadata",{}),"parent_chain":chain,"decision":"insufficient_evidence","unresolved":"Tier purpose and complete member-derived footprint require independent semantic, source, settlement and neighbor review; parent labels and complete chains do not certify purpose."})
    area=next((a for a in SCOPE["area_scopes"] if a["id"]==pid),None)
    if area:
        parents[-1]["area_workload_counts"]={"full_area_location_count":area["full_area_location_count"],"owned_member_location_count":area["owned_member_location_count"],"partial":area["partial"]}

assessment={
 "issue":496,"snapshot_date":"2026-10-03","region_id":"framework:region:western-south-america:7fe9d26228d5",
 "release_pins":{"release":"geography:review:df86cbaeaf2e18f16ddf2906ef089768baac22f4428e28ed0a4724296cbb413e","hierarchy_sha256":"03d23534f87cdd0582bcb228780f00f65090bec2e8a760acbab528383f28549d","footprints_sha256":"2ac42eeb9fef8af923a0d4c4e55af49ca0a103de891ffbfb2c1181ad75950286","macro_certificate_sha256":"979afaf22e10dc936ecfe80a8cd288b2ef33d8c7bf509aba9fae4255e3d94d6e","region_geometry_sha256":SCOPE["frozen_region_geometry_sha256"],"region_member_ids_sha256":SCOPE["frozen_region_member_ids_sha256"]},
 "scope":{"member_count":len(IDS),"scope_sha256":hashlib.sha256("\n".join(sorted(IDS)).encode()).hexdigest(),"areas":SCOPE["area_scopes"],"source_counts":counts,"not_a_published_partition":True},
 "sources":source_specs,
 "source_role_notes":{"Ecuador":"Pinned geoBoundaries metadata identifies INEC and OCHA ROLAC as producers, canonical ADM2 role Cantons, 2019 vintage, source data updated 2023-01-19, CC BY 3.0 IGO, declared unit count 224. The downloaded feature file has 223 shapes. Official INEC/OCHA 2023 tabular data has 224 ADM2 rows and 2023 assignment fields; the latest 2024 COD-AB gazetteer has 223 rows. Every assigned ID has a matched source/official candidate except the separately classified remainder Las Golondrinas has no row in the newer gazetteer. The official 2023 table places Las Golondrinas (EC9001) under Zona No Delimitada, whereas the Atlas parent is Imbabura; 2024 has no ADM2 row for it. The evidence supports a source-role and effective-date conflict, not a unilateral parent edit. The two Bolívar homonyms are disambiguated by the pinned Carchi parent and code EC0402. Manga del Cura is in sibling #495 and also absent from the pinned 2019 shape collection despite its metadata count.","Peru":"Pinned geoBoundaries metadata identifies Peru's Instituto Geográfico Nacional and OCHA ROLAC as producers, canonical ADM2 role Provinces, 2020 vintage, source data updated 2023-01-19, CC BY 3.0 IGO, declared unit count 196. Download contains 196 features and all 115 assigned IDs. Every distinct location name matches the official INEI Bulletin 26 (2020) roster of 196 provinces current at 2019-12-31; three upstream strings are mojibake, while INEI independently confirms Atlas spellings. `Lima`/MML and `Callao` special parent chains remain role/extent questions; no physical or settlement completeness conclusion follows from the administrative match. The complete Peru-area partition and Loreto ecological-fragment issue are detailed in merged PR #565."},
 "source_completeness_findings":[{"country":"ECU","source_feature_count":223,"metadata_declared_count":224,"official_INEC_tabular_ADM2_count":224,"current_full_area_admin_source_count":224,"assigned_here":113,"outside_packet_mapped_id":"gb:ECU:ADM2:8360857B97342174923698","outside_packet_name":"Manga del Cura","assigned_packet":"#495 (held by another worker; ID not in #496 scope)","finding":"Pinned geoBoundaries collection has one fewer feature than both its metadata declaration and the official INEC/COD-AB tabular count. The current complete Ecuador+Galápagos member ID family nevertheless includes Manga del Cura, which the sibling #495 worker owns. INEC identifies it as a distinct Zona No Delimitada (EC9003), not a canton. Coordinate its exact source restoration/role and extent with #495; do not infer that it is physically or legally part of neighboring Manabí from parent assignment alone."},{"country":"PER","source_feature_count":196,"metadata_declared_count":196,"official_INEI_province_count":196,"current_full_area_admin_source_ids":193,"assigned_here":115,"sibling_497_whole_admin_source_ids":78,"sibling_497_ecological_fragments":11,"finding":"The 193 source province IDs in whole ADM2 locations plus three remaining source province identities (Loreto, Maynas, Requena) represented by eleven RESOLVE ecoregion fragments in sibling issue #497 account for all 204 current Peru-area members. PR #565 reports approximate source area-mass checks only and leaves exact partition/alignment unresolved; follow its documented coordination with #489."}],
 "administrative_exceptions":[{"location_id":"gb:ECU:ADM2:8360857B1829680752404","name":"Las Golondrinas","GB_current_parent":"framework:province:imbabura:5b3789120dfb","INEC_2023_code":"EC9001","INEC_2023_ADM1":"Zona No Delimitada","INEC_2024_gazetteer_match":False,"finding":"The 2019 geoBoundaries source calls this ADM2 unit a Canton and Atlas groups it under Imbabura. The official 2023 INEC/OCHA table instead identifies EC9001 as part of the special remainder Zona No Delimitada; the later 2024 COD-AB gazetteer does not list it at ADM2. Its effective legal/source status and whole-area physical boundary therefore remain unresolved. Flag a bounded source/role/parent follow-up; do not edit geometry or parent until dated authoritative source and complete land coverage are reconciled."},{"location_id":"gb:ECU:ADM2:8360857B4480682421183","name":"Bolivar","finding":"Name-only joins are ambiguous: the official roster has Bolívar (EC0402, Carchi) and Bolívar (EC1302, Manabí). The pinned parent Carchi selects EC0402, so this source crosswalk supports the existing identity and is not a parent mismatch. Future joins must include parent/code, never name alone."}],
 "geometry_edge_cases":{"current_type_counts":{"Polygon":225,"MultiPolygon":3},"multi_component_or_interior_ring_locations":["gb:ECU:ADM2:8360857B73941749048341","gb:ECU:ADM2:8360857B96374734157472","gb:ECU:ADM2:8360857B49822942031092","gb:ECU:ADM2:8360857B665042104792","gb:ECU:ADM2:8360857B37850433241159","gb:ECU:ADM2:8360857B40737212656211","gb:ECU:ADM2:8360857B67239224798881","gb:PER:ADM2:86281439B246740541536"],"finding":"Three multipart locations are Galápagos cantons; their 14 combined current components cannot be named or certified complete from counts. Five interior-ring geometries occur in mainland Ecuador/Peru units and need hydrography/topology review to distinguish water holes from enclaves, source artifacts or omitted land. The location rows retain individual component/ring counts and bboxes."},
 "locations":decisions,"parents":parents,
 "neighbor_consistency":{"decision":"unresolved","note":"The three declared areas are partial workload partitions (Ecuador 110/221; Peru 115/204), not new geographic units. The remaining Ecuador and Peru children are assigned to other packets; Galápagos has 3/3. #496 and #495 IDs are disjoint; #495 currently owns the Ecuador-side Manga del Cura source gap and the Manabí parent cohort. No outer boundary was edited. Compare full source families and regional neighboring areas Colombia, Brazil, Bolivia and Chile during coordinated integration; this packet has not independently reconciled shared-region edges."},
 "methods":{"inventory":"Exact IDs from issue 496 JSON workload block were matched to current world-index features, then source_id + original_id was matched to the pinned geoBoundaries feature. Ecuador official ADM2 attributes were crosswalked to the retained INEC/OCHA 224-row table by name, reference aliases, and parent code/name, explicitly disambiguating duplicate Bolívar names. Peru province names were checked against the 196-row INEI official roster extract used by merged sibling packet #497. Full parent links were followed through location/province/area/region/subcontinent/continent. All 228 matches required; no ID was omitted.","geometry":"Inventoried current atlas and original-source geometry type, multipart count, ring count, interior-ring count, vertex count and geographic bbox. Degree-coordinate shoelace sum is included only as an anomaly-screening statistic; not an area estimate. No source/current geometry was rewritten or repaired.","limits":"This is source and scope screening, not formal validity or settlement/coastline completeness certification. GSHHG centroid screening is a coarse independent physical-land signal; it does not prove boundaries or completeness. Official administrative identity is stronger than settlement/physical completeness; all missing evidence remains explicitly listed."},
 "decision_summary":{"assessed":len(decisions),"administrative_identity_crosswalked":sum(1 for x in decisions if x["official_administrative_crosswalk"]),"justified":0,"correction_needed":sum(1 for x in decisions if x["decision"]=="correction_needed"),"insufficient_evidence":sum(1 for x in decisions if x["decision"]=="insufficient_evidence"),"per_location_decision_recorded":len(decisions)},
 "follow_up":"PR 2 extends independent physical-land screening over all assigned IDs and records blocked child issue #575 for dated source restoration for Las Golondrinas. Settlement, authoritative island inventory and boundary topology remain unresolved; preserve those gaps and do not close #496 until each assigned subject has sourced support or a bounded follow-up."
}
(HERE/"assessment.json").write_text(json.dumps(assessment,ensure_ascii=False,indent=2)+"\n")
release_pin_audit.load_v5_context(ROOT, SCOPE, assessment)
release_pin_audit.v5_world_inventory(ROOT, SCOPE, assessment)
if release_pin_audit.v5_footprints_sha256(ROOT)["sha256"] != assessment["release_pins"]["footprints_sha256"]:
    raise SystemExit("canonical Node footprint hash differs from the assigned V5 catalog")
print(json.dumps({"locations":len(decisions),"parents":len(parents),"source_counts":counts,"decision_summary":assessment["decision_summary"]},indent=2))
