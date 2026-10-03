# Offline installation of three reference hierarchy corrections

Issue #6, second permitted PR, worker `engineering-hierarchy-crosswalk-a9c25e14-20261003`. The actual same reservation was rotated after PR673 merged; `reservation-renewal.json` retains the accepted bot result. Original immutable data baseline is `277b8ecbb3199ae3d5fb07bab96353d17a049b1c`; concurrent storage PR671 and typed integration PR677 are incorporated intact without changing the original data baseline.

The reviewed correction retains Monaco/Luxembourg area identities and names, consolidates Hancock into the existing West Virginia province, and preserves the retired province with its exact reference record and explicit same-tier merge. The complete original identity/source chronology is replayed through prior-v4/prior-v5 archives. Existing registered definitions, historical claims, source bytes and published releases remain preserved. No new location or factual assertion is introduced.

## Reconstruct from committed inputs

Use Node24, Python3.12 and the committed requirements in an isolated environment. Outputs must be fresh external directories; replace the example paths if they already exist. Once this PR installs the candidate in Git, reconstruct from the retained original baseline in a separate detached worktree. This is an offline reproduction of this same job, not a second branch/writer or live operation. The old baseline-specific 49,589-location preparer is not used.

```sh
atlas_source_root=$(pwd)
git worktree add --detach /tmp/atlas-correction-baseline 277b8ecbb3199ae3d5fb07bab96353d17a049b1c
git archive HEAD scripts src | tar -x -C /tmp/atlas-correction-baseline
cd /tmp/atlas-correction-baseline
python scripts/rebase-reference-hierarchy.py --request "$atlas_source_root/data/engineering/hierarchy-crosswalk-20261003-a9c2/baseline-request.json" --output /tmp/atlas-correction-crosswalk
python scripts/verify-hierarchy-install-baseline.py --inventory "$atlas_source_root/data/engineering/hierarchy-install-20261003-a9c2/baseline-inventory.json.gz" --receipt /tmp/atlas-correction-baseline.json
node scripts/prepare-hierarchy-correction-release.mjs --candidate /tmp/atlas-correction-crosswalk --output /tmp/atlas-correction-release
node scripts/prepare-hierarchy-correction-install.mjs --candidate /tmp/atlas-correction-crosswalk --release /tmp/atlas-correction-release --stage /tmp/atlas-correction-install
```

Full historical proof replay invokes the existing geographic creation validators and therefore needs the pinned Python dependencies. Use the isolated environment's Python on `PATH` and set `ATLAS_PYTHON` to that interpreter. Initial adapter field-name and missing-dependency failures are recorded in the execution checkpoint; they are not counted as passing validation. Intermediate stage logs remain distinct vintages. Final publisher-integrated generation, including source-assessment/profile composition and pending-publication flags, reproduced894 complete files twice with validation SHA-256 `1cd3329cc68bb3914b59416c2854e75d4082892e7a2c6491738e6808e308bd0b`. The earlier source-assessment-only `a89fc808b6a44366224b6e7f9b476a85a445df19e51c3d2d7fe16914b322fad0` vintage remains separately retained. All2,941 protected payloads and56 ownership buffers matched their original bytes. Five current-v5 assessment objects are retained exactly. The full installed projection passed inventory/provenance consistency for49,625 locations and5,733 groups; this is not semantic approval. Initial893-file output and failed intermediate generations remain separate vintages.

## Evidence and approval limits

`baseline-inventory.json.gz` has3,307 exact whole-file descriptors. `baseline-verification.json` verifies each committed blob and checkout byte with the shared immutable preparation helper, split into ten bounded partitions without raising limits. Compressed identity-proof archives preserve whole-file bytes; replay separately hashes every safely extracted member. A larger archive's aggregate expansion is not represented as a single bounded JSON input.

The offline install composes both existing producer receipts through their actual archived predecessor bytes, retaining migration chronology and source/record/interval bytes. Existing legacy detached projection hashes remain explicitly limited; their archived `prior_revalidation` links govern the preserved generations. It does not assign dated memberships or transfer historical claims.

The new open membership projection preserves current-v5 individual source assessments and its pinned owner-profile context. Some older archived projections omitted assessments; those vintages remain archived, and are not reclassified as new inspections or retroactively declared compliant. Unknown/unspecified owners stay unknown/unspecified. All newly emitted projections promise and validate retention of unchanged-location assessments.

Macro compatibility proves all116 existing macro identities, memberships, geometry fingerprints and envelope bytes unchanged. Approval remains the original reporting-convention approval. Candidate certificate/publication state is explicitly pending, including database-release readback=false, with no new semantic, source-completeness, physical-precision or regional approval. All regional location-attribute imports remain closed. Original certificate, review, handoff, gate and publication receipts retain their archived vintages.

