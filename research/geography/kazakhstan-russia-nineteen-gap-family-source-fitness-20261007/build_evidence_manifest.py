#!/usr/bin/env python3
"""Build the issue-scoped evidence receipt from the frozen packet bytes."""

import gzip
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
PREFIX = ROOT.relative_to(REPO).as_posix()
BASE = "cbae22cc877f6f8a70650069d91d2b34240582f7"
MANIFEST = ROOT / "evidence-quality.json"
WORKER = "01a112c2-1d0f-7bf2-a50e-74956219b9c1"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def descriptor(path: Path, *, role=None) -> dict:
    raw = path.read_bytes()
    result = {"path": f"{PREFIX}/{path.relative_to(ROOT).as_posix()}", "bytes": len(raw),
              "sha256": sha(raw), "hash_kind": "file-bytes"}
    if path.suffix == ".gz":
        decoded = gzip.decompress(raw)
        result.update(uncompressed_bytes=len(decoded), uncompressed_sha256=sha(decoded))
    if role:
        result["role"] = role
    return result


def baseline_file(path: str) -> dict:
    raw = subprocess.check_output(["git", "-C", str(REPO), "show", f"{BASE}:{path}"])
    return {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}


def main() -> None:
    source_rel = [
        "inputs/geoboundaries-kaz-adm2-2017-full-source.geojson",
        "inputs/geoboundaries-kaz-adm2-2017-simplified-full-source.geojson",
        "inputs/geoboundaries-rus-adm2-2017-simplified-full-source.geojson",
        "inputs/metadata/KAZ-geoBoundaries-KAZ-ADM2-metaData.json",
        "inputs/metadata/RUS-geoBoundaries-RUS-ADM2-metaData.json",
        "inputs/metadata/KAZ-CITATION-AND-USE-geoBoundaries.txt",
        "inputs/metadata/RUS-CITATION-AND-USE-geoBoundaries.txt",
        "inputs/metadata/unsimplified-source-retrieval.json",
    ]
    source_paths = {f"{PREFIX}/{name}" for name in source_rel}
    source_files = [descriptor(ROOT / name, role="original-source") for name in source_rel]
    output_files = []
    for path in sorted(p for p in ROOT.rglob("*") if p.is_file() and p != MANIFEST):
        repo_path = f"{PREFIX}/{path.relative_to(ROOT).as_posix()}"
        if repo_path not in source_paths:
            output_files.append(descriptor(path, role="original-source" if "/inputs/" in repo_path else None))

    baseline_paths = [
        "data/world-index.json",
        "data/geography/part-12.json",
        "data/geography/part-20.json",
        "data/geography/part-21.json",
        "coordination/engineering/global-actionability-routing-20261007/results/report.json",
        "coordination/engineering/global-actionability-routing-20261007/input-config.json",
    ]
    base_files = [baseline_file(path) for path in baseline_paths]
    pin_files = {
        "audited_world_index": "data/world-index.json",
        "delivered_routing_report": "coordination/engineering/global-actionability-routing-20261007/results/report.json",
        "delivered_routing_input_config": "coordination/engineering/global-actionability-routing-20261007/input-config.json",
        "scoped_part_12": "data/geography/part-12.json",
        "scoped_part_20": "data/geography/part-20.json",
        "scoped_part_21": "data/geography/part-21.json",
    }
    pins = {key: next(f["sha256"] for f in base_files if f["path"] == path)
            for key, path in pin_files.items()}
    contacts = json.loads((ROOT / "executions/run-1/contact-lineage.json").read_text())
    subject_files = {row["id"]: row["source_path"] for row in contacts["contacts"]}
    subject_ids = sorted(subject_files)
    subject_hash = sha(json.dumps(subject_ids, ensure_ascii=False, separators=(",", ":")).encode())

    family_path = f"{PREFIX}/executions/run-1/family-reconciliation.json"
    contact_path = f"{PREFIX}/executions/run-1/contact-lineage.json"
    products_path = f"{PREFIX}/executions/run-1/source-products.json"
    family_sha = descriptor(ROOT / "executions/run-1/family-reconciliation.json")["sha256"]
    contact_sha = descriptor(ROOT / "executions/run-1/contact-lineage.json")["sha256"]
    products_sha = descriptor(ROOT / "executions/run-1/source-products.json")["sha256"]
    metrics = [
        {"id": "complete-family-count", "value": 19, "unit": "families", "vintage": "baseline", "evaluation_commit": BASE, "input_sha256": family_sha},
        {"id": "complete-component-count", "value": 52, "unit": "components", "vintage": "baseline", "evaluation_commit": BASE, "input_sha256": family_sha},
        {"id": "numeric-first-family-count", "value": 0, "unit": "families", "vintage": "baseline", "evaluation_commit": BASE, "input_sha256": family_sha},
        {"id": "complete-contact-count", "value": 41, "unit": "Atlas contacts", "vintage": "baseline", "evaluation_commit": BASE, "input_sha256": contact_sha},
        {"id": "kazakhstan-simplified-source-feature-count", "value": 174, "unit": "source features", "vintage": "baseline", "evaluation_commit": BASE, "input_sha256": products_sha},
        {"id": "russia-simplified-source-feature-count", "value": 2327, "unit": "source features", "vintage": "baseline", "evaluation_commit": BASE, "input_sha256": products_sha},
        {"id": "russia-advertised-source-feature-count", "value": 2328, "unit": "source features", "vintage": "baseline", "evaluation_commit": BASE, "input_sha256": products_sha},
    ]
    bindings = [
        {"metric_id": "complete-family-count", "path": family_path, "json_pointer": "/family_count"},
        {"metric_id": "complete-component-count", "path": family_path, "json_pointer": "/component_count"},
        {"metric_id": "numeric-first-family-count", "path": family_path, "json_pointer": "/numeric_first_family_count"},
        {"metric_id": "complete-contact-count", "path": contact_path, "json_pointer": "/contact_count"},
        {"metric_id": "kazakhstan-simplified-source-feature-count", "path": products_path, "json_pointer": "/sources/gb:KAZ:ADM2/feature_count"},
        {"metric_id": "russia-simplified-source-feature-count", "path": products_path, "json_pointer": "/sources/gb:RUS:ADM2/feature_count"},
        {"metric_id": "russia-advertised-source-feature-count", "path": products_path, "json_pointer": "/sources/gb:RUS:ADM2/advertised_feature_count"},
    ]
    summaries = [{"metric_id": m["id"], "value": m["value"], "unit": m["unit"]} for m in metrics]
    changed_paths = sorted(p for p in ROOT.rglob("*") if p.is_file())
    change_receipts = [{"path": f"{PREFIX}/{p.relative_to(ROOT).as_posix()}", "status": "added"}
                       for p in changed_paths]
    manifest = {
        "version": 1,
        "issue": 1322,
        "lane": "geography",
        "worker_id": WORKER,
        "subject_ids": subject_ids,
        "subject_ids_sha256": subject_hash,
        "baseline": {"commit": BASE, "files": base_files, "pins": pins, "pin_files": pin_files,
                     "subject_files": subject_files},
        "sources": [
            {"id": "assigned-routing-assessment", "url": "https://github.com/ChengshuLi/WorldAtlas/tree/cbae22cc877f6f8a70650069d91d2b34240582f7/coordination/engineering/global-actionability-routing-20261007",
             "role": "Immutable route scope, family/component cohort and original source-fitness observations; not boundary authority",
             "vintage": "Pinned route report and input configuration in baseline commit cbae22cc877f6f8a70650069d91d2b34240582f7",
             "retrieved_at": "2026-10-07", "license": {"status": "unknown", "terms": "Internal repository evidence; no standalone licensing determination is made here."},
             "retention": "restoration-only", "verification": "verified", "temporal_status": "unknown",
             "restoration": "Restore coordination/engineering/global-actionability-routing-20261007/results/report.json and input-config.json from the exact pinned baseline commit; the packet also preserves complete assigned source bodies in inputs/routing/.",
             "limit": "Defines the assigned analysis cohort and inherited observations only; it does not establish legal boundary ownership or physical truth."},
            {"id": "geoboundaries-2017-adm2", "url": "https://github.com/wmgeolab/geoBoundaries/tree/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen",
             "role": "2017 single-country ADM2 source products used in original comparison; full and simplified identity lineage assessed",
             "vintage": "Represented year 2017; release commit 9469f09592ced973a3448cf66b6100b741b64c0d; metadata build date 2023-12-12",
             "retrieved_at": "2026-10-07", "license": {"status": "redistributable", "terms": "geoBoundaries gbOpen states CC-BY 4.0 with attribution; country metadata records underlying ODbL 1.0 source. Attribution/citation files are retained. No independent legal opinion."},
             "retention": "retained", "verification": "verified", "temporal_status": "unknown",
             "files": source_files, "limit": "Represented year and recorded source metadata do not establish effective date, completeness, legal authority, current applicability, or positional equivalence between full and simplified geometries."},
            {"id": "geoboundaries-rus-full-resolution", "url": "https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/RUS/ADM2/geoBoundaries-RUS-ADM2.geojson",
             "role": "Pinned full-resolution RUS ADM2 product used only for identity-set comparison",
             "vintage": "2017 represented source; geoBoundaries release commit 9469f09592ced973a3448cf66b6100b741b64c0d",
             "retrieved_at": "2026-10-07", "license": {"status": "redistributable", "terms": "geoBoundaries gbOpen CC-BY 4.0 attribution; metadata records underlying ODbL 1.0; the full file is restoration-only in this packet due to its size."},
             "retention": "restoration-only", "verification": "verified", "temporal_status": "unknown",
             "restoration": "Retrieve the exact URL above; verify 120489189 bytes and SHA-256 74012237384e53061aa63b6e20b9be24f94facfe615b52bbe72e62a81fa68ff0; run compare_source_ids.py with --rus-full set to that file.",
             "limit": "Full source is larger than 32 MiB and is retained only at the local restoration cache; its identities were compared, but its geometries were not compared to simplified geometry."},
            {"id": "gshhg-2.3.7-physical-comparison", "url": "https://www.ngdc.noaa.gov/mgg/shorelines/shorelines.html",
             "role": "Historical shoreline, lake and river support context from retained physical comparison outputs",
             "vintage": "GSHHG 2.3.7 release 2017-06-15; source observation dates heterogeneous",
             "retrieved_at": "2026-10-06", "license": {"status": "unknown", "terms": "The source archive's applicable reuse terms were not independently confirmed in this assessment; verify before reuse."},
             "retention": "restoration-only", "verification": "unverified", "temporal_status": "unknown",
             "restoration": "See inputs/physical/report.json for the producer, release and restoration context; retrieve the exact archived release and verify its terms and hashes before reproducing.",
             "limit": "Underlying GSHHG source archive is not included in the packet; only prior comparison records and their complete receipts are retained. Its mapped support does not prove physical land or current water status."},
            {"id": "kazakhstan-admin-territorial-law-2026", "url": "https://adilet.zan.kz/rus/docs/Z2600000300",
             "role": "Primary legal process reference for administrative-territorial establishment/change procedure in Kazakhstan",
             "vintage": "Constitutional Law adopted 2026-06-05; effective 2026-07-01",
             "retrieved_at": "2026-10-07", "license": {"status": "unknown", "terms": "Official legal text; reproduction and reuse terms not independently assessed."},
             "retention": "restoration-only", "verification": "verified", "temporal_status": "reference",
             "restoration": "Consult the official Adilet law URL above, particularly Article 20 and the current amended text.",
             "limit": "Describes procedure and required map documentation; does not authenticate the 2017 geoBoundaries product or resolve any candidate component."},
            {"id": "rosreestr-map-display-order-2021", "url": "https://publication.pravo.gov.ru/document/0001202112300112",
             "role": "Official Rosreestr requirements for displaying national, subject and municipal territories on map materials",
             "vintage": "Order P/0559 dated 2021-12-01; published 2021-12-30",
             "retrieved_at": "2026-10-07", "license": {"status": "unknown", "terms": "Official legal text; reproduction and reuse terms not independently assessed."},
             "retention": "restoration-only", "verification": "verified", "temporal_status": "unknown",
             "restoration": "Consult official publication ID 0001202112300112 at the official publication portal URL above.",
             "limit": "Map-display requirements only; not a boundary dataset, boundary registration or proof of candidate boundary position."},
        ],
        "outputs": output_files,
        "change_receipts": change_receipts,
        "metric_bindings": bindings,
        "methods": [
            {"id": "assessment-producer", "kind": "code", "description": "Validate pinned ordered source bodies, exact 19-family/52-component closure, source fitness records, all 41 contact features, and complete physical run/source restoration rows; emit deterministic assessment outputs.", "software": "Python 3.12.14; standard library; producer bytes pinned by source-freeze.json", "units": "whole records, features, families, components and Atlas contacts"},
            {"id": "source-id-comparison", "kind": "source", "description": "Parse pinned full and simplified GeoJSONs, compare unique shapeID sets, and hash sorted IDs; no geometry comparison.", "software": "Python 3.12.14; standard library; compare_source_ids.py", "units": "feature IDs"},
            {"id": "assessment-controls", "kind": "code", "description": "Check positive roster closure and deliberate negative controls for omission, duplication, family rebinding and source identity drift; compare the two retained complete producer run receipts.", "software": "Python 3.12.14; standard library; assessment_controls.py", "units": "record counts, identity sets and SHA-256"},
        ],
        "metrics": metrics,
        "summaries": summaries,
        "conclusions": [
            {"text": "The retained assessment contains the exact assigned 19-family, 52-component and 41-contact cohort with zero numeric-first families.", "status": "supported", "source_ids": ["assigned-routing-assessment"]},
            {"text": "The pinned KAZ and RUS full and simplified products have matching unique shapeID sets; this does not show geometry equivalence.", "status": "supported", "source_ids": ["geoboundaries-2017-adm2", "geoboundaries-rus-full-resolution"]},
            {"text": "RUS metadata advertises one more feature than exists in either pinned product; whether this is stale metadata or a missing feature is unresolved.", "status": "unresolved", "source_ids": ["geoboundaries-2017-adm2", "geoboundaries-rus-full-resolution"]},
            {"text": "Current legal authority, effective applicability and physical land/water truth remain unresolved for all candidate components.", "status": "unresolved", "source_ids": ["geoboundaries-2017-adm2", "gshhg-2.3.7-physical-comparison", "kazakhstan-admin-territorial-law-2026", "rosreestr-map-display-order-2021"]},
        ],
        "stages": {"research": "complete", "implementation": "not-proposed", "geographic_approval": "unapproved"},
        "commands": [
            "python3.12 build_assessment.py --out executions/run-1 (completed 2026-10-07T07:12:45Z; exit 0)",
            "python3.12 build_assessment.py --out executions/run-2 (completed 2026-10-07T07:16:34Z; exit 0)",
            "python3.12 compare_source_ids.py --packet <packet> --rus-full <restoration-cache>/geoBoundaries-RUS-ADM2.geojson --out executions/source-id-comparison.json (exit 0)",
            "python3.12 assessment_controls.py (exit 0)",
        ],
        "validation": [
            {"method_id": "assessment-producer", "kind": "positive-control", "outcome": "passed", "evidence_path": f"{PREFIX}/executions/positive-control.json"},
            {"method_id": "assessment-producer", "kind": "negative-control", "outcome": "passed", "evidence_path": f"{PREFIX}/executions/negative-control.json"},
            {"method_id": "assessment-producer", "kind": "reproducibility", "outcome": "passed", "evidence_path": f"{PREFIX}/executions/reproducibility-control.json"},
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"outputs": len(output_files), "source_files": len(source_files), "baseline_files": len(base_files),
                      "changed_files": len(change_receipts), "subject_ids": len(subject_ids), "metrics": len(metrics)}, sort_keys=True))


if __name__ == "__main__":
    main()
