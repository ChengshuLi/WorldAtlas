#!/usr/bin/env python3
"""Rebuild the Guangdong/Guangxi roster crosswalk from the pinned PR1 row inventory."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path("data/regional-review/regional-review-173ccc74c2fd93ae")
ASSESSMENT = ROOT / "row-assessments.json"
SCOPE = ROOT / "scope.json"
GB_PATH = Path("data/regional-review/regional-review-365cbd6478904888/source/geoBoundaries-CHN-ADM2.geojson")
GB_SHA256 = "2b68d8a808742fc6d7acd769584db960d8fc2c25b9f1d20e3e98c72e9f1c4d34"
rows_all = json.loads(ASSESSMENT.read_text())["rows"]
rows = [r for r in rows_all if r["area_name"] in ("Guangdong", "Guangxi") and r.get("source_shape_name")]
assert len(rows) == 180
assert sum(r["area_name"] == "Guangdong" for r in rows) == 92
assert sum(r["area_name"] == "Guangxi" for r in rows) == 88

# Recheck the declared issue roster, digest, and exact source-shape joins rather
# than treating PR1's row inventory alone as a reproduction of its own claims.
scope = json.loads(SCOPE.read_text())
ordered = scope["workload"]["member_location_ids"]
assert len(ordered) == 200 and len(set(ordered)) == 200
assert hashlib.sha256(json.dumps(ordered, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest() == scope["member_location_ids_sha256"]
expected_order = [r["id"] for r in rows_all if r["area_name"] in ("Guangdong", "Guangxi") and r.get("source_shape_name")]
assert [i for i in ordered if i in set(expected_order)] == expected_order
gb_bytes = GB_PATH.read_bytes()
assert hashlib.sha256(gb_bytes).hexdigest() == GB_SHA256
gb = json.loads(gb_bytes)
source_by_shape = {}
for feature in gb["features"]:
    shape_id = feature.get("properties", {}).get("shapeID")
    if shape_id:
        assert shape_id not in source_by_shape
        source_by_shape[shape_id] = feature
for row in rows:
    feature = source_by_shape.get(row["source_shape_id"])
    assert feature is not None, f"missing source shapeID {row['source_shape_id']}"
    assert feature["properties"].get("shapeName") == row["source_shape_name"]
assert len({r["source_shape_id"] for r in rows}) == len(rows)

# Same-toponym current names/statuses visible in the 2025 Guangdong government
# table or the 2025 Guangxi government roster. Candidate only: no code or
# official boundary crosswalk is present in the 2017 source.
known = {
    "Panyushi": ("Guangdong", "番禺市", "Panyu District"),
    "Zengchengshi": ("Guangdong", "增城市", "Zengcheng District"),
    "Chonghuashi": ("Guangdong", "从化市", "Conghua District"),
    "Huadushi": ("Guangdong", "花都市", "Huadu District"),
    "Nanhaishi": ("Guangdong", "南海市", "Nanhai District"),
    "Shundeshi": ("Guangdong", "顺德市", "Shunde District"),
    "Gaomingshi": ("Guangdong", "高明市", "Gaoming District"),
    "Chenghaishi": ("Guangdong", "澄海市", "Chenghai District"),
    "Chaoyangxian": ("Guangdong", "潮阳县", "Chaoyang District"),
    "Qujiangxian": ("Guangdong", "曲江县", "Qujiang District"),
    "Huiyangshi": ("Guangdong", "惠阳市", "Huiyang District"),
    "Dianbaxian": ("Guangdong", "电白县", "Dianbai District"),
    "Xinhuishi": ("Guangdong", "新会市", "Xinhui District"),
    "Gaoyaoshi": ("Guangdong", "高要市", "Gaoyao District"),
    "Pingguoxian": ("Guangxi", "平果县", "Pingguo City"),
    "Tianyangxian": ("Guangxi", "田阳县", "Tianyang District"),
    "Jingxixian": ("Guangxi", "靖西县", "Jingxi City"),
    "Hengxian": ("Guangxi", "横县", "Hengzhou City"),
    "Wumingxian": ("Guangxi", "武鸣县", "Wuming District"),
    "Yongningxian": ("Guangxi", "邕宁县", "Yongning District"),
    "Linguixian": ("Guangxi", "临桂县", "Lingui District"),
    "Lipuxian": ("Guangxi", "荔浦县", "Lipu City"),
    "Liujiangxian": ("Guangxi", "柳江县", "Liujiang District"),
    "Yizhoushi": ("Guangxi", "宜州市", "Yizhou District"),
}
longan = "gb:CHN:ADM2:17275852B2033650787942"
zhaoping_wuzhou = "gb:CHN:ADM2:17275852B79176055066883"
fields = [
    "location_id", "area", "source_shape_id", "source_shape_name_2017",
    "current_atlas_parent_id", "current_atlas_parent_name", "prior_row_classification",
    "crosswalk_status", "candidate_current_name", "candidate_current_name_zh", "finding",
]
out_path = ROOT / "findings/pr2-current-roster-crosswalk.csv"
out_path.parent.mkdir(parents=True, exist_ok=True)
with out_path.open("w", newline="") as out:
    writer = csv.DictWriter(out, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in sorted(rows, key=lambda r: (r["area_name"], r["id"])):
        name = row["source_shape_name"]
        status = "unresolved-no-current-code-or-official-boundary-join"
        english = chinese = finding = ""
        if name in known and known[name][0] == row["area_name"]:
            _, chinese, english = known[name]
            status = "candidate-name-or-tier-change-needs-code-and-geometry-check"
            finding = "Same-toponym name/status lead in the 2025 official roster; one-to-one identity and geometry remain unverified."
        if row["id"] == longan:
            status = "candidate-current-parent-conflict-needs-code-and-geometry-check"
            english, chinese = "Nanning (current official roster)", "南宁市"
            finding = "Longanxian is grouped under current Atlas parent Chongzuo; the official 2025 roster lists 隆安县 under 南宁市 and not 崇左市."
        if row["id"] == zhaoping_wuzhou:
            status = "duplicate-name-current-roster-conflict-needs-source-identity-check"
            english, chinese = "unresolved", "昭平县 (official roster: Hezhou only)"
            finding = "A second distinct retained shape named Zhaopingxian is grouped under Wuzhou; the official 2025 roster lists 昭平县 under 贺州市 and no Zhaoping unit under 梧州市. Do not infer which polygon is current Zhaoping without code/boundary evidence."
        writer.writerow({
            "location_id": row["id"], "area": row["area_name"],
            "source_shape_id": row["source_shape_id"], "source_shape_name_2017": name,
            "current_atlas_parent_id": row["current_main_parent_id"],
            "current_atlas_parent_name": row["current_main_parent_name"],
            "prior_row_classification": row["classification"], "crosswalk_status": status,
            "candidate_current_name": english, "candidate_current_name_zh": chinese,
            "finding": finding,
        })

prefecture_cities = {
    "Guangdong": set("Guangzhou Shenzhen Zhuhai Shantou Foshan Shaoguan Heyuan Meizhou Huizhou Shanwei Dongguan Zhongshan Jiangmen Yangjiang Zhanjiang Maoming Zhaoqing Qingyuan Chaozhou Jieyang Yunfu".split()),
    "Guangxi": set("Nanning Liuzhou Guilin Wuzhou Beihai Fangchenggang Qinzhou Guigang Yulin Baise Hezhou Hechi Laibin Chongzuo".split()),
}
city_rows = []
for row in rows:
    name = row["source_shape_name"] or ""
    stem = name[:-3] if name.lower().endswith("shi") else name
    if any(stem.lower() == city.lower() for city in prefecture_cities[row["area_name"]]):
        city_rows.append({
            "id": row["id"], "area": row["area_name"], "source_name": name,
            "atlas_parent": row["current_main_parent_name"],
            "source_role": "2017 geoBoundaries metadata: County Level (ADM2)",
            "finding": "Name matches a present-day prefecture-level city while retained source metadata declares County Level. Semantic review lead only; no official source code or current boundary join.",
        })
findings = ROOT / "findings"
(findings / "pr2-source-role-review.json").write_text(json.dumps({
    "version": 1, "issue": 408, "scope_source_rows": 180,
    "source_role": "2017 geoBoundaries CHN ADM2 metadata declares County Level",
    "prefecture_name_rows": city_rows,
    "limits": [
        "Name matches identify review leads only; the retained source has no official current code or canonical parent.",
        "No candidate city geometry was adjudicated as a present-day boundary.",
    ],
}, ensure_ascii=False, indent=2) + "\n")
candidate_ids = [
    row["id"] for row in rows
    if (row["source_shape_name"] in known and known[row["source_shape_name"]][0] == row["area_name"])
    or row["id"] in (longan, zhaoping_wuzhou)
]
(findings / "pr2-candidate-ids.json").write_text(json.dumps({
    "version": 1, "issue": 408, "research_date_utc": "2026-10-06",
    "candidate_ids": candidate_ids, "candidate_count": len(candidate_ids),
    "interpretation": "Sourced current-name/tier/parent leads for follow-up only; no one-to-one boundary identity is certified.",
}, indent=2) + "\n")
print(f"rows={len(rows)} Guangdong={sum(r['area_name']=='Guangdong' for r in rows)} Guangxi={sum(r['area_name']=='Guangxi' for r in rows)} candidates={len(candidate_ids)} prefecture_name_rows={len(city_rows)}")

outputs = [
    ROOT / "findings/pr2-current-roster-crosswalk.csv",
    findings / "pr2-source-role-review.json",
    findings / "pr2-candidate-ids.json",
]
result = {
    "version": 1,
    "issue": 408,
    "baseline_commit": scope["baseline_commit"],
    "scope_member_location_ids_sha256": scope["member_location_ids_sha256"],
    "source": {"path": str(GB_PATH), "bytes": len(gb_bytes), "sha256": GB_SHA256,
               "join_key": "properties.shapeID", "matched_unique_rows": len(rows)},
    "counts": {"scope_members": 200, "guangdong_source_rows": 92, "guangxi_source_rows": 88,
               "crosswalk_rows": len(rows), "candidate_ids": len(candidate_ids),
               "prefecture_name_role_leads": len(city_rows)},
    "outputs": [{"path": str(p), "bytes": p.stat().st_size,
                 "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in outputs],
    "limits": ["Reproduction proves roster and source identity joins only; it does not prove current administrative codes, boundaries, completeness, legal meaning, or license."]
}
(findings / "pr2-reproduction-results.json").write_text(json.dumps(result, indent=2) + "\n")
