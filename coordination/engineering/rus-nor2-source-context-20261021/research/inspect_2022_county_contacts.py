#!/usr/bin/env python3
"""Targeted read-only comparison of two retained native centers to the official 2022 Fylke family.

The downloaded GML is read from the adjacent exact ZIP. This is not an owner
observer, source scanner, ownership assignment, or geometry repair. It tests
only the two pre-existing coordinates against the complete 11-feature county
family, in the source CRS EPSG:25833.
"""
import hashlib
import json
import math
import pathlib
import zipfile
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
ZIP = HERE / "Basisdata_0000_Norge_25833_Fylker2022_GML.zip"
ZIP_SHA256 = "0162fff92a3354104a5e5380c82836ab50d4f8353de1a2d28f75d8a345746ad7"
GML_MEMBER = "Basisdata_0000_Norge_25833_Fylker2022_GML.gml"
GML_LENGTH = 37491789
G = "{http://www.opengis.net/gml/3.2}"
S = "{http://skjema.geonorge.no/SOSI/produktspesifikasjon/AdmEnheter/4.1}"

# Retained original native-center coordinates; no coordinate resampling.
POINTS = [
    {"x": 152965, "y": 59862, "latitude": 69.4336981394968, "longitude": 30.048518877352535},
    {"x": 152972, "y": 59849, "latitude": 69.43996822160625, "longitude": 30.058131107771402},
]

# EPSG:25833 is ETRS89 / UTM zone 33N. This standard forward transverse
# Mercator formula uses the GRS80 ellipsoid; results below are comparisons to
# published polygon coordinates, not positional-accuracy or legal conclusions.
A = 6378137.0
F = 1 / 298.257222101
E2 = F * (2 - F)
EP2 = E2 / (1 - E2)
K0 = 0.9996
LON0 = math.radians(15.0)

def lonlat_to_utm33(lon, lat):
    phi, lam = math.radians(lat), math.radians(lon)
    n = A / math.sqrt(1 - E2 * math.sin(phi) ** 2)
    t = math.tan(phi) ** 2
    c = EP2 * math.cos(phi) ** 2
    aa = math.cos(phi) * (lam - LON0)
    m = A * ((1 - E2/4 - 3*E2**2/64 - 5*E2**3/256) * phi
             - (3*E2/8 + 3*E2**2/32 + 45*E2**3/1024) * math.sin(2*phi)
             + (15*E2**2/256 + 45*E2**3/1024) * math.sin(4*phi)
             - (35*E2**3/3072) * math.sin(6*phi))
    east = 500000 + K0*n*(aa + (1-t+c)*aa**3/6
             + (5-18*t+t*t+72*c-58*EP2)*aa**5/120)
    north = K0*(m + n*math.tan(phi)*(aa**2/2
             + (5-t+9*c+4*c*c)*aa**4/24
             + (61-58*t+t*t+600*c-330*EP2)*aa**6/720))
    return east, north

def rings_from_patch(patch):
    rings = []
    for boundary in list(patch):
        if boundary.tag not in (G + "exterior", G + "interior"):
            continue
        coordinates = []
        for pos_list in boundary.iter(G + "posList"):
            values = list(map(float, pos_list.text.split()))
            seq = list(zip(values[::2], values[1::2]))
            if coordinates and seq and coordinates[-1] == seq[0]:
                coordinates.extend(seq[1:])
            else:
                coordinates.extend(seq)
        rings.append({"exterior": boundary.tag == G + "exterior", "coordinates": coordinates})
    return rings

def point_in_ring(point, ring):
    x, y = point
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        if (y1 > y) != (y2 > y):
            crossing_x = (x2-x1) * (y-y1) / (y2-y1) + x1
            if x < crossing_x:
                inside = not inside
    return inside

def distance_to_ring(point, ring):
    best = float("inf")
    px, py = point
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        vx, vy = x2-x1, y2-y1
        den = vx*vx + vy*vy
        t = 0 if den == 0 else max(0, min(1, ((px-x1)*vx + (py-y1)*vy)/den))
        best = min(best, math.hypot(px-x1-t*vx, py-y1-t*vy))
    return best

def feature_props(feature):
    props = {}
    for node in feature:
        name = node.tag.split("}")[-1]
        if name in ("fylkesnummer", "fylkesnavn", "oppdateringsdato", "datauttaksdato"):
            props.setdefault(name, []).append(" ".join("".join(node.itertext()).split()))
    ident = feature.find(".//" + S + "lokalId")
    props["local_id"] = ident.text if ident is not None else None
    props["gml_id"] = feature.attrib.get(G + "id")
    return props

