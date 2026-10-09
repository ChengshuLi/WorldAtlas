#!/usr/bin/env python3
"""Assemble issue #1629's whole-file evidence manifest."""
import gzip
import hashlib
import json
import pathlib
import subprocess
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[3]
PACKET = ROOT / "research/geography/central-africa-20-source-fit-20261009"
BASE = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
COMPONENT_COMMIT = "7c7cdf2388e0e7200b937c2cfb440b53165d9d98"
GSHHG_SOURCE_COMMIT = "f8f99612e4d83d561b370189a1969c3e4301a1e3"
WORKER = "01a112b9-e2b7-7d03-8000-eb2890649612"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def git_show(commit, path):
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def desc(path, commit=None, uncompressed=None):
    if commit is None:
        raw = (ROOT / path).read_bytes()
    else:
        raw = git_show(commit, path)
    d = {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}
    if uncompressed is not None:
        d.update({"uncompressed_bytes": uncompressed[0], "uncompressed_sha256": uncompressed[1]})
    return d if commit is None else {"commit": commit, **d}


def source_file(path, uncompressed=None):
    return desc(path, uncompressed=uncompressed)


def main():
    component_custody = json.loads((PACKET / "component-custody.json").read_bytes())
    comparison_custody = json.loads((PACKET / "source-comparison-custody.json").read_bytes())
    source_custody = json.loads((PACKET / "source-custody.json").read_bytes())
    fit = json.loads((PACKET / "results/simplified-source-fit.json").read_bytes())
    ids = sorted(f["id"] for f in json.load(gzip.open(PACKET / "inputs/components/selected-20-components.json.gz", "rt"))["features"])

    baseline = {}
    def add(path, commit=BASE, uncompressed=None):
        d = desc(path, commit, uncompressed)
        key = (d["commit"], d["path"])
        baseline[key] = d
        return d

    # Exact administrative source recipe, registry, policy and refresh contract.
    add("data/administrative-sources.json")
    add("scripts/administrative.py")
    add("research/geography/arctic-seven-source-fit-20261008/README.md")
    add("coordination/engineering/global-gap-candidate-refresh-20261009/README.md")
    for part in [2, 5, 23, 29]:
        add(f"data/geography/part-{part}.json")

    # Source generation lineage: complete selected component payloads and index.
    source_index_path = component_custody["source_index"]["path"]
    # The current baseline durably copies the exact original payload bytes;
    # pin those baseline copies while preserving source-generation commit IDs
    # in component-custody.json.
    add(source_index_path, BASE)
    subject_files = {}
    for payload in component_custody["component_payloads"]:
        d = add(payload["custody_payload_path"], BASE,
                (payload["uncompressed_bytes"], payload["uncompressed_sha256"]))
        for cid in payload["matched_candidate_ids"]:
            assert cid in ids and cid not in subject_files
            subject_files[cid] = {"commit": BASE, "path": payload["custody_payload_path"]}
    assert set(subject_files) == set(ids)

    # Retained full-resolution comparison inputs are identity lineage only.
    for row in comparison_custody["source_files"]:
        add(row["path"], row["commit"])
    fitness = comparison_custody["fitness_rows_pin"]
    add(fitness["path"], comparison_custody["baseline_commit"])
    add("coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/report.json")
    add("coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json")

    # Native GSHHG byte custody: entire retained record metadata and exact member aliases.
    gshhg_base = "coordination/engineering/gshhg-native-member-custody-20261007/"
    member_index = json.loads(git_show(BASE, gshhg_base + "results/member-index.json"))
    add("coordination/engineering/global-physical-sources-20261006/catalogue.json", BASE)
    add(gshhg_base + "results/member-index.json")
    add(gshhg_base + "results/members.json")
    add(gshhg_base + "results/downstream-reader.json")
    for row in member_index["records"]:
        add(gshhg_base + "results/" + row["path"], uncompressed=(row["uncompressed_bytes"], row["uncompressed_sha256"]))
    for row in member_index["parts"]:
        add(gshhg_base + "results/" + row["path"], uncompressed=(row["uncompressed_bytes"], row["uncompressed_sha256"]))

    pins = {
        "baseline_administrative_metadata": "ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633",
        "baseline_administrative_recipe": "d9df8285f1c270856a8e79b95636cf4b8d8496f48b30348a1e4d6d20619b2f22",
        "accepted_arctic_fit_rule": "27c1155b5c917e90324886d0a4d75a9b567de5e4f1bd370e21e5eebf08d003f6",
        "candidate_refresh_contract": "a34ab3987cb024e01f941eadbba2705ef67e8837aa3ba5d414408fb7f387d20b",
    }
    pin_files = {
        "baseline_administrative_metadata": "data/administrative-sources.json",
        "baseline_administrative_recipe": "scripts/administrative.py",
        "accepted_arctic_fit_rule": "research/geography/arctic-seven-source-fit-20261008/README.md",
        "candidate_refresh_contract": "coordination/engineering/global-gap-candidate-refresh-20261009/README.md",
    }

    outputs, source_products = [], []
    product_rows = {row["registry_key"].split(":")[1]: row for row in source_custody["products"]}
    product_filenames = {"AGO": "geoBoundaries-AGO-ADM2_simplified.geojson", "TCD": "geoBoundaries-TCD-ADM2_simplified.geojson",
                         "COG": "geoBoundaries-COG-ADM2_simplified.geojson", "CAF": "geoBoundaries-CAF-ADM3_simplified.geojson"}
    for country, filename in product_filenames.items():
        row = product_rows[country]
        path = f"research/geography/central-africa-20-source-fit-20261009/inputs/sources/{filename}"
        d = source_file(path)
        source_products.append({"id": row["registry_key"], "url": row["actual_consumed_product_url"],
                                "role": "Exact baseline-consumed simplified administrative reference product; source-relative fit only",
                                "vintage": f"geoBoundaries commit 9469f09; represented year {row['boundary_year_represented']}",
                                "retrieved_at": "Whole bytes reauthenticated and captured 2026-10-09; first retrieval time unknown",
                                "license": {"status": "redistributable", "terms": row["boundary_license"]},
                                "retention": "retained", "verification": "unverified", "temporal_status": "reference",
                                "files": [d],
                                "publication": {"encoding": "plain UTF-8 GeoJSON; identity byte decoding",
                                                "published_product_bytes": d["bytes"], "published_product_sha256": d["sha256"],
                                                "decoded_product_bytes": d["bytes"], "decoded_product_sha256": d["sha256"],
                                                "retained_candidate_path": path},
                                "limit": "Product authenticity and coverage do not establish legal/current authority, historical truth or physical land/water status."})

    source_output_paths = {s["files"][0]["path"] for s in source_products}
    for p in sorted(PACKET.rglob("*")):
        if not p.is_file() or p.name == "evidence-quality.json":
            continue
        rel = str(p.relative_to(ROOT))
        if rel in source_output_paths:
            continue
        outputs.append(source_file(rel))

    source_registry = [
        {"id": "gshhg-native-2.3.7", "url": "https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-bin-2.3.7.zip",
         "role": "Exact native-byte custody only; selected records are bbox candidates and are not geometric evidence",
         "vintage": "GSHHG 2.3.7, released 2017-06-15; heterogeneous observation dates",
         "retrieved_at": "Original immutable Git source capture reauthenticated 2026-10-09; first retrieval time unknown",
         "license": {"status": "unknown", "terms": "GSHHG redistribution terms were not adjudicated in this bounded assessment."},
         "retention": "restoration-only", "verification": "unverified", "temporal_status": "reference",
         "restoration": f"Restore original source records through {gshhg_base}results/member-index.json and the pinned native byte parts in baseline.files.",
         "limit": "The retained custody explicitly records geometry validity as not evaluated; bytes and bounding boxes establish no physical class."},
        {"id": "atlas-current-reference-map", "url": f"https://github.com/ChengshuLi/WorldAtlas/tree/{BASE}/data/geography",
         "role": "Exact current-map target and complete five-country neighbor input records",
         "vintage": f"Repository baseline {BASE}", "retrieved_at": "Immutable Git blobs authenticated 2026-10-09",
         "license": {"status": "unknown", "terms": "Mixed source rights remain as recorded in the baseline administrative registry; no new license conclusion."},
         "retention": "restoration-only", "verification": "verified", "temporal_status": "reference",
         "restoration": "Restore the four exact data/geography part blobs listed in baseline.files; packet copies are candidate outputs.",
         "limit": "Reference map input only; no source authority, legal status or publication approval is implied."},
        {"id": "retained-physical-gap-component-custody", "url": f"https://github.com/ChengshuLi/WorldAtlas/tree/{COMPONENT_COMMIT}/coordination/engineering/physical-gap-components-1005-20261005-local19",
         "role": "Original exact component identities/geometries and prior source-comparison lineage",
         "vintage": f"Immutable component custody commit {COMPONENT_COMMIT}",
         "retrieved_at": "Immutable Git blobs reauthenticated 2026-10-09",
         "license": {"status": "unknown", "terms": "Underlying source rights are heterogeneous; no generalized redistribution statement is made."},
         "retention": "restoration-only", "verification": "verified", "temporal_status": "reference",
         "restoration": "Restore the original component whole-file payloads and comparison files listed in baseline.files.",
         "limit": "Component and comparison records preserve identities and diagnostics; they do not certify factual land/water status."},
    ]
    methods = [{"id": "simplified-source-fit", "kind": "measurement",
                "description": "Exact Shapely/GEOS predicates and set operations on the actual baseline-consumed simplified geoBoundaries products and current country feature sets; candidate overlays limited to ten unique land-support IDs. GSHHG selection is a separate integer-bounds byte-custody filter only. No snapping, tolerance, buffering, repair, or normalization.",
                "software": "Python 3.12.14; Shapely 2.1.2; GEOS 3.13.1",
                "coordinate_order": "longitude-latitude as stored in source GeoJSON; no coordinate transformation",
                "overlay_area": "Exact planar GEOS in source coordinates; area is used only for exact zero/nonzero topology predicates, not as physical area",
                "distance_method": "Not used",
                "units": "square degrees for exact overlay predicates; integer microdegrees for GSHHG record bbox custody"}]
    metrics = [
        {"id": "fit-pass-count", "value": fit["fit_pass_count"], "unit": "components", "vintage": "baseline", "evaluation_commit": BASE,
         "input_sha256": sha((PACKET / "results/simplified-source-fit.json").read_bytes()),
         "input_file": {"path": "research/geography/central-africa-20-source-fit-20261009/results/simplified-source-fit.json", "commit": "candidate"}},
        {"id": "fit-refusal-count", "value": fit["fit_refusal_count"], "unit": "components", "vintage": "baseline", "evaluation_commit": BASE,
         "input_sha256": sha((PACKET / "results/simplified-source-fit.json").read_bytes()),
         "input_file": {"path": "research/geography/central-africa-20-source-fit-20261009/results/simplified-source-fit.json", "commit": "candidate"}},
        {"id": "unresolved-count", "value": fit["unknown_count"], "unit": "components", "vintage": "baseline", "evaluation_commit": BASE,
         "input_sha256": sha((PACKET / "results/simplified-source-fit.json").read_bytes()),
         "input_file": {"path": "research/geography/central-africa-20-source-fit-20261009/results/simplified-source-fit.json", "commit": "candidate"}},
    ]
    metrics[0]["value"] = fit["fit_pass_count"]
    summaries = [{"metric_id": m["id"], "value": m["value"], "unit": m["unit"]} for m in metrics]
    manifest_path = "research/geography/central-africa-20-source-fit-20261009/evidence-quality.json"
    manifest = {
        "version": 1, "issue": 1629, "lane": "geography", "worker_id": WORKER,
        "subject_ids": ids, "subject_ids_sha256": sha(json.dumps(ids, separators=(",", ":")).encode()),
        "baseline": {"version": 2, "commit": BASE, "files": sorted(baseline.values(), key=lambda f: (f["commit"], f["path"])),
                     "pins": pins, "pin_files": pin_files, "subject_files": subject_files},
        "sources": source_products + source_registry,
        "outputs": outputs,
        "methods": methods,
        "metrics": metrics,
        "metric_bindings": [
            {"metric_id": "fit-pass-count", "path": "research/geography/central-africa-20-source-fit-20261009/results/simplified-source-fit.json", "json_pointer": "/fit_pass_count"},
            {"metric_id": "fit-refusal-count", "path": "research/geography/central-africa-20-source-fit-20261009/results/simplified-source-fit.json", "json_pointer": "/fit_refusal_count"},
            {"metric_id": "unresolved-count", "path": "research/geography/central-africa-20-source-fit-20261009/results/simplified-source-fit.json", "json_pointer": "/unknown_count"},
        ],
        "summaries": summaries,
        "conclusions": [
            {"status": "supported", "text": "Nine exact COG components pass the narrow source-relative additive fit and exact current-neighbor predicates against the baseline-consumed simplified product; their geometries remain proposals only.",
             "source_ids": ["gb:COG:ADM2", "atlas-current-reference-map", "retained-physical-gap-component-custody"]},
            {"status": "unresolved", "text": "Eleven candidates remain unresolved: one unique water-support exception, seven mixed/partial coverage cases, two contact-only cases, and one CAF sliver whose union gain is not exactly the candidate. Physical class, cause, current water/ice, legal authority, and publication status remain unknown.",
             "source_ids": ["gb:COG:ADM2", "gb:CAF:ADM3", "gb:AGO:ADM2", "gb:TCD:ADM2", "gshhg-native-2.3.7", "atlas-current-reference-map", "retained-physical-gap-component-custody"]},
        ],
        "stages": {"research": "complete", "implementation": "proposed", "geographic_approval": "unapproved"},
        "validation": [
            {"method_id": "simplified-source-fit", "kind": "positive-control", "outcome": "passed", "evidence_path": "research/geography/central-africa-20-source-fit-20261009/controls/positive-control.json"},
            {"method_id": "simplified-source-fit", "kind": "negative-control", "outcome": "passed", "evidence_path": "research/geography/central-africa-20-source-fit-20261009/controls/negative-control.json"},
        ],
        "commands": [
            "python3 research/geography/central-africa-20-source-fit-20261009/pin_gshhg_records.py",
            "python3 research/geography/central-africa-20-source-fit-20261009/fit_simplified_sources.py",
            "python3 research/geography/central-africa-20-source-fit-20261009/run_controls.py",
            "python3 research/geography/central-africa-20-source-fit-20261009/assemble_proposals.py",
        ],
    }
    # Change receipts cover every tracked addition in this packet plus the manifest itself.
    receipts = []
    for p in sorted(PACKET.rglob("*")):
        if p.is_file() and p.name != "evidence-quality.json":
            receipts.append({"path": str(p.relative_to(ROOT)), "status": "added", "previous_path": None})
    receipts.append({"path": manifest_path, "status": "added", "previous_path": None})
    manifest["change_receipts"] = receipts
    dest = PACKET / "evidence-quality.json"
    raw = json.dumps(manifest, indent=2, ensure_ascii=False).encode() + b"\n"
    dest.write_bytes(raw)
    print(json.dumps({"manifest": str(dest), "sha256": sha(raw), "baseline_files": len(manifest["baseline"]["files"]),
                      "baseline_bytes": sum(f["bytes"] for f in manifest["baseline"]["files"]),
                      "outputs": len(outputs), "output_bytes": sum(f["bytes"] for f in outputs),
                      "sources": len(source_products) + len(source_registry), "subject_files": len(subject_files),
                      "pins": pins, "pin_files": pin_files}, indent=2))


if __name__ == "__main__":
    main()
