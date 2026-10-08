#!/usr/bin/env python3
"""One bounded seven-case source/shoreline/topology measurement; never repairs input geometry."""
from __future__ import annotations
import hashlib, json, math, xml.etree.ElementTree as ET
from pathlib import Path
from shapely.geometry import shape, Polygon, LineString, MultiLineString, GeometryCollection, box
from shapely.ops import transform, unary_union
from shapely.validation import explain_validity
from pyproj import CRS, Transformer
import shapely, pyproj, sys, platform

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
PLAN = ROOT / "bounded-measurement-plan.json"
OUT = ROOT / "physical-applicability-v1.json"
CANDIDATES = REPO / "research/geography/norway-adm2-source-fit-1492/vintages/component-geometries-20261008/selected-components.json"
OVERLAY = REPO / "research/geography/norway-adm2-source-fit-1492/vintages/exact-overlay-acceptance-20261008/overlay-v1.json"
FAMILY = REPO / "research/geography/norway-adm2-source-fit-1492/vintages/family-scope-corrected-20261008/family-scope.json"
ADMIN = REPO / "research/geography/norway-adm2-source-fit-1492/vintages/official-source-capture-20261008/adm2-simplified.geojson"
PARENT = REPO / "research/geography/norway-adm2-source-fit-1492/vintages/official-source-capture-20261008/adm1-simplified.geojson"
ATLAS = REPO / "data/geography/part-17.json"
INDEX = ROOT / "sources/sjoekart-dybdedata-wfs-20261008/source-snapshot-index.json"
SOURCES = ROOT / "sources/sjoekart-dybdedata-wfs-20261008"
EXPECTED_IDS = [
"physical-component:1f5426f5180aa4f5b7fd9991b5ae4816d56cb642c31d0937a4977da516f28f2b",
"physical-component:764b247eb21da38adac0b925bededbbb4dccaefa4b52b16976f20543a7ac3384",
"physical-component:7bad7bdf9b1203fe6c676eb2efde10b09ce394ad7d6d554eb557709d7704df35",
"physical-component:8fb9f3f0d7df1c96ac452792fd4a9dbc7a45a576437550dd5b198424ceca14a9",
"physical-component:a92cac9c4c3d3a91286eca0e4890becd63441647c7fe7c4cdcc5e1aa167d4803",
"physical-component:b6ba064b4525f0c75459a8d1aa05c25e9740cc46b9964f96983d61d6a9b4253a",
"physical-component:eb2b6c25d1a2b8ead2bcb67f7e0423b5f1cc5609ac3f600bb98cd6d5cb11db40"]

