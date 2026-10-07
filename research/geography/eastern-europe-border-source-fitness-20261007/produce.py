#!/usr/bin/env python3
"""Bounded source-fitness overlay for the single #1344 candidate and its nine contacts."""
from __future__ import annotations
import argparse, csv, gzip, hashlib, json, math, sys
from importlib.machinery import SourceFileLoader
from collections import Counter
from pathlib import Path
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent
EXPECTED_BASELINE = "432c5b8e0ac9b9597738a31f5386569312c75966"
EXPECTED_CUSTODY_SHA = "db511bb8db98154ea189e6c0f8e3a6551277e68873084e0148e875a46e8cb01f"
FAMILY = "gap-source-batch:70c8e23708e01b28b207d2e8"
COMPONENT = "physical-component:e30c80444254d81f52df404c8a084164b44849c5a93d2abb7fc1212e31b030a8"
CANDIDATE = "physical-gap:1624:42:d40fef6eb0e28f8ab7556c90e2a934b6d2114f155c633c17d324cbf319058184"
EXPECTED_GEOMETRY_SHA = "d40fef6eb0e28f8ab7556c90e2a934b6d2114f155c633c17d324cbf319058184"
EXPECTED_FEATURE_SHA = "93441ce2d620d643d84d122715b3a9e635489843e8dffdeb8613ce0fe4daac90"
CONTACTS = [
    "gb:BLR:ADM2:67162791B30498032594927",
    "gb:POL:ADM2:97123803B24100086136213",
    "gb:POL:ADM2:97123803B33088815311851",
    "gb:POL:ADM2:97123803B66371363243422",
    "gb:UKR:ADM2:74538382B51634820959847",
    "gb:UKR:ADM2:74538382B5714887404176",
    "gb:UKR:ADM2:74538382B72123275564902",
    "gb:UKR:ADM2:74538382B9478118461291",
    "gb:UKR:ADM2:74538382B97249439308301",
]
PRODUCTS = {
    "BLR": ("gb:BLR:ADM2", "8d88002a6b05014da9af4dc1f33f8cb928d961b23c1912654cc056cddca5841a", 1138204, 118),
    "POL": ("gb:POL:ADM2", "c19830763e611df9b4b56bab55c0c856a9a33dc7b80a6d28fe611f3462e1f3ce", 2906313, 380),
    "UKR": ("gb:UKR:ADM2", "c102ab08775ce4dc25a64e133bb7726a1b50715d31140e9846eaad26602631cb", 698065, 495),
}
PARTS = {2: "93eeb8f5dab7d8ca6c86593f7ab7b1310312757abcef33d4e7200a270624a1bf",
         19: "baeade0e3ad11cdd65beb101e7b79284ae2b6ee8794f9b08e86631c7f20e6269",
         25: "dada55df1b7f0f2a2b307f4aea071d0e48791e3105875755fe74a292a6763394"}

class EvidenceError(ValueError): pass

