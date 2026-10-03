# Western Polynesia frozen baseline and source path correction

**Issue:** [#619](https://github.com/ChengshuLi/WorldAtlas/issues/619)
**Parent review:** #134; merged evidence PR #617.
**Ownership:** `research/geography/western-polynesia-evidence-pins/` only.

## Superseding reproduction notice

This campaign supersedes the provenance and frozen-input validation behavior of `data/regional-review/regional-review-a5b86fc6ff2463cd/build_baseline_extract.py` and `verify_packet.py`. It preserves their committed outputs, row-by-row assessments, sources and screens unchanged. It does not replace those assessments, finish unresolved source/shoreline research, certify the regional interior, or enable imports.

The old builder searched all geography parts and correctly inlined all 24 assigned features, but discarded the actual containing paths. It reconstructed the path list from `feature.properties.part`, which is absent on all 24 features and therefore defaulted to `data/geography/part-0.json`. That file’s recorded byte count and hash are valid, but it contains none of the assigned IDs. Against the packet’s exact baseline commit, the authoritative `data/world-index.json` path inventory locates the IDs uniquely in three files:

| Frozen source path | Assigned subjects | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| `data/geography/part-23.json` | 5 Tonga ADM1 locations | 4,962,410 | `d61082ccd69b319723fadc4cad582b8d5c8a8ced3e50b4f90f00b4eb17e6a9c2` |
| `data/geography/part-24.json` | 8 Tuvalu ADM1 locations | 4,816,899 | `b816b89f2d6b9e4aed1bca44748e1ca74e775a8f850793c7b3e8751d88a9705c` |
| `data/geography/part-28.json` | 11 existing locations: American Samoa (5), Wallis and Futuna (3), Niue (1), Samoa (1), and the Tokelau source unit (1) | 6,613,963 | `2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d` |

Every assigned ID resolves exactly once. The canonical feature digest is SHA-256 of UTF-8 `json.dumps(feature, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`; the raw containing-file digest hashes exact Git blob bytes. The name, parent ID, geometry type and complete location-to-continent parent chain are recorded for each ID in `baseline-source-crosswalk.json`. All 24 inlined features in the original baseline extract exactly match the feature stored at the reconstructed path in the frozen source commit.

## Frozen baseline and release-pin reconciliation

The preserved baseline extract and assessment both name `dd83dcad2ec486b89844a78e5e137935b101c167` (commit time 2026-10-03 15:39:25 UTC). That historical commit is intentionally distinct from current main. The preserved #134 issue snapshot was updated at 15:42 UTC; its recorded release-5 values match the data at the baseline commit. Reproduction never refreshes or overwrites the original baseline from a newer checkout.

The exact 24 issue subjects and their SHA-256 over sorted IDs joined by newline (no trailing newline) match the original issue scope and extracted subjects. The release ID/version, hierarchy SHA-256, footprint SHA-256 and macro-certificate SHA-256 match across the preserved issue scope, certificate, publication verification and research gate. The frozen region row, compressed envelope bytes, decompressed geometry hash and current-membership inventory independently reproduce the issue’s frozen region and member pins.

The original workload has 24 assigned subjects. The complete frozen region membership has 25: `atlas:macro-coverage:location:a0457f0d44c94b71f00d` is the additional region member, outside #134’s 24-ID workload. The assigned 24 remain a subset of that region. This is an expected difference between a bounded issue scope and a full current region, not a pin mismatch. The previous issue scope release remains archived in the original body; the current active scope is release v5 and is what the verifier validates.

`baseline-source-crosswalk.json` records and the verifier reopens all 36 paths in the frozen `world-index.json` (including empty-of-scope candidate files), proving each assigned ID occurs once. It includes byte counts and SHA-256 for every source input it verifies: the original baseline-file list, all actual containing feature files, world index, hierarchy, semantic report, current inventory and projection, regional handoffs, macro certificate, v5 region envelope, publication verification and research gate. It also inventories and pins every file in the preserved #134 evidence directory (including issue snapshot, baseline extract, assessments, screens, scripts, manifests and retained sources) at PR #617’s merge commit. These hashes allow future clones to verify immutable Git objects without checking out or changing that old baseline.

## Reproduction and negative checks

Run these commands from the repository root in a clone with the relevant history available:

```sh
python research/geography/western-polynesia-evidence-pins/build_packet.py
python research/geography/western-polynesia-evidence-pins/verify_packet.py
python research/geography/western-polynesia-evidence-pins/test_negative_cases.py
```

The builder validates all input paths, hashes, exact IDs, feature identities, parent chains and release pins before writing the new output. It refuses to overwrite an existing output; an intentional new baseline requires a separately versioned campaign and recomputation of dependent assessments/screens. The verifier is read-only. It checks Git object identity as well as recorded SHA-256/byte counts, and re-scans every index-listed source file to detect duplicate or missing assigned IDs.

The negative-check command actually performed five rejection checks:

1. Appending bytes to a frozen source input fails the committed SHA/size check.
2. The builder rejects changed baseline bytes before creating an output file.
3. Pointing a Tonga ID at the valid but non-containing `part-0.json` fails feature identity/content validation.
4. Changing the preserved issue’s release ID fails comparison with the certificate.
5. The builder rejects that issue/release mismatch before creating an output file.

The new ledger accounts for 18 preserved parent-packet files, 46 frozen baseline/release inputs (including all 36 indexed geography files), and 24 subject/parent-chain rows. The preserved PR #617 baseline, assessments and screens remain the authorities for the original review. This campaign corrects the reproducibility and provenance ledger only. It makes no geography, hierarchy, ownership, grid, approval, certificate, historical, application or live-data changes.
