#!/usr/bin/env python3
"""Reproduce geometry diagnostics for the 230 #421 locations (not boundary approval)."""
import csv, gzip, json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import median

from pyproj import Transformer
from shapely import make_valid
from shapely.geometry import box, shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from evidence.immutable import Baseline
BASELINE_PIN = json.loads((HERE / "baseline-inputs.json").read_text())
BASE = Baseline(ROOT, BASELINE_PIN["commit"], BASELINE_PIN["files"])
scope = json.loads((HERE / "scope.json").read_text())
wanted = set(scope["member_location_ids"])
locations = {}
for part in ("part-9.json", "part-28.json", "part-29.json"):
    for feature in json.loads(BASE.read("data/geography/" + part))["features"]:
        p = feature["properties"]
        if p["id"] in wanted:
            locations[p["id"]] = p, shape(feature["geometry"])
assert len(locations) == 230

grc = json.loads(gzip.decompress(BASE.read("data/regional-review/regional-review-ef67318527f5f3a3/sources/geoBoundaries-GRC-ADM3.geojson.gz")))
xkx = json.loads((HERE / "sources/geoBoundaries-XKX-ADM1.geojson").read_text())
source_features = {}
for fc in (grc, xkx):
    for f in fc["features"]:
        source_features[f["properties"]["shapeID"]] = (f["properties"], shape(f["geometry"]))
equal_area = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform

def clean(g):
    return g if g.is_valid else make_valid(g)

def polygon_components(g):
    g = clean(g)
    if g.geom_type == "Polygon": return 1
    if hasattr(g, "geoms"):
        return sum(polygon_components(x) for x in g.geoms if x.geom_type in ("Polygon", "MultiPolygon", "GeometryCollection"))
    return 0

rows=[]
for loc_id,(p,baseline) in sorted(locations.items()):
    m=p["metadata"]
    member_ids=m.get("source_member_ids") or [loc_id]
    shapes=[]
    for source_id in member_ids:
        fid=source_id.rsplit(":",1)[-1]
        if fid not in source_features: continue
        shapes.append(source_features[fid][1])
    src=unary_union(shapes) if shapes else None
    b=clean(transform(equal_area,clean(baseline)))
    src_proj=clean(transform(equal_area,clean(src))) if src is not None else None
    if src_proj is not None:
        inter=b.intersection(src_proj).area
        union=b.union(src_proj).area
        iou=inter/union if union else 0
        src_cover=inter/src_proj.area if src_proj.area else 0
    else: iou=src_cover=0
    rows.append({"location_id":loc_id,"location_name":p["name"],"atlas_parent_id":p["parent_id"],
                 "source_id":m["source_id"],"source_member_count":len(member_ids),
                 "baseline_polygon_components":polygon_components(baseline),
                 "source_polygon_components":polygon_components(src) if src is not None else 0,
                 "baseline_area_km2_equal_area":round(b.area/1e6,4),
                 "source_area_km2_equal_area":round(src_proj.area/1e6,4) if src_proj is not None else 0,
                 "baseline_source_iou":round(iou,6),"source_area_coverage":round(src_cover,6),
                 "measurement_note":"EPSG:6933 planar diagnostic; invalid inputs repaired only in memory; neither geometry is authoritative."})

