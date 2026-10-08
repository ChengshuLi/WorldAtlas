"""Fail-closed, source-free admission accounting for Central India #1339."""

from __future__ import annotations

import gzip
import io
import re

MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_PHASE_BYTES = 256 * 1024 * 1024
MAX_RECEIPT_BYTES = 4096
_HEX = re.compile(r"^[a-f0-9]{64}$")


class AdmissionError(ValueError):
    """Malformed or incomplete admission declaration."""


class DecodedBodyTooLarge(ValueError):
    def __init__(self, observed_bytes: int, limit_bytes: int):
        self.observed_bytes = observed_bytes
        self.limit_bytes = limit_bytes
        super().__init__(f"decoded body exceeds {limit_bytes} bytes (observed at least {observed_bytes})")


def gzip_footer_isize(raw: bytes) -> int:
    """Read the final member's RFC 1952 size claim without decompressing data."""
    if not isinstance(raw, bytes) or len(raw) < 18 or len(raw) > MAX_FILE_BYTES or raw[:2] != b"\x1f\x8b" or raw[2] != 8:
        raise AdmissionError("not a minimally valid gzip member")
    return int.from_bytes(raw[-4:], "little")


def decode_gzip_bounded(raw: bytes, limit_bytes: int = MAX_FILE_BYTES) -> bytes:
    """Decode one bounded logical body; stop after limit+1 instead of buffering it all."""
    if not isinstance(raw, bytes) or len(raw) > MAX_FILE_BYTES:
        raise AdmissionError("encoded input exceeds file byte limit")
    if not isinstance(limit_bytes, int) or isinstance(limit_bytes, bool) or not 0 <= limit_bytes <= MAX_FILE_BYTES:
        raise AdmissionError("invalid decoded-body limit")
    with gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as stream:
        body = stream.read(limit_bytes + 1)
        if len(body) > limit_bytes:
            raise DecodedBodyTooLarge(len(body), limit_bytes)
        # Force EOF so gzip validates CRC/ISIZE and any concatenated members.
        extra = stream.read(1)
        if extra:
            raise DecodedBodyTooLarge(len(body) + len(extra), limit_bytes)
    return body


def _input_key(row: dict) -> tuple[str, str, int, str]:
    if not isinstance(row, dict):
        raise AdmissionError("input descriptor must be an object")
    identity, category = row.get("identity"), row.get("category")
    size, digest = row.get("bytes"), row.get("sha256")
    if (not isinstance(identity, str) or not identity.strip() or "\0" in identity or
            not isinstance(category, str) or not category.strip() or "\0" in category):
        raise AdmissionError("input needs a logical identity and category")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise AdmissionError("input byte count must be a nonnegative integer")
    if not isinstance(digest, str) or not _HEX.fullmatch(digest):
        raise AdmissionError("input needs a whole-file SHA-256")
    return identity, category, size, digest


def _reservation(row: dict) -> tuple[str, int]:
    if not isinstance(row, dict):
        raise AdmissionError("output reservation must be an object")
    name, size = row.get("name"), row.get("max_bytes")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", name):
        raise AdmissionError("output reservation needs a plain filename")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise AdmissionError("output reservation must have a nonnegative byte ceiling")
    return name, size


