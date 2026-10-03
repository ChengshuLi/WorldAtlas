#!/usr/bin/env python3
"""Screen the three assigned Galápagos cantons against GSHHG 2.3.7."""
import gzip, hashlib, json, pathlib, struct, sys

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
if len(sys.argv)!=2:
    raise SystemExit("usage: inspect_gshhg.py /path/to/gshhs_f.b")
data=pathlib.Path(sys.argv[1]).read_bytes()
member_sha="af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6"
if hashlib.sha256(data).hexdigest()!=member_sha:
    raise SystemExit("GSHHG gshhs_f.b hash does not match 2.3.7 release")

index=json.loads((ROOT/"data/world-index.json").read_text())
gal_ids={"gb:ECU:ADM2:8360857B49822942031092","gb:ECU:ADM2:8360857B73941749048341","gb:ECU:ADM2:8360857B96374734157472"}
features={}
for part_name in index["parts"]:
    for f in json.loads((ROOT/"data"/part_name).read_text())["features"]:
        if f["properties"]["id"] in gal_ids: features[f["properties"]["id"]]=f
if set(features)!=gal_ids: raise SystemExit("Galápagos assigned-ID set changed")

def polygons(g):
    c=g["coordinates"]
    return [c] if g["type"]=="Polygon" else c

def centroid(ring):
    area2=sx=sy=0.0
    for i,(x,y) in enumerate(ring):
        x2,y2=ring[(i+1)%len(ring)]; z=x*y2-x2*y
        area2+=z; sx+=(x+x2)*z; sy+=(y+y2)*z
    if abs(area2)<1e-14: return (sum(p[0] for p in ring)/len(ring),sum(p[1] for p in ring)/len(ring))
    return (sx/(3*area2),sy/(3*area2))

def in_ring(x,y,ring):
    inside=False
    for i,(x1,y1) in enumerate(ring):
        x2,y2=ring[(i+1)%len(ring)]
        if (y1>y)!=(y2>y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1: inside=not inside
    return inside

def in_geometry(x,y,g):
    return any(in_ring(x,y,poly[0]) and not any(in_ring(x,y,hole) for hole in poly[1:]) for poly in polygons(g))

gals={i:f["properties"]["name"] for i,f in features.items()}
geoms={i:f["geometry"] for i,f in features.items()}
domain=[-92.0,-2.0,-89.0,1.0]
pos=0; records=[]; counts={}; all_records=0; selected=[]
while pos<len(data):
    if len(data)-pos<44: raise SystemExit("trailing truncated GSHHG header")
    lid,num,flag,west,east,south,north,area,area_full,container,ancestor=struct.unpack_from(">IIIiiiiIIii",data,pos)
    start=pos; pos+=44; end=pos+num*8
    if end>len(data): raise SystemExit(f"truncated GSHHG coordinates at {lid}")
    level=flag&255; counts[str(level)]=counts.get(str(level),0)+1; all_records+=1
    west/=1e6; east/=1e6; south/=1e6; north/=1e6
    if west>=180: west-=360; east-=360
    if level==1 and west<domain[2] and east>domain[0] and south<domain[3] and north>domain[1]:
        coords=[]
        for j in range(num):
            lon,lat=struct.unpack_from(">ii",data,pos+j*8); lon/=1e6;lat/=1e6
            if lon>180:lon-=360
            coords.append((lon,lat))
        center=centroid(coords)
        containing=[{"location_id":i,"name":n} for i,n in gals.items() if in_geometry(*center,geoms[i])]
        records.append({"gshhg_id":lid,"level":level,"coordinate_count":num,"container_id":container,"ancestor_id":ancestor,"area_km2_header":area/10**(flag>>26),"bounds":[west,south,east,north],"representative_point":list(center),"current_assigned_units_containing_point":containing,"classification":"candidate source land polygon; attribution uses one point-in-polygon test only"})
        selected.append(data[start:end])
    pos=end

native=b"".join(selected); compressed=gzip.compress(native,mtime=0)
(HERE/"sources/gshhg-galapagos-level1.bin.gz").write_bytes(compressed)
archive=pathlib.Path("/tmp/gshhg-2.3.7.zip")
assessment={"source":{"title":"Global Self-consistent Hierarchical High-resolution Geography (GSHHG), full resolution binary, release 2.3.7","release_date":"2017-06-15","archive_url":"https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-bin-2.3.7.zip","archive_sha256":"28600e8f7a08645aab43079326df6504212ec5ccb2b4bcf3b5f4f12ed60e82bc","archive_bytes":archive.stat().st_size if archive.exists() else None,"member":"gshhs_f.b","member_sha256":member_sha,"member_bytes":len(data),"license":"LGPLv3 or later; see archive LICENSE.TXT and retained WorldAtlas copy data/macro-improvements/macro-coverage-oceania/gshhg-LGPL.txt","restore":"Download the pinned archive, verify archive SHA-256, extract gshhs_f.b, and verify member SHA-256."},"selection":{"purpose":"screen known Galápagos land components for three assigned Ecuador ADM2 features","bbox_wgs84":domain,"source_level":1,"whole_records_retained":True,"retained_file":"sources/gshhg-galapagos-level1.bin.gz","retained_compressed_sha256":hashlib.sha256(compressed).hexdigest(),"retained_uncompressed_sha256":hashlib.sha256(native).hexdigest(),"retained_bytes":len(native),"record_count":len(records),"member_source_polygon_level_counts":counts},"method":{"records":"Big-endian 44-byte GSHHG header and coordinate pairs; normalize 0–360 longitudes to −180–180. Select complete level-1 source records by bbox overlap. No records or atlas geometries are edited.","candidate_attribution":"Calculate one planar vertex centroid per source polygon and use ray-crossing point-in-polygon against each assigned current Polygon/MultiPolygon, respecting interior rings. A matched point is screening only; it does not prove full overlap or containment. A non-match does not prove omission."},"galapagos_admin_features":{i:{"name":gals[i],"current_polygon_components":len(polygons(geoms[i]))} for i in sorted(gals)},"source_land_candidates":records,"limitations":["GSHHG is a 2017 global physical-shoreline compilation, not an authoritative Ecuador island register, cadastral source, administrative boundary, settlement gazetteer, or complete modern shoreline.","The GSHHG polygon IDs have no toponyms. The 2017 source and this coarse screening do not establish the names or completeness of the 14 current canton components.","A bbox selector and one centroid overlay do not validate shoreline topology or certify complete land assignment. All named island, settlement, coastal, and land-hole review remains open.","No political ownership or current parent membership is inferred from physical land polygons."]}
(HERE/"gshhg-screen.json").write_text(json.dumps(assessment,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"source_records":len(records),"assigned_point_counts":{n:sum(any(q["location_id"]==i for q in r["current_assigned_units_containing_point"]) for r in records) for i,n in gals.items()},"retained_bytes":len(native),"retained_sha256":hashlib.sha256(native).hexdigest()},indent=2))
