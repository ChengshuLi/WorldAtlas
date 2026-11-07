"""Synthetic protocol tests only. No rasterio, raw tiles, network or maps."""

from dataclasses import replace
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sequential_tiles as seq


class BoundedReader(io.BytesIO):
    def __init__(self, data, observations):
        super().__init__(data)
        self.observations = observations

    def read(self, size=-1):
        if not 0 < size <= 7:
            raise AssertionError("non-bounded part read")
        self.observations.append(size)
        return super().read(size)


def fixture():
    values = {
        "gap00.raw": [10, None, 30, 40],
        "gap02a.raw": [1, None, 3, None],
        "gap02b.raw": [None, 2, 9, None],
    }
    sources = []
    part_bytes = {}
    for name, pixels in values.items():
        raw = seq.canonical(pixels)
        split = [raw[:6], raw[6:12], raw[12:]]
        parts = []
        for index, data in enumerate(split):
            key = f"synthetic/{name}/part-{index}"
            part_bytes[key] = data
            parts.append({"key": key, "size": len(data), "sha256": seq.digest(data)})
        manifest = seq.canonical({"full_sha256": seq.digest(raw), "parts": parts,
                                  "method": "ordered synthetic byte chunks"})
        sources.append(seq.Source(name, "synthetic-" + name, "test-only", manifest,
                                  seq.digest(manifest), seq.digest(raw)))
    cases = (
        seq.Case("gap00.mock", ("gap00.raw",),
                 {"mock_cells": 4, "projection": "NONE", "overwrite": "valid pixels only"},
                 seq.digest(seq.canonical(values["gap00.raw"]))),
        seq.Case("gap02.mock", ("gap02a.raw", "gap02b.raw"),
                 {"mock_cells": 4, "projection": "NONE", "overwrite": "valid pixels only"},
                 seq.digest(seq.canonical([1, 2, 9, None]))),
    )
    geometry = {"type": "LineString", "coordinates": [[1, 0], [2, 0], [9, 0]]}
    boundary = seq.canonical(geometry) + b"\n"
    plan = seq.Plan(tuple(sources), cases, seq.digest(boundary),
                    seq.digest(seq.canonical(geometry)), "mock-valid-overwrite-v1",
                    "mock-pixel-list-to-dummy-line-v1", {"selector": "synthetic-only"})
    return plan, part_bytes


