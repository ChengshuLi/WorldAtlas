# Issue #614 — protected #485 baseline reproduction

This directory supersedes the unsafe baseline extraction procedure identified in issue #614. It is a reproduction/provenance correction, not a new geographic assessment. It leaves all 222 source conclusions, the shared baseline, geometry, hierarchy, grid, approval state, and historical records unchanged.

## Immutable vintages

| Role | Commit | Commit date (UTC) | Use |
| --- | --- | --- | --- |
| Source geography baseline | `276d72e1f316ad58d52c8fea7974a873c2ec9387` | 2026-10-03 13:44:09 | The parent commit of PR #610. All geography, hierarchy, release pins, membership inventory, and part files are read from this commit. |
| Original packet and artifact snapshot | `39188aadf6efdae60357d9d4a1bbb62ffd981003` | 2026-10-03 15:00:27 | The #610 merge commit, containing the pinned `scope.json`, original two extract archives, original receipt, source manifest, issue metadata, and source packet. |
| Correction start main | `5bcd4273d81d7bcc6537330fbf6a39481745db74` | 2026-10-03 | Fresh `origin/main` when #614 work began. This is not relabeled as the geography input baseline. |

The exact 222 member IDs, issue metadata, region release, frozen region geometry/member hashes, macro-certificate hash, and owned packet prefix are pinned separately in `correction-spec.json`. The source baseline's hierarchy SHA, canonical-grid hierarchy/footprint pins, macro-certificate bytes, regional handoff envelope, membership inventory, world-index, and all 36 geography parts are each bound by byte count and SHA-256. Gzip source inputs also record expanded byte counts and hashes. The issue/scope snapshot is distinct from the earlier source baseline.

## Original evidence preservation

The original `sources/current-scope-and-parents.geojson.gz`, `sources/current-parent-chains.json.gz`, `baseline-extract-receipt.json`, `sources-manifest.json`, and the rest of the original source packet are read from commit `39188...` and checked against their exact recorded bytes. The source manifest lists 40 original source artifacts, including the retained Census, TIGER, Statistics Canada, AAFC, NRCan, GNIS, GSHHG-derived data and the IBC restoration receipt. The reproduction controls verify all 45 distinct retained source/artifact files remain byte-identical to their pinned snapshot; the parent packet README is deliberately amended with safe run instructions, while its original bytes remain pinned and read from the immutable artifact commit. No source artifact is copied, modified, re-licensed, refreshed, or deleted by this correction.

The legacy extractor's original behavior is retained for audit only. It has no immutable source pins, follows current `world-index.json`/parts/membership/hierarchy, overwrites the two historical output paths, and updates its receipt without reconciling the source manifest. Do not run it. The original archives and manifest values remain historical evidence; the corrected generated files below have different paths and a separate manifest rather than replacing those values.

## Corrected reproduction

The verifier reads only immutable Git objects. Before opening an output path, it validates every declared input byte/hash, the exact issue/scope snapshot, v5 hierarchy and footprint pins, macro-certificate hash/research-only flag, frozen WNA envelope, and all original packet/source hashes. It scans every part enumerated by `data/world-index.json`; each of the 222 IDs must be found exactly once. It verifies complete parent chains against both the pinned membership inventory and hierarchy and requires their identities to agree.

The reconstructed compact UTF-8 JSON bytes match the original archives' uncompressed SHA-256 and byte counts exactly. The new gzip files use separate names with MTIME 0, XFL 2, OS 255, raw DEFLATE level 9 and standard CRC-32/ISIZE trailer. Python 3.12.14 and zlib 1.3.2 are pinned in the spec; a different runtime fails closed before writing. The generated `deterministic-reproduction-manifest.json` contains compressed and uncompressed byte counts and hashes for each new file, exact scope/release pins, scan accounting and links to the original archives.

Run from the repository root, using the pinned runtime:

```sh
python data/regional-review/regional-review-4254da254d94f450/reproduction-correction-614/reproduce.py
python data/regional-review/regional-review-4254da254d94f450/reproduction-correction-614/reproduce.py --check
python data/regional-review/regional-review-4254da254d94f450/reproduction-correction-614/verify_controls.py
```

Generation is exclusive and cannot replace existing output. `--check` recomputes all inputs and outputs from the pinned commits and compares exact bytes. The controls cover positive output, two independently written identical runs, changed-baseline rejection before destination creation, changed-output rejection in check mode, overwrite refusal, and unchanged hashes for all 48 original packet/source files. Their recorded results are in `control-results.json`.

## Source dating, licensing and limits

This correction adds no external source and makes no new claims about administrative identity, settlements, political ownership, physical boundaries, or source completeness. The official source references, retrieval/source dates, licenses, lawful retained bytes or IBC restoration instructions, methods, and uncertainty are already documented in the parent packet's [source and license section](../README.md) and `sources-manifest.json`; both are retained unchanged. The deterministic output reproduces the original extraction content only. Source citations or inherited decisions are not independently revalidated here.

The original packet was merged by PR #610. This correction links to the parent/regional integration issues #485/#488. Completion of #614 does not approve the Western North America regional branch or enable location-attribute research imports; outstanding #606–#609 follow-ups remain separate.