This checkpoint has a reversible installation in the author's isolated checkout and no live installation or publication. Exhaustive prepared data, local Chromium inspector chains/map modes and static/hosted packaging passed. Local checks do not verify served assets or physical mobile hardware. The first broad suite recorded630/638 passing: one coverage-profile regression, one old proposal-state assumption, four missing packaged migration derivatives during concurrent build and two credential controls rejecting this managed environment's `/tmp/.git` marker. The corrected broad run passed638 of640 tests; only the two credential-environment failures remained and were reproduced against the unchanged baseline. Later publisher-integrated focused checks are separate; no full-suite pass is claimed. Credential protections stay intact.

Exact-head independent review, required CI and serialized accepted merge still precede publisher handoff. The designated publisher must recheck actual served release and serialize release/Site verification, including preserved claims and archive readback. Use a partial issue reference until complete acceptance is actually verified; if publication requires scope beyond the two-PR budget, propose bounded coordinator-reviewed follow-ups.

The complete generation is larger than one512-descriptor evidence contract. Repository evidence rules allow reviewed partitioning. Planned voluntary aggregate evidence binds bounded manifests and exact union of changed-file receipts; it will explicitly verify descriptor count, byte limits, baseline/original hashes and every preservation file. The current legacy queue does not automatically enforce this aggregate contract; do not claim it does. Final independent review must inspect every partition and unique hash.

## Reviewed partition method for this legacy scope

Thousands of literal hashes exceed GitHub's single-comment body limit. The independently assessed voluntary method binds individually bounded manifests, exact changed-file assignments, complete baseline/preservation inventories and a root manifest that hashes the partition index. Each partition runs the existing trusted descriptor, byte, change-accounting and method checks without raising their limits. The executed index must match the bound bytes; omitted changes or protected candidate payloads reject.

Independent review uses subordinate `worldatlas-review-partition:v1` comments with standard receipt fields validated against each partition's actual files/hashes. One coherent final comment contains a `worldatlas-review:v1` receipt explicitly scoped to the bounded root manifest and a `worldatlas-review-aggregate:v1` index binding every subordinate manifest, exact PR head, same distinct reviewer, comment URL and actual body SHA-256. All linked comments must be read and validated; subordinate comments do not accumulate as ordinary latest-worker receipts. An edited body or changed head invalidates the aggregate.

This is an explicitly reviewed voluntary extension for legacy #6, not automatic queue enforcement or a substitute for an adopted whole-PR contract. The root-only standard receipt does not represent all-PR machine enforcement. All source, geometry, release, approval and publication limits remain. The active #627 worker owns enforcement rollout; this job does not change its policy, issue contract or shared review documentation.

```sh
node scripts/validate-evidence-partitions.mjs coordination/engineering/hierarchy-install-20261003-a9c2/partitions.json EXACT-PR-BASE HEAD
node scripts/validate-evidence-partition-review.mjs ACTUAL-PR-NUMBER coordination/engineering/hierarchy-install-20261003-a9c2/partitions.json
```

## Complete generation controls

Repeat the install preparation into a second fresh stage, then run:

```sh
node scripts/verify-hierarchy-install-generation.mjs --one /tmp/atlas-correction-install --two /tmp/atlas-correction-install-two --data /tmp/atlas-correction-baseline/data --receipt /tmp/atlas-correction-reproducibility.json
node scripts/check-hierarchy-install-controls.mjs
```

The meaningful scoped suite has45 passing tests, including38 named negative/preservation scenarios. Positive/negative typed receipts bind the actual log bytes; full generation proof binds every raw output, not only sampled catalog rows. New release/macro and owned evidence outputs use the shared Python canonical encoding; existing projection/archive producers retain their established encodings. Two-run proof compares actual bytes of both kinds.

## Regeneration disk and failure preservation

One later second generation failed when the managed8.8GiB temporary filesystem filled. Its log and complete partial whole-file inventory remain in this owned job; it is not counted as a passing run. `regeneration-disk-cleanup.json` records removal of only explicitly named, regenerable offline stages after preserving their reports. Original sources, crosswalk/release inputs and other workers' artifacts were preserved. Subsequent full runs use fresh external workspace-storage directories. `generation-code-inventory.json` pins the exact scripts and JavaScript dependencies copied to the immutable before-data checkout; separately tested non-generation tools are explicitly listed.

Current publisher-integrated verification passed45 preservation controls,46 typed-runtime/release tests, pinned-Python hosted packaging and fresh actual local Chromium checks. Complete local package inventory records546 output whole-file hashes; these are local derivatives, not served publication receipts. Reservation renewal run37154493208 failed because trusted-main sparse checkout omits `src/regional-import-gate.js`; canonical claim remains active. Publisher/627 coordination must repair authoritative Actions before renewal/merge; no bypass or repeated unchanged retry.
