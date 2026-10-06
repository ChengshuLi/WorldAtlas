"""Input guards shared by the source overlay and its mutation controls."""
import hashlib
from evidence.immutable import canonical_json


class EvidenceGuardError(ValueError):
    """A retained input failed the declared source/scope/vintage contract."""


def verify_source_bytes(raw, expected_sha256):
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256:
        raise EvidenceGuardError("Source whole-file SHA-256 mismatch")
    return actual


def verify_roster(ids, expected_count, expected_sha256):
    if len(ids) != expected_count or len(set(ids)) != len(ids):
        raise EvidenceGuardError("Exact component roster count/uniqueness mismatch")
    ordered = sorted(ids)
    if hashlib.sha256(canonical_json(ordered)).hexdigest() != expected_sha256:
        raise EvidenceGuardError("Exact component roster digest mismatch")
    return ordered


def verify_contact_rows(rows, expected_count, expected_types):
    counts = {}
    for row in rows:
        kind = row.get("kind")
        counts[kind] = counts.get(kind, 0) + 1
    if len(rows) != expected_count or counts != expected_types:
        raise EvidenceGuardError("Complete selected contact inventory mismatch")
    if any(not isinstance(row.get("geometry"), dict) for row in rows):
        raise EvidenceGuardError("Contact geometry must be retained for every row")
    return counts


def verify_vintage(dataset_title, response_date, source_snapshot_label):
    if "2017" not in dataset_title or "2026" not in response_date:
        raise EvidenceGuardError("Source dataset and retrieval vintages are not distinguished")
    if source_snapshot_label != "current-service-response":
        raise EvidenceGuardError("Current service bytes cannot be labelled as a historical snapshot")
    return source_snapshot_label


def verify_admin_selector(level, full_url, simplified_url):
    if level != "ADM1" or not full_url.endswith(".geojson"):
        raise EvidenceGuardError("Pinned administrative selector is not the expected ADM1 source")
    expected = full_url[:-len(".geojson")] + "_simplified.geojson"
    if simplified_url != expected:
        raise EvidenceGuardError("Simplified download URL does not follow the pinned selector transform")
    return expected
