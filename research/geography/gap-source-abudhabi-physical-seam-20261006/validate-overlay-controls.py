"""Run real changed-source, omitted-scope, and vintage mutation controls."""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from overlay_guards import EvidenceGuardError, verify_contact_rows, verify_roster, verify_source_bytes, verify_vintage, verify_admin_selector

OWNED = ROOT / "research/geography/gap-source-abudhabi-physical-seam-20261006"
overlay = json.loads((OWNED / "overlay-v1.json").read_bytes())
expected_roster = "b7af8568f5972dd935d8cc85d16c19f349938ea6810b6b2b391c92d4a1b9df94"
expected_source = "5a7c0583209df1145fb542d595b122b90147ac2e62c0f5dc442f8909f7d67c65"
ids = [row["component"] for row in overlay["components"]]
contacts = overlay["component_contact_records"]
raw = (OWNED / "sources/v1/resolve-ecoregions-abu-dhabi-envelope.geojson").read_bytes()
layer = json.loads((OWNED / "sources/v1/resolve-ecoregions-layer-metadata.json").read_bytes())
receipt = json.loads((OWNED / "sources/v1/resolve-ecoregions-envelope-retrieval.json").read_bytes())

verify_source_bytes(raw, expected_source)
verify_roster(ids, 134, expected_roster)
verify_contact_rows(contacts, 51, {"point-only-ambiguous": 45, "shared-edge": 6})
verify_vintage(layer["name"], receipt["response_date"], "current-service-response")
policy = json.loads(__import__("subprocess").check_output(["git", "-C", str(ROOT), "show", "cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1:data/location-policy.json"]))
rule = policy["countries"]["ARE"]
selector_url = rule["source_url"][:-len(".geojson")] + "_simplified.geojson"
verify_admin_selector(rule["level"], rule["source_url"], selector_url)


def rejected(label, call):
    try:
        call()
    except EvidenceGuardError as exc:
        return {"control": label, "outcome": "rejected-as-required", "guard": str(exc)}
    raise AssertionError(label + " mutation escaped the production guard")


negative = [
    rejected("changed-source-bytes", lambda: verify_source_bytes(raw + b"\n", expected_source)),
    rejected("omitted-component", lambda: verify_roster(ids[:-1], 134, expected_roster)),
    rejected("omitted-contact-row", lambda: verify_contact_rows(contacts[:-1], 51, {"point-only-ambiguous": 45, "shared-edge": 6})),
    rejected("historical-vintage-laundering", lambda: verify_vintage(layer["name"], receipt["response_date"], "historical-2017-snapshot")),
    rejected("altered-selector-transform", lambda: verify_admin_selector(rule["level"], rule["source_url"], selector_url.replace("_simplified", ""))),
]
result = {
    "method_id": "exact-source-overlay",
    "kind": "measurement",
    "outcome": "passed",
    "positive_controls": {
        "source_pin_sha256": hashlib.sha256(raw).hexdigest(),
        "component_roster_sha256": expected_roster,
        "component_contact_rows": len(contacts),
        "current_service_response_vintage": "accepted-with-explicit-current-label",
        "pinned_ADM1_selector_transform": selector_url,
    },
    "negative_controls": negative,
}
(OWNED / "validation-controls-v1.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
