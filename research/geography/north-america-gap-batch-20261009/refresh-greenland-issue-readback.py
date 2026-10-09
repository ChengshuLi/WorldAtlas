#!/usr/bin/env python3
"""Capture a live GitHub issue/claim overlap readback for the five GEO5 IDs."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


DIR = Path(__file__).resolve().parent
OUTPUT = DIR / "greenland-five-live-issue-readback.json"
ISSUES = [1202, 1630, 1394, 457, 888, 1377, 1362, 1488, 1508, 1620]
COMPONENTS = {
    "physical-component:0441b8d2c49152a8ad4e5c8a0426eba450eb7298957b46eceadcac5c59c904ad",
    "physical-component:074e4f2fbdd5d53d94cd654c9737406325cfc851b36abb17940b3609187a2cc2",
    "physical-component:26f7658cfe2bed03c9cca108e8c2d08277f9efdd0a8143c308a7d6d0357662ee",
    "physical-component:f840c42d9967e89c74e47e4693392c474df5bfd4014d7c04acee9d04f58ed2f5",
    "physical-component:ff63cb9b104fd5baada0f18a8426c9d0e11ddb99ceed1392c7f6f715e4b27064",
}
COMPONENT_RE = re.compile(r"physical-component:[a-f0-9]{64}")
CLAIM_RE = re.compile(r"<!-- worldatlas-claim:v1\s*(\{.*?\})\s*-->", re.S)


def main() -> None:
    captured_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    result = []
    for number in ISSUES:
        raw = subprocess.check_output([
            "gh", "issue", "view", str(number), "--repo", "ChengshuLi/WorldAtlas",
            "--json", "number,title,state,updatedAt,labels,assignees,body,comments",
        ])
        issue = json.loads(raw)
        comments = issue.get("comments", [])
        texts = [issue.get("body", "")] + [comment.get("body", "") for comment in comments]
        full_text = "\n".join(texts)
        all_roster_ids = sorted(set(COMPONENT_RE.findall(full_text)))
        claim_records = []
        for text in texts:
            for match in CLAIM_RE.finditer(text):
                try:
                    claim = json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
                if claim.get("active") is True:
                    claim_records.append({
                        key: claim.get(key)
                        for key in ("worker_id", "claim_id", "branch", "issue_number", "expires_at", "live_work", "mode")
                    })
        result.append({
            "number": number,
            "title": issue["title"],
            "state": issue["state"],
            "updated_at": issue["updatedAt"],
            "labels": sorted(label["name"] for label in issue.get("labels", [])),
            "assignees": sorted(user["login"] for user in issue.get("assignees", [])),
            "body_sha256": hashlib.sha256(issue.get("body", "").encode()).hexdigest(),
            "body_comment_component_id_count": len(all_roster_ids),
            "exact_five_component_ids_present": sorted(COMPONENTS.intersection(all_roster_ids)),
            "active_claims": claim_records,
        })
    OUTPUT.write_text(json.dumps({
        "version": 1,
        "repository": "ChengshuLi/WorldAtlas",
        "captured_at": captured_at,
        "scope_component_ids": sorted(COMPONENTS),
        "issues": result,
        "limits": [
            "The live issue bodies/comments are read-only snapshots; absence of an exact component ID does not prove absence from an owner's private work files.",
            "#1394 records active 97-subject ownership in #1630 context, but its live body/comments do not publish those exact IDs.",
        ],
    }, indent=2) + "\n")
    print(json.dumps({"status": "captured", "issues": len(result), "captured_at": captured_at, "output": str(OUTPUT)}))


if __name__ == "__main__":
    main()
