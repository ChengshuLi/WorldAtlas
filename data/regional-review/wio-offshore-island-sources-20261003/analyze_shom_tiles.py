#!/usr/bin/env python3
"""Offline screen of retained Shom tile bboxes against the three pinned Atlas shapes.

This is catalog-metadata screening only; it does not inspect raster pixels, source
masks, vertical datums, legal shorelines, or physical island completeness.
"""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json, re
from xml.etree import ElementTree as ET
from pyproj import CRS, Transformer
from shapely.geometry import box, shape, mapping
from shapely.ops import transform, unary_union

PACKET = Path(__file__).parent
CATALOG = PACKET / "sources/shom_litto3d_catalog_20261008"
CAPTURE = CATALOG / "catalog-capture.json"
OUT = PACKET / "shom-catalog-analysis.json"
NS = {"gmd":"http://www.isotc211.org/2005/gmd","gco":"http://www.isotc211.org/2005/gco","gmx":"http://www.isotc211.org/2005/gmx"}
GROUPS = {"eparses":"LITTO3D_EPARSES_2012_PACK_DL","mayotte":"LITTO3D_MAYOT_2012_PACK_DL","reunion":"LITTO3D_REUNION_2016_PACK_DL"}
TARGETS = {"atlas:coverage:ATF-5919":"Eparses", "atlas:coverage:FRA-4601":"Réunion", "atlas:coverage:FRA-4602":"Mayotte"}
AREAS = {"atlas:coverage:ATF-5919":"eparses", "atlas:coverage:FRA-4601":"reunion", "atlas:coverage:FRA-4602":"mayotte"}
PARTS = ["data/geography/part-16.json","data/geography/part-23.json","data/geography/part-28.json"]
ROOT = PACKET.parent.parent.parent
BASELINE = "c90773357da171d97367332cb53154da95796bff"

def file_hash(path):
    b=Path(path).read_bytes()
    return {"bytes":len(b),"sha256":sha256(b).hexdigest()}

def val(root, name):
    x=root.find(".//gmd:"+name+"/gco:Decimal", NS)
    if x is None or not x.text: raise ValueError("missing bbox "+name)
    return float(x.text)

def parse_metadata(record):
    p=CATALOG / record["path"]
    b=p.read_bytes()
    if sha256(b).hexdigest()!=record["sha256"] or len(b)!=record["bytes"]:
        raise ValueError("metadata hash mismatch: "+record["path"])
    root=ET.fromstring(b)
    href=None
    for a in root.findall(".//gmx:Anchor",NS):
        for k,v in a.attrib.items():
            if k.endswith("}href") and "/EPSG/0/" in v:
                href=v; break
        if href: break
    code=root.find(".//gmd:referenceSystemIdentifier//gmd:code/*",NS)
    crs_text=(code.text or "").strip() if code is not None else None
    if not crs_text and href: crs_text=href
    if not crs_text: raise ValueError("CRS missing: "+record["path"])
    epsg=int(href.rstrip("/").split("/")[-1]) if href else None
    identifier=root.find("./gmd:fileIdentifier/gco:CharacterString",NS)
    if identifier is None or identifier.text != record["metadata_id"]:
        raise ValueError("catalog metadata ID does not match XML fileIdentifier: "+record["path"])
    if record["package"] not in record["metadata_id"]:
        raise ValueError("catalog package does not match XML metadata ID: "+record["path"])
    extent=[val(root,k) for k in ("westBoundLongitude","southBoundLatitude","eastBoundLongitude","northBoundLatitude")]
    if extent[0]>=extent[2] or extent[1]>=extent[3]: raise ValueError("invalid extent")
    if extent[0] < -180 or extent[2] > 180 or extent[1] < -90 or extent[3] > 90:
        raise ValueError("geographic extent outside WGS84 limits: "+record["path"])
    licenses=[(x.text or "").strip() for x in root.findall(".//gmd:otherConstraints//gco:CharacterString",NS)]
    limitations=[(x.text or "").strip() for x in root.findall(".//gmd:useLimitation//gco:CharacterString",NS)]
    dist=[{"value":float(x.text),"uom":x.attrib.get("uom")} for x in root.findall(".//gmd:distance/gco:Distance",NS) if x.text]
    return {"source_crs":crs_text,"epsg":epsg,"bbox_wgs84":extent,"title": next(((x.text or "").strip() for x in root.findall(".//gmd:title/gco:CharacterString",NS) if x.text),None),
        "license_constraints":sorted(set(licenses)),"use_limitations":sorted(set(limitations)),"spatial_resolution":dist}