with (HERE/"geometry-screen.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)

# Scale screens are descriptive within the exact workload parent subset, never a tier rule.
by_parent=defaultdict(list)
for row in rows: by_parent[row["atlas_parent_id"]].append(row["baseline_area_km2_equal_area"])
hier={x["id"]:x for x in json.loads(BASE.read("data/hierarchy.json"))}
scales=[]
for pid,areas in sorted(by_parent.items()):
    name=hier[pid]["name"]
    med=median(areas)
    scales.append({"province_id":pid,"province_name":name,"workload_n":len(areas),
                   "min_area_km2":round(min(areas),4),"median_area_km2":round(med,4),
                   "max_area_km2":round(max(areas),4),"max_to_median":round(max(areas)/med,3) if med else None,
                   "note":"Within-packet area contrast is a review trigger only; area is not an administrative-tier test."})
with (HERE/"parent-scale-screen.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,list(scales[0]),lineterminator="\n");w.writeheader();w.writerows(scales)

# Inspect scoped Greece adjacency within the complete retained 326-feature 2010 layer.
grc_items=[]
for fid,(props,g) in source_features.items():
    if props.get("shapeGroup")=="GRC": grc_items.append((fid,props,g))
geoms=[transform(equal_area,clean(g)) for _,_,g in grc_items]
tree=STRtree(geoms)
id_index={fid:i for i,(fid,_,_) in enumerate(grc_items)}
scope_grc_ids=set()
for p,_ in locations.values():
    m=p["metadata"]
    if m["source_id"]=="gb:GRC:ADM3":
        ids=m.get("source_member_ids") or ["gb:GRC:ADM3:"+m["original_id"]]
        scope_grc_ids.update(x.rsplit(":",1)[-1] for x in ids)
neighbors=defaultdict(set); overlaps=[]
for i,g in enumerate(geoms):
    for j in tree.query(g):
        j=int(j)
        if j<=i: continue
        inter=g.intersection(geoms[j])
        if inter.area>1000:
            overlaps.append((grc_items[i][0],grc_items[j][0],inter.area))
        if inter.length>0.1:
            neighbors[grc_items[i][0]].add(grc_items[j][0]);neighbors[grc_items[j][0]].add(grc_items[i][0])
scoped_neighbor_counts={fid:len(neighbors[fid]) for fid in scope_grc_ids}
positive = box(0, 0, 1, 1)
negative_a, negative_b = box(0, 0, 1, 1), box(2, 2, 3, 3)
positive_iou = positive.intersection(positive).area / positive.union(positive).area
negative_iou = negative_a.intersection(negative_b).area / negative_a.union(negative_b).area
axis_control = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform(10,45)
assert positive_iou == 1.0 and negative_iou == 0.0
assert abs(axis_control[0]-1113194.9079)<0.01 and abs(axis_control[1]-5621521.4862)<0.01
summary={"method":"EPSG:6933 equal-area transforms; make_valid only for diagnostics; STRtree exact layer pair screens.",
 "grc_source_feature_count":len(grc_items),"scoped_grc_source_feature_count":len(scope_grc_ids),
 "scoped_source_features_with_shared_edge_over_0_1m":sum(v>0 for v in scoped_neighbor_counts.values()),
 "scoped_source_features_without_shared_edge_over_0_1m":sum(v==0 for v in scoped_neighbor_counts.values()),
 "scoped_features_in_pairs_with_overlap_over_1000m2":len({a for a,b,_ in overlaps if a in scope_grc_ids}|{b for a,b,_ in overlaps if b in scope_grc_ids}),
 "source_pairs_total_overlap_over_1000m2":len(overlaps),
 "scope_ids_with_no_same_layer_edge":[{"shapeID":fid,"shapeName":source_features[fid][0]["shapeName"]} for fid,n in sorted(scoped_neighbor_counts.items()) if n==0],
 "controls":{"positive_control":{"method_id":"epsg6933-source-comparison","kind":"positive-control","outcome":"passed","expectation":"identical synthetic squares have IoU exactly 1","observed_iou":positive_iou},
             "negative_control":{"method_id":"epsg6933-source-comparison","kind":"negative-control","outcome":"passed","expectation":"disjoint synthetic squares have IoU exactly 0","observed_iou":negative_iou},
             "axis_order_control":{"input_longitude_latitude":[10,45],"target_crs":"EPSG:3857","x_m":axis_control[0],"y_m":axis_control[1],"outcome":"passed"}},
 "limits":["Coastlines and islands naturally have no same-layer land neighbor.","No-edge/overlap results do not establish coverage, legal boundaries, omitted islands, or correct parent assignments.","The selected source inventory itself is stale for present-day completeness; these are 2010 geometry screens only."]}
(HERE/"geometry-method-and-neighbor-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
run_summary={"locations":len(rows),"scope_grc_source_features":len(scope_grc_ids),
                  "multipart_atlas_locations":sum(r["baseline_polygon_components"]>1 for r in rows),
                  "iou_below_0_95":sum(r["baseline_source_iou"]<0.95 for r in rows),
                  "neighbor_summary":summary}
(HERE/"geometry-run-summary.json").write_text(json.dumps(run_summary,indent=2)+"\n")
print(json.dumps(run_summary,indent=2))
