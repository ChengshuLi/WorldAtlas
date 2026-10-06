# Turkey batch 4 acceptance-pin correction (#1088)

This packet corrects one provenance label in the historical acceptance summary from PR #863. The old record placed the frozen macro-region member digest in a field describing the partial 229-member packet. The digest itself is valid for the separate 939-member Anatolia and Eastern Mediterranean envelope. No original file is rewritten, and no geographic boundary is adjudicated.

## Three digest roles

The correction distinguishes three existing hashes rather than repinning any roster:

- **Packet membership digest:** `50597f85cd48e244f864325a474f44013c1212375e977196cfd53812edba9d14`. It is the SHA-256 of the exact 229 scope IDs sorted lexically, joined with line feeds, and encoded as UTF-8 without a trailing line feed. The unchanged `scope.json:/member_location_ids_sha256` and `district-assessments.json:/scope/subject_ids_sha256` both carry this value.
- **Prior evidence-manifest subject digest:** `dfcd4696b6c63deeee2cc1e693537b86afccc9ef3ae873dd2390b143a78e906a`. The original evidence-quality manifest computes this from the compact JSON array of sorted IDs. That field and its convention remain unchanged.
- **Frozen macro-region membership digest:** `c192f338b815c029ea0c8338cbf153686a11bfd5e102d733272417f290ae85eb`. The immutable region envelope identifies this value with `atlas:macro-foundation:region:anatolia-eastern-mediterranean`, which records 939 locations in release version 6 at baseline `cbb829672d18801e4310c30896a7ddb13a79b451`.

The historical `acceptance-review.json:/scope/member_ids_sha256` incorrectly labels the third digest as the packet digest. The corrective receipt at [`corrective-record.json`](corrective-record.json) records the error and the correct field interpretation; the historical acceptance summary remains byte-for-byte intact.

## Reproduction and controls

Run from the repository root with Python 3.12 or compatible Python 3:

```sh
python3 data/regional-review/turkey-229-acceptance-pin-correction-863/reproduce.py
```

The script checks the six exact issue-pinned whole-file hashes, the current issue contract snapshot, the 229 sorted subject IDs and their presence exactly once in `data/geography/part-24.json`, the original packet and assessment digests, the macro-region ID/count/digest association, and all 229 prior `insufficient-evidence` findings. It reads original files only and writes its three result records inside this packet.

- Positive control: the exact 229-ID list reproduces the packet digest and agrees with both packet-specific fields.
- Negative control: substituting the 939-member region digest for the packet digest fails the packet comparison, while that same digest matches the region envelope.
- Two separate script executions produced byte-identical generated result files; the aggregate digests are recorded in [`validation/reproducibility.json`](validation/reproducibility.json).

The input hashes, control outputs, numeric bindings and added-file receipts are in [`evidence-quality.json`](evidence-quality.json). That manifest verifies repository bytes and result relationships; it does not establish geographic truth.

## Source and preservation limits

The issue and PR are repository records for the provenance finding. The exact issue contract/body hash is preserved in `sources/issue-snapshot.json`; the original packet inputs remain at their existing paths and are pinned by whole-file SHA-256 in the manifest. The macro handoff file is read as compressed bytes and decoded in memory. No external legal, statistical or boundary source was restored or newly asserted by this correction.

The original 229 assessments remain insufficient evidence. The previous packet's official-source, legal crosswalk, completeness and source-release follow-ups remain open (#852, #817 and #827). This packet does not complete those reviews, approve Turkey or the region, change release pins, authorize imports, or transfer historical claims.