def digest(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def local(tag: str) -> str: return tag.rsplit("}",1)[-1]
def coord_list(text: str, dimension: int, lon_first: bool) -> list[tuple[float,float]]:
    vals=[float(x) for x in text.split()]
    if dimension != 2 or len(vals)<2 or len(vals)%dimension: raise ValueError("unsupported/invalid GML coordinate dimension or cardinality")
    pairs=list(zip(vals[::dimension],vals[1::dimension]))
    return pairs if lon_first else [(b,a) for a,b in pairs]
def node_dimension(node: ET.Element) -> int:
    cur=node
    while cur is not None:
        if cur.get("srsDimension"): return int(cur.get("srsDimension"))
        cur=getattr(cur,"_parent",None)
    return 2
def ring_coords(node: ET.Element) -> list[tuple[float,float]]:
    parts=[]
    for e in node.iter():
        if local(e.tag) in ("posList","pos") and e.text:
            dim=int(e.get("srsDimension", node.get("srsDimension","2")))
            parts.append(coord_list(e.text,dim,False))
    coords=[]
    for part in parts:
        if coords and part and coords[-1]==part[0]: coords.extend(part[1:])
        else: coords.extend(part)
    if len(coords)<4: raise ValueError("GML ring has too few coordinates")
    return coords
def gml_land_feature(feature: ET.Element):
    geom_prop=next((x for x in feature.iter() if local(x.tag)=="område"),None)
    if geom_prop is None: raise ValueError("Landareal feature missing område")
    polys=[]
    for patch in geom_prop.iter():
        if local(patch.tag) not in ("PolygonPatch","Polygon"): continue
        ext=next((x for x in patch if local(x.tag)=="exterior"),None)
        if ext is None: raise ValueError("polygon patch missing exterior")
        holes=[ring_coords(x) for x in patch if local(x.tag)=="interior"]
        poly=Polygon(ring_coords(ext),holes)
        polys.append(poly)
    if not polys: raise ValueError("unsupported Landareal GML surface representation")
    return polys[0] if len(polys)==1 else GeometryCollection(polys)
def gml_coast_feature(feature: ET.Element):
    prop=next((x for x in feature.iter() if local(x.tag)=="grense"),None)
    if prop is None: raise ValueError("Kystkontur feature missing grense")
    lines=[]
    for seg in prop.iter():
        if local(seg.tag) not in ("LineStringSegment","LineString"): continue
        pts=[]
        for el in seg.iter():
            if local(el.tag) in ("posList","pos") and el.text:
                dim=int(el.get("srsDimension",seg.get("srsDimension","2")))
                part=coord_list(el.text,dim,False)
                if pts and pts[-1]==part[0]: pts.extend(part[1:])
                else: pts.extend(part)
        if len(pts)>=2: lines.append(LineString(pts))
    if not lines: raise ValueError("unsupported Kystkontur curve segment; no approximation permitted")
    return lines[0] if len(lines)==1 else MultiLineString(lines)
def read_layer(index: dict, typename: str):
    geoms=[]; ids=[]; invalid=[]; dates={"førsteDatafangstdato":[],"oppdateringsdato":[],"datauttaksdato":[]}
    for rec in index["captures"]:
        if rec["typename"]!=typename: continue
        raw=(ROOT/rec["path"]).read_bytes()
        if len(raw)!=rec["bytes"] or digest(ROOT/rec["path"])!=rec["sha256"]: raise ValueError("source response changed after custody verification")
        root=ET.fromstring(raw)
        members=[child for member in list(root) if local(member.tag)=="member" for child in list(member)]
        if len(members)!=rec["member_count"]: raise ValueError("WFS members do not match hits ledger")
        for feature in members:
            fid=next((v for k,v in feature.attrib.items() if local(k)=="id"),None)
            if not fid: raise ValueError("source feature lacks gml:id")
            ids.append(fid)
            g=(gml_land_feature(feature) if typename=="app:Landareal" else gml_coast_feature(feature))
            if not g.is_valid:
                invalid.append({"feature_id":fid,"response_path":rec["path"],"reason":explain_validity(g),"bbox_lon_lat":list(g.bounds),"unrepaired":True})
            else:
                geoms.append(g)
            for e in feature.iter():
                k=local(e.tag)
                if k in dates and e.text: dates[k].append(e.text.strip())
    if len(ids)!=len(set(ids)): raise ValueError("duplicate feature id across query windows")
    return geoms,ids,dates,invalid

def relation(a,b) -> dict:
    inter=a.intersection(b)
    def types(g):
        if hasattr(g,"geoms") and g.geom_type=="GeometryCollection": return [t for part in g.geoms for t in types(part)]
        if g.geom_type.startswith("Multi"): return [t for part in g.geoms for t in types(part)]
        return [g.geom_type]
    parts=types(inter)
    if inter.is_empty: kind="disjoint"
    elif inter.area>0: kind="area-overlap"
    elif any(t in ("LineString","LinearRing") for t in parts): kind="shared-edge"
    else: kind="point-contact"
    return {"kind":kind,"intersection_area_m2":inter.area,"intersection_length_m":inter.length if "Line" in inter.geom_type else 0.0,"intersection_geometry_type":inter.geom_type,"intersects":a.intersects(b)}

def main() -> None:
    plan=json.loads(PLAN.read_text()); pins=plan["measurement_inputs"]["pins"]
    expected={
      CANDIDATES:("exact_candidate_geometries",), OVERLAY:("measured_candidate_minus_target_receipts",), FAMILY:("family_context",),
      ADMIN:("pinned_administrative_product",), PARENT:("pinned_administrative_parent_product",), ATLAS:("pinned_atlas_target_context",),
      REPO/"data/administrative-sources.json":("pinned_administrative_source_registry",),
      REPO/"research/geography/norway-adm2-source-fit-1492/vintages/official-source-capture-20261008/selected-source-rows.json":("selected_source_row_manifest",)}
    for path,keys in expected.items():
        d=pins[keys[0]]
        if path.stat().st_size!=d["bytes"] or digest(path)!=d["sha256"]: raise ValueError("pinned input bytes changed: "+str(path))
    if OUT.exists(): raise SystemExit("refusing to overwrite prior measured result")
    overlay=json.loads(OVERLAY.read_text()); candidates=json.loads(CANDIDATES.read_text()); family=json.loads(FAMILY.read_text())
    if overlay["scope"]["complete_family_member_count"]!=400 or len(overlay["scope"]["complete_positive_length_neighbor_ids"])!=36: raise ValueError("frozen 400/36 scope mismatch")
    if len(candidates["selected_components"])!=15: raise ValueError("frozen 15-candidate context mismatch")
    cand={f["id"]:shape(f["geometry"]) for f in candidates["selected_components"]}
    rows={r["component_id"]:r for r in overlay["components"]}
    if set(EXPECTED_IDS)-set(cand) or set(EXPECTED_IDS)-set(rows): raise ValueError("assigned seven subjects absent from exact pinned inputs")
    atlas=json.loads(ATLAS.read_text()); atlas_by_id={f["properties"]["id"]:shape(f["geometry"]) for f in atlas["features"]}
    neighbor_ids=overlay["scope"]["complete_positive_length_neighbor_ids"]
    if len(neighbor_ids)!=36 or set(neighbor_ids)-set(atlas_by_id): raise ValueError("one or more exact 36 neighbor geometries missing")
    assigned_targets={rows[cid]["current_atlas_target_id"] for cid in EXPECTED_IDS}
    if not assigned_targets<=set(neighbor_ids): raise ValueError("the 36-neighbor context omits an assigned current target")
    admin=json.loads(ADMIN.read_text()); admin_by_id={f["properties"]["shapeID"]:shape(f["geometry"]) for f in admin["features"] if f["properties"].get("shapeID")}
    parent=json.loads(PARENT.read_text()); parent_by_id={f["properties"]["shapeID"]:shape(f["geometry"]) for f in parent["features"] if f["properties"].get("shapeID")}
    forward=Transformer.from_crs(CRS.from_epsg(4326),CRS.from_epsg(25833),always_xy=True).transform
    gml_forward=Transformer.from_crs(CRS.from_epsg(4258),CRS.from_epsg(25833),always_xy=True).transform
    index=json.loads(INDEX.read_text())
    land_geoms,land_ids,land_dates,invalid_land=read_layer(index,"app:Landareal")
    coast_geoms,coast_ids,coast_dates,invalid_coast=read_layer(index,"app:Kystkontur")
    # GML coordinate lists are EPSG:4258 latitude,longitude by schema axis order;
    # parser reorders to longitude,latitude, then this always_xy transform is applied.
    land_m=[transform(gml_forward,g) for g in land_geoms]
    coast_m=[transform(gml_forward,g) for g in coast_geoms]
    land=unary_union(land_m); coast=unary_union(coast_m)
    invalid_land_boxes=[(item,transform(gml_forward,box(*item["bbox_lon_lat"]))) for item in invalid_land]
    invalid_coast_boxes=[(item,transform(gml_forward,box(*item["bbox_lon_lat"]))) for item in invalid_coast]
    for label,g in [("Landareal union",land),("Kystkontur union",coast)]:
        if not g.is_valid: raise ValueError(label+" invalid; no repair permitted: "+explain_validity(g))
    records=[]; neighbors=[]; status_counts={}
    for cid in EXPECTED_IDS:
        base=rows[cid]; target_id=base["current_atlas_target_id"]
        if target_id not in atlas_by_id: raise ValueError("current target missing: "+target_id)
        c=cand[cid]; t=atlas_by_id[target_id]
        if not c.is_valid or not t.is_valid: raise ValueError("invalid exact candidate or Atlas target; no repair permitted")
        extra_geo=c.difference(t)
        expected_extra=shape(base["candidate_minus_current_target"])
        if not extra_geo.equals(expected_extra): raise ValueError("recomputed added area differs from exact #1492 receipt")
        c_m=transform(forward,c); t_m=transform(forward,t); extra=transform(forward,extra_geo)
        if not c_m.is_valid or not t_m.is_valid or not extra.is_valid: raise ValueError("projection yielded invalid geometry; no repair permitted")
        proposal=unary_union([t_m,c_m])
        if not proposal.is_valid: raise ValueError("proposed union invalid; no repair permitted")
        lost=t_m.difference(proposal)
        added_land=extra.intersection(land)
        added_unknown=extra.difference(land)
        coast_touch=extra.boundary.intersection(coast)
        coast_distance=extra.distance(coast)
        invalid_land_hits=[item["feature_id"] for item,bbox_geom in invalid_land_boxes if bbox_geom.intersects(extra)]
        invalid_coast_hits=[item["feature_id"] for item,bbox_geom in invalid_coast_boxes if bbox_geom.intersects(extra)]
        target_source=admin_by_id.get(target_id.split(":")[-1])
        if target_source is None: raise ValueError("same-ID 2013 administrative source feature is missing")
        source_added_area=extra.intersection(transform(forward,target_source)).area
        parent_id=base.get("parent_product_feature_shapeID")
        parent_geom=parent_by_id.get(parent_id)
        parent_covers=bool(parent_geom is not None and transform(forward,parent_geom).covers(proposal))
        row={"component_id":cid,"target_id":target_id,"target_name":next((x["properties"].get("name") for x in atlas["features"] if x["properties"]["id"]==target_id),None),
             "current_target_sha256":base["current_atlas_target_geometry_sha256"],"candidate_sha256":base["component_geometry_sha256"],
             "candidate_valid":c.is_valid,"target_valid":t.is_valid,"added_area_matches_pinned_1492_receipt":True,
             "added_area_geometry_type":extra.geom_type,"added_area_m2":extra.area,"landareal_intersection_m2":added_land.area,
             "landareal_fraction_of_added_area":(added_land.area/extra.area if extra.area else None),
             "not_covered_by_valid_landareal_m2":added_unknown.area,"invalid_landareal_source_bbox_overlaps":invalid_land_hits,"invalid_kystkontur_source_bbox_overlaps":invalid_coast_hits,
             "kystkontur_added_area_boundary_intersection_m":coast_touch.length,
             "distance_added_area_to_kystkontur_m":coast_distance,"parent_source_feature_id":parent_id,"parent_coverage_pass":parent_covers,
             "strict_no_loss_pass":lost.is_empty,"strict_no_loss_residual_area_m2":lost.area,
             "added_area_intersection_2013_geoBoundaries_same_shapeID_m2":source_added_area,
             "added_area_fraction_covered_by_2013_geoBoundaries_same_shapeID":(source_added_area/extra.area if source_added_area is not None and extra.area else None),
             "status":"unresolved-invalid-source-bbox-overlap" if invalid_land_hits or invalid_coast_hits else "source-overlap-diagnostic-only; physical-applicability-unresolved"}
        records.append(row)
        for nid in neighbor_ids:
            if nid==target_id:
                neighbors.append({"component_id":cid,"neighbor_id":nid,"relation_status":"own-current-target-preserved-by-union","before":None,"after":None,"new_positive_area_overlap":False})
                continue
            before=relation(t_m,transform(forward,atlas_by_id[nid])); after=relation(proposal,transform(forward,atlas_by_id[nid]))
            neighbors.append({"component_id":cid,"neighbor_id":nid,"relation_status":"measured-neighbor","before":before,"after":after,"new_positive_area_overlap":after["intersection_area_m2"]>before["intersection_area_m2"]})
    result={"version":1,"issue":1510,"created_at":__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
      "scope":{"measured_subject_count":len(records),"candidate_context_count":15,"complete_family_member_count":400,"positive_length_neighbor_count":36,
        "candidate_ids":overlay["scope"]["selected_ids"],"family_member_ids":overlay["scope"]["complete_family_member_ids"],"neighbor_ids":neighbor_ids,
        "family_scope_sha256":pins["family_context"]["sha256"]},
      "source_products":{"kartverket":{"endpoint":index["endpoint"],"license":index["license"],"crs":index["crs"],"kystkontur_count":len(coast_ids),"landareal_count":len(land_ids),"valid_landareal_count":len(land_geoms),"invalid_landareal_count":len(invalid_land),"invalid_landareal_feature_ids":[x["feature_id"] for x in invalid_land],"invalid_kystkontur_count":len(invalid_coast),"invalid_kystkontur_feature_ids":[x["feature_id"] for x in invalid_coast],"bytes":index["total_response_bytes"],"index_sha256":digest(INDEX),"kystkontur_ids_sha256":hashlib.sha256(json.dumps(sorted(coast_ids),separators=(",",":")).encode()).hexdigest(),"landareal_ids_sha256":hashlib.sha256(json.dumps(sorted(land_ids),separators=(",",":")).encode()).hexdigest()},
        "feature_date_ranges":{"Kystkontur":coast_dates,"Landareal":land_dates},
        "invalid_landareal_features_excluded_unrepaired":invalid_land,"invalid_kystkontur_features_excluded_unrepaired":invalid_coast,
        "limits":["Kystkontur is the official mean-high-water line, but feature registration/accuracy is unknown.","Landareal source is chart-derived saltwater-only context; uncovered area is not classified as water. Invalid polygons were excluded without repair; their coordinate bounding boxes were used only to flag potentially affected cases.","The WFS is dynamically served; each response is separately pinned; WFS count attributes can report unknown/0 despite feature members.","Source overlap and geometry predicates are diagnostics; no physical, legal, historical, ownership or map correction conclusion is certified."]},
      "method":{"input_source_crs":"GeoJSON WGS84 longitude,latitude; Kartverket GML EPSG:4258 latitude,longitude axis order, explicitly reordered to longitude,latitude.","metric_crs":"EPSG:25833 ETRS89 / UTM zone 33N","area_units":"square metres in EPSG:25833","distance_units":"metres in EPSG:25833","software":{"python":sys.version,"shapely":shapely.__version__,"geos":shapely.geos_version_string,"pyproj":pyproj.__version__,"platform":platform.platform()},"no_snap_buffer_simplify_repair":True},
      "cases":records,"neighbor_relations":neighbors,"controls":{"all_7_added_areas_equal_pinned_1492_receipt":all(x["added_area_matches_pinned_1492_receipt"] for x in records),"all_7_strict_no_loss":all(x["strict_no_loss_pass"] for x in records),"all_7_parent_coverage":all(x["parent_coverage_pass"] for x in records),"relation_rows":len(neighbors),"own_target_rows":sum(1 for x in neighbors if x["relation_status"]=="own-current-target-preserved-by-union"),"evaluated_neighbor_relations":sum(1 for x in neighbors if x["relation_status"]=="measured-neighbor"),"expected_relation_rows":7*36,"identity_context":"15/400/36 preserved in every result"},
      "stages":{"research":"measured-source-diagnostics","implementation":"not-proposed","geographic_approval":"unapproved"}}
    tmp=OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    tmp.replace(OUT)
    print(json.dumps({"status":"measurement-complete","output":OUT.relative_to(ROOT).as_posix(),"case_count":len(records),"neighbor_relations":len(neighbors),"controls":result["controls"]},indent=2))

if __name__=="__main__": main()
