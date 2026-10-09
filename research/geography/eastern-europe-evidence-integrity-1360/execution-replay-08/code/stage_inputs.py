#!/usr/bin/env python3
"""Restore exact, bounded source records from the pinned main tree."""
from __future__ import annotations
import gzip, hashlib, json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "432c5b8e0ac9b9597738a31f5386569312c75966"
EXPECTED_PRODUCTS = {
    "BLR": ("gb:BLR:ADM2", "8d88002a6b05014da9af4dc1f33f8cb928d961b23c1912654cc056cddca5841a", 1138204, 118),
    "POL": ("gb:POL:ADM2", "c19830763e611df9b4b56bab55c0c856a9a33dc7b80a6d28fe611f3462e1f3ce", 2906313, 380),
    "UKR": ("gb:UKR:ADM2", "c102ab08775ce4dc25a64e133bb7726a1b50715d31140e9846eaad26602631cb", 698065, 495),
}
TRANSPORT = {
    "BLR": ("coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-BLR-ADM2-000.bin.gz", "308fe6563c7735f625ee11b725a67dda2b729b3c1e1d72034a28edc4e06a120e"),
    "POL": ("coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-POL-ADM2-000.bin.gz", "d6ddf97bcf615136b4be684ca630f4eb12eb675f0dd054e409efa492054ff24f"),
    "UKR": ("coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-UKR-ADM2-000.bin.gz", "35cef639ce0928d52a51699b0183d5369ba725befec9de43415e8b51664405b9"),
}
PINNED_PATHS = {
    "world-index": "data/world-index.json",
    "administrative-registry": "data/administrative-sources.json",
    "atlas-part-2": "data/geography/part-2.json",
    "atlas-part-19": "data/geography/part-19.json",
    "atlas-part-25": "data/geography/part-25.json",
    "immutable-code": "scripts/evidence/immutable.py",
    "geometry-code": "scripts/evidence/geometry.py",
    "ellipsoidal-area-code": "scripts/ellipsoidal_area.py",
    "administrative-script": "scripts/administrative.py",
    "source-corpus-catalogue": "coordination/engineering/original-geography-source-corpus-20261006/catalogue.json",
    "source-corpus-citation": "coordination/engineering/original-geography-source-corpus-20261006/CITATION-AND-USE-geoBoundaries-original.txt",
    "source-corpus-evidence": "coordination/engineering/original-geography-source-corpus-20261006/evidence-quality.json",
    "candidate-source": "coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/candidates-012.geojson.gz",
    "candidate-receipt": "coordination/engineering/physical-gap-audit-1005-20261005-local18/evidence-quality.json",
    "routing-component": "coordination/engineering/global-actionability-routing-20261007/results/components-022.bin.gz",
    "routing-family": "coordination/engineering/global-actionability-routing-20261007/results/families-005.bin.gz",
    "routing-batch": "coordination/engineering/global-actionability-routing-20261007/results/batches-001.bin.gz",
    "routing-admin-binding": "coordination/engineering/global-actionability-routing-20261007/results/admin-bindings-007.bin.gz",
    "physical-component-input": "coordination/engineering/global-physical-comparison-20261006/results/components-062.jsonl.gz",
    "physical-input-config": "coordination/engineering/global-physical-comparison-20261006/input-config.json",
    "physical-source-pins": "coordination/engineering/global-physical-comparison-20261006/control-source-pins.json",
    "physical-audit-input-manifest": "coordination/engineering/physical-gap-audit-1005-20261005-local18/input-envelope-v1/manifest.json",
    "numeric-run-one": "coordination/engineering/complete-numeric-closure-diagnosis-20261007/r1/diagnoses-027.jsonl.gz",
    "numeric-run-two": "coordination/engineering/complete-numeric-closure-diagnosis-20261007/r2/diagnoses-027.jsonl.gz",
    "lakes-source": "coordination/engineering/coverage-gaps-907-20261005-local01/sources/natural-earth-lakes.geojson.gz",
    "lakes-receipt": "coordination/engineering/coverage-gaps-907-20261005-local01/sources/receipt.json",
}
EXPECTED_BASELINE = {
    "world-index": "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03",
    "administrative-registry": "ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633",
    "atlas-part-2": "93eeb8f5dab7d8ca6c86593f7ab7b1310312757abcef33d4e7200a270624a1bf",
    "atlas-part-19": "baeade0e3ad11cdd65beb101e7b79284ae2b6ee8794f9b08e86631c7f20e6269",
    "atlas-part-25": "dada55df1b7f0f2a2b307f4aea071d0e48791e3105875755fe74a292a6763394",
}

def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def git_bytes(path: str) -> bytes:
    return subprocess.run(["git", "show", f"{BASELINE}:{path}"], check=True, stdout=subprocess.PIPE).stdout

def git_entry(path: str) -> tuple[str, str]:
    row = subprocess.run(["git", "ls-tree", BASELINE, "--", path], check=True, text=True, stdout=subprocess.PIPE).stdout.strip().split()
    if len(row) < 4 or row[3] != path:
        raise ValueError(f"baseline Git tree entry missing: {path}")
    return row[0], row[2]

