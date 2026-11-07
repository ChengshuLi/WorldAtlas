"""Research-only sequential source-integrity protocol with injected mock math.

This is NOT the admitted Ural gate, a geographic replay, or a publisher.
It has no network client and imports only the Python standard library.
Success returns small synthetic artifacts in memory; it publishes nothing.
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile


SCHEMA = "ural-sequential-synthetic-research-v0"
BOUNDARY_ARTIFACT = "synthetic-boundary.json"


class IntegrityError(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _hash_string(value):
    return (isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def _filename(value):
    return (isinstance(value, str) and value not in ("", ".", "..")
            and "/" not in value and "\\" not in value
            and "\x00" not in value)


@dataclass(frozen=True)
class Source:
    name: str
    source_id: str
    version: str
    manifest_bytes: bytes
    manifest_sha256: str
    full_sha256: str


@dataclass(frozen=True)
class Case:
    name: str
    source_names: tuple
    grid: dict
    output_sha256: str


@dataclass(frozen=True)
class Plan:
    sources: tuple
    cases: tuple
    boundary_file_sha256: str
    boundary_geometry_sha256: str
    projector_contract: str
    boundary_contract: str
    static_input_pins: dict


def plan_payload(plan):
    return {
        "schema": SCHEMA,
        "sources": [{"name": s.name, "source_id": s.source_id,
                     "version": s.version,
                     "manifest_sha256": s.manifest_sha256,
                     "full_sha256": s.full_sha256} for s in plan.sources],
        "cases": [{"name": c.name, "source_names": list(c.source_names),
                   "grid": c.grid, "output_sha256": c.output_sha256}
                  for c in plan.cases],
        "boundary_file_sha256": plan.boundary_file_sha256,
        "boundary_geometry_sha256": plan.boundary_geometry_sha256,
        "projector_contract": plan.projector_contract,
        "boundary_contract": plan.boundary_contract,
        "static_input_pins": plan.static_input_pins,
    }


def plan_sha256(plan):
    return digest(canonical(plan_payload(plan)))


def _manifest(source):
    if not _filename(source.name):
        raise IntegrityError("invalid source filename")
    if (not isinstance(source.manifest_bytes, bytes)
            or not _hash_string(source.manifest_sha256)
            or digest(source.manifest_bytes) != source.manifest_sha256):
        raise IntegrityError("manifest byte pin mismatch: " + source.name)
    if not _hash_string(source.full_sha256):
        raise IntegrityError("invalid full-source pin")
    try:
        obj = json.loads(source.manifest_bytes)
    except (ValueError, UnicodeError) as exc:
        raise IntegrityError("invalid manifest JSON") from exc
    if (not isinstance(obj, dict)
            or set(obj) != {"full_sha256", "parts", "method"}
            or obj["full_sha256"] != source.full_sha256
            or not isinstance(obj["method"], str)
            or not isinstance(obj["parts"], list) or not obj["parts"]):
        raise IntegrityError("manifest full-source identity/schema mismatch")
    keys = set()
    for part in obj["parts"]:
        if (not isinstance(part, dict) or set(part) != {"key", "size", "sha256"}
                or not isinstance(part["key"], str) or not part["key"]
                or part["key"] in keys
                or type(part["size"]) is not int or part["size"] <= 0
                or not _hash_string(part["sha256"])):
            raise IntegrityError("invalid or duplicate manifest part")
        keys.add(part["key"])
    return obj


def _measure_file(path, block_bytes):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise IntegrityError("materialized source is not a regular file")
    h = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        while True:
            block = stream.read(block_bytes)
            if not block:
                break
            h.update(block)
            count += len(block)
    after = path.lstat()
    identity = (info.st_dev, info.st_ino)
    if identity != (after.st_dev, after.st_ino):
        raise IntegrityError("materialized source identity changed while hashing")
    return count, h.hexdigest(), identity


def _materialize(source, manifest, path, open_part, block_bytes):
    """Append authenticated parts directly, with no second part-sized file."""
    full = hashlib.sha256()
    observed_parts = []
    with path.open("xb") as target:
        for part in manifest["parts"]:
            ph = hashlib.sha256()
            count = 0
            # Reader must be a bounded streaming context manager, not a tool
            # response containing a whole object in memory.
            with open_part(part["key"]) as reader:
                while count < part["size"]:
                    block = reader.read(min(block_bytes, part["size"] - count))
                    if not isinstance(block, bytes):
                        raise IntegrityError("part reader did not return bytes")
                    if not block:
                        raise IntegrityError("truncated part: " + part["key"])
                    if len(block) > min(block_bytes, part["size"] - count):
                        raise IntegrityError("part reader exceeded requested bound")
                    ph.update(block)
                    full.update(block)
                    if target.write(block) != len(block):
                        raise IntegrityError("short write while materializing source")
                    count += len(block)
                if reader.read(1) != b"":
                    raise IntegrityError("overlong part: " + part["key"])
            actual = ph.hexdigest()
            if actual != part["sha256"]:
                raise IntegrityError("part SHA-256 mismatch: " + part["key"])
            observed_parts.append({**part, "observed_size": count,
                                   "observed_sha256": actual})
    if full.hexdigest() != source.full_sha256:
        raise IntegrityError("concatenated full-source SHA-256 mismatch")
    expected_size = sum(p["size"] for p in manifest["parts"])
    before = _measure_file(path, block_bytes)
    if before[:2] != (expected_size, source.full_sha256):
        raise IntegrityError("pre-use full-source readback mismatch")
    # Private scratch plus read-only mode prevents accidental writes. It is
    # NOT a sandbox against malicious code running under the same OS identity.
    path.chmod(0o400)
    return expected_size, observed_parts, before


def _check_owned_raw_directory(tile_dir, expected=()):
    """Check only this protocol's raw directory, not callback resources."""
    scratch = tile_dir.parent
    if (not stat.S_ISDIR(scratch.lstat().st_mode)
            or set(scratch.iterdir()) != {tile_dir}
            or not stat.S_ISDIR(tile_dir.lstat().st_mode)):
        raise IntegrityError("owned raw scratch directory was replaced")
    children = list(tile_dir.iterdir())
    if (set(children) != set(expected)
            or any(not stat.S_ISREG(p.lstat().st_mode) for p in children)):
        raise IntegrityError("owned raw scratch directory mismatch")