def evaluate_phase(
    *,
    raw_inputs: list[dict],
    decoded_inputs: list[dict],
    output_reservations: list[dict],
    expected_input_identities: list[str] | None = None,
    runtime_complete: bool = True,
    receipt_bytes: int = MAX_RECEIPT_BYTES,
    file_limit_bytes: int = MAX_FILE_BYTES,
    phase_limit_bytes: int = MAX_PHASE_BYTES,
) -> dict:
    """Account one complete operation before computation or output publication.

    Repeated declarations for the same logical input are counted once only when
    every descriptor field agrees. Different identities are always retained and
    counted separately, even when their SHA-256 values are equal.
    """
    if not isinstance(raw_inputs, list) or not isinstance(decoded_inputs, list) or not isinstance(output_reservations, list):
        raise AdmissionError("complete input and output inventories must be lists")
    if not isinstance(runtime_complete, bool):
        raise AdmissionError("runtime closure status must be an explicit boolean")
    if not isinstance(file_limit_bytes, int) or isinstance(file_limit_bytes, bool) or not 0 < file_limit_bytes <= MAX_FILE_BYTES:
        raise AdmissionError("invalid file limit")
    if not isinstance(phase_limit_bytes, int) or isinstance(phase_limit_bytes, bool) or not 0 < phase_limit_bytes <= MAX_PHASE_BYTES:
        raise AdmissionError("invalid phase limit")
    if not isinstance(receipt_bytes, int) or isinstance(receipt_bytes, bool) or not 0 <= receipt_bytes <= MAX_RECEIPT_BYTES:
        raise AdmissionError("invalid completion-receipt reserve")

    reasons: list[dict] = []
    unique_inputs: dict[str, tuple[str, int, str]] = {}
    categories: dict[str, int] = {}
    for row in [*raw_inputs, *decoded_inputs]:
        identity, category, size, digest = _input_key(row)
        previous = unique_inputs.get(identity)
        descriptor_value = (category, size, digest)
        if previous is not None and previous != descriptor_value:
            raise AdmissionError(f"conflicting descriptors for logical input {identity}")
        unique_inputs[identity] = descriptor_value
        if row.get("authenticated") is not True:
            reasons.append({"code": "input-not-authenticated", "identity": identity})
        if size > file_limit_bytes:
            reasons.append({"code": "body-exceeds-file-limit", "identity": identity, "bytes": size})

    if expected_input_identities is not None:
        if (not isinstance(expected_input_identities, list) or
                any(not isinstance(identity, str) or not identity.strip() for identity in expected_input_identities)):
            raise AdmissionError("expected logical input identities must be nonempty strings")
        if len(expected_input_identities) != len(set(expected_input_identities)):
            raise AdmissionError("expected logical input identities contain duplicates")
        missing = sorted(set(expected_input_identities) - set(unique_inputs))
        extra = sorted(set(unique_inputs) - set(expected_input_identities))
        if missing:
            reasons.append({"code": "missing-input-descriptors", "identities": missing})
        if extra:
            reasons.append({"code": "unexpected-input-descriptors", "identities": extra})

    input_bytes = 0
    for identity, (category, size, _digest) in unique_inputs.items():
        input_bytes += size
        categories[category] = categories.get(category, 0) + size

    names: set[str] = set()
    output_bytes = 0
    for row in output_reservations:
        name, size = _reservation(row)
        if name in names:
            raise AdmissionError("duplicate output reservation: " + name)
        names.add(name)
        if size > file_limit_bytes:
            reasons.append({"code": "output-exceeds-file-limit", "name": name, "bytes": size})
        output_bytes += size
    if not runtime_complete:
        reasons.append({"code": "runtime-closure-incomplete"})

    complete_bytes = input_bytes + output_bytes + receipt_bytes
    if complete_bytes > phase_limit_bytes:
        reasons.append({"code": "complete-phase-exceeds-limit", "bytes": complete_bytes})
    return {
        "version": 1,
        "status": "refused" if reasons else "admitted",
        "limits": {"file_bytes": file_limit_bytes, "phase_bytes": phase_limit_bytes,
                   "completion_receipt_bytes": receipt_bytes},
        "input_count": len(unique_inputs),
        "input_bytes": input_bytes,
        "input_bytes_by_category": dict(sorted(categories.items())),
        "decoded_input_count": len(decoded_inputs),
        "output_count": len(output_reservations),
        "reserved_output_bytes": output_bytes,
        "complete_phase_bytes": complete_bytes,
        "runtime_complete": runtime_complete,
        "reasons": reasons,
    }


def require_admitted(plan: dict) -> None:
    if not isinstance(plan, dict) or plan.get("status") != "admitted" or plan.get("reasons"):
        raise AdmissionError("complete operation was not admitted")


def run_if_admitted(plan: dict, operation, *args, **kwargs):
    """Invoke a producer only after the complete operation has been admitted."""
    if not callable(operation):
        raise AdmissionError("admitted operation must be callable")
    require_admitted(plan)
    return operation(*args, **kwargs)