def digest(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()
def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()
def obj_hash(value) -> str: return digest(canonical(value))
def read_json(path: Path): return json.loads(path.read_text())
def rows_gzip(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip(): yield json.loads(line)
def load_shared_geometry(inputs: Path):
    baseline=inputs/"baseline"
    area_module=SourceFileLoader("ellipsoidal_area",str(baseline/"ellipsoidal-area-code.json")).load_module()
    sys.modules["ellipsoidal_area"]=area_module
    return SourceFileLoader("evidence_geometry",str(baseline/"geometry-code.json")).load_module()

def area_m2(g, helper):
    if g.is_empty: return 0.0
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return helper.land_area_m2(g)
    if g.geom_type == "GeometryCollection":
        parts=[]
        for part in g.geoms:
            if part.geom_type=="Polygon": parts.append(part)
            elif part.geom_type=="MultiPolygon": parts.extend(part.geoms)
            elif part.geom_type=="GeometryCollection":
                for sub in part.geoms:
                    if sub.geom_type=="Polygon": parts.append(sub)
                    elif sub.geom_type=="MultiPolygon": parts.extend(sub.geoms)
        if not parts: return 0.0
        return helper.land_area_m2(unary_union(parts))
    return 0.0

def verify_custody(inputs: Path):
    cp = inputs / "source-custody.json"
    raw = cp.read_bytes()
    if EXPECTED_CUSTODY_SHA == "PENDING" or digest(raw) != EXPECTED_CUSTODY_SHA:
        raise EvidenceError("pinned source-custody manifest hash mismatch")
    custody = json.loads(raw)
    if custody.get("baseline_commit") != EXPECTED_BASELINE: raise EvidenceError("wrong input baseline")
    checked=[]
    for rec in custody["files"]:
        rel=rec["path"]
        if not rel.startswith("inputs/"): raise EvidenceError(f"custody path is outside owned input tree: {rel}")
        p=inputs / rel.removeprefix("inputs/")
        b=p.read_bytes()
        if len(b)!=rec["bytes"] or digest(b)!=rec["sha256"]: raise EvidenceError(f"whole-file custody mismatch: {rec['path']}")
        if rec.get("origin_blob_oid") and not rec.get("transport_path"):
            oid=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
            if oid!=rec["origin_blob_oid"]: raise EvidenceError(f"Git blob identity mismatch: {rec['origin_path']}")
        checked.append({"path":rec["path"],"bytes":len(b),"sha256":digest(b),"origin_path":rec.get("origin_path"),"origin_blob_oid":rec.get("origin_blob_oid")})
        if rec.get("transport_path"):
            tp=inputs / rec["transport_path"].removeprefix("inputs/")
            tb=tp.read_bytes()
            if len(tb)!=rec.get("transport_bytes") or digest(tb)!=rec.get("transport_sha256"): raise EvidenceError(f"source transport bytes mismatch: {rec['origin_path']}")
            toid=hashlib.sha1(b"blob "+str(len(tb)).encode()+b"\0"+tb).hexdigest()
            if toid!=rec.get("origin_blob_oid") or rec.get("origin_mode")!="100644": raise EvidenceError(f"source transport Git identity/mode mismatch: {rec['origin_path']}")
            checked.append({"path":rec["transport_path"],"bytes":len(tb),"sha256":digest(tb),"origin_path":rec["origin_path"],"origin_mode":rec["origin_mode"],"origin_blob_oid":toid})
    expected_checked=len(custody["files"])+sum(bool(rec.get("transport_path")) for rec in custody["files"])
    if len(checked)!=expected_checked: raise EvidenceError("incomplete custody inventory")
    return custody, checked

def extract_contact_features(inputs: Path):
    found=Counter(); features={}; source_file={}
    for part, expected in PARTS.items():
        path=inputs/f"baseline/atlas-part-{part}.json"; raw=path.read_bytes()
        if digest(raw)!=expected: raise EvidenceError(f"pinned current Atlas part changed: {part}")
        data=json.loads(raw)
        for f in data.get("features",[]):
            fid=f.get("id") or f.get("properties",{}).get("id")
            if fid in CONTACTS:
                found[fid]+=1; features[fid]=f; source_file[fid]={"path":str(path.relative_to(inputs)),"part":part,"part_sha256":expected,"feature_sha256":obj_hash(f)}
    if set(found)!=set(CONTACTS) or any(v!=1 for v in found.values()): raise EvidenceError(f"Atlas contact roster mismatch: {dict(found)}")
    return features, source_file

def source_products(inputs: Path, registry, catalogue):
    products={}; features_by_contact={}; summaries={}
    for country,(key,expected_sha,expected_bytes,expected_count) in PRODUCTS.items():
        raw=(inputs/f"source-products/geoBoundaries-{country}-ADM2_simplified.geojson").read_bytes()
        if len(raw)!=expected_bytes or digest(raw)!=expected_sha: raise EvidenceError(f"whole source product mismatch: {country}")
        data=json.loads(raw); feats=data.get("features",[])
        ids=[f.get("properties",{}).get("shapeID") for f in feats]
        if data.get("type")!="FeatureCollection" or len(feats)!=expected_count or any(not isinstance(x,str) or not x for x in ids) or len(set(ids))!=len(ids):
            raise EvidenceError(f"whole source feature inventory mismatch: {country}")
        row=registry.get(key)
        if not row or row.get("sha256")!=expected_sha or int(row.get("admUnitCount",-1))!=expected_count: raise EvidenceError(f"registry source identity mismatch: {country}")
        corpus=next((x for x in catalogue.get("products",[]) if x.get("key")==key),None)
        if not corpus or corpus.get("original_sha256")!=expected_sha or corpus.get("original_bytes")!=expected_bytes or corpus.get("feature_count")!=expected_count:
            raise EvidenceError(f"original source-corpus catalogue identity mismatch: {country}")
        if corpus.get("recorded_consumed_url")!=row.get("simplifiedGeometryGeoJSON") or str(corpus.get("source_represented_year_claim"))!=str(row.get("boundaryYearRepresented")) or corpus.get("recorded_license")!=row.get("boundaryLicense"):
            raise EvidenceError(f"source-corpus and baseline registry metadata disagree: {country}")
        by_shape=dict(zip(ids,feats)); products[country]={"data":data,"features":feats,"by_shape":by_shape,"registry":row,"raw_sha256":expected_sha}
        for fid in CONTACTS:
            if fid.split(":")[1]==country:
                sid=fid.split(":")[-1]
                if sid not in by_shape: raise EvidenceError(f"contact shapeID absent from complete original {country} source: {fid}")
                features_by_contact[fid]=by_shape[sid]
        summaries[country]={"product_key":key,"raw_bytes":len(raw),"raw_sha256":expected_sha,"feature_count":len(feats),"unique_shape_ids":len(set(ids)),"declared_crs_member":data.get("crs"),"coordinate_order_used":"GeoJSON [x,y], interpreted as longitude,latitude for diagnostic overlay; registry gives no per-feature positional accuracy","metadata":{k:row.get(k) for k in ("boundaryYearRepresented","boundaryCanonical","boundarySource","boundaryLicense","licenseDetail","licenseSource","boundarySourceURL","sourceDataUpdateDate","buildDate","admUnitCount","simplifiedGeometryGeoJSON")},"source_corpus_catalogue_entry":{k:corpus.get(k) for k in ("cohort","recorded_consumed_url","recorded_license","source_represented_year_claim","original_bytes","original_sha256","feature_count","metadata_sha256","original_metadata_file","partition_method","parts")}}
    if set(features_by_contact)!=set(CONTACTS): raise EvidenceError("source contact shapeID join incomplete")
    return products,features_by_contact,summaries

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--inputs",default="inputs"); ap.add_argument("--output",required=True); ap.add_argument("--candidate-override",default=None); ap.add_argument("--control",default=None)
    a=ap.parse_args(); inputs=Path(a.inputs).resolve(); output=Path(a.output).resolve()
    if output.exists(): raise EvidenceError(f"output already exists: {output}")
    custody, checked=verify_custody(inputs)
    acquisition_script=(inputs/"baseline/administrative-script.py").read_bytes()
    if b"row['simplifiedGeometryGeoJSON'] = rule['source_url'].replace('.geojson','_simplified.geojson')" not in acquisition_script or b"download(row['simplifiedGeometryGeoJSON'], path)" not in acquisition_script:
        raise EvidenceError("pinned administrative source acquisition script no longer binds the simplified product")
    geometry_helper=load_shared_geometry(inputs)
    registry=read_json(inputs/"baseline/administrative-registry.json")
    catalogue=read_json(inputs/"baseline/source-corpus-catalogue.json")
    current,contact_files=extract_contact_features(inputs)
    products,source_contacts,source_summaries=source_products(inputs,registry,catalogue)
    candidate_data=json.loads(gzip.decompress((inputs/"baseline/candidate-source.gz").read_bytes()))
    candidates=[f for f in candidate_data.get("features",[]) if f.get("id")==CANDIDATE]
    if len(candidates)!=1: raise EvidenceError(f"expected exactly one original full candidate: {len(candidates)}")
    candidate=candidates[0]
    if a.candidate_override:
        override=json.loads(Path(a.candidate_override).read_text())
        if override.get("id")!=CANDIDATE: raise EvidenceError("candidate override identity mismatch")
        candidate=override
    geom_hash=obj_hash(candidate["geometry"])
    if geom_hash!=EXPECTED_GEOMETRY_SHA: raise EvidenceError(f"candidate geometry binding mismatch: {geom_hash}")
    if obj_hash(candidates[0])!=EXPECTED_FEATURE_SHA: raise EvidenceError("candidate full feature binding mismatch")
    if candidate.get("properties",{}).get("area_m2") is None or not math.isclose(candidate["properties"]["area_m2"],860328102.1759481,rel_tol=0,abs_tol=1e-6): raise EvidenceError("candidate area declaration mismatch")
    candidate_geom=shape(candidate["geometry"])
    if candidate_geom.is_empty or candidate_geom.geom_type!="Polygon" or not candidate_geom.is_valid: raise EvidenceError("candidate original geometry is empty, invalid or not one Polygon")
    contacts_prop=candidate.get("properties",{}).get("exact_location_contacts",[])
    prop_ids=[x.get("id") for x in contacts_prop]
    if a.control=="omit-contact": prop_ids=prop_ids[:-1]
    elif a.control=="duplicate-contact": prop_ids=prop_ids+[prop_ids[0]]
    elif a.control=="foreign-subject": prop_ids=prop_ids+["gb:POL:ADM2:FOREIGN-CONTROL"]
    if len(prop_ids)!=len(set(prop_ids)): raise EvidenceError("duplicate candidate contact ID")
    if set(prop_ids)!=set(CONTACTS): raise EvidenceError("candidate contact roster missing or foreign relative to issue contract")
    feature_hashes={fid:obj_hash(current[fid]) for fid in CONTACTS}
    contact_results=[]; line_contacts={x["id"]:shape(x["geometry"]) for x in contacts_prop}
    for fid in CONTACTS:
        source=source_contacts[fid]; atlas=current[fid]; country=fid.split(":")[1]
        sg=shape(source["geometry"]); ag=shape(atlas["geometry"])
        if sg.is_empty or not sg.is_valid or ag.is_empty or not ag.is_valid: raise EvidenceError(f"invalid contact geometry, no repair attempted: {fid}")
        line=line_contacts[fid]
        source_meta=source.get("properties",{})
        current_meta=atlas.get("properties",{}).get("metadata",{})
        contact_results.append({"contact_id":fid,"country":country,"name":atlas.get("properties",{}).get("name"),"source_shape_id":source_meta.get("shapeID"),"atlas_source_id":current_meta.get("source_id"),"atlas_metadata_url":current_meta.get("source_url"),"atlas_reference_year":current_meta.get("reference_year"),"source_product_feature_sha256":obj_hash(source),"current_atlas_feature_sha256":feature_hashes[fid],"current_geometry_equals_simplified_source_topologically":ag.equals(sg),"current_geometry_equals_simplified_source_exact_coordinates":ag.equals_exact(sg,0),"sym_difference_area_m2":area_m2(ag.symmetric_difference(sg),geometry_helper),"candidate_contact_geometry_covers_candidate_line":ag.boundary.covers(line),"source_geometry_boundary_covers_candidate_line":sg.boundary.covers(line),"source_geometry_type":sg.geom_type,"current_atlas_geometry_type":ag.geom_type,"full_current_feature":atlas})
    # The accepted issue contract binds one complete family/component and nine contacts.
    # Reconcile that scope independently against the full candidate Feature and all nine full
    # current Atlas Feature bodies; do not reconstruct or rerun the global routing producer.
    # All original whole-source records are scanned; no clipping or geometry repair.
    source_rows=[]; country_metrics={}; all_country_geoms={}
    for country,(key,_,_,_) in PRODUCTS.items():
        product=products[country]; geoms=[]; invalid=0; intersects=0; positive=0; covering=0; overlap_area=0.0; contact_ids=[]
        for f in product["features"]:
            g=shape(f["geometry"])
            if g.is_empty or not g.is_valid or g.geom_type not in ("Polygon","MultiPolygon"):
                invalid+=1; source_rows.append({"country":country,"source_shape_id":f.get("properties",{}).get("shapeID"),"name":f.get("properties",{}).get("shapeName"),"geometry_valid":False,"candidate_intersects":None,"positive_intersection_area_m2":None})
                continue
            geoms.append(g); ix=g.intersects(candidate_geom); inter=g.intersection(candidate_geom) if ix else None; ar=area_m2(inter,geometry_helper) if ix else 0.0
            intersects+=int(ix); positive+=int(ar>1e-5); covering+=int(g.covers(candidate_geom)); overlap_area+=ar
            source_rows.append({"country":country,"source_shape_id":f.get("properties",{}).get("shapeID"),"name":f.get("properties",{}).get("shapeName"),"geometry_valid":True,"candidate_intersects":ix,"positive_intersection_area_m2":ar,"source_covers_whole_candidate":g.covers(candidate_geom)})
        if invalid: raise EvidenceError(f"{country} whole source has invalid geometries; no repairs attempted; {invalid} source rows prevent complete overlay")
        union=unary_union(geoms)
        inter_union=union.intersection(candidate_geom)
        union_area=area_m2(inter_union,geometry_helper)
        all_country_geoms[country]=union
        country_metrics[country]={"complete_source_features_scanned":len(product["features"]),"invalid_geometry_count":invalid,"candidate_intersecting_features":intersects,"positive_area_intersection_features":positive,"source_features_covering_entire_candidate":covering,"summed_feature_intersection_area_m2_overlap_may_be_double_counted":overlap_area,"dissolved_country_coverage_area_m2":union_area,"dissolved_country_candidate_coverage_fraction":union_area/area_m2(candidate_geom,geometry_helper),"dissolved_country_covers_entire_candidate":union.covers(candidate_geom)}
    all_source_union=unary_union(list(all_country_geoms.values()))
    all_cover=all_source_union.intersection(candidate_geom)
    total_area=area_m2(candidate_geom,geometry_helper)
    lakes_raw=(inputs/"source-products/natural-earth-10m-lakes.geojson").read_bytes()
    lakes_receipt=read_json(inputs/"baseline/lakes-receipt.json")
    retained_lakes=(inputs/"baseline/lakes-source.gz").read_bytes()
    if digest(retained_lakes)!=lakes_receipt.get("retained_sha256") or len(lakes_raw)!=lakes_receipt.get("original_bytes") or digest(lakes_raw)!=lakes_receipt.get("original_sha256"):
        raise EvidenceError("whole Natural Earth lake source does not match its retained receipt")
    lakes_data=json.loads(lakes_raw)
    lake_hits=[]; lake_invalid=[]
    for i,f in enumerate(lakes_data.get("features",[])):
        g=shape(f["geometry"])
        if g.is_empty or not g.is_valid or g.geom_type not in ("Polygon","MultiPolygon"):
            lake_invalid.append({"feature_index":i,"name":f.get("properties",{}).get("name"),"bounds":list(g.bounds) if not g.is_empty else None,"candidate_bbox_disjoint":g.is_empty or not g.envelope.intersects(candidate_geom.envelope)}); continue
        if g.intersects(candidate_geom):
            lake_hits.append({"feature_index":i,"name":f.get("properties",{}).get("name"),"intersection_area_m2":area_m2(g.intersection(candidate_geom),geometry_helper)})
    if any(not row["candidate_bbox_disjoint"] for row in lake_invalid): raise EvidenceError("Natural Earth invalid lake geometry bbox overlaps candidate; no repair attempted")
    # Reuse existing source-relative physical/numerical findings; do not regenerate their global producers.
    physical_rows=[r for r in rows_gzip(inputs/"baseline/physical-component-input.gz") if r.get("component_id")==COMPONENT]
    if len(physical_rows)!=1: raise EvidenceError("physical output does not contain exactly one original complete component row")
    physical=physical_rows[0]
    numeric_rows=[]
    for run in ("one","two"):
        found=[r for r in rows_gzip(inputs/f"baseline/numeric-run-{run}.gz") if r.get("component_id")==COMPONENT]
        if len(found)!=1: raise EvidenceError(f"numeric original run {run} does not contain exactly one component row")
        numeric_rows.append(found[0])
    if numeric_rows[0]!=numeric_rows[1]: raise EvidenceError("the two previously delivered numeric rows differ")
    support=physical.get("complete_support",{})
    source_lineage={"candidate_id":CANDIDATE,"candidate_geometry_sha256":geom_hash,"candidate_feature_sha256":obj_hash(candidates[0]),"candidate_fragment_properties":candidate.get("properties",{}),"component_id":COMPONENT,"complete_family_id":FAMILY,"contract_scope_source":"current issue #1344 exact machine contract; complete candidate Feature and all nine full current Atlas contact Feature bodies independently rebound here","physical_source_context":{"source_vintage":physical.get("source_vintage"),"physical_status":physical.get("physical_status"),"physical_authority":physical.get("physical_authority"),"physical_limits":physical.get("physical_limits"),"support_areas_m2":{k:v.get("area_m2") for k,v in support.items() if isinstance(v,dict)},"contact_ids_in_physical_record":physical.get("complete_contact_ids")},"prior_numeric_context":{"conservative_class":numeric_rows[0].get("conservative_class"),"full_current_feature_sha256":numeric_rows[0].get("full_current_feature_sha256"),"full_current_geometry_sha256":numeric_rows[0].get("full_current_geometry_sha256"),"original_physical_status":numeric_rows[0].get("original_physical_status"),"physical_authority":numeric_rows[0].get("physical_authority"),"partition_recovery":numeric_rows[0].get("partition_recovery"),"original_physical_limits":numeric_rows[0].get("original_physical_limits"),"demonstrated_local_contradictions":numeric_rows[0].get("demonstrated_local_contradictions")}}
    if numeric_rows[0].get("full_current_geometry_sha256")!=EXPECTED_GEOMETRY_SHA: raise EvidenceError("prior exact diagnostic does not bind candidate geometry hash")
    feature_inventory={"candidate_feature":candidate,"candidate_feature_sha256":obj_hash(candidates[0]),"current_contacts":contact_results,"current_atlas_contact_part_shas":PARTS}
    fitness={"version":1,"scope":{"family_id":FAMILY,"component_id":COMPONENT,"candidate_id":CANDIDATE,"candidate_area_declared_m2":candidate["properties"]["area_m2"],"candidate_area_wgs84_helper_m2":total_area,"contact_count":len(contact_results),"source_products":list(PRODUCTS)},"source_product_assessments":source_summaries,"source_acquisition_script":{"baseline_path":"scripts/administrative.py","baseline_sha256":digest(acquisition_script),"rewrites_configured_source_url_to_simplified_geometry_url":True,"downloads_simplified_geometry_member":True},"country_overlays":country_metrics,"all_three_country_products_union":{"intersecting":all_source_union.intersects(candidate_geom),"positive_area_m2":area_m2(all_cover,geometry_helper),"candidate_coverage_fraction":area_m2(all_cover,geometry_helper)/total_area,"covers_entire_candidate":all_source_union.covers(candidate_geom)},"current_atlas_contact_source_comparisons":contact_results,"independent_physical_reference":{"source":"Natural Earth 1:10m lakes, pinned whole product","product_bytes":len(lakes_raw),"product_sha256":digest(lakes_raw),"feature_count":len(lakes_data.get("features",[])),"candidate_intersecting_feature_count":len(lake_hits),"candidate_intersecting_features":lake_hits,"complete_product_invalid_geometries":lake_invalid,"limits":["Major lakes/reservoirs only; not complete river or small-water coverage.","Modern reference, not year-specific hydrology; absence of a hit is not evidence of dry land.","Two invalid geometries were excluded without repair; both bounding boxes are disjoint from the candidate."]},"reused_original_physical_and_numeric_context":source_lineage["physical_source_context"],"source_fitness_conclusion":{"administrative_product_role":"Three complete geoBoundaries gbOpen ADM2 simplified products; their recorded roles and source descriptions differ by country and the represented-year claims are 2005, 2017 and 2006.","direct_source_contact_result":f"All nine current Atlas contact IDs join uniquely to a complete original simplified source feature by shapeID; {sum(r['current_geometry_equals_simplified_source_topologically'] for r in contact_results)}/9 current Atlas geometries are topologically equal to those source features. Atlas feature metadata points to the unsimplified .geojson URL while scripts/administrative.py consumes simplifiedGeometryGeoJSON; URL provenance and geometry lineage therefore remain distinct and unexplained.","authority":"No source in this packet establishes the legal international border or authorizes an administrative assignment.","cause":"The complete polygon is source-compared only. The local numerical contradiction and source overlaps do not explain the full candidate or establish its physical or historical cause.","current_physical_status":"unknown; source coverage and date/registration limits remain.","engineering_next_action":"Any repair investigation must coordinate Poland, Belarus and Ukraine, first preserve the current and source vintages, trace why the current contacts differ from the consumed simplified products, and obtain candidate-scale authoritative boundary and contemporary hydrography evidence. No unilateral country clipping, affiliation or geometry change is supported."},"scope_reconciliation":{"expected_contact_ids":CONTACTS,"candidate_property_ids":prop_ids,"current_atlas_selected_ids":sorted(current),"source_shapeID_join_ids":sorted(source_contacts),"candidate_geometry_sha256":geom_hash,"candidate_feature_sha256":obj_hash(candidates[0]),"issue_contract_component_ids":[COMPONENT],"issue_contract_family_ids":[FAMILY],"duplicate_candidate_ids":False,"missing_foreign_ids":False}}
    output.mkdir(parents=True)
    (output/"source-fitness.json").write_text(json.dumps(fitness,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n")
    (output/"scope-reconciliation.json").write_text(json.dumps(source_lineage,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n")
    (output/"feature-inventory.json").write_text(json.dumps(feature_inventory,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n")
    with (output/"whole-source-neighbor-overlays.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(source_rows[0].keys()));w.writeheader();w.writerows(source_rows)
    summary={"status":"complete","family_id":FAMILY,"component_id":COMPONENT,"candidate_id":CANDIDATE,"complete_current_contacts":len(contact_results),"source_products_scanned":{k:v["feature_count"] for k,v in source_summaries.items()},"source_files_verified":len(checked),"source_custody_sha256":digest((inputs/"source-custody.json").read_bytes()),"metric_units":"m²; shared worldatlas-evidence-geometry-v1 WGS84 straight-source-edge ellipsoidal integral; predicates in longitude,latitude EPSG:4326 coordinate plane","unknowns_preserved":["legal international boundary and historical ownership","whether the candidate is current dry land, river/channel, wetland, or registration mismatch","source positional accuracy and transformation history for current Atlas contact geometry","cause of full candidate; one prior local exact numerical contradiction is not a whole-component explanation","source approval or engineering/publication permission"],"outputs":{}}
    for p in sorted(output.iterdir()):
        b=p.read_bytes();summary["outputs"][p.name]={"bytes":len(b),"sha256":digest(b)}
    (output/"run-summary.json").write_text(json.dumps(summary,sort_keys=True,separators=(",",":"))+"\n")
    if a.control:
        raise EvidenceError("control flag unexpectedly reached successful output path")
    print(json.dumps(summary,sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    try: main()
    except Exception as e:
        print(json.dumps({"status":"rejected","reason":str(e)},sort_keys=True),file=sys.stderr)
        raise