def write_exact(category: str, key: str, origin: str, expected_sha: str | None = None) -> dict:
    data = git_bytes(origin)
    digest = sha(data)
    if expected_sha and digest != expected_sha:
        raise ValueError(f"baseline digest mismatch for {origin}: {digest}")
    target = ROOT / "inputs" / category / key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    mode, oid = git_entry(origin)
    return {"origin_path": origin, "origin_commit": BASELINE, "origin_mode": mode, "origin_blob_oid": oid, "path": str(target.relative_to(ROOT)), "bytes": len(data), "sha256": digest}

def main() -> None:
    head = subprocess.run(["git", "rev-parse", "HEAD"], check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
    remote = subprocess.run(["git", "rev-parse", "origin/main"], check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
    subprocess.run(["git", "cat-file", "-e", f"{BASELINE}^{{commit}}"], check=True, stdout=subprocess.DEVNULL)
    records = []
    for name, path in PINNED_PATHS.items():
        suffix = ".py" if name == "administrative-script" else ".txt" if name == "source-corpus-citation" else ".gz" if name in {"candidate-source", "physical-component-input", "numeric-run-one", "numeric-run-two", "lakes-source"} else ".json"
        records.append(write_exact("baseline", name + suffix, path, EXPECTED_BASELINE.get(name)))
    for country, (path, expected) in TRANSPORT.items():
        transported = git_bytes(path)
        if sha(transported) != expected:
            raise ValueError(f"transport digest mismatch: {country}")
        raw = gzip.decompress(transported)
        _, expected_raw, expected_bytes, expected_features = EXPECTED_PRODUCTS[country]
        if len(raw) != expected_bytes or sha(raw) != expected_raw:
            raise ValueError(f"whole source reconstruction mismatch: {country}")
        product = json.loads(raw)
        if product.get("type") != "FeatureCollection" or len(product.get("features", [])) != expected_features:
            raise ValueError(f"source feature inventory mismatch: {country}")
        destination = ROOT / "inputs" / "source-products" / f"geoBoundaries-{country}-ADM2_simplified.geojson"
        destination.write_bytes(raw)
        mode, oid = git_entry(path)
        transport_path = ROOT / "inputs" / "source-transports" / Path(path).name
        transport_path.parent.mkdir(parents=True, exist_ok=True)
        transport_path.write_bytes(transported)
        records.append({"origin_path": path, "origin_commit": BASELINE, "origin_mode": mode, "origin_blob_oid": oid, "transport_path": str(transport_path.relative_to(ROOT)), "transport_sha256": sha(transported), "transport_bytes": len(transported), "path": str(destination.relative_to(ROOT)), "bytes": len(raw), "sha256": sha(raw), "feature_count": len(product["features"]), "product_key": EXPECTED_PRODUCTS[country][0]})
    lakes_gzip = ROOT / "inputs" / "baseline" / "lakes-source.gz"
    lakes_raw = gzip.decompress(lakes_gzip.read_bytes())
    expected_lakes_sha = "2d036f53dedec578001c5c30c2959ee7d4eebc1306900fa4367c49929ec8f2d9"
    if len(lakes_raw) != 5043554 or sha(lakes_raw) != expected_lakes_sha:
        raise ValueError("Natural Earth whole source reconstruction mismatch")
    lakes = json.loads(lakes_raw)
    if len(lakes.get("features", [])) != 1355:
        raise ValueError("Natural Earth complete feature inventory mismatch")
    lakes_path = ROOT / "inputs" / "source-products" / "natural-earth-10m-lakes.geojson"
    lakes_path.write_bytes(lakes_raw)
    records.append({"origin_path": PINNED_PATHS["lakes-source"], "origin_commit": BASELINE, "transport_sha256": sha(lakes_gzip.read_bytes()), "path": str(lakes_path.relative_to(ROOT)), "bytes": len(lakes_raw), "sha256": sha(lakes_raw), "feature_count": len(lakes["features"]), "role": "modern major-lakes context only; not complete rivers or small-water coverage"})
    registry = json.loads((ROOT / "inputs" / "baseline" / "administrative-registry.json").read_text())
    for country, (key, expected, _, _) in EXPECTED_PRODUCTS.items():
        row = registry[key]
        if row.get("sha256") != expected:
            raise ValueError(f"administrative registry source hash mismatch: {key}")
    (ROOT / "inputs" / "source-custody.json").write_text(json.dumps({"version": 1, "baseline_commit": BASELINE, "files": records}, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"status": "restored", "baseline_commit": BASELINE, "working_head": head, "origin_main_at_stage": remote, "files": len(records), "source_products": 4, "restored_source_bytes": sum(r["bytes"] for r in records if r.get("feature_count")), "custody_manifest": "inputs/source-custody.json"}, sort_keys=True))

if __name__ == "__main__":
    main()
