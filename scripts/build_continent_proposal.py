"""Build an explicitly provisional, native-resolution continent review grid.

These are proposed atlas groupings, not sovereignty or legal maritime boundaries.
The source audit and review notes are required companions to the output.
"""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import shapefile
from PIL import Image
from rasterio.features import rasterize
from rasterio.transform import from_origin
from scipy.ndimage import binary_erosion, distance_transform_edt, label
from scipy.spatial import cKDTree
from shapely.geometry import Polygon, box, shape
from shapely import make_valid, STRtree, box as boxes, intersection, area

W, H, STEP = 16384, 6827, 360 / 16384
TRANSFORM = from_origin(-180, 90, STEP, STEP)
GROUPS = {
    1: "Africa",
    2: "Asia",
    3: "Europe",
    4: "North America",
    5: "South America",
    6: "Oceania",
    7: "Atlantic Ocean",
    8: "Pacific Ocean",
    9: "Indian Ocean",
    10: "Arctic Ocean",
}
COLORS = [
    "#000000",
    "#e9b44c",
    "#de766e",
    "#8b91d4",
    "#70b890",
    "#c28bca",
    "#73bac4",
    "#285e88",
    "#214778",
    "#347ca0",
    "#8aa9bd",
]


def features(root, name):
    for feature in shapefile.Reader(
        str(root / name / (name + ".shp"))
    ).iterShapeRecords():
        yield (
            feature.record.as_dict(),
            make_valid(shape(feature.shape.__geo_interface__)),
        )


def parts(g):
    if g.geom_type == "Polygon":
        yield g
    elif hasattr(g, "geoms"):
        for child in g.geoms:
            yield from parts(child)


def xyz(rows, cols):
    lat = np.deg2rad(90 - (rows + 0.5) * STEP)
    lon = np.deg2rad(-180 + (cols + 0.5) * STEP)
    return np.column_stack(
        (np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat))
    )


def majority_land(records):
    """Use polygon intersection area for boundary cells, rather than center sampling."""
    records = [(part, code) for geom, code in records for part in parts(geom)]
    land = rasterize(
        records, out_shape=(H, W), transform=TRANSFORM, fill=0, dtype="uint8"
    )
    boundary = rasterize(
        [(g.boundary, 1) for g, _ in records],
        out_shape=(H, W),
        transform=TRANSFORM,
        all_touched=True,
        fill=0,
        dtype="uint8",
    )
    rows, cols = np.where(boundary)
    del boundary
    geometries = np.array([g for g, _ in records], dtype=object)
    codes = np.array([i for _, i in records])
    tree = STRtree(geometries)
    changed = 0
    overlap_cells = 0
    for start in range(0, len(rows), 10000):
        r, c = rows[start : start + 10000], cols[start : start + 10000]
        x, y = -180 + c * STEP, 90 - r * STEP
        cells = boxes(x, y - STEP, x + STEP, y)
        pair = tree.query(cells, predicate="intersects")
        areas = area(intersection(cells[pair[0]], geometries[pair[1]])) / STEP**2
        coverage = np.zeros((7, len(r)), dtype="float64")
        np.add.at(coverage, (codes[pair[1]], pair[0]), areas)
        total = coverage.sum(axis=0)
        overlap_cells += int((total > 1.00001).sum())
        winner = coverage.argmax(axis=0).astype("uint8")
        winner[total < 0.5 - 1e-10] = 0
        changed += int((land[r, c] != winner).sum())
        land[r, c] = winner
    print(
        f"Boundary-area check: {len(rows)} cells, {changed} corrected, {overlap_cells} overlap flags",
        flush=True,
    )
    return land, {
        "boundary_cells_checked": len(rows),
        "changed_from_center_sampling": changed,
        "source_overlap_flags": overlap_cells,
        "area_basis": "planar longitude/latitude within each small grid cell",
    }


