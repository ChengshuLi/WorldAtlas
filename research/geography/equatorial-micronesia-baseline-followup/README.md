# Issue #661: immutable Equatorial Micronesia extract

This is a reproduction and provenance repair for the three subjects in the preserved #140 packet. It does not reassess administrative geography, propose a location edit, approve the region, or enable imports. The original packet and its conclusions remain byte-for-byte at source commit `dd83dcad2ec486b89844a78e5e137935b101c167`; the corrected extract is a separate dated vintage.

## Immutable inputs and scope

The builder reads only Git objects from geometry baseline `39188aadf6efdae60357d9d4a1bbb62ffd981003` and original packet snapshot `dd83dcad2ec486b89844a78e5e137935b101c167`. It checks the active v5 release, hierarchy and macro-certificate pins from the original issue scope, preserving the archived v3 release separately. It hashes and scans all 36 files listed by the frozen world index, resolves actual containing files, requires each of the three exact IDs once, and verifies the complete parent chains, membership rows and projection against the preserved extract. Inputs are validated before output creation.

The original source receipt includes geoBoundaries KIR and NRU administrative profiles. Original retained bytes and descriptors are checked against the frozen source manifest. The KIR 2020 census, KIR 2022 census atlas, Nauru 2021 census report, and GSHHG 2.3.7 archive were restored to temporary storage and matched exactly to the original receipt sizes and SHA-256 values; none is retained here because reuse rights were not established (the GSHHG archive also remains restoration-only). No workbook input appears in either original source inventory. `external-source-verification.json` records canonical URLs, dates, byte descriptors and limits. Census/profile vintages are evidence references, not assertions of current legal boundaries or political ownership.

## Reproduction

From the repository root:

```sh
python3 research/geography/equatorial-micronesia-baseline-followup/build_packet.py --check
python3 research/geography/equatorial-micronesia-baseline-followup/build_packet.py --check --vintage 20261003-pinned
python3 research/geography/equatorial-micronesia-baseline-followup/build_packet.py --create --vintage 20261003-pinned
python3 research/geography/equatorial-micronesia-baseline-followup/verify_packet.py
python3 research/geography/equatorial-micronesia-baseline-followup/test_negative_cases.py
node scripts/evidence-quality.mjs research/geography/equatorial-micronesia-baseline-followup/evidence-quality.json
```

`--check` is the default and never writes. `--create` requires a new explicit vintage and refuses to overwrite. Re-running a full check independently constructs and compares both payloads. Controls also test invalid commit/descriptor, absent or duplicate subjects, the actual containing-part mapping, and exclusive output. See `vintages/20261003-pinned/` for the extract and receipts.

## Findings preserved, not re-decided

The original assessment's unresolved Nauru district/alias mapping and Kiribati component crosswalk remain unresolved. This follow-up corrects provenance mechanics only; it does not make a new physical-geography or administrative conclusion. Its limit is the evidence and bytes already cited by the original packet. A full regional review and engineering integration remain separate work.
