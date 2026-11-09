"""Build the Ural boundary using only its pinned source recipe and raw inputs."""
import argparse
from collections import defaultdict
import heapq
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from pyproj import Geod
import shapefile
from shapely.geometry import LineString, Point
from shapely.ops import substring

from construct_cop_spring_flow import model_spring
from geodesic_spring_join import build as join_spring, canonical, digest
from reproduce_arctic_gap_rasters import build_crops, sha
from spring_connector_graph import basin_labels
from spring_triple_route import interfaces, route


def hydrobasins_paths(folder, pins):
    return [
        (str(folder / f"ural-hydro-{area}.zip"), pins[f"ural-hydro-{area}.zip"],
         str(folder / f"ural-hydro-{area}/hybas_{area}_lev12_v1c.shp"))
        for area in ("eu", "si")
    ]


def source_vertices(basins, recipe):
    section_refs = recipe["hydrobasins_sections"]
    required = {ref[0] for refs in section_refs.values() for ref in refs}
    required.update(cut["hydrobasins_edge"][0] for gap in recipe["terrain_gaps"].values()
                    for side, cut in gap.items() if side in ("north", "south"))
    with shapefile.Reader(basins[0][2]) as layer:
        features = {}
        for record in layer.iterRecords(fields=["HYBAS_ID"]):
            ident = record["HYBAS_ID"]
            if ident in required:
                assert ident not in features
                features[ident] = layer.shape(record.oid)
    assert features.keys() == required

    sections = {}
    for name, refs in section_refs.items():
        points = []
        for ident, offset, *axes in refs:
            point = features[ident].points[offset]
            if axes:
                point = [round(v * step) / step if step else v for v, step in zip(point, axes)]
            points.append(list(point))
        sections[name] = points
    return features, sections


def point_intersection(a, b):
    hit = a.intersection(b)
    if not isinstance(hit, Point) or hit.is_empty:
        raise ValueError("expected one source edge intersection")
    return (hit.x, hit.y)


def gap_path(gap, terrain_folder, basins, features, recipe):
    labels, transform, geographic, _ = basin_labels(
        terrain_folder / gap["terrain_crop"], gap["terrain_crop_sha256"], None, None, basins,
        gap["bounds"], recipe["terrain_outlet_basins"], recipe["terrain_resolution_m"],
    )
    _, graph_edges, coordinates = interfaces(labels, transform, geographic)
    edges = graph_edges[2]
    cuts = {}
    for side, name in enumerate(("north", "south")):
        marker = gap[name]
        cell_edge = tuple(map(tuple, marker["terrain_edge"]))
        assert cell_edge in edges and cell_edge not in cuts
        ident, first, last = marker["hydrobasins_edge"]
        feature = features[ident]
        assert last == first + 1 and last not in feature.parts
        source_edge = LineString([feature.points[first], feature.points[last]])
        terrain_edge = LineString([coordinates[node] for node in cell_edge])
        # Negative row indices keep the virtual crossings distinct from raster nodes.
        terminal = (-1, side)
        coordinates[terminal] = point_intersection(terrain_edge, source_edge)
        cuts[cell_edge] = terminal

    geod = Geod(ellps="WGS84")
    adjacent = defaultdict(list)

    def add(a, b):
        weight = geod.inv(*coordinates[a], *coordinates[b])[2]
        adjacent[a].append((b, weight))
        adjacent[b].append((a, weight))

    for a, b in sorted(edges, key=lambda edge: (edge[0][0] == edge[1][0], edge)):
        if (a, b) in cuts:
            terminal = cuts[a, b]
            add(a, terminal)
            add(terminal, b)
        else:
            add(a, b)
    start, end = (-1, 0), (-1, 1)
    distance = {start: 0.0}
    parent = {}
    queue = [(0.0, 0, start)]
    order = 0
    while queue:
        length, _, node = heapq.heappop(queue)
        if node == end:
            break
        if length != distance[node]:
            continue
        for neighbor, weight in adjacent[node]:
            candidate = length + weight
            if candidate < distance.get(neighbor, float("inf")):
                distance[neighbor] = candidate
                parent[neighbor] = node
                order += 1
                heapq.heappush(queue, (candidate, order, neighbor))
    path = [end]
    while path[-1] != start:
        path.append(parent[path[-1]])
    return [list(coordinates[node]) for node in reversed(path)]


def xml_nodes(root):
    return {node.get("id"): [float(node.get("lon")), float(node.get("lat"))]
            for node in root.findall("node")}


def coast_terminal(path, way_id, hydro_edge):
    root = ET.parse(path).getroot()
    nodes = xml_nodes(root)
    way, = [w for w in root.findall("way") if w.get("id") == way_id]
    assert any(tag.attrib == {"k": "natural", "v": "coastline"} for tag in way.findall("tag"))
    coast = LineString([nodes[node.get("ref")] for node in way.findall("nd")])
    return list(point_intersection(coast, LineString(hydro_edge)))