def apply_ocean_meridians(grid):
    """Use the stated S-23 meridians instead of generalized label-polygon seams."""
    longitude = -180 + (np.arange(W) + 0.5) * STEP
    for south_of, west, east, boundary, west_group, east_group in [
        (-34.8333, 18, 22, 20, 7, 9),
        (-43.6333, 145, 149, 146 + 55 / 60, 9, 8),
        (-55.9667, -70, -64, -(67 + 16 / 60), 8, 7),
    ]:
        y0 = max(0, int(np.ceil((90 - south_of) / STEP - 0.5)))
        columns = np.where((longitude >= west) & (longitude < east))[0]
        values = grid[y0:, columns]
        marine = (values == west_group) | (values == east_group)
        assignments = np.broadcast_to(
            np.where(longitude[columns] < boundary, west_group, east_group),
            values.shape,
        )
        values[marine] = assignments[marine]
        grid[y0:, columns] = values


def fill_connected_seas(grid, land):
    """Fill named-sea label gaps using connected water cells, not label extents."""
    edge = (land > 0) & ~binary_erosion(land > 0)
    rr, cc = np.where(edge)
    groups = land[rr, cc]
    tree = cKDTree(xyz(rr, cc))
    for name, bounds, seed in [
        ("Mediterranean", (-6.1, 30, 37, 46), (15, 35)),
        ("Black Sea", (27, 40.5, 42, 47.5), (34, 43)),
        ("Caribbean", (-89, 9, -60, 23), (-75, 15)),
    ]:
        west, south, east, north = bounds
        x0 = int((west + 180) / STEP)
        x1 = int((east + 180) / STEP) + 1
        y0 = int((90 - north) / STEP)
        y1 = int((90 - south) / STEP) + 1
        components, _ = label(land[y0:y1, x0:x1] == 0)
        sy = int((90 - seed[1]) / STEP) - y0
        sx = int((seed[0] + 180) / STEP) - x0
        component = components[sy, sx]
        assert component > 0
        r, c = np.where(components == component)
        _, indices = tree.query(xyz(r + y0, c + x0), workers=2)
        grid[r + y0, c + x0] = groups[indices]
        print(f"{name}: {len(r)} connected water cells assigned", flush=True)


def write_grid_assets(grid, land, output):
    assert grid.min() > 0 and grid.max() <= 10 and grid.size == 111853568
    raw_hash = hashlib.sha256(grid.tobytes()).hexdigest()
    with gzip.open(output / "continent-cells.u8.gz", "wb") as handle:
        handle.write(grid.tobytes())
    palette = [0] * 768
    for code, color in enumerate(COLORS):
        rgb = [int(color[i : i + 2], 16) for i in (1, 3, 5)]
        water_rgb = [round(v * 0.55 + 232 * 0.45) for v in rgb] if code <= 6 else rgb
        palette[code * 3 : code * 3 + 3] = water_rgb
        palette[(code + 16) * 3 : (code + 16) * 3 + 3] = rgb
    display = grid + (land > 0).astype("uint8") * 16
    with gzip.open(output / "display-cells.u8.gz", "wb") as handle:
        handle.write(display.tobytes())
    image = Image.fromarray(display, "P")
    image.putpalette(palette)
    image.resize((2048, 854), Image.Resampling.NEAREST).save(output / "overview.png")
    return raw_hash, palette, hashlib.sha256(display.tobytes()).hexdigest()


