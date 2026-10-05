#!/usr/bin/env node
"use strict";

// Offline reproducibility, issue-scope, retained-byte and semantic-limit checks.
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const zlib = require("node:zlib");
const {spawnSync} = require("node:child_process");
const ROOT = __dirname;
const REPO = path.resolve(ROOT, "../../..");
const read = (name) => fs.readFileSync(path.join(ROOT, name));
const json = (name) => JSON.parse(read(name));
const sha = (bytes) => crypto.createHash("sha256").update(bytes).digest("hex");
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const requireExactRoster = (actual, expected) => {
  if (!Array.isArray(actual) || !eq(actual, expected)) throw new Error("exact issue roster mismatch");
};
const requireHash = (bytes, expected) => {
  if (sha(bytes) !== expected) throw new Error("whole-file hash mismatch");
};

const scope = json("issue-scope-pinned.json");
const receipt = json("baseline-receipt.json");
const assessment = json("assessment.json");
const provinces = json("province-assessments.json");
const handoffs = json("findings-and-handoffs.json");
const coverage = json("coverage-screen.json");
const claimRenewal = json("reservation-renewal.json");
const reviewIndex = json("evidence-review-index.json");
assert(scope.location_count === 229 && scope.member_location_ids.length === 229, "wrong issue subject count");
assert(new Set(scope.member_location_ids).size === 229, "duplicate issue subject IDs");
requireExactRoster(scope.member_location_ids, scope.member_location_ids);
assert(eq(assessment.rows.map((r) => r.subject_id), scope.member_location_ids), "assessment roster/order differs from pinned issue scope");
assert(assessment.source_member_count === 229 && provinces.province_count === 31 && provinces.assigned_province_members === 229, "assessment/province totals differ from scope");
assert(eq(receipt.current_release, scope.release), "baseline receipt release differs from issue pins");
assert(claimRenewal.accepted === true && claimRenewal.claim_id === "e28683e2-1b80-4bb4-8fa6-d2f33d07c254" && claimRenewal.expires_at === "2026-10-06T00:21:27.144Z" && claimRenewal.live_work === false, "serialized reservation renewal receipt mismatch");
assert(reviewIndex.issue === 473 && reviewIndex.baseline_commit === receipt.baseline_commit && reviewIndex.exact_subject_count === 229 && reviewIndex.region_release.macro_certificate_sha256 === scope.macro_certificate_sha256, "review index issue/scope/release binding mismatch");
for (const item of reviewIndex.changed_files_excluding_this_index) {
  const bytes = fs.readFileSync(path.resolve(REPO, item.path));
  assert(bytes.length === item.bytes && sha(bytes) === item.sha256, `review index byte receipt mismatch: ${item.path}`);
}
assert(assessment.publication_v5_release.id === scope.release.id && assessment.macro_certificate_sha256 === scope.macro_certificate_sha256, "assessment release/certificate differs from issue pins");

const packedBaseline = read("baseline-members.geojson.gz");
assert(sha(packedBaseline) === receipt.compressed_sha256 && packedBaseline.length === receipt.compressed_bytes, "retained baseline gzip checksum/length mismatch");
const rawBaseline = zlib.gunzipSync(packedBaseline);
assert(sha(rawBaseline) === receipt.uncompressed_sha256 && rawBaseline.length === receipt.uncompressed_bytes, "restored baseline bytes mismatch");
const baseline = JSON.parse(rawBaseline);
assert(baseline.features.length === 229 && eq(baseline.features.map((f) => f.id), scope.member_location_ids), "retained baseline feature roster mismatch");
assert(sha(Buffer.from(scope.member_location_ids.join("\n") + "\n")) === receipt.member_roster_sha256_lf_separated, "member roster digest mismatch");

const register = json("sources/register.json");
for (const source of register.sources) {
  const compressed = read(path.relative(ROOT, path.join(ROOT, source.retained_gzip_path)));
  const restored = zlib.gunzipSync(compressed);
  assert(sha(compressed) === source.retained_gzip_sha256, `${source.country_code} compressed ADM2 hash mismatch`);
  assert(sha(restored) === source.original_sha256 && restored.length === source.original_bytes, `${source.country_code} restored ADM2 hash/length mismatch`);
  const parentPath = path.relative(ROOT, path.join(ROOT, source.adm1_source.retained_gzip_path));
  const parentZip = read(parentPath);
  const parentRaw = zlib.gunzipSync(parentZip);
  assert(sha(parentZip) === source.adm1_source.retained_gzip_sha256, `${source.country_code} compressed ADM1 hash mismatch`);
  assert(sha(parentRaw) === source.adm1_source.sha256 && parentRaw.length === source.adm1_source.bytes, `${source.country_code} restored ADM1 hash/length mismatch`);
}
const ecoReceipt = json("sources/resolve-query-receipt.json");
const ecoGzip = read(path.relative(ROOT, path.join(ROOT, ecoReceipt.retained_gzip_path)));
const ecoRaw = zlib.gunzipSync(ecoGzip);
assert(sha(ecoGzip) === ecoReceipt.retained_gzip_sha256, "RESOLVE compressed hash mismatch");
assert(sha(ecoRaw) === ecoReceipt.response_sha256 && ecoRaw.length === ecoReceipt.response_bytes, "RESOLVE restored response hash/length mismatch");
assert(JSON.parse(ecoRaw).features.length === 5, "RESOLVE query did not return the five recorded ecoregions");