def run_research(plan, expected_plan_sha256, work_parent, open_part,
                 make_destination, project_mock, encode_output_mock,
                 construct_boundary_mock, preserve_partial_mock, block_bytes=1 << 20):
    """Execute a new integrity protocol, never the existing geographic gate.

    All callback names end in 'mock' deliberately. Their behavior, native
    libraries, credentials and geographic correctness are outside this test.
    A failure raises, removes only this run's private raw scratch files, and
    returns no success trace. The injected diagnostic sink retains candidate
    outputs explicitly marked unverified, including partially updated cases.
    """
    if type(block_bytes) is not int or not 1 <= block_bytes <= (1 << 20):
        raise IntegrityError("invalid bounded reader buffer")
    # These bytes are the immutable authoritative plan snapshot. Never return
    # aliases to the caller's mutable nested grid/static-input dictionaries.
    contract_bytes = canonical(plan_payload(plan))
    contract_sha = digest(contract_bytes)
    if contract_sha != expected_plan_sha256:
        raise IntegrityError("new research plan pin mismatch")
    if any(case.name == BOUNDARY_ARTIFACT for case in plan.cases):
        raise IntegrityError("reserved boundary artifact name used by case")
    if (not plan.projector_contract or not plan.boundary_contract
            or not all(_hash_string(x) for x in (
                plan.boundary_file_sha256, plan.boundary_geometry_sha256))):
        raise IntegrityError("invalid artifact/callback pins")
    sources = {s.name: s for s in plan.sources}
    if len(sources) != len(plan.sources) or not sources:
        raise IntegrityError("duplicate or absent source declarations")
    manifests = {name: _manifest(source) for name, source in sources.items()}
    names = [name for case in plan.cases for name in case.source_names]
    if (len(set(names)) != len(names) or set(names) != set(sources)
            or len({case.name for case in plan.cases}) != len(plan.cases)
            or any(not _filename(c.name) or not c.source_names
                   or not _hash_string(c.output_sha256) for c in plan.cases)):
        raise IntegrityError("each source must occur exactly once in the pinned case order")
    # Observe rather than claim production runtime admission.
    module_path = Path(__file__).resolve()
    module_sha = digest(module_path.read_bytes())
    python_path = Path(sys.executable).resolve()
    python_sha = _measure_file(python_path, 1 << 20)[1]
    trace_sources = []
    artifacts = {}
    peak_raw_bytes = 0
    max_live_tiles = 0
    output_records = []
    work_parent = Path(work_parent).resolve(strict=True)
    if not work_parent.is_dir():
        raise IntegrityError("work_parent is not a directory")
    with tempfile.TemporaryDirectory(prefix="synthetic-sequential-", dir=work_parent) as raw:
        scratch = Path(raw)
        tile_dir = scratch / "one-tile"
        tile_dir.mkdir()
        for case in plan.cases:
            destination = make_destination(case)
            for name in case.source_names:
                _check_owned_raw_directory(tile_dir)
                source = sources[name]
                path = tile_dir / name
                expected_size, parts, before = _materialize(
                    source, manifests[name], path, open_part, block_bytes)
                _check_owned_raw_directory(tile_dir, (path,))
                max_live_tiles = max(max_live_tiles, 1)
                peak_raw_bytes = max(peak_raw_bytes, expected_size)
                try:
                    project_mock(path, destination, case, source)
                    _check_owned_raw_directory(tile_dir, (path,))
                except Exception:
                    # Do not discard a useful partial mock output when the
                    # projector fails. Sink/encoder errors also fail closed.
                    preserve_partial_mock(case.name, encode_output_mock(destination, case), {
                        "schema": SCHEMA, "status": "unverified_partial",
                        "source": name, "reason": "projector or owned raw scratch check failed",
                        "source_post_use_hash_passed": False,
                        "complete_replay_verified": False,
                    })
                    raise
                preserve_partial_mock(case.name, encode_output_mock(destination, case), {
                    "schema": SCHEMA, "status": "unverified_partial",
                    "source": name, "reason": "post-use integrity or final case pin still pending",
                    "source_post_use_hash_passed": False,
                    "complete_replay_verified": False,
                })
                _check_owned_raw_directory(tile_dir, (path,))
                after = _measure_file(path, block_bytes)
                if after != before:
                    raise IntegrityError("post-use full-source integrity/identity mismatch")
                trace_sources.append({
                    "source_id": source.source_id, "version": source.version,
                    "name": name, "case": case.name,
                    "manifest_sha256": source.manifest_sha256,
                    "full_source_sha256": source.full_sha256,
                    "full_source_bytes": expected_size,
                    "parts": parts, "pre_use_sha256": before[1],
                    "post_use_sha256": after[1],
                    "same_local_file_before_after": True,
                })
                _check_owned_raw_directory(tile_dir, (path,))
                path.unlink()
                _check_owned_raw_directory(tile_dir)
            payload = encode_output_mock(destination, case)
            if not isinstance(payload, bytes) or digest(payload) != case.output_sha256:
                raise IntegrityError("pinned raster-output byte hash mismatch: " + case.name)
            preserve_partial_mock(case.name, payload, {
                "schema": SCHEMA, "status": "pinned_crop_match_uncommitted",
                "source": case.source_names[-1], "reason": "final boundary/replay still pending",
                "source_post_use_hash_passed": True,
                "complete_replay_verified": False,
            })
            _check_owned_raw_directory(tile_dir)
            artifacts[case.name] = payload
            output_records.append({"name": case.name,
                                   "sha256": digest(payload), "bytes": len(payload),
                                   "source_order": list(case.source_names),
                                   "grid": json.loads(canonical(case.grid))})
        boundary = construct_boundary_mock(dict(artifacts))
        if isinstance(boundary, bytes):
            preserve_partial_mock(BOUNDARY_ARTIFACT, boundary, {
                "schema": SCHEMA, "status": "unverified_partial",
                "reason": "final file/canonical hashes and runtime checks still pending",
                "complete_replay_verified": False,
            })
        if (not isinstance(boundary, bytes) or len(boundary) > (4 << 20)
                or digest(boundary) != plan.boundary_file_sha256):
            raise IntegrityError("pinned final-boundary file hash mismatch")
        try:
            geometry = json.loads(boundary)
            geometry_sha = digest(canonical(geometry))
        except (ValueError, UnicodeError) as exc:
            raise IntegrityError("invalid final-boundary JSON") from exc
        if geometry_sha != plan.boundary_geometry_sha256:
            raise IntegrityError("pinned final-boundary canonical geometry hash mismatch")
        if (plan_sha256(plan) != contract_sha
                or digest(module_path.read_bytes()) != module_sha
                or _measure_file(python_path, 1 << 20)[1] != python_sha):
            raise IntegrityError("research plan/code/runtime changed during execution")
        _check_owned_raw_directory(tile_dir)
    artifacts[BOUNDARY_ARTIFACT] = boundary
    trace = {
        "schema": SCHEMA, "status": "synthetic_checks_passed",
        "geographic_accuracy_verified": False,
        "existing_gate_contract_satisfied": False,
        "independent_review_and_real_data_test_required": True,
        "plan_sha256": contract_sha, "plan": json.loads(contract_bytes),
        "prototype_code_sha256": module_sha,
        "python_executable_sha256_observed": python_sha,
        "source_use_order": names, "sources": trace_sources,
        "outputs": output_records,
        "boundary_file_sha256": digest(boundary),
        "boundary_geometry_sha256": geometry_sha,
        "peak_owned_raw_source_bytes": peak_raw_bytes,
        "max_owned_raw_sources_at_checks": max_live_tiles,
        "resource_accounting_scope": "protocol-owned raw sources at directory validation boundaries only; not arbitrary callback disk, memory, or transient allocations",
        "reader_buffer_bytes": block_bytes,
        "publication": "none; synthetic artifacts returned in memory; diagnostic partials remain uncommitted",
        "limitations": [
            "Projection, output encoding and boundary construction are injected mocks.",
            "No actual Ural raw source, manifest, geographic raster or boundary was replayed.",
            "The former global pre/post inventory is replaced by per-use authenticated materialization.",
            "Read-only mode and hash brackets do not sandbox malicious callbacks or native libraries.",
            "Owned-source accounting is not a total disk/RAM bound or a continuous monitor of callback allocations.",
            "No network reader, credential boundary, production admission or crash recovery is implemented.",
        ],
    }
    # Canonical text is immutable audit evidence; the convenience dict is a
    # detached JSON copy and has no mutable aliases to plan or callback state.
    trace_bytes = canonical(trace)
    return {"trace": json.loads(trace_bytes),
            "trace_canonical_json": trace_bytes.decode("utf-8"),
            "trace_sha256": digest(trace_bytes), "artifacts": artifacts}
