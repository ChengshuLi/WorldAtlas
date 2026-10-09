#!/usr/bin/env python3
"""Join every scoped contact to its Atlas feature, parents, and families."""
import hashlib
import json
from pathlib import Path

OWN = Path(__file__).resolve().parent
ROOT = OWN.parents[2]
OLD = ROOT / "research/geography/portugal-spain-gap-source-families-20261007"
DATA = [ROOT / f"data/geography/part-{n}.json" for n in (8, 19, 20, 28, 29)]
MATRIX = OLD / "outputs/source-status-matrix.json"
GEOM = OLD / "inputs/selected-70-component-geometries.geojson"
OUT = OWN / "subject-lineage.json"
MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def roster_sha(values):
    return hashlib.sha256(("\n".join(sorted(values)) + "\n").encode()).hexdigest()

def main():
    assert not OUT.exists() and not OUT.is_symlink(), "refuse overwrite"
    files = [*DATA, MATRIX, GEOM]
    assert all(p.stat().st_size <= MAX_FILE for p in files), "per-file budget failed"
    code_bytes = Path(__file__).stat().st_size
    projected = sum(p.stat().st_size for p in files) + code_bytes + 256 * 1024
    assert projected <= MAX_TOTAL, "complete subject-lineage phase exceeds 256 MiB"
    matrix = json.loads(MATRIX.read_text())
    features = {}
    for p in DATA:
        for f in json.loads(p.read_text()).get("features", []):
            sid = f.get("id") or f.get("properties", {}).get("id")
            if sid:
                features[sid] = (p, f)
    families = matrix["families"]
    components = matrix["components"]
    subject_ids = sorted({sid for c in components for sid in c["contact_ids"]})
    family_map = {sid: set() for sid in subject_ids}
    component_map = {sid: set() for sid in subject_ids}
    neighbors = {sid: set() for sid in subject_ids}
    family_rows = []
    for fam in families:
        for sid in fam["contact_ids"]:
            family_map[sid].add(fam["family_id"])
            neighbors[sid].update(set(fam.get("edge_neighbor_ids", [])) - {sid})
            for cid in fam["component_ids"]:
                component_map[sid].add(cid)
        family_rows.append({"family_id": fam["family_id"], "components": fam["component_ids"],
                            "contacts": fam["contact_ids"], "edge_neighbors": fam.get("edge_neighbor_ids", []),
                            "country_product_context": fam.get("other_source_status"),
                            "known_limits": fam.get("limits", [])})
    rows = []
    for sid in subject_ids:
        assert sid in features, f"scope subject has no exact Atlas feature: {sid}"
        p, f = features[sid]
        props = f.get("properties", {})
        meta = props.get("metadata", {})
        rows.append({"subject_id": sid, "name": props.get("name"), "reference_owner": props.get("reference_owner"),
                     "parent_id": props.get("parent_id"), "subject_container": str(p.relative_to(ROOT)),
                     "source": {"source_id": meta.get("source_id"), "source_name": meta.get("source_name"),
                                "source_url": meta.get("source_url"), "license": meta.get("license"),
                                "reference_year": meta.get("reference_year"), "administrative_level": meta.get("administrative_level"),
                                "parent_source_level": meta.get("parent_source_level"), "source_role": meta.get("source_role"),
                                "selection_reason": meta.get("selection_reason"), "parent_match": meta.get("parent_match")},
                     "families": sorted(family_map[sid]), "components": sorted(component_map[sid]),
                     "edge_neighbors_in_scope": sorted(neighbors[sid]),
                     "territorial_interpretation": "Atlas source contact and its recorded framework parent. Parent/source lineage is inherited catalog context; it does not establish rightful ownership of the contacted physical component or a boundary finding."})
    assert len(rows) == 57 and len(families) == 52 and len(components) == 70
    geom = json.loads(GEOM.read_text())
    assert len(geom["features"]) == 70
    OUT.write_text(json.dumps({"schema": "worldatlas-scoped-subject-lineage-v1", "issue": 1458,
                               "method": "Exact issue contact identifiers joined to immutable Atlas data-part features by native id; component and family memberships come from the retained source-status matrix.",
                               "admission": {"max_file_bytes": MAX_FILE, "max_phase_bytes": MAX_TOTAL,
                                             "input_bytes": projected - 256 * 1024, "output_reserve": 256 * 1024,
                                             "status": "admitted"},
                               "inputs": [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p)} for p in files],
                               "scope": {"subjects": len(rows), "families": len(families), "components": len(components),
                                         "subject_roster_sha256": hashlib.sha256(json.dumps(subject_ids, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest(),
                                         "component_roster_sha256": matrix["scope"]["component_roster_sha256"],
                                         "family_roster_sha256": matrix["scope"]["family_roster_sha256"]},
                               "subjects": rows, "families": family_rows,
                               "limits": ["Atlas parent IDs and source administrative levels are recorded source context, not an adjudication of border entitlement.",
                                          "Spain contacts are agricultural comarcas (MAPA), whose boundaries/license/history remain unresolved; geoBoundaries Spain ADM3 municipalities and Portugal ADM2 municipalities are adjacent source granularity, not substitute physical boundaries.",
                                          "The Portugal and Spain geoBoundaries products have respective recorded vintages 2020 and 2018. Their source-year values do not prove effective dates for any physical component.",
                                          "Prior MAPA/APA findings are retained separately; historical MAPA bytes, current MAPA geometry terms, APA reuse license and MITECO vectors remain unresolved."]}, indent=2, sort_keys=True) + "\n")
    assert OUT.stat().st_size <= 256 * 1024
    assert projected - 256 * 1024 + OUT.stat().st_size <= MAX_TOTAL
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, sha256 {sha(OUT)}); subjects={len(rows)}")

if __name__ == "__main__":
    main()
