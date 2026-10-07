#!/usr/bin/env python3
"""Verify the complete dual-stream source closure and measure three literal geometries."""
import argparse
import gzip
import hashlib
import json
import importlib
import inspect
import marshal
import os
import platform
from pathlib import Path
import subprocess
import sys
import zlib

from shapely.geometry import shape
import shapely

PACKET = Path(__file__).resolve().parent
BASE = "6a47b43025d963daf80915c6d219c75ebcc8cd91"
ANCESTOR = "83bed8c4c49e8f54077bb4abf0f32d41d0992f81"
META = "data/regional-review/regional-review-d0984f717127fb3e/sources/geoBoundaries-IND-ADM3-2018-retained-metadata.json"
INVENTORY = "data/regional-review/regional-review-d0984f717127fb3e/source-inventory.json"
SOURCE_BYTES, SOURCE_SHA = 13_794_274, "211a72c2c80bb60d10214944fa8cc4764e9ba888116e802ce6d87084872f5301"
RAW_BYTES, RAW_SHA = 40_040_002, "4ea6807d0a0c5aac0b46ee8e31ed7c30fbec273b44345bba1e4a2bb5f299f5fb"
ENCODED_LAYOUT = [(0, 8_388_608), (8_388_608, 5_405_666)]
DECODED_LAYOUT = [(0, 16_777_216), (16_777_216, 16_777_216), (33_554_432, 6_485_570)]
EXPECTED_COMPONENT = "physical-component:81713fe9120ee5e30d3e0e4ceb1785ca890e6fb6327a4939026c276d448141eb"
EXPECTED_CONTACT = "atlas:local:IND:7132399B91549871673633"
EXPECTED_SOURCE_ID = "7132399B91549871673633"
EXPECTED_FEATURE_SHA = "8d4c511ac4c1a541544598d1dec855779711ed75e7263a93d410f0bd15b08726"
EXPECTED_COMPONENT_FEATURE_SHA = "26d4ada18b01926a37bd8cc9f6e9d1d34a32d4ede5de1a9e5e1db0554af8a211"
EXPECTED_FAMILY_ID = "gap-source-batch:f41df3bc72099aca02d08c88"
EXPECTED_BATCH_ID = "gap-operational-batch:5d2491ded831bcb754b0fdb3"
FAMILY_SHARD_BYTES, FAMILY_SHARD_SHA = 8_388_608, "a1663477a0e01de8bb56736262b57e95c3c49647d54db95c4d2fd6d86600c328"
FAMILY_ROW_OFFSET, FAMILY_ROW_BYTES = 6_232_978, 5_040
FAMILY_ROW_SHA = "b2ac5aaf19131ff0cf778c56f56fb0a8eae60a6d1b4198bfeb5b80be897e2fbd"
MAX_FILE, MAX_TOTAL, MAX_DESCRIPTORS = 32 * 1024 * 1024, 256 * 1024 * 1024, 512
CHUNK = 64 * 1024
PINS = {
    "routing-family-roster": ("coordination/engineering/global-actionability-routing-20261007/results/families-012.bin.gz", "483fb0b6c5b9a8e1b905bf2dc3aa0ca232dcede6f34ef357381770a603e52df0", 965771),
    "source-fitness-candidates": ("coordination/engineering/global-actionability-routing-20261007/results/land-source-fitness-000.bin.gz", "98382c95655a927c4075e7de5c8aa5204980340d001cfb28d9993823cc3d8476", 301503),
    "numeric-source-priority": ("coordination/engineering/physical-gap-priorities-1005-20261006-local20/priorities-v3/investigations-016.json.gz", "36423a8ef87ad3cbe63bff3183446468a9503e62420b46223e9f0bf9ec747db3", 1016389),
    "original-physical-components": ("coordination/engineering/global-source-comparisons-a-001-20261006/scientific/components-011.json.gz", "c23403bddb316a691126954828294061daf09b4305f58e18d53b1010a57df317", 754172),
    "original-comparison-scope": ("coordination/engineering/global-source-comparisons-a-001-20261006/scope.json", "7e74cb58f1c111316522ad92a09767bdc315c2c710eba1642e33ae907f9592c0", 1825364),
    "retained-source-metadata": (META, "f7bb99ddfcadaa1091c4b634b48c8843ee9d8b636af4f6da1cefccb0d424fc33", 2206),
    "retained-source-2018-byte-identity-metadata": (META, "f7bb99ddfcadaa1091c4b634b48c8843ee9d8b636af4f6da1cefccb0d424fc33", 2206),
    "source-inventory": (INVENTORY, "ef561241b2c81afe4eaea501963a955d7d57d06cc925cc8090310205e2e55e56", 5547),
    "current-location-part-32": ("data/geography/part-32.json", "00f3dbcca1a5ff99c8b7c430ca96287acc88bd95e52524e01984ee23aba7ef64", 10211739),
    "current-hierarchy": ("data/hierarchy.json", "568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b", 10164089),
    "original-component-payload": ("coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/payloads/f3d7b0803f108a10ec800797ac8e83f122833a209fd864eabea209fc199d09bf.bin", "f3d7b0803f108a10ec800797ac8e83f122833a209fd864eabea209fc199d09bf", 2080606),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def bounded_candidate(root, relative, limit=MAX_FILE):
    """Read a lexical packet-relative ordinary file, refusing symlinks and growth."""
    root = Path(root)
    if ".." in root.parts: raise ValueError("Candidate root must not contain parent traversal")
    root = Path(os.path.abspath(root))
    rel = Path(relative)
    if rel.is_absolute() or any(p in ("", ".", "..") for p in rel.parts):
        raise ValueError("Candidate path is not a safe relative name")
    cursor = root
    if cursor.is_symlink() or not cursor.is_dir(): raise ValueError("Candidate root is not an ordinary directory")
    for part in rel.parts[:-1]:
        cursor = cursor / part
        if cursor.is_symlink() or not cursor.is_dir(): raise ValueError("Candidate ancestor is not an ordinary directory")
    target = cursor / rel.parts[-1]
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(target, flags)
    try:
        info = os.fstat(fd)
        if not __import__("stat").S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError("Candidate is not an ordinary bounded file")
        chunks = []; total = 0
        while True:
            block = os.read(fd, min(CHUNK, limit + 1 - total))
            if not block: break
            total += len(block)
            if total > limit: raise ValueError("Candidate grew beyond its ordinary-file cap")
            chunks.append(block)
        if total != info.st_size: raise ValueError("Candidate size changed while being read")
        return b"".join(chunks)
    finally:
        os.close(fd)


def geometry_observations(source, component, current):
    if not all(g.is_valid and g.geom_type == "Polygon" for g in (source, component, current)):
        raise ValueError("Geometry fixture contains invalid or non-Polygon input")
    values = {
        "source_covers_component": bool(source.covers(component)),
        "current_contact_covers_component": bool(current.covers(component)),
        "source_minus_component_empty": bool(source.difference(component).is_empty),
        "component_minus_source_empty": bool(component.difference(source).is_empty),
        "source_current_symmetric_difference": float(source.symmetric_difference(current).area),
        "source_current_topologically_equal": bool(source.equals(current)),
    }
    return values


def geometry_subject_gate(source, component, current):
    values = geometry_observations(source, component, current)
    if (values["source_covers_component"] is not True or
            values["current_contact_covers_component"] is not False or
            values["component_minus_source_empty"] is not True or
            values["source_current_symmetric_difference"] <= 0):
        raise ValueError("Subject geometry relation differs from the reviewed source/current expectation")
    return values


def runtime_receipt():
    module_names = ["shapely.geometry.geo", "shapely.geometry.base", "shapely.predicates", "shapely.set_operations"]
    modules = {name: importlib.import_module(name) for name in module_names}
    source_files = {}
    for name, module in modules.items():
        path = Path(module.__file__)
        source_files[name] = {"path": str(path.resolve()), "bytes": path.stat().st_size,
                              "sha256": sha(path.read_bytes())}
    package_root = Path(shapely.__file__).parent
    for label, path in {
        "shapely-native-extension": Path(shapely.lib.__file__),
        "geos-c": package_root / ".dylibs" / "libgeos_c.1.19.2.dylib",
        "geos": package_root / ".dylibs" / "libgeos.3.13.1.dylib",
    }.items():
        if not path.is_file(): raise ValueError("Pinned native geometry runtime body is absent: " + label)
        source_files[label] = {"path": str(path.resolve()), "bytes": path.stat().st_size,
                              "sha256": sha(path.read_bytes())}
    callables = {
        "shape": modules["shapely.geometry.geo"].shape,
        "covers": modules["shapely.geometry.base"].BaseGeometry.covers,
        "difference": modules["shapely.geometry.base"].BaseGeometry.difference,
        "symmetric_difference": modules["shapely.geometry.base"].BaseGeometry.symmetric_difference,
        "is_valid": modules["shapely.geometry.base"].BaseGeometry.is_valid.fget,
        "predicates_covers": modules["shapely.predicates"].covers,
        "set_symmetric_difference": modules["shapely.set_operations"].symmetric_difference,
    }
    identities = {}
    for name, value in callables.items():
        code = getattr(value, "__code__", None)
        if code is None: raise ValueError("Protected runtime callable has no inspectable Python body: " + name)
        identities[name] = {"module": value.__module__, "qualname": value.__qualname__,
                            "code_sha256": sha(marshal.dumps(code))}
    exe = Path(sys.executable).resolve()
    exe_digest = hashlib.sha256()
    with exe.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""): exe_digest.update(block)
    return {"executable": {"path": str(exe), "sha256": exe_digest.hexdigest()},
            "python": sys.version, "python_version": platform.python_version(),
            "zlib_compile": zlib.ZLIB_VERSION, "zlib_runtime": zlib.ZLIB_RUNTIME_VERSION,
            "shapely": shapely.__version__, "geos": shapely.geos_version_string,
            "module_files": source_files, "callables": identities}


