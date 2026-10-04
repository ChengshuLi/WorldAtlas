# Issue #486 deterministic baseline reproduction

This is a superseding reproduction packet for [issue #605](https://github.com/ChengshuLi/WorldAtlas/issues/605). It repairs the #486 baseline-extract method. It does not change the original #486 packet, its 211-subject assessment, any source bytes, shared geography, regional certification or historical imports.

## Finding and immutable inputs

The original packet is preserved at source snapshot [`276d72e1f316ad58d52c8fea7974a873c2ec9387`](https://github.com/ChengshuLi/WorldAtlas/commit/276d72e1f316ad58d52c8fea7974a873c2ec9387). Its first parent, [`0ea5b92969a37e404daded7a5c1d8931bd74b19c`](https://github.com/ChengshuLi/WorldAtlas/commit/0ea5b92969a37e404daded7a5c1d8931bd74b19c), is the project baseline used for the original extraction. The exact 211-ID scope and current issue #605 contract are captured in `scope.json`.

The old extractor called `gzip.open(..., "wb")` without fixing gzip metadata. The preserved feature and parent-chain archives both have gzip mtime `1791033028` (`2026-10-03T13:10:28Z`) and their generated filenames in the header. A later identical run therefore changes compressed hashes. The extractor also read mutable checkout files and wrote directly over those archives and the receipt without verifying input hashes first.

The correction reads ordinary Git blobs only. It pins the historical world index and all 36 indexed parts, `data/hierarchy.json`, current membership inventory, macro certificate, envelope index and frozen region envelope at the exact evaluation commit. It reads every ordinary file in the original packet at the exact source snapshot commit, checks the 24 retained source file byte/hash rows against `sources.json`, and verifies the original extract receipt and archive hashes before constructing output. All 211 IDs must occur exactly once in the indexed parts. Their actual containing paths, complete parent chains, province/area memberships, hierarchy/macro pins and frozen region geometry/member pins are recorded in `baseline-source-crosswalk.json`.

## Canonical new-vintage outputs

The two files under `vintages/20261004-canonical-gzip/` are new artifacts. They use the shared `worldatlas-evidence-preparation-v1` serializer and gzip helper: sorted-key compact UTF-8 JSON with one newline, gzip level 9, an empty filename, mtime 0 and fixed OS header 255. The receipt records compressed and uncompressed byte counts and SHA-256 values for both new artifacts and the preserved originals. Parsed contents match the original snapshots. Because canonical key ordering differs from the original insertion-order JSON, the new uncompressed hashes are identified separately; they are not presented as the originals' uncompressed byte stream.

The original compressed archives, their uncompressed payloads, source registry, source files, assessment and all 211 identities remain unchanged in the source snapshot. The source inventory carries canonical references, source vintages/dates, source roles, recorded licenses, retained file hashes and restoration instructions from the original README and `sources.json`. No external source was downloaded or re-adjudicated for this compression repair. The original issue packet notes that the national TIGER county archive and raw GSHHG archive/member were omitted; their saved hashes and restoration URLs remain unchanged. The International Boundary Commission reuse-language tension and the scale/role limits for the other sources remain unresolved as recorded.

## Reproduction

From the repository root, the default command is read-only. It rebuilds twice from immutable Git objects and checks the saved new vintage without overwriting anything:

```sh
python3 data/regional-review/regional-review-93f8f3bee8e205be/superseding-reproduction-605/build_packet.py --check
python3 data/regional-review/regional-review-93f8f3bee8e205be/superseding-reproduction-605/test_negative_cases.py
python3 data/regional-review/regional-review-93f8f3bee8e205be/superseding-reproduction-605/verify_packet.py
node scripts/evidence-quality.mjs data/regional-review/regional-review-93f8f3bee8e205be/superseding-reproduction-605/evidence-quality.json
```

An explicit new-vintage creation uses exclusive writes and refuses an existing target:

```sh
python3 data/regional-review/regional-review-93f8f3bee8e205be/superseding-reproduction-605/build_packet.py --create --vintage 20261004-canonical-gzip
```

Negative controls retain their actual results in `negative-control-results.json`. They check changed issue scope, changed commits, changed whole-file pins, changed source registry rows, missing/duplicate subjects, deterministic headers, failed-pin-before-output and exclusive overwrite refusal. No command in this correction invokes the old extractor or mutates the original packet.

## Limits

This packet verifies the archived baseline reproduction and makes its compressed output repeatable. It does not recreate the geographic assessment from external source archives, re-evaluate county/settlement/ecoregion findings, prove island/coastline completeness, resolve the Alaska–Canada boundary screen, infer political ownership, or decide source licenses beyond preserving the earlier source-role and reuse statements. Original findings requiring source or integration follow-up remain unchanged. This is not regional approval or import authority.