def land_records(source, maldives=None):
    # Explicit approximate convention line, requiring review at the continental seam.
    # Longitude/latitude vertices trace Urals, Ural River and Greater Caucasus.
    seam = [
        (67, 90),
        (67, 70),
        (66.5, 68),
        (63.2, 66),
        (59.6, 64),
        (59, 62),
        (59, 60),
        (59.1, 58),
        (59.3, 56),
        (59.2, 54),
        (60, 52),
        (58.5, 51),
        (55, 51),
        (53, 51),
        (51.4, 50),
        (51.7, 48),
        (52.1, 46.7),
        (50, 44.5),
        (48.5, 41.9),
        (46.5, 42),
        (44.5, 42.7),
        (42.5, 43.2),
        (40, 43.7),
        (37.5, 44),
        (29.1, 41.2),
        (29, 41),
        (28.9, 40.8),
        (27.3, 40.5),
        (26.2, 40),
        (25.5, 39),
    ]
    # Only applies to transcontinental Eurasian source units; never reaches
    # negative-longitude Chukotka across the date line.
    europe_side = Polygon([(-30, 90), *seam, (-30, 39)])
    from correct_suez import SINAI
    sinai = Polygon(SINAI)
    records = []
    island_groups = {
        "French Southern and Antarctic Lands": 1,
        "Seychelles": 1,
        "Heard Island and McDonald Islands": 1,
        "Saint Helena": 1,
        "Reunion": 1,
        "Mauritius": 1,
        "Azores": 3,
        "British Indian Ocean Territory": 2,
        "Maldives": 2,
        "South Georgia and the Islands": 5,
        "Clipperton Island": 4,
    }
    for attr, geom in features(source, "ne_10m_admin_0_map_units"):
        if maldives is not None and attr["ADMIN"] == "Maldives":
            continue
        if attr["CONTINENT"] == "Antarctica":
            continue
        continent = next((i for i, n in GROUPS.items() if n == attr["CONTINENT"]), None)
        for poly in parts(geom):
            point = poly.representative_point()
            x, y = point.x, point.y
            group = island_groups.get(attr["GEOUNIT"], continent)
            if group is None:
                raise ValueError("Unreviewed continent tag: " + attr["GEOUNIT"])
            if attr["ADMIN"] == "Russia" and y > 70 and 35 < x < 75:
                records.append((poly, 3))
                continue
            if attr["ADMIN"] in {
                "Russia",
                "Kazakhstan",
                "Turkey",
                "Georgia",
                "Azerbaijan",
            }:
                records += [
                    (poly.intersection(europe_side), 3),
                    (poly.difference(europe_side), 2),
                ]
                continue
            if attr["ADMIN"] == "Egypt":
                records += [(poly.difference(sinai), 1), (poly.intersection(sinai), 2)]
                continue
            if attr["ADMIN"] == "Yemen" and 51 < x < 55 and 11 < y < 13.5:
                group = 1
            if attr["ADMIN"] == "Indonesia" and x >= 130 and y < 0:
                group = 6
            # Reviewed Papuan offshore groups north of the equator.
            if attr["ADMIN"] == "Indonesia" and (
                (134.1 <= x <= 134.5 and .65 <= y <= 1.1)
                or (130.7 <= x <= 131.4 and .15 <= y <= 1.25)
            ):
                group = 6
            if attr["ADMIN"] == "Japan" and 153.7 <= x <= 154.2 and 24.1 <= y <= 24.5:
                group = 6
            if attr["ADMIN"] in {"Cyprus", "Northern Cyprus"}:
                group = 2
            if attr["ADMIN"] == "United States of America" and x < -140 and 15 < y < 30:
                group = 6
            if attr["ADMIN"] == "Chile" and x < -100:
                group = 6
            if attr["ADMIN"] == "Colombia" and x < -80 and y > 11:
                group = 4
            if attr["ADMIN"] == "Spain" and x < -12 and y < 31:
                group = 1
            if attr["GEOUNIT"] == "Madeira":
                group = 1
            if attr["GEOUNIT"] == "Greenland":
                group = 4
            records.append((poly, group))
    if maldives is not None:
        for feature in json.loads(maldives.read_text())["features"]:
            records.append((make_valid(shape(feature["geometry"])), 2))
    records = [(g, i) for g, i in records if not g.is_empty]
    return records, island_groups, seam