class SequentialProtocol(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ural-mock-test-")
        self.root = Path(self.temp.name)
        self.work = self.root / "work"
        self.work.mkdir()
        self.evidence = self.root / "unverified-diagnostics"
        self.evidence.mkdir()
        self.plan, self.parts = fixture()
        self.read_keys = []
        self.read_sizes = []
        self.projected = []
        self.partial = {}
        self.boundary_calls = 0

    def tearDown(self):
        self.temp.cleanup()

    def open_part(self, key):
        self.read_keys.append(key)
        return BoundedReader(self.parts[key], self.read_sizes)

    @staticmethod
    def make_destination(case):
        return [None] * case.grid["mock_cells"]

    def project(self, path, destination, case, source):
        self.projected.append(source.name)
        pixels = json.loads(path.read_bytes())
        for index, value in enumerate(pixels):
            if value is not None:
                destination[index] = value

    @staticmethod
    def encode(destination, case):
        return seq.canonical(destination)

    def boundary(self, outputs):
        self.boundary_calls += 1
        pixels = json.loads(outputs["gap02.mock"])
        geometry = {"type": "LineString", "coordinates": [[x, 0] for x in pixels if x is not None]}
        return seq.canonical(geometry) + b"\n"

    def preserve(self, name, payload, record):
        self.partial[name] = (payload, record)
        (self.evidence / (name + ".partial")).write_bytes(payload)
        (self.evidence / (name + ".status.json")).write_bytes(seq.canonical(record))

    def run_protocol(self, **changes):
        args = dict(plan=self.plan, expected_plan_sha256=seq.plan_sha256(self.plan),
                    work_parent=self.work, open_part=self.open_part,
                    make_destination=self.make_destination, project_mock=self.project,
                    encode_output_mock=self.encode, construct_boundary_mock=self.boundary,
                    preserve_partial_mock=self.preserve, block_bytes=7)
        args.update(changes)
        return seq.run_research(**args)

    def assert_clean_raw(self):
        self.assertEqual(list(self.work.iterdir()), [])

    def assert_failure(self, expected, **changes):
        with self.assertRaisesRegex(seq.IntegrityError, expected):
            self.run_protocol(**changes)
        self.assert_clean_raw()
        for _, record in self.partial.values():
            self.assertFalse(record["complete_replay_verified"])

    def test_happy_path_exact_trace_order_hashes_one_live_tile_and_bounded_reads(self):
        result = self.run_protocol()
        trace = result["trace"]
        self.assertEqual(self.projected, ["gap00.raw", "gap02a.raw", "gap02b.raw"])
        self.assertEqual(trace["source_use_order"], self.projected)
        self.assertEqual(trace["max_owned_raw_sources_at_checks"], 1)
        self.assertEqual(trace["peak_owned_raw_source_bytes"],
                         max(sum(p["size"] for p in json.loads(s.manifest_bytes)["parts"])
                             for s in self.plan.sources))
        self.assertEqual(json.loads(result["artifacts"]["gap02.mock"]), [1, 2, 9, None])
        for source, record in zip(self.plan.sources, trace["sources"]):
            self.assertEqual(record["manifest_sha256"], seq.digest(source.manifest_bytes))
            self.assertEqual(record["pre_use_sha256"], source.full_sha256)
            self.assertEqual(record["post_use_sha256"], source.full_sha256)
            for part in record["parts"]:
                self.assertEqual(part["sha256"], part["observed_sha256"])
                self.assertEqual(part["size"], part["observed_size"])
        self.assertEqual(trace["status"], "synthetic_checks_passed")
        self.assertFalse(trace["geographic_accuracy_verified"])
        self.assertFalse(trace["existing_gate_contract_satisfied"])
        self.assertTrue(trace["independent_review_and_real_data_test_required"])
        self.assertLessEqual(max(self.read_sizes), 7)
        self.assert_clean_raw()

    def test_manifest_exact_bytes_not_just_json_semantics_are_pinned(self):
        source = replace(self.plan.sources[0], manifest_bytes=self.plan.sources[0].manifest_bytes + b" ")
        self.plan = replace(self.plan, sources=(source, *self.plan.sources[1:]))
        self.assert_failure("manifest byte pin mismatch")
        self.assertEqual(self.read_keys, [])

    def test_manifest_full_source_identity_must_match_external_pin(self):
        source = replace(self.plan.sources[0], full_sha256="0" * 64)
        self.plan = replace(self.plan, sources=(source, *self.plan.sources[1:]))
        self.assert_failure("full-source identity")
        self.assertEqual(self.read_keys, [])

    def test_full_source_hash_checked_even_when_all_part_hashes_pass(self):
        source = self.plan.sources[0]
        obj = json.loads(source.manifest_bytes)
        obj["full_sha256"] = "0" * 64
        raw = seq.canonical(obj)
        source = replace(source, manifest_bytes=raw, manifest_sha256=seq.digest(raw),
                         full_sha256="0" * 64)
        self.plan = replace(self.plan, sources=(source, *self.plan.sources[1:]))
        self.assert_failure("concatenated full-source SHA-256 mismatch")
        self.assertEqual(self.projected, [])

    def test_truncated_part_fails_before_any_projection(self):
        first = next(iter(self.parts))
        self.parts[first] = self.parts[first][:-1]
        self.assert_failure("truncated part")
        self.assertEqual(self.projected, [])

    def test_extra_part_bytes_fail(self):
        first = next(iter(self.parts))
        self.parts[first] += b"x"
        self.assert_failure("overlong part")

    def test_same_size_corrupt_part_fails(self):
        first = next(iter(self.parts))
        self.parts[first] = b"x" + self.parts[first][1:]
        self.assert_failure("part SHA-256 mismatch")

    def test_part_order_swap_fails(self):
        keys = list(self.parts)
        self.parts[keys[0]], self.parts[keys[1]] = self.parts[keys[1]], self.parts[keys[0]]
        self.assert_failure("part SHA-256 mismatch")

    def test_duplicate_part_key_rejected_before_reads(self):
        source = self.plan.sources[0]
        obj = json.loads(source.manifest_bytes)
        obj["parts"][1]["key"] = obj["parts"][0]["key"]
        raw = seq.canonical(obj)
        source = replace(source, manifest_bytes=raw, manifest_sha256=seq.digest(raw))
        self.plan = replace(self.plan, sources=(source, *self.plan.sources[1:]))
        self.assert_failure("duplicate manifest part")
        self.assertEqual(self.read_keys, [])

    def test_source_pre_use_readback_detects_post_download_corruption(self):
        original = seq._measure_file
        changed = False
        def corrupt_before_measure(path, size):
            nonlocal changed
            if path.name == "gap00.raw" and not changed:
                changed = True
                path.write_bytes(b"corrupted local storage")
            return original(path, size)
        with mock.patch.object(seq, "_measure_file", side_effect=corrupt_before_measure):
            self.assert_failure("pre-use full-source readback mismatch")
        self.assertEqual(self.projected, [])

    def test_post_use_source_mutation_fails_and_preserves_unverified_output(self):
        def mutate(path, destination, case, source):
            self.project(path, destination, case, source)
            path.chmod(0o600)
            path.write_bytes(b"same-user accidental mutation")
        self.assert_failure("post-use full-source integrity", project_mock=mutate)
        payload, record = self.partial["gap00.mock"]
        self.assertEqual(json.loads(payload), [10, None, 30, 40])
        self.assertEqual(record["status"], "unverified_partial")
        self.assertFalse(record["source_post_use_hash_passed"])
        self.assertTrue((self.evidence / "gap00.mock.partial").is_file())

    def test_local_inode_substitution_even_with_same_bytes_fails(self):
        def substitute(path, destination, case, source):
            self.project(path, destination, case, source)
            payload = path.read_bytes()
            old = path.with_name(path.name + ".old")
            path.rename(old)
            path.write_bytes(payload)
            old.unlink()
        self.assert_failure("post-use full-source integrity", project_mock=substitute)

    def test_gap02_reversal_fails_output_pin(self):
        case = replace(self.plan.cases[1], source_names=("gap02b.raw", "gap02a.raw"))
        self.plan = replace(self.plan, cases=(self.plan.cases[0], case))
        self.assert_failure("raster-output byte hash mismatch")
        self.assertEqual(self.boundary_calls, 0)
        self.assertEqual(json.loads(self.partial["gap02.mock"][0]), [1, 2, 3, None])

    def test_mid_case_network_failure_preserves_prior_unverified_state(self):
        def failing_reader(key):
            if "gap02b.raw" in key:
                raise OSError("synthetic transport failure; no retry")
            return self.open_part(key)
        with self.assertRaisesRegex(OSError, "synthetic transport failure"):
            self.run_protocol(open_part=failing_reader)
        self.assert_clean_raw()
        self.assertEqual(json.loads(self.partial["gap02.mock"][0]), [1, None, 3, None])
        self.assertFalse(self.partial["gap02.mock"][1]["complete_replay_verified"])
        self.assertEqual(self.boundary_calls, 0)

    def test_projector_exception_preserves_partial_destination(self):
        def crash(path, destination, case, source):
            destination[0] = 999
            raise RuntimeError("synthetic projector failure")
        with self.assertRaisesRegex(RuntimeError, "synthetic projector failure"):
            self.run_protocol(project_mock=crash)
        self.assert_clean_raw()
        self.assertEqual(json.loads(self.partial["gap00.mock"][0]), [999, None, None, None])
        self.assertEqual(self.partial["gap00.mock"][1]["status"], "unverified_partial")

    def test_final_file_hash_fails_without_success_and_retains_candidate(self):
        self.assert_failure("final-boundary file hash", construct_boundary_mock=lambda _: b"bad boundary")
        self.assertEqual(self.partial["synthetic-boundary.json"][0], b"bad boundary")

    def test_final_canonical_hash_separately_checked(self):
        self.plan = replace(self.plan, boundary_geometry_sha256="0" * 64)
        self.assert_failure("canonical geometry hash")
        self.assertIn("synthetic-boundary.json", self.partial)

    def test_plan_pin_rejects_changed_order_before_read(self):
        old_pin = seq.plan_sha256(self.plan)
        case = replace(self.plan.cases[1], source_names=("gap02b.raw", "gap02a.raw"))
        self.plan = replace(self.plan, cases=(self.plan.cases[0], case))
        self.assert_failure("research plan pin mismatch", expected_plan_sha256=old_pin)
        self.assertEqual(self.read_keys, [])

    def test_plan_mutation_during_callback_fails_final_check(self):
        def mutate_plan(path, destination, case, source):
            self.project(path, destination, case, source)
            self.plan.static_input_pins["selector"] = "changed"
        self.assert_failure("plan/code/runtime changed", project_mock=mutate_plan)

    def test_preexisting_files_not_deleted_on_failure(self):
        sentinel = self.work / "preexisting-project-artifact"
        sentinel.write_bytes(b"do not alter")
        first = next(iter(self.parts))
        self.parts[first] = b"short"
        with self.assertRaises(seq.IntegrityError):
            self.run_protocol()
        self.assertEqual(sentinel.read_bytes(), b"do not alter")
        self.assertEqual(list(self.work.iterdir()), [sentinel])

    def test_duplicate_source_use_rejected(self):
        case = replace(self.plan.cases[1], source_names=("gap02a.raw", "gap02a.raw"))
        self.plan = replace(self.plan, cases=(self.plan.cases[0], case))
        self.assert_failure("each source must occur exactly once")
        self.assertEqual(self.read_keys, [])

    def test_extra_raw_file_from_projector_is_rejected_after_callback(self):
        def create_extra(path, destination, case, source):
            self.project(path, destination, case, source)
            (path.parent / "untracked.raw").write_bytes(b"unexpected allocation")
        self.assert_failure("owned raw scratch directory mismatch", project_mock=create_extra)
        self.assertEqual(self.projected, ["gap00.raw"])
        self.assertEqual(self.partial["gap00.mock"][1]["status"], "unverified_partial")

    def test_extra_raw_file_from_diagnostic_sink_is_rejected(self):
        current = []
        def remember(path, destination, case, source):
            current[:] = [path]
            self.project(path, destination, case, source)
        def create_extra(name, payload, record):
            self.preserve(name, payload, record)
            (current[0].parent / "sink-extra.raw").write_bytes(b"unexpected")
        self.assert_failure("owned raw scratch directory mismatch", project_mock=remember,
                            preserve_partial_mock=create_extra)
        self.assertEqual(self.projected, ["gap00.raw"])

    def test_extra_file_in_owned_scratch_root_is_rejected(self):
        def create_sibling(path, destination, case, source):
            self.project(path, destination, case, source)
            (path.parent.parent / "root-extra.raw").write_bytes(b"unexpected")
        self.assert_failure("owned raw scratch directory was replaced", project_mock=create_sibling)
        self.assertEqual(self.projected, ["gap00.raw"])

    def test_pre_unlink_directory_check_rejects_extra_file_after_post_hash(self):
        original = seq._measure_file
        source_hashes = 0
        def extra_after_hash(path, size):
            nonlocal source_hashes
            result = original(path, size)
            if path.name == "gap00.raw":
                source_hashes += 1
                if source_hashes == 2:
                    (path.parent / "post-hash-extra.raw").write_bytes(b"unexpected")
            return result
        with mock.patch.object(seq, "_measure_file", side_effect=extra_after_hash):
            self.assert_failure("owned raw scratch directory mismatch")
        self.assertEqual(self.projected, ["gap00.raw"])

    def test_extra_raw_file_created_after_unlink_blocks_next_source(self):
        original = Path.unlink
        inserted = False
        def add_after_unlink(path, *args, **kwargs):
            nonlocal inserted
            result = original(path, *args, **kwargs)
            if path.name == "gap00.raw" and not inserted:
                inserted = True
                (path.parent / "between-sources.raw").write_bytes(b"unexpected")
            return result
        with mock.patch.object(Path, "unlink", new=add_after_unlink):
            self.assert_failure("owned raw scratch directory mismatch")
        self.assertEqual(self.projected, ["gap00.raw"])

    def test_final_callback_cannot_leave_extra_raw_file_and_get_success(self):
        current = []
        def remember(path, destination, case, source):
            current[:] = [path]
            self.project(path, destination, case, source)
        def create_extra(outputs):
            (current[0].parent / "late-extra.raw").write_bytes(b"unexpected")
            return self.boundary(outputs)
        self.assert_failure("owned raw scratch directory mismatch", project_mock=remember,
                            construct_boundary_mock=create_extra)

    def test_returned_trace_and_canonical_evidence_do_not_alias_original_plan(self):
        self.plan.cases[0].grid["nested"] = {"dimensions": [4, 1]}
        self.plan.static_input_pins["nested"] = {"labels": ["baseline"]}
        result = self.run_protocol()
        trace_before = seq.canonical(result["trace"])
        canonical_before = result["trace_canonical_json"]
        self.plan.cases[0].grid["nested"]["dimensions"].append(99)
        self.plan.static_input_pins["nested"]["labels"].append("changed")
        self.assertEqual(seq.canonical(result["trace"]), trace_before)
        self.assertEqual(result["trace_canonical_json"], canonical_before)
        self.assertEqual(seq.digest(canonical_before.encode()), result["trace_sha256"])
        self.assertEqual(seq.digest(seq.canonical(result["trace"]["plan"])),
                         result["trace"]["plan_sha256"])
        self.assertEqual(result["trace"]["outputs"][0]["grid"]["nested"]["dimensions"], [4, 1])
        # Even convenience dict branches are independent; canonical evidence
        # remains immutable if a consumer deliberately edits that dict.
        result["trace"]["plan"]["cases"][0]["grid"]["nested"]["dimensions"].append(100)
        self.assertEqual(result["trace"]["outputs"][0]["grid"]["nested"]["dimensions"], [4, 1])
        self.assertEqual(result["trace_canonical_json"], canonical_before)
        self.assert_clean_raw()

    def test_reserved_boundary_artifact_name_rejected_before_source_reads(self):
        case = replace(self.plan.cases[0], name=seq.BOUNDARY_ARTIFACT)
        self.plan = replace(self.plan, cases=(case, self.plan.cases[1]))
        self.assert_failure("reserved boundary artifact name")
        self.assertEqual(self.read_keys, [])

    def test_resource_claim_is_explicitly_limited_to_owned_source_checks(self):
        trace = self.run_protocol()["trace"]
        self.assertIn("protocol-owned raw sources", trace["resource_accounting_scope"])
        self.assertIn("not arbitrary callback disk, memory", trace["resource_accounting_scope"])
        self.assertNotIn("peak_transient_raw_bytes", trace)
        self.assertNotIn("max_live_raw_tiles", trace)


if __name__ == "__main__":
    unittest.main(verbosity=2)