def main():
    archive_bytes = ZIP.read_bytes()
    if hashlib.sha256(archive_bytes).hexdigest() != ZIP_SHA256:
        raise SystemExit("Exact source ZIP hash mismatch")
    family = []
    feature_counts = {}
    with zipfile.ZipFile(ZIP) as zf:
        if zf.namelist() != [GML_MEMBER]:
            raise SystemExit("Unexpected GML archive members")
        info = zf.getinfo(GML_MEMBER)
        if info.file_size != GML_LENGTH:
            raise SystemExit("Unexpected decoded GML member length")
        with zf.open(GML_MEMBER) as source:
            for _, member in ET.iterparse(source, events=("end",)):
                if member.tag == G + "featureMember":
                    feature = list(member)[0]
                    kind = feature.tag.split("}")[-1]
                    feature_counts[kind] = feature_counts.get(kind, 0) + 1
                    if kind == "Fylke":
                        number = feature.find(S + "fylkesnummer")
                        if number is None:
                            raise SystemExit("Fylke feature missing number")
                        patches = [rings_from_patch(p) for p in feature.iter(G + "PolygonPatch")]
                        prop = feature_props(feature)
                        canonical_geometry = json.dumps(patches, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
                        prop["polygon_coordinate_structure_sha256"] = hashlib.sha256(canonical_geometry).hexdigest()
                        prop["polygon_patch_count"] = len(patches)
                        prop["ring_count"] = sum(len(p) for p in patches)
                        prop["vertex_count"] = sum(len(r["coordinates"]) for p in patches for r in p)
                        family.append({"properties": prop, "patches": patches})
                    member.clear()
    if len(family) != 11:
        raise SystemExit(f"Expected complete 11-feature Fylke family, got {len(family)}")
    match_results = []
    for original in POINTS:
        point = lonlat_to_utm33(original["longitude"], original["latitude"])
        matches = []
        nearest = (float("inf"), None)
        for feature in family:
            props, patches = feature["properties"], feature["patches"]
            inside_feature = False
            for patch in patches:
                exteriors = [r["coordinates"] for r in patch if r["exterior"]]
                interiors = [r["coordinates"] for r in patch if not r["exterior"]]
                for ring in exteriors + interiors:
                    dist = distance_to_ring(point, ring)
                    if dist < nearest[0]:
                        nearest = (dist, props)
                if any(point_in_ring(point, ring) for ring in exteriors) and not any(point_in_ring(point, ring) for ring in interiors):
                    inside_feature = True
            if inside_feature:
                matches.append({"fylkesnummer": props["fylkesnummer"], "fylkesnavn": props["fylkesnavn"], "local_id": props["local_id"], "gml_id": props["gml_id"], "polygon_coordinate_structure_sha256": props["polygon_coordinate_structure_sha256"]})
        match_results.append({
            "native_key_xy": [original["x"], original["y"]],
            "retained_center_lon_lat": [original["longitude"], original["latitude"]],
            "transformed_center_epsg25833_metres": [point[0], point[1]],
            "matching_2022_fylke_features": matches,
            "nearest_2022_fylke_boundary_distance_m": nearest[0],
            "nearest_boundary_feature": {"fylkesnummer": nearest[1]["fylkesnummer"], "fylkesnavn": nearest[1]["fylkesnavn"], "local_id": nearest[1]["local_id"], "gml_id": nearest[1]["gml_id"], "polygon_coordinate_structure_sha256": nearest[1]["polygon_coordinate_structure_sha256"]} if nearest[1] else None,
        })
    out = {
        "method": "Streamed the exact 2022 GML and tested only the two pre-existing native center coordinates against each of the complete 11 Fylke polygons. EPSG:25833 GRS80 UTM forward formula, even-odd point-in-ring, polygon patch union with interiors excluded. No geometry was repaired, simplified, or redistributed.",
        "source": {"url": "https://nedlasting.geonorge.no/geonorge/Basisdata/Fylker2022/GML/Basisdata_0000_Norge_25833_Fylker2022_GML.zip", "zip_bytes": len(archive_bytes), "zip_sha256": ZIP_SHA256, "member": GML_MEMBER, "decoded_bytes": GML_LENGTH, "feature_counts_by_type": feature_counts, "fylke_feature_count": len(family), "crs": "urn:ogc:def:crs:EPSG::25833", "license_and_terms_limit": "The feed says rights=Kartverket; Kartverket's general free-product terms state CC BY 4.0 and attribution, but the dataset-specific Data Norge record page returned HTTP 404 and was not independently read."},
        "tested_points": match_results,
        "limits": ["Point-in-polygon results are geometric comparisons to this 2022 source, not legal or sovereign determinations.", "Boundary distances are computed from transformed centers with a local GRS80 UTM formula and are not stated source accuracy; no independent CRS library was installed.", "The comparison does not establish other territorial/physical predicates or authorize a native assignment.", "Original 2022 geoBoundaries source was the simplified Kartverket-derived product, distinct from this full official Kartverket GML extraction."]
    }
    path = HERE / "two-center-2022-fylke-comparison.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()