def get_features():
    out={}
    input_files={}
    for rel in PARTS:
        p=ROOT/rel; d=json.loads(p.read_text())
        input_files[rel]=file_hash(p)
        for f in d["features"]:
            if f.get("id") in TARGETS: out[f["id"]]=shape(f["geometry"])
    if set(out)!=set(TARGETS): raise ValueError("target scope mismatch")
    return out,input_files

def validate_capture_membership(cap):
    expected_counts={"eparses":80,"mayotte":192,"reunion":134}
    if set(cap.get("product_groups",{}))!=set(expected_counts):
        raise ValueError("product-group inventory differs from declared scope")
    records=[]; listings=[]
    for area,expected in expected_counts.items():
        group=cap["product_groups"][area]
        if group.get("package_count")!=expected:
            raise ValueError("unexpected product package count: "+area)
        group_path=CATALOG/group["path"]
        group_bytes=group_path.read_bytes()
        if sha256(group_bytes).hexdigest()!=group["sha256"] or len(group_bytes)!=group["bytes"]:
            raise ValueError("product-group response hash mismatch: "+area)
        names=[x["prepackageName"] for x in json.loads(group_bytes).get("prepackageResources",[])]
        if len(names)!=expected or len(set(names))!=expected:
            raise ValueError("product group has missing or duplicate package: "+area)
        area_records=[x for x in cap.get("metadata_records",[]) if x.get("area")==area]
        area_listings=[x for x in cap.get("package_file_listings",[]) if x.get("area")==area]
        record_names=[x.get("package") for x in area_records]
        listing_names=[x.get("package") for x in area_listings]
        if len(area_records)!=expected or len(set(record_names))!=expected or set(record_names)!=set(names):
            raise ValueError("package metadata membership mismatch: "+area)
        if len(area_listings)!=expected or len(set(listing_names))!=expected or set(listing_names)!=set(names):
            raise ValueError("package file-list membership mismatch: "+area)
        records.extend(area_records); listings.extend(area_listings)
    record_map={(x["area"],x["package"]):x for x in records}
    listing_map={(x["area"],x["package"]):x for x in listings}
    if len(record_map)!=406 or record_map.keys()!=listing_map.keys():
        raise ValueError("catalog metadata/listing membership mismatch")
    return record_map,listing_map

