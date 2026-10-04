#!/usr/bin/env python3
"""Create a six-country neighbor-only GeoJSON view from the retained OCHA WCA ZIPs."""
from __future__ import annotations
import gzip, hashlib, json, pathlib, subprocess, tempfile

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "sources"
COUNTRIES = "'Sierra Leone','Togo','Guinea','Liberia','Ghana','Benin'"
outputs = {}
with tempfile.TemporaryDirectory(prefix="wa479-neighbors-") as temp:
    tmp = pathlib.Path(temp)
    for level, layer_dir, layer_name, file_prefix in [
        (0, "wca_admbnda_adm0_edgematched_942026", "wca_admbnda_adm0_edgematched", "wca_admbnda_adm0_edgematched_942026"),
        (1, "wca_admbnda_adm1_edgematched_942026", "wca_admbnda_adm1_edgematched", "wca_admbnda_adm1_edgematched_942026"),
    ]:
        archive = SRC / f"hdx-wca-{file_prefix}.zip.gz"
        zip_path = tmp / f"{layer_dir}.zip"
        zip_path.write_bytes(gzip.decompress(archive.read_bytes()))
        shp = f"/vsizip/{zip_path}/{layer_dir}/{layer_name}.shp"
        out = tmp / f"wca-adm{level}-neighbors.geojson"
        subprocess.run(["ogr2ogr", "-f", "GeoJSON", "-lco", "RFC7946=YES", "-where",
                        f"adm0_name IN ({COUNTRIES})", str(out), shp], check=True)
        raw = out.read_bytes()
        name = f"wca-edge-matched-adm{level}-neighbors.geojson.gz"
        target = SRC / name
        target.write_bytes(gzip.compress(raw, mtime=0))
        data = json.loads(raw)
        outputs[str(level)] = {"file": f"sources/{name}", "features": len(data["features"]),
            "countries": sorted({f["properties"].get("adm0_name") for f in data["features"]}),
            "sha256": hashlib.sha256(raw).hexdigest(), "gzip_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "ogr_version": subprocess.check_output(["ogr2ogr", "--version"], text=True).strip(),
            "source_archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "filter": f"adm0_name IN ({COUNTRIES})"}
(SRC / "neighbor-extract.json").write_text(json.dumps(outputs, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(outputs, indent=2, ensure_ascii=False))