def geometry_method_controls():
    from shapely.geometry import Polygon, box
    source, component, current = box(0, 0, 2, 2), box(.5, .5, 1.5, 1.5), box(1, 0, 3, 2)
    observed = geometry_subject_gate(source, component, current)
    expected = {"source_covers_component": True, "current_contact_covers_component": False,
                "source_minus_component_empty": False, "component_minus_source_empty": True,
                "source_current_symmetric_difference": 4.0, "source_current_topologically_equal": False}
    if observed != expected: raise ValueError("Directed positive method geometry control differs")
    rejected = {}
    cases = {
        "uncovered-source": (box(0, 0, .75, .75), component, current),
        "contact-covers": (source, component, source),
        "invalid-source": (Polygon([(0, 0), (2, 2), (0, 2), (2, 0), (0, 0)]), component, current),
    }
    for name, args in cases.items():
        try: geometry_subject_gate(*args)
        except ValueError: rejected[name] = True
        else: raise ValueError("Directed negative method geometry control was accepted: " + name)
    return {"positive": observed, "expected": expected, "negative_rejections": rejected}


def canonical_sha(value):
    raw = (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()
    return sha(raw)


def baseline(path, expected_hash, expected_bytes, max_bytes=MAX_FILE):
    if expected_bytes > max_bytes:
        raise ValueError("Baseline ordinary input exceeds the file cap")
    row = subprocess.check_output(["git", "ls-tree", "-z", BASE, "--", path]).decode().rstrip("\0")
    if not row.startswith(("100644 blob ", "100755 blob ")) or row.split("\t", 1)[1] != path:
        raise ValueError("Pinned baseline input is not an ordinary file: " + path)
    oid = row.split()[2]
    object_size = int(subprocess.check_output(["git", "cat-file", "-s", oid], text=True).strip())
    if object_size != expected_bytes or object_size > max_bytes:
        raise ValueError("Pinned baseline ordinary file has wrong or excessive size: " + path)
    raw = subprocess.check_output(["git", "cat-file", "blob", oid])
    if len(raw) != expected_bytes or sha(raw) != expected_hash:
        raise ValueError("Pinned baseline whole bytes differ: " + path)
    return raw


class SourceJSON:
    """Incremental top-level GeoJSON parser; one complete feature is its largest value."""
    def __init__(self):
        import codecs
        self.utf8 = codecs.getincrementaldecoder("utf-8")("strict")
        self.decoder = json.JSONDecoder()
        self.buf = ""
        self.pos = 0
        self.state = "root-open"
        self.key = None
        self.root_type = None
        self.feature_count = 0
        self.ids = set()
        self.selected = None
        self.selected_raw_sha256 = None
        self.selected_canonical_sha256 = None

    def feed(self, raw, final=False):
        self.buf += self.utf8.decode(raw, final=final)
        while True:
            self._ws()
            if self.state == "root-open":
                if not self._char("{"): break
                self.pos += 1; self.state = "root-key"
            elif self.state == "root-key":
                if self._char("}"):
                    self.pos += 1; self.state = "done"; continue
                parsed = self._value()
                if parsed is None: break
                self.key, self.pos = parsed
                if not isinstance(self.key, str): raise ValueError("GeoJSON root key is not a string")
                self.state = "root-colon"
            elif self.state == "root-colon":
                if not self._char(":"): break
                self.pos += 1; self.state = "root-value"
            elif self.state == "root-value":
                if self.key == "features":
                    if not self._char("["): raise ValueError("GeoJSON features is not an array")
                    self.pos += 1; self.state = "feature-value"
                else:
                    parsed = self._value()
                    if parsed is None: break
                    value, self.pos = parsed
                    if self.key == "type": self.root_type = value
                    self.state = "root-separator"
            elif self.state == "feature-value":
                if self._char("]"):
                    self.pos += 1; self.state = "root-separator"; continue
                start = self.pos
                parsed = self._value()
                if parsed is None: break
                value, self.pos = parsed
                if not isinstance(value, dict) or value.get("type") != "Feature" or not isinstance(value.get("properties"), dict):
                    raise ValueError("Source member is not a complete GeoJSON Feature")
                props = value["properties"]
                source_id = props.get("shapeID") or props.get("shapeId")
                if not isinstance(source_id, str) or source_id in self.ids:
                    raise ValueError("Source has missing or duplicated native shapeID")
                self.ids.add(source_id)
                self.feature_count += 1
                if source_id == EXPECTED_SOURCE_ID:
                    self.selected = value
                    self.selected_raw_sha256 = sha(self.buf[start:self.pos].encode("utf-8"))
                    self.selected_canonical_sha256 = canonical_sha(value)
                self.state = "feature-separator"
            elif self.state == "feature-separator":
                if self._char(","):
                    self.pos += 1; self.state = "feature-value"
                elif self._char("]"):
                    self.pos += 1; self.state = "root-separator"
                else: break
            elif self.state == "root-separator":
                if self._char(","):
                    self.pos += 1; self.state = "root-key"
                elif self._char("}"):
                    self.pos += 1; self.state = "done"
                else: break
            elif self.state == "done":
                if self.pos < len(self.buf): raise ValueError("Trailing data after GeoJSON root")
                break
            if self.pos > 1024 * 1024:
                self.buf = self.buf[self.pos:]
                self.pos = 0
        if final:
            self._ws()
            if self.state != "done" or self.pos != len(self.buf):
                raise ValueError("Truncated or malformed complete source JSON")
            if self.root_type != "FeatureCollection" or self.feature_count != 6822 or len(self.ids) != 6822 or self.selected is None:
                raise ValueError("Complete source roster or FeatureCollection identity differs")
            if self.selected.get("properties", {}).get("shapeName") != "Kakinada (Rural)":
                raise ValueError("Selected original source member name/ID join differs")
        return self.selected

    def _ws(self):
        while self.pos < len(self.buf) and self.buf[self.pos] in " \t\r\n": self.pos += 1

    def _char(self, value):
        return self.pos < len(self.buf) and self.buf[self.pos] == value

    def _value(self):
        try:
            return self.decoder.raw_decode(self.buf, self.pos)
        except json.JSONDecodeError:
            if len(self.buf) - self.pos > MAX_FILE:
                raise ValueError("One JSON value exceeds the ordinary 32 MiB bound")
            return None


class RawParts:
    def __init__(self, root, parts):
        self.root = root
        self.parts = parts
        self.part_index = 0
        self.stream = None
        self.remaining = 0

    def read(self, count):
        chunks = []
        needed = count
        while needed and self.part_index < len(self.parts):
            part = self.parts[self.part_index]
            if self.stream is None:
                self.stream = memoryview(bounded_candidate(self.root, part["path"], MAX_FILE))
                self.remaining = part["bytes"]
            count = min(needed, self.remaining)
            block = self.stream[:count].tobytes()
            self.stream = self.stream[count:]
            if not block: raise ValueError("Decoded fragment ended before its declared length")
            chunks.append(block); needed -= len(block); self.remaining -= len(block)
            if self.remaining == 0:
                if self.stream: raise ValueError("Decoded fragment has trailing bytes")
                self.stream = None; self.part_index += 1
        return b"".join(chunks)

    def finish(self):
        if self.read(1): raise ValueError("Decoded fragments contain bytes after the gzip stream")
        if self.part_index != len(self.parts): raise ValueError("Decoded fragment chain was not fully consumed")


def validate_index(root, index):
    if index.get("version") != 1 or len(index.get("streams", [])) != 2:
        raise ValueError("Unsupported dual-stream fragment index")
    if index.get("ancestor") != {"commit": ANCESTOR, "metadata_path": META,
          "metadata_sha256": PINS["retained-source-metadata"][1], "inventory_path": INVENTORY,
          "inventory_sha256": PINS["source-inventory"][1]}:
        raise ValueError("Fragment index does not bind the authentic ancestor metadata/index")
    expected = [
        ("original-encoded-gzip", "opaque-encoded-original-source", SOURCE_BYTES, SOURCE_SHA, ENCODED_LAYOUT, "encoded-gzip-opaque-fragment", "encoded"),
        ("original-decoded-json", "complete-decoded-original-source", RAW_BYTES, RAW_SHA, DECODED_LAYOUT, "decoded-raw-source-fragment", "decoded")
    ]
    verified = []
    paths = set()
    total_parts = 0
    for stream, (sid, role, whole_bytes, whole_sha, layout, part_role, prefix) in zip(index["streams"], expected):
        if (stream.get("id"), stream.get("role"), stream.get("bytes"), stream.get("sha256")) != (sid, role, whole_bytes, whole_sha):
            raise ValueError("Whole source relation does not match frozen original identities")
        parts = stream.get("parts")
        if not isinstance(parts, list) or len(parts) != len(layout) or stream.get("part_bytes") != whole_bytes:
            raise ValueError("Part count or byte relation is incomplete")
        cursor = 0
        for ordinal, (part, (offset, size)) in enumerate(zip(parts, layout)):
            if part.get("ordinal") != ordinal or part.get("offset") != offset or part.get("bytes") != size or part.get("role") != part_role or part.get("path") != f"{prefix}-{ordinal:03d}.bin":
                raise ValueError("Part ordinal/offset/length/role/path differs from exact reviewed ranges")
            if part["path"] in paths or size > MAX_FILE: raise ValueError("Duplicate or oversized source part")
            paths.add(part["path"]); cursor += size; total_parts += size
            raw = bounded_candidate(root, part["path"], MAX_FILE)
            digest = hashlib.sha256(); actual_size = 0
            for offset in range(0, len(raw), CHUNK):
                block = raw[offset:offset + CHUNK]
                digest.update(block); actual_size += len(block)
            if actual_size != size or digest.hexdigest() != part.get("sha256"):
                raise ValueError("Literal source part bytes do not match their authenticated index entry")
        if cursor != whole_bytes: raise ValueError("Part ranges contain a gap or trailing byte")
        verified.append(parts)
    if total_parts != 53_834_276 or total_parts > MAX_TOTAL or index.get("literal_part_body_bytes") != total_parts:
        raise ValueError("Dual-stream ordinary phase exceeds or misstates its literal body budget")
    meta = json.loads(baseline(META, PINS["retained-source-metadata"][1], 2206))
    inv = json.loads(baseline(INVENTORY, PINS["source-inventory"][1], 5547))
    if meta.get("compressed_sha256") != SOURCE_SHA or meta.get("sha256") != RAW_SHA:
        raise ValueError("Ancestor metadata no longer authenticates original encoded and decoded identities")
    if meta.get("admUnitCount") != "6836" or index["original_source"].get("features") != 6822:
        raise ValueError("Provider versus observed feature count discrepancy changed")
    matches = [x for x in inv.get("sources", []) if x.get("path") == "sources/geoBoundaries-IND-ADM3-2018-retained.geojson.gz"]
    if len(matches) != 1 or (matches[0].get("sha256"), matches[0].get("bytes")) != (SOURCE_SHA, SOURCE_BYTES):
        raise ValueError("Ancestor inventory does not bind the historical encoded stream")
    return verified


def validate_freeze(packet, index_path, index_bytes, index, parts):
    freeze_bytes = bounded_candidate(packet, "closure-freeze.json")
    freeze = json.loads(freeze_bytes)
    if freeze.get("version") != 1 or freeze.get("baseline_commit") != BASE or freeze.get("subject_ids") != [EXPECTED_CONTACT] or freeze.get("component_ids") != [EXPECTED_COMPONENT]:
        raise ValueError("Frozen closure scope/commit differs from the reviewed issue")
    if freeze.get("original_source_identities") != {"encoded_bytes": SOURCE_BYTES, "encoded_sha256": SOURCE_SHA,
            "decoded_bytes": RAW_BYTES, "decoded_sha256": RAW_SHA}:
        raise ValueError("Frozen closure rebinds the original complete source identities")
    if freeze.get("family_row_locator") != {"decoded_shard_bytes": FAMILY_SHARD_BYTES, "decoded_shard_sha256": FAMILY_SHARD_SHA,
            "offset": FAMILY_ROW_OFFSET, "row_bytes": FAMILY_ROW_BYTES, "row_sha256": FAMILY_ROW_SHA,
            "family_id": EXPECTED_FAMILY_ID, "component_ids": [EXPECTED_COMPONENT], "contact_ids": [EXPECTED_CONTACT]}:
        raise ValueError("Frozen closure rebinds the complete original routed family row/member relation")
    expected_baseline = {key: {"path": path, "sha256": digest, "bytes": size} for key, (path, digest, size) in PINS.items()}
    if freeze.get("baseline_inputs") != expected_baseline:
        raise ValueError("Frozen closure coherently rebinds a foreign component/context source")
    actual_inputs = {"inputs/fragment-index.json": {"bytes": len(index_bytes), "sha256": sha(index_bytes)}}
    for part in index["streams"][0]["parts"] + index["streams"][1]["parts"]:
        actual_inputs["inputs/" + part["path"]] = {"bytes": part["bytes"], "sha256": part["sha256"]}
    if freeze.get("candidate_inputs") != actual_inputs:
        raise ValueError("Frozen closure candidate fragment/index descriptors changed")
    code_root = Path(__file__).parent
    expected_code = freeze.get("code")
    if not isinstance(expected_code, dict) or set(expected_code) != {"capture-fragments.py", "measure.py", "controls.py", "runner.py"}:
        raise ValueError("Frozen closure lacks the complete executable producer/control inventory")
    for name, expected_hash in expected_code.items():
        actual = sha(bounded_candidate(code_root, name))
        if actual != expected_hash: raise ValueError("Frozen producer/import/control source changed: " + name)
        committed = subprocess.check_output(["git", "show", freeze["execution_commit"] + ":research/geography/india-kakinada-rural-source-fitness-20261007/" + name], text=False)
        if sha(committed) != expected_hash:
            raise ValueError("Frozen execution commit does not contain authenticated producer body: " + name)
    runtime = freeze.get("runtime")
    actual_runtime = runtime_receipt()
    if runtime != actual_runtime: raise ValueError("Frozen runtime/import receipt differs from actual execution")
    if not isinstance(freeze.get("execution_commit"), str) or len(freeze["execution_commit"]) != 40:
        raise ValueError("Frozen closure lacks its immutable execution commit")
    return freeze, sha(freeze_bytes), actual_inputs, expected_baseline, expected_code


def read_and_decompress(root, encoded_parts, decoded_parts):
    expected = RawParts(root, decoded_parts)
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    parser = SourceJSON()
    encoded_hash, decoded_hash = hashlib.sha256(), hashlib.sha256()
    encoded_count = decoded_count = 0

    def consume(raw):
        nonlocal decoded_count
        if not raw: return
        compared = expected.read(len(raw))
        if compared != raw: raise ValueError("A decompressed byte differs from the ordered decoded fragment chain")
        decoded_hash.update(raw); decoded_count += len(raw)
        if decoded_count > RAW_BYTES: raise ValueError("Gzip output exceeds the pinned complete decoded length")
        parser.feed(raw)

    for part in encoded_parts:
        raw_part = bounded_candidate(root, part["path"], MAX_FILE)
        for offset in range(0, len(raw_part), CHUNK):
            block = raw_part[offset:offset + CHUNK]
            encoded_hash.update(block); encoded_count += len(block)
            pending = block
            while True:
                out = decoder.decompress(pending, CHUNK)
                pending = decoder.unconsumed_tail
                consume(out)
                if pending:
                    continue
                if len(out) == CHUNK:
                    pending = b""
                    continue
                break
    while True:
        out = decoder.decompress(b"", CHUNK)
        if not out: break
        consume(out)
    tail = decoder.flush()
    consume(tail)
    if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError("Virtual encoded source is truncated, concatenated or has trailing bytes")
    expected.finish()
    parser.feed(b"", final=True)
    if parser.selected_canonical_sha256 != EXPECTED_FEATURE_SHA:
        raise ValueError("Selected full source feature canonical identity differs from independent retained record")
    if encoded_count != SOURCE_BYTES or encoded_hash.hexdigest() != SOURCE_SHA:
        raise ValueError("Virtual encoded source does not match original full encoded bytes")
    if decoded_count != RAW_BYTES or decoded_hash.hexdigest() != RAW_SHA:
        raise ValueError("Virtual decoded source does not match original full decoded bytes")
    return parser.selected, {
        "encoded_bytes": encoded_count, "encoded_sha256": encoded_hash.hexdigest(),
        "decoded_bytes": decoded_count, "decoded_sha256": decoded_hash.hexdigest(),
        "feature_count": parser.feature_count, "unique_native_shape_id_count": len(parser.ids),
        "selected_shapeID": EXPECTED_SOURCE_ID, "selected_name": "Kakinada (Rural)",
        "selected_raw_feature_sha256": parser.selected_raw_sha256,
        "selected_canonical_feature_sha256": parser.selected_canonical_sha256,
        "selected_feature_hash_matches_independent_record": parser.selected_canonical_sha256 == EXPECTED_FEATURE_SHA,
        "source_feature_ids_sorted": sorted(parser.ids),
        "whole_decoded_file_written": False
    }


def find_features(value, identity):
    matches = []
    if isinstance(value, dict):
        if value.get("type") == "Feature" and (value.get("id") == identity or value.get("properties", {}).get("id") == identity):
            matches.append(value)
        for child in value.values(): matches.extend(find_features(child, identity))
    elif isinstance(value, list):
        for child in value: matches.extend(find_features(child, identity))
    return matches


def find_key(value, key, expected):
    found = []
    if isinstance(value, dict):
        if value.get(key) == expected: found.append(value)
        for child in value.values(): found.extend(find_key(child, key, expected))
    elif isinstance(value, list):
        for child in value: found.extend(find_key(child, key, expected))
    return found


def family_shard_row():
    """Authenticate the complete containing gzip/shard and exact in-shard JSONL record."""
    packed = baseline(*PINS["routing-family-roster"])
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    shard = decoder.decompress(packed, MAX_FILE + 1)
    if decoder.unconsumed_tail or not decoder.eof or decoder.unused_data or len(shard) > MAX_FILE:
        raise ValueError("Complete routed family shard exceeds bounded decode or gzip integrity")
    if len(shard) != FAMILY_SHARD_BYTES or sha(shard) != FAMILY_SHARD_SHA:
        raise ValueError("Complete routed family containing-byte shard differs")
    start, end = FAMILY_ROW_OFFSET, FAMILY_ROW_OFFSET + FAMILY_ROW_BYTES
    if end >= len(shard) or shard[end:end+1] != b"\n":
        raise ValueError("Reviewed family row byte range is not line-delimited")
    raw = shard[start:end]
    if sha(raw) != FAMILY_ROW_SHA:
        raise ValueError("Exact original routed family row bytes differ")
    row = json.loads(raw)
    if row.get("id") != EXPECTED_FAMILY_ID or row.get("operational_batch") != EXPECTED_BATCH_ID:
        raise ValueError("Original routed family identity/batch differs")
    ids = row.get("complete_component_ids")
    original = row.get("original_fine_family", {})
    if (row.get("component_count") != 1 or row.get("fine_family_count") != 1 or
            ids != [EXPECTED_COMPONENT] or original.get("component_ids") != ids or
            original.get("component_count") != 1 or original.get("contact_ids") != [EXPECTED_CONTACT] or
            row.get("compatible_original_admin_component_ids") != ids or
            row.get("admin_status_counts") != {"one-compatible-recorded-subject-uniquely-covers-component": 1} or
            row.get("exclusive_next_prerequisite_counts") != {"land-plus-compatible-original-processing-reproduction-candidate": 1} or
            row.get("numeric_closure_component_count") != 0 or row.get("hierarchy_unknown_component_count") != 0 or
            row.get("invalid_original_source_component_count") != 0 or row.get("native_invalid_component_ids") != [] or
            row.get("components_with_unmeasured_fragments") != 0 or
            row.get("dispatch_ready") is not False or row.get("boundary_length_m") is not None or
            original.get("cause_status") != "unknown"):
        raise ValueError("Complete family member/count/contact/prerequisite/uncertainty flags differ")
    return row, {"whole_encoded_bytes": len(packed), "whole_encoded_sha256": sha(packed),
                 "whole_decoded_shard_bytes": len(shard), "whole_decoded_shard_sha256": sha(shard),
                 "row_offset": start, "row_bytes": len(raw), "row_sha256": sha(raw),
                 "whole_shard_written": False}


def json_bytes(path, packed=False):
    raw = baseline(*PINS[path]) if path in PINS else None
    if raw is None: raise KeyError(path)
    if packed:
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        out = decoder.decompress(raw, MAX_FILE + 1)
        if decoder.unconsumed_tail or not decoder.eof or decoder.unused_data or len(out) > MAX_FILE:
            raise ValueError("Baseline JSON input exceeds bounded decode or has a malformed gzip")
        raw = out
    return json.loads(raw)


def run(packet, out_path):
    packet = Path(packet)
    if ".." in packet.parts: raise ValueError("Packet root must not contain parent traversal")
    packet = Path(os.path.abspath(packet))
    cursor = packet
    while True:
        if cursor.is_symlink(): raise ValueError("Packet root ancestry contains a symlink")
        if cursor.parent == cursor: break
        cursor = cursor.parent
    if not packet.is_dir(): raise ValueError("Packet root must be an ordinary directory")
    index_path = packet / "inputs" / "fragment-index.json"
    index_bytes = bounded_candidate(packet, "inputs/fragment-index.json", 1024 * 1024)
    index = json.loads(index_bytes)
    encoded, decoded = validate_index(index_path.parent, index)
    freeze, freeze_sha, candidate_inputs, baseline_inputs, code_inputs = validate_freeze(packet, index_path, index_bytes, index, encoded + decoded)
    selected, byte_summary = read_and_decompress(packet / "inputs", encoded, decoded)

    component_payload_raw = baseline(*PINS["original-component-payload"])
    component_decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    component_json = component_decoder.decompress(component_payload_raw, MAX_FILE + 1)
    if component_decoder.unconsumed_tail or not component_decoder.eof or len(component_json) > MAX_FILE:
        raise ValueError("Original component payload exceeds bounded decode")
    component_collection = json.loads(component_json)
    components = [f for f in component_collection["features"] if f.get("id") == EXPECTED_COMPONENT]
    if len(components) != 1: raise ValueError("Frozen original component feature is not unique")
    component_feature = components[0]
    component_feature_sha = canonical_sha(component_feature)
    component_geometry_sha = canonical_sha(component_feature["geometry"])
    if component_feature_sha != EXPECTED_COMPONENT_FEATURE_SHA or component_geometry_sha != "5c68774784a2d75180bd200e2a7a2d34ea900a32d8ae132268292c98bd9244f7":
        raise ValueError("Original component feature/geometry digest differs from the pinned roster")

    current_data = json_bytes("current-location-part-32")
    current_features = find_features(current_data, EXPECTED_CONTACT)
    if len(current_features) != 1: raise ValueError("Current Atlas contact is absent or duplicated")
    current_feature = current_features[0]
    if current_feature.get("properties", {}).get("parent_id") != "atlas:province:IND:d7cc05599eb6":
        raise ValueError("Current contact parent differs from frozen original record")
    hierarchy = json_bytes("current-hierarchy")
    if not find_key(hierarchy, "id", "atlas:province:IND:d7cc05599eb6"):
        # Existing hierarchy records may name the native ID in a parent field; record its absence rather than infer.
        hierarchy_parent_found = False
    else:
        hierarchy_parent_found = True

    scope = json_bytes("original-comparison-scope")
    components_row = json_bytes("original-physical-components", packed=True)
    component_rows = [row for row in components_row if isinstance(row, dict) and row.get("component") == EXPECTED_COMPONENT]
    if len(component_rows) != 1: raise ValueError("Pinned complete comparison input lacks exactly one component row")
    component_row = component_rows[0]
    candidate_set = json_bytes("source-fitness-candidates", packed=True)
    candidate_rows = [row for row in find_key(candidate_set, "component", EXPECTED_COMPONENT)
                      if row.get("family") == "gap-source-batch:f41df3bc72099aca02d08c88" and
                      row.get("operational_batch") == "gap-operational-batch:5d2491ded831bcb754b0fdb3"]
    if len(candidate_rows) != 1:
        raise ValueError("Pinned complete source-fitness row differs from the exact family/component roster")
    admin_observations = candidate_rows[0].get("original_admin_observations", [])
    if len(admin_observations) != 1 or admin_observations[0].get("component") != EXPECTED_COMPONENT or admin_observations[0].get("uniquely_covering_compatible_recorded_subject", {}).get("id") != EXPECTED_CONTACT:
        raise ValueError("Pinned source-fitness row does not bind the unique original component/contact relation")
    component_row_sha = canonical_sha(component_row)
    if len(component_rows) != 1 or component_row.get("family") != EXPECTED_FAMILY_ID or component_row.get("component_geometry_sha256") != "5c68774784a2d75180bd200e2a7a2d34ea900a32d8ae132268292c98bd9244f7" or component_row.get("full_component_feature_sha256") != EXPECTED_COMPONENT_FEATURE_SHA or component_row_sha != "3e2e95f7d9ff4ce6c17ed5f3acf81c35d5b8c44750379f17fd1b027064befa9c":
        raise ValueError("Pinned complete component row differs from the original whole-row/component identity")
    family_row, family_receipt = family_shard_row()
    if (family_row["complete_component_ids"] != [component_row["component"]] or
            family_row["operational_batch"] != candidate_rows[0]["operational_batch"] or
            EXPECTED_COMPONENT not in scope.get("complete_component_ids", []) or
            EXPECTED_FAMILY_ID not in scope.get("complete_family_ids", [])):
        raise ValueError("Original family/component/source-fitness/scope relation differs")
    priority = json_bytes("numeric-source-priority", packed=True)
    priority_rows = find_key(priority, "component", EXPECTED_COMPONENT)
    if len(priority_rows) != 1 or priority_rows[0].get("distinct_contact_ids") != [EXPECTED_CONTACT] or priority_rows[0].get("original_domain_flags", {}).get("touches_reference_shore") is not False:
        raise ValueError("Pinned original priority row/contact/domain flags differ")

    source_geom = shape(selected["geometry"])
    component_geom = shape(component_feature["geometry"])
    current_geom = shape(current_feature["geometry"])
    if not source_geom.is_valid or not component_geom.is_valid or not current_geom.is_valid:
        raise ValueError("One of the three complete Polygon inputs is invalid")
    observed_geometry = geometry_subject_gate(source_geom, component_geom, current_geom)
    source_covers = observed_geometry["source_covers_component"]
    current_covers = observed_geometry["current_contact_covers_component"]
    area_diag = observed_geometry["source_current_symmetric_difference"]
    metrics = {
        "source_covers_component": {"value": source_covers, "unit": "boolean set coverage", "domain": "stored longitude/latitude coordinates; no transformation"},
        "current_contact_covers_component": {"value": current_covers, "unit": "boolean set coverage", "domain": "stored longitude/latitude coordinates; no transformation"},
        "source_current_symmetric_difference": {"value": area_diag, "unit": "square coordinate units (degrees squared)", "domain": "literal stored longitude/latitude; diagnostic only, not ground area"},
        "source_polygon_covers_entire_component": {"value": source_covers, "unit": "boolean set coverage"},
        "source_minus_component_empty": {"value": observed_geometry["source_minus_component_empty"], "unit": "boolean"},
        "component_minus_source_empty": {"value": observed_geometry["component_minus_source_empty"], "unit": "boolean"},
        "source_current_topologically_equal": {"value": observed_geometry["source_current_topologically_equal"], "unit": "boolean"}
    }
    result = {
        "version": 1, "status": "bounded-source-only-diagnostic", "issue": 1392,
        "subject_ids": [EXPECTED_CONTACT], "component_ids": [EXPECTED_COMPONENT],
        "index_sha256": sha(index_bytes), "index_path": str(index_path.relative_to(packet)),
        "closure_freeze_sha256": freeze_sha,
        "frozen_code_sha256": code_inputs,
        "frozen_baseline_inputs": baseline_inputs,
        "frozen_candidate_inputs": candidate_inputs,
        "source_integrity": byte_summary,
        "source_selection": {"shapeID": EXPECTED_SOURCE_ID, "shapeName": "Kakinada (Rural)",
                              "shapeType": selected.get("properties", {}).get("shapeType"),
                              "feature_raw_sha256": byte_summary["selected_raw_feature_sha256"],
                              "feature_canonical_sha256": byte_summary["selected_canonical_feature_sha256"],
                              "feature_digest_matches_retained_record": byte_summary["selected_feature_hash_matches_independent_record"]},
        "source_feature_ids": byte_summary["source_feature_ids_sorted"],
        "source_feature_ids_sha256": sha(json.dumps(byte_summary["source_feature_ids_sorted"], ensure_ascii=False, separators=(",", ":")).encode()),
        "feature_inventory_discrepancy": {"provider_admUnitCount": 6836, "observed_complete_feature_count": byte_summary["feature_count"],
                                           "difference": 14, "status": "unresolved"},
        "context": {"component_feature_id": EXPECTED_COMPONENT,
                    "component_geometry_sha256_as_prior_recorded": component_row.get("component_geometry_sha256"),
                    "component_feature_sha256_as_prior_recorded": component_row.get("full_component_feature_sha256"),
                    "component_original_row_sha256_as_prior_recorded": component_row.get("whole_original_row_sha256"),
                    "component_feature_sha256_recomputed": component_feature_sha,
                    "component_geometry_sha256_recomputed": component_geometry_sha,
                    "component_touches_reference_shore": component_feature.get("properties", {}).get("touches_reference_shore"),
                    "component_water_status": component_feature.get("properties", {}).get("water_status"),
                    "priority_original_domain_flags": priority_rows[0].get("original_domain_flags"),
                    "family_source_fitness_contact_roster": [admin_observations[0]["uniquely_covering_compatible_recorded_subject"]["id"]],
                    "complete_original_family_row": family_receipt,
                    "complete_original_family_members": family_row["complete_component_ids"],
                    "complete_original_family_contacts": family_row["original_fine_family"]["contact_ids"],
                    "complete_original_family_counts": {"component_count": family_row["component_count"], "fine_family_count": family_row["fine_family_count"]},
                    "component_comparison_whole_row_sha256_recomputed": component_row_sha,
                    "current_contact_parent_id": current_feature["properties"].get("parent_id"),
                    "current_parent_found_in_pinned_hierarchy": hierarchy_parent_found,
                    "source_scope_sha256": PINS["original-comparison-scope"][1]},
        "geometry": {"validity": [bool(source_geom.is_valid), bool(component_geom.is_valid), bool(current_geom.is_valid)],
                     "types": [source_geom.geom_type, component_geom.geom_type, current_geom.geom_type],
                     "bounds": [list(source_geom.bounds), list(component_geom.bounds), list(current_geom.bounds)],
                     "metrics": metrics,
                     "measurement_method": "Shapely overlay on complete stored pointsets; no CRS transform, snap or normalization",
                     "limitations": ["coordinate area is diagnostic only, not ground or ellipsoidal area",
                                     "coverage supports source availability/correspondence only, not authority or approval"]},
        "metric_values": {
            "source_covers_component": 1 if source_covers else 0,
            "current_contact_covers_component": 1 if current_covers else 0,
            "source_current_symmetric_difference_coordinate_area": area_diag,
            "source_minus_component_empty": 1 if source_geom.difference(component_geom).is_empty else 0,
            "component_minus_source_empty": 1 if component_geom.difference(source_geom).is_empty else 0,
            "source_current_topologically_equal": 1 if source_geom.equals(current_geom) else 0
        },
        "runtime": runtime_receipt(),
        "bounded_bytes": {"fragment_bodies": index["literal_part_body_bytes"], "max_file": MAX_FILE,
                          "max_total": MAX_TOTAL, "max_descriptors": MAX_DESCRIPTORS,
                          "decoded_whole_file_written": False}
    }
    encoded_result = (json.dumps(result, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(encoded_result)
    return result, sha(encoded_result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", default=str(PACKET))
    parser.add_argument("--result")
    parser.add_argument("--geometry-method-controls", action="store_true")
    args = parser.parse_args()
    if args.geometry_method_controls:
        print(json.dumps({"ok": True, "geometry_method_controls": geometry_method_controls()}, sort_keys=True))
        raise SystemExit(0)
    if not args.result: parser.error("--result is required")
    result, result_sha = run(args.packet, args.result)
    print(json.dumps({"ok": True, "result_sha256": result_sha, "metrics": result["geometry"]["metrics"],
                      "source_integrity": result["source_integrity"], "runtime": result["runtime"]}, sort_keys=True))