def main(source, output):
    output.mkdir(parents=True, exist_ok=True)
    records, island_groups, seam = land_records(source)
    land, boundary_audit = majority_land(records)
    with gzip.open(output / "source-land-groups.u8.gz", "wb") as handle:
        handle.write(land.tobytes())
    print("Land source raster complete", flush=True)
    edge = (land > 0) & ~binary_erosion(land > 0)
    rr, cc = np.where(edge)
    shore_groups = land[rr, cc]
    tree = cKDTree(xyz(rr, cc))
    del edge, rr, cc
    # Basins are explicit proposed grouping envelopes. Named sea overrides below.
    lon = -180 + (np.arange(W) + 0.5) * STEP
    grid = np.empty((H, W), dtype="uint8")
    marine = list(features(source, "ne_10m_geography_marine_polys"))
    names = [a["name"] for a, _ in marine]
    ocean_ids = {
        "Arctic Ocean": 10,
        "North Atlantic Ocean": 7,
        "South Atlantic Ocean": 7,
        "North Pacific Ocean": 8,
        "South Pacific Ocean": 8,
        "INDIAN OCEAN": 9,
    }
    oceans = [(g, ocean_ids[a["name"]]) for a, g in marine if a["name"] in ocean_ids]
    ocean_labels = rasterize(
        oceans, out_shape=(H, W), transform=TRANSFORM, fill=0, dtype="uint8"
    )
    arctic_names = {
        "Chukchi Sea",
        "Beaufort Sea",
        "East Siberian Sea",
        "Laptev Sea",
        "Kara Sea",
        "Barents Sea",
        "Greenland Sea",
        "Lincoln Sea",
    }
    shared = {
        "Mediterranean Sea",
        "Black Sea",
        "Red Sea",
        "Gulf of Aden",
        "Bering Sea",
        "Caribbean Sea",
        "Caspian Sea",
        "Aegean Sea",
        "Sea of Azov",
    }
    # Seas not on this list remain ocean waters except their near-shore margins.
    continent_seas = {
        2: [
            "South China Sea",
            "East China Sea",
            "Yellow Sea",
            "Sea of Japan",
            "Sea of Okhotsk",
            "Persian Gulf",
            "Gulf of Oman",
            "Bay of Bengal",
            "Arabian Sea",
            "Andaman Sea",
            "Java Sea",
            "Sulu Sea",
            "Celebes Sea",
            "Banda Sea",
            "Gulf of Thailand",
            "Philippine Sea",
        ],
        3: [
            "Baltic Sea",
            "North Sea",
            "Irish Sea",
            "English Channel",
            "Bay of Biscay",
            "White Sea",
        ],
        4: [
            "Gulf of Mexico",
            "Hudson Bay",
            "Hudson Strait",
            "James Bay",
            "The North Western Passages",
        ],
        6: [
            "Coral Sea",
            "Tasman Sea",
            "Arafura Sea",
            "Timor Sea",
            "Bismarck Sea",
            "Solomon Sea",
            "Gulf of Carpentaria",
            "Great Australian Bight",
            "Gulf of Papua",
        ],
        1: ["Mozambique Channel"],
    }
    named = []
    for attrs, geom in marine:
        n = attrs["name"]
        if n in shared:
            named.append((geom, 99))
        for code, selected in continent_seas.items():
            if n in selected:
                named.append((geom, code))
        if n in arctic_names:
            named.append((geom, 10))
        if n == "Norwegian Sea":
            named.append((geom, 7))
    seas = rasterize(
        named, out_shape=(H, W), transform=TRANSFORM, fill=0, dtype="uint8"
    )
    # Conservative near-shore search envelope; exact distance is evaluated on a sphere.
    # Horizontal wrap avoids losing candidates across the date line.
    padded = np.pad(land > 0, ((0, 0), (256, 256)), mode="wrap")
    pixel_distance = distance_transform_edt(~padded)[:, 256:-256].astype("float32")
    del padded
    for start in range(0, H, 64):
        end = min(H, start + 64)
        lat = 90 - (np.arange(start, end)[:, None] + 0.5) * STEP
        base = (
            np.broadcast_to(
                np.where(
                    (lon >= 20) & (lon < 147),
                    9,
                    np.where((lon >= -67.25) & (lon < 20), 7, 8),
                ),
                (end - start, W),
            )
            .copy()
            .astype("uint8")
        )
        base[np.broadcast_to(lat >= 66.55, base.shape)] = 10
        source_ocean = ocean_labels[start:end]
        base[source_ocean > 0] = source_ocean[source_ocean > 0]
        overrides = seas[start:end]
        land_part = land[start:end]
        threshold = 100 / (111 * STEP * np.maximum(np.cos(np.deg2rad(lat)), 0.01))
        query_mask = (land_part == 0) & (
            ((pixel_distance[start:end] <= threshold) & (base != 10))
            | (overrides == 99)
        )
        rows, cols = np.where(query_mask)
        distance, index = tree.query(xyz(rows + start, cols), workers=2)
        distance = 2 * 6371.0088 * np.arcsin(np.minimum(distance / 2, 1))
        nearest = np.zeros(base.shape, dtype="uint8")
        nearest[rows, cols] = shore_groups[index]
        # 100 km is an editorial review proposal, NOT territorial waters or an EEZ.
        near = np.zeros(base.shape, dtype=bool)
        near[rows, cols] = distance <= 100
        near &= base != 10
        base[near] = nearest[near]
        base[(overrides > 0) & (overrides != 99)] = overrides[
            (overrides > 0) & (overrides != 99)
        ]
        base[overrides == 99] = nearest[overrides == 99]
        base[land_part > 0] = land_part[land_part > 0]
        grid[start:end] = base
        if start % 512 == 0:
            print(f"Rows {end}/{H}", flush=True)
    # Inland lakes inherit surrounding continental geography, even if wider than
    # the coastal-water envelope. They never become open-ocean pockets.
    lake_shapes = [(g, 1) for _, g in features(source, "ne_10m_lakes")]
    lake_mask = rasterize(
        lake_shapes, out_shape=(H, W), transform=TRANSFORM, fill=0, dtype="uint8"
    )
    lr, lc = np.where((lake_mask > 0) & (land == 0))
    if len(lr):
        _, nearest_index = tree.query(xyz(lr, lc), workers=2)
        grid[lr, lc] = shore_groups[nearest_index]
    del lake_mask
    # Preserve island-region waters around source islands that have no majority
    # land cell. This does NOT invent land cells or resolve their resolution issue.
    tiny_islands = []
    for geom, code in records:
        for island in parts(geom):
            if island.area >= 4 * STEP**2:
                continue
            p = island.representative_point()
            if not (-60 <= p.y < 90):
                continue
            tiny_islands.append((p.x, p.y, code))
    for longitude, latitude, code in tiny_islands:
        cy, cx = int((90 - latitude) / STEP), int((longitude + 180) / STEP)
        dy = int(np.ceil(0.91 / STEP)) + 1
        dx = int(np.ceil(0.91 / (STEP * max(np.cos(np.deg2rad(latitude)), 0.05)))) + 1
        rows = np.arange(max(0, cy - dy), min(H, cy + dy + 1))
        cols = np.arange(cx - dx, cx + dx + 1) % W
        rr, cc = np.meshgrid(rows, cols, indexing="ij")
        point = np.array(
            [
                np.cos(np.deg2rad(latitude)) * np.cos(np.deg2rad(longitude)),
                np.cos(np.deg2rad(latitude)) * np.sin(np.deg2rad(longitude)),
                np.sin(np.deg2rad(latitude)),
            ]
        )
        chord = np.linalg.norm(xyz(rr.ravel(), cc.ravel()) - point, axis=1).reshape(
            rr.shape
        )
        values = grid[rr, cc]
        chosen = (
            (chord <= 2 * np.sin(100 / (2 * 6371.0088)))
            & (values >= 7)
            & (values != 10)
        )
        grid[rr[chosen], cc[chosen]] = code
    fill_connected_seas(grid, land)
    apply_ocean_meridians(grid)
    raw_hash, palette, display_hash = write_grid_assets(grid, land, output)
    metadata = {
        "status": "draft_not_approval_ready",
        "width": W,
        "height": H,
        "step": STEP,
        "west": -180,
        "north": 90,
        "southern_edge": 90 - H * STEP,
        "sha256_uncompressed": raw_hash,
        "display_sha256_uncompressed": display_hash,
        "palette": [palette[i : i + 3] for i in range(0, 768, 3)],
        "groups": [
            {"id": i, "name": name, "color": COLORS[i], "cells": int((grid == i).sum())}
            for i, name in GROUPS.items()
        ],
        "boundary_audit": boundary_audit,
        "tiny_source_island_count": len(tiny_islands),
        "caveats": [
            "Transcontinental seams use approximate convention lines and need lower-level compatibility checks.",
            "Marine label polygons are generalized; no claim of precise IHO boundaries.",
            "100-km near-shore grouping and shared-sea nearest-shore allocation are editorial proposals.",
            "Small inhabited-island exceptions are not yet fully audited.",
        ],
        "island_groups": island_groups,
        "seam_vertices": seam,
        "shared_seas": sorted(shared),
        "continent_seas": continent_seas,
        "arctic_seas": sorted(arctic_names),
    }
    (output / "proposal.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({"output": str(output), "sha256": raw_hash}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("sources", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.sources, args.output)