const statuses = assessment.rows.reduce((out, row) => (out[row.individual_status] = (out[row.individual_status] || 0) + 1, out), {});
assert(eq(statuses, {"correction-needed":56,"insufficient-evidence":173}), "unexpected evidence classification totals");
assert(assessment.rows.every((r) => r.parent_chain.length >= 3 && r.parent_chain[r.parent_chain.length - 1].name === "Africa"), "a subject parent chain is incomplete or leaves the continent context");
assert(assessment.rows.every((r) => r.adm1_source_point_agrees_with_atlas_parent_name === true), "one or more ADM1 representative-point screens failed; investigate rather than waive");
const physical = assessment.rows.filter((r) => r.subject_kind === "ecoregion portion");
assert(physical.length === 17, "ecological portion subject count mismatch");
assert(physical.every((r) => r.source_geometry_measurement_role.includes("not the ecological portion") && r.source_feature_geometry_screen && r.representative_point_in_resolve_ecoregion === true), "ecological source/measurement role is ambiguous or point screen failed");
assert(physical.every((r) => r.individual_status === "correction-needed"), "ecological role findings not preserved");
assert(assessment.rows.every((r) => r.completeness.startsWith("Not established:")), "a structural screen was misrepresented as completeness proof");
assert(handoffs.engineering_handoffs.length === 4 && handoffs.findings.length === 4, "bounded follow-up inventory mismatch");
for (const handoff of handoffs.engineering_handoffs) assert(handoff.subject_ids.length > 0 && new Set(handoff.subject_ids).size === handoff.subject_ids.length, `invalid handoff roster: ${handoff.id}`);
assert(eq(Object.fromEntries(handoffs.engineering_handoffs.map((h) => [h.id, h.github_issue])), {"physical-ecoregion-role":801,"liberia-2022-crosswalk":802,"mali-post-2023-crosswalk":803,"mauritania-current-crosswalk":804}), "follow-up issue links differ from the registered handoffs");
assert(handoffs.engineering_handoffs.every((h) => h.status === "blocked"), "a source follow-up was incorrectly made ready before its parent packet");
assert(coverage.subject_count === 229 && coverage.city_and_parent_granularity_candidates.length === 4, "coverage-category screen incomplete");
assert(coverage.repeated_tier_and_large_unit_candidates.count === 2 && coverage.name_and_anonymous_remainder_screen.candidate_count === 0, "unexpected name or scale screen results");
assert(coverage.unassessed_completeness.length >= 4, "unresolved completeness limits missing");

// Negative controls: altered roster and altered evidence bytes must fail exact-byte/scope checks.
let changedRosterRejected = false;
try { requireExactRoster(scope.member_location_ids.slice(1), scope.member_location_ids); }
catch (error) { changedRosterRejected = error.message === "exact issue roster mismatch"; }
assert(changedRosterRejected, "negative roster control was not rejected by the exact-roster validator");
const corrupted = Buffer.from(ecoGzip); corrupted[corrupted.length - 1] ^= 1;
let corruptRejected = false;
try { requireHash(corrupted, ecoReceipt.retained_gzip_sha256); }
catch (error) { corruptRejected = error.message === "whole-file hash mismatch"; }
assert(corruptRejected, "negative source-byte corruption control unexpectedly passed");

// Two full independent builder executions must reproduce identical whole-file results.
const outputPaths = ["assessment.json", "province-assessments.json", "scale-screens.json", "baseline-members.geojson.gz", "baseline-receipt.json", "sources/register.json"];
const hashOutputs = () => Object.fromEntries(outputPaths.map((p) => [p, sha(read(p))]));
const first = hashOutputs();
for (let run = 0; run < 2; run++) {
  const result = spawnSync(process.execPath, [path.join(ROOT, "build_assessment.cjs")], {cwd: REPO, encoding: "utf8"});
  assert(result.status === 0, `builder run ${run + 1} failed: ${result.stderr || result.stdout}`);
  assert(eq(first, hashOutputs()), `builder run ${run + 1} changed a whole-file result`);
}
console.log(JSON.stringify({result:"passed",subjects:229,provinces:31,statuses,physical_portions:physical.length,followups:handoffs.engineering_handoffs.length,retained_sources_verified:register.sources.length+1,reproducible_runs:2,negative_controls:{changed_roster_rejected:true,corrupted_source_rejected:true},limits:["Point screens are not polygon overlays.","Administrative source inventories do not establish completeness.","No regional approval, boundary change, publication or import is performed."]},null,2));
