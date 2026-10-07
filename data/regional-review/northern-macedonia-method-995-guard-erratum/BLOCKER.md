# Durable checkpoint — issue #1237 evidence-gate conflict

Recorded 2026-10-06 (America/Los_Angeles). Author worker: `01a10947-7d6e-7ba2-98a1-a9f91dedabfc`. Claim: `ffdc507b-b08a-4bb4-aab7-36154b7116ad`. Branch: `geography/north-macedonia-guard-1237-20261006`, allocated from fresh main `c9bd47774b1ea8216d9cd4608ce2a20e15a2962b`.

## Completed, scoped work

- `guarded_reproduce.py` authenticates all 30 original source/input files from immutable Git blobs, the previous runner and its self-pin, and the full code of the original decoder, geometry helper and ellipsoidal helper at the actual module loader boundary. It publishes only by exclusive open beneath the issue-owned prefix, with traversal and symlink-parent refusal.
- Two actual separate-process runs in `controls/` reproduce both retained 21,617-byte reports exactly (SHA-256 `d3d23c61368d3db4fb5acf049cfaff9f3533a1da7c37c5b96d02070d50b3fef3`). The exact contract roster of 84 IDs and its eight open, read-only Atlas parent contexts are enumerated in `scope-audit.json`. The previous Atlas representation report is separately referenced, not recomputed.
- Eleven negative controls reject traversal, an absolute output, a symlink parent escaping to the old packet, full geometry/ellipsoidal/decoder code drift, wrong descriptor/input bytes, old runner/pin drift, and current runner pin drift. Existing-output sentinel and old packet reports remain byte-identical. Full synthetic code fixtures and observed outputs are retained.
- `SOURCES.md` records per-source roles, dates, license uncertainty, exact retained hashes/restoration instructions, official SSO neighboring granularity, per-subject name/parent context, and a narrowly scoped engineering handoff. It does not claim legal boundary validity, complete territory coverage, license clearance, or regional approval.

## Blocking repository contract mismatch

The issue contract declares 46 exact immutable input pins across two commits: `b6cfaada43a1e0472cd833d16733d1fd6065eaec` and `31ad959c0c91d4b0495a0de2c79b05f5d6861e11`. Every declared hash is valid at its declared commit. The shared premerge evidence format requires one `baseline.commit` for every `baseline.files` descriptor and every `baseline.pins` binding.

At the later commit, 45 pins match but `data/geographic-releases/current-manifest.json` is `5bffef7aa5cf7f3256d648674ed66b4293ba545097bd9c32d85d8987cedc5178`; the issue expressly requires preserving the earlier `85075dd4eceebf5bc8e7b554fb4e1573aed2c5baae546ca21746643852c55b81` bytes from `b6cfaada43a1e0472cd833d16733d1fd6065eaec`. At the earlier commit the 16 successor evidence files pinned from #1213 do not exist. No single baseline tree can satisfy the declared pin set. This is not a failed geographic reproduction and is not evidence drift: the issue correctly says the later legitimate release-manifest advancement must not replace the earlier pin.

The normal PR gate therefore cannot produce a truthful `evidence-quality.json` for this exact contract under the current single-commit baseline schema. Do not alter the old release pin, omit it, fabricate an alias, or bypass the queue. No PR was opened and no review/merge/closure was requested. The issue's one-PR budget remains unused.

## Resume conditions and next steps

1. Ask the evidence-contract maintainers to support per-file immutable commit bindings (or another reviewed representation that preserves every declared pin and the legitimate later release state).
2. Keep the work contract's b6 release-manifest pin and the #1213 evidence pins unchanged while that support is added. Re-run readiness and the trusted evidence/premerge validator afterward.
3. Resume this branch, produce and validate the issue-bound manifest/change receipts, then open one focused PR. Obtain a distinct substantive exact-head implementation/source/geometry review and use the serialized merge queue.
4. Preserve the documented source/licensing, legal-date, parent-role and regional-approval limits. Do not close #1237 until its full guard acceptance is reviewed and verified.

Current packet files are limited to `data/regional-review/northern-macedonia-method-995-guard-erratum/`. No core geography, production data, original source archive, release pin, or previous worker artifact was changed.