def river_path(raw, recipe):
    root = ET.fromstring(raw)
    nodes = xml_nodes(root)
    ways = {way.get("id"): way for way in root.findall("way")}
    relation, = [entry for entry in root.findall("relation")
                 if (entry.get("id"), entry.get("version")) ==
                 (recipe["osm_river_relation"], recipe["osm_river_relation_version"])]
    members = relation.findall("member")
    spring, = [m.get("ref") for m in members if (m.get("type"), m.get("role")) == ("node", "spring")]
    mouth, = [m.get("ref") for m in members if (m.get("type"), m.get("role")) == ("node", "mouth")]
    assert spring == recipe["osm_spring_node"]
    adjacent = defaultdict(set)
    for member in members:
        if (member.get("type"), member.get("role")) != ("way", "main_stream"):
            continue
        refs = [node.get("ref") for node in ways[member.get("ref")].findall("nd")]
        for a, b in zip(refs, refs[1:]):
            assert a != b and b not in adjacent[a]
            adjacent[a].add(b)
            adjacent[b].add(a)
    assert len(adjacent[spring]) == 1 and all(len(v) <= 2 for v in adjacent.values())
    order = [spring]
    seen = {spring}
    while adjacent[order[-1]] - seen:
        node, = adjacent[order[-1]] - seen
        order.append(node)
        seen.add(node)
    assert len(order) == len(adjacent) and mouth in seen and len(adjacent[order[-1]]) == 1
    return [nodes[node] for node in order]


def connect_spring(north, folder, basins, pins, river):
    report, labels, transform, geographic = model_spring(
        folder / "ural-copernicus-dem.tif", pins["ural-copernicus-dem.tif"], basins, river[0],
    )
    flow = report["radius_cell_square"]["0"]["candidate"]
    (rr, cc), (nr, nc) = flow["interface_cells"]
    assert abs(rr - nr) + abs(cc - nc) == 1
    assert (labels[rr, cc], labels[nr, nc]) == (2, 1)
    if rr == nr:
        col = max(cc, nc)
        edge = ((rr, col), (rr + 1, col))
    else:
        row = max(rr, nr)
        edge = ((row, cc), (row, cc + 1))
    _, edges, coordinates = interfaces(labels, transform, geographic)
    assert edge in edges[2]
    a, b = [list(coordinates[node]) for node in edge]
    midpoint = [(x + y) / 2 for x, y in zip(a, b)]
    candidate = route(labels, transform, geographic, north[-300:], midpoint)["candidate"]
    near = candidate["river_interface_lonlat"]
    assert near in (a, b)
    other = b if near == a else a
    if candidate["coordinates"][-3] == other:
        candidate["coordinates"].pop(-2)
    northern_line = LineString(north)
    cut = Point(candidate["retained_intersection_lonlat"])
    prefix = substring(northern_line, 0, northern_line.project(cut))
    prefix_points = [list(point) for point in prefix.coords]
    return prefix_points[:-1] + candidate["coordinates"] + flow["terrain_centers"] + river


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--recipe-sha256", required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    args = parser.parse_args()
    raw = args.recipe.read_bytes()
    assert digest(raw) == args.recipe_sha256
    recipe = json.loads(raw)
    assert recipe["schema"] == "worldatlas-v8-ural-source-recipe-v1"
    folder = args.inputs.resolve(strict=True)
    run = args.workdir.resolve()
    run.mkdir()
    pins = {}
    for pin in recipe["source_inputs"]:
        name = pin["name"]
        assert Path(name).name == name and name not in pins
        path = folder / name
        assert path.stat().st_size == pin["size_bytes"] and sha(path) == pin["sha256"]
        pins[name] = pin["sha256"]
    build_crops(folder, run)
    basins = hydrobasins_paths(folder, pins)
    features, sections = source_vertices(basins, recipe)
    coast = coast_terminal(folder / "ural-kara-coast.osm", recipe["kara_coast_way"], sections["kara_edge"])
    gaps = {name: gap_path(gap, run, basins, features, recipe) for name, gap in recipe["terrain_gaps"].items()}
    north = [coast] + sections["north"] + gaps["00"] + sections["middle"] + gaps["02"] + sections["south"]
    assert LineString(north).is_simple
    (run / "ural-north.geometry.json").write_bytes(canonical({"type": "LineString", "coordinates": north}) + b"\n")
    river_raw = (folder / "ural-river-r2.osm").read_bytes()
    river = river_path(river_raw, recipe)
    full = connect_spring(north, folder, basins, pins, river)
    before_spring = {"type": "LineString", "coordinates": full}
    assert LineString(full).is_simple
    (run / "ural-before-spring.geometry.json").write_bytes(canonical(before_spring) + b"\n")
    result, receipt = join_spring(before_spring, river_raw)
    data = canonical(result)
    (run / "ural-reviewed.geometry.json").write_bytes(data + b"\n")
    assert digest(data) == recipe["expected_geometry_sha256"], receipt
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