def main():
    cap=json.loads(CAPTURE.read_text())
    # Verify the retained original group-response bodies and exact inventory membership.
    records,listing=validate_capture_membership(cap)
    parsed={}
    for key,rec in records.items():
        row=parse_metadata(rec)
        listed=listing[key]
        # File-list metadata is retained as exact restoration URL/hash and parsed
        # filename/size/MD5. Each normal product tile must have a deliverable file.
        if len(listed["files"]) != 1 or not all(x.get("fileName") == key[1]+".7z" and x.get("fileSize",0)>0 and re.fullmatch(r"[0-9a-f]{32}",x.get("fileMd5","")) for x in listed["files"]):
            raise ValueError("missing or malformed listed package file "+str(key))
        parsed[key]={**row,"catalog_record":rec,"file_listing":listed}
    features,feature_hashes=get_features()
    to_6933=Transformer.from_crs(4326,6933,always_xy=True).transform
    to_4326=Transformer.from_crs(4326,4326,always_xy=True).transform
    tile_geoms={}
    for key,row in parsed.items():
        tile_geoms[key]=transform(to_6933,box(*row["bbox_wgs84"]))
    component_results={}
    feature_results={}
    for fid,geom in features.items():
        area=AREAS[fid]
        candidates=[(k,g) for k,g in tile_geoms.items() if k[0]==area]
        geom_m=transform(to_6933,geom)
        comps=list(geom.geoms) if geom.geom_type=="MultiPolygon" else [geom]
        comp_rows=[]
        for i,comp in enumerate(comps):
            cm=transform(to_6933,comp)
            exact=[k for k,g in candidates if g.intersects(cm)]
            near=[k for k,g in candidates if g.intersects(cm.buffer(1000))]
            comp_rows.append({"component_index":i,"feature_component_bbox_wgs84":list(comp.bounds),
                "intersecting_metadata_bbox_count":len(exact),"intersecting_packages":[parsed[k]["catalog_record"]["package"] for k in exact],
                "within_1km_metadata_bbox_count":len(near),"within_1km_packages":[parsed[k]["catalog_record"]["package"] for k in near]})
        exact=[(k,g) for k,g in candidates if g.intersects(geom_m)]
        near=[(k,g) for k,g in candidates if g.intersects(geom_m.buffer(1000))]
        components_without_near_package=sum(not row["within_1km_packages"] for row in comp_rows)
        feature_results[fid]={"source_label":TARGETS[fid],"component_count":len(comps),
            "feature_bbox_wgs84":list(geom.bounds),"product_package_count":len(candidates),
            "intersecting_metadata_bbox_count":len(exact),"intersecting_packages":[parsed[k]["catalog_record"]["package"] for k,g in exact],
            "within_1km_metadata_bbox_count":len(near),"within_1km_packages":[parsed[k]["catalog_record"]["package"] for k,g in near],
            "components_without_package_bbox_within_1km_count":components_without_near_package,
            "components":comp_rows}
    product_summaries={}
    for area,product in GROUPS.items():
        rows=[parsed[k] for k in parsed if k[0]==area]
        product_summaries[area]={"product_name":product,"catalog_metadata_tile_count":len(rows),
            "source_crs_identifiers":sorted({x["source_crs"] for x in rows}),
            "package_file_count":sum(len(x["file_listing"]["files"]) for x in rows),
            "total_listed_package_bytes":sum(f["fileSize"] for x in rows for f in x["file_listing"]["files"]),
            "license_constraints_observed":sorted({v for x in rows for v in x["license_constraints"]}),
            "use_limitations_observed":sorted({v for x in rows for v in x["use_limitations"]}),
            "metadata_date_stamps":sorted({x["catalog_record"]["retrieved_utc"] for x in rows})}
    out={"version":1,"issue":633,"retrieved_utc":cap["retrieved_utc"],
        "baseline_snapshot_commit":BASELINE,"capture_file":str(CAPTURE.relative_to(ROOT)),
        "producers":{"analysis":{"path":str(Path(__file__).relative_to(ROOT)),**file_hash(__file__)},
          "capture":{"path":str((PACKET/"capture_shom_catalog.py").relative_to(ROOT)),**file_hash(PACKET/"capture_shom_catalog.py")}},
        "capture_sha256":file_hash(CAPTURE)["sha256"],"product_groups":product_summaries,
        "target_results":feature_results,"input_files":{str(CAPTURE.relative_to(ROOT)):file_hash(CAPTURE),**feature_hashes,
           **{str((CATALOG/x["path"]).relative_to(ROOT)):file_hash(CATALOG/x["path"]) for x in cap["product_groups"].values()},
           **{str((CATALOG/x["path"]).relative_to(ROOT)):{"bytes":x["bytes"],"sha256":x["sha256"]} for x in cap["metadata_records"]}},
        "method":{"geometry":"transform each metadata EX_GeographicBoundingBox polygon and pinned feature components from WGS84 to EPSG:6933; count direct intersections and intersections with a 1,000 m buffer",
          "interpretation":"Catalog-bbox proximity only. An XML bbox is a rectangular catalog footprint and does not establish raster mask coverage, valid source pixels, island occurrence, coast accuracy, completeness, datum, or legal boundary. Absence of a nearby listed tile is only a candidate-source catalog gap.",
          "license":"Catalog XMLs and parsed file listings identify terms per package; attribution and reuse terms must be respected. Shom says not for navigation in product metadata."}}
    with OUT.open("w",encoding="utf-8") as f:
        f.write(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"output":str(OUT.relative_to(ROOT)),"output_sha256":file_hash(OUT)["sha256"],
       "products":{k:v["catalog_metadata_tile_count"] for k,v in product_summaries.items()},
       "targets":{k:{"components":v["component_count"],"intersect":v["intersecting_metadata_bbox_count"],"within_1km":v["within_1km_metadata_bbox_count"]} for k,v in feature_results.items()}},indent=2))
if __name__=="__main__": main()
