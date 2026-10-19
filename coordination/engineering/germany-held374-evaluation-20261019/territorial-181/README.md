# Germany territorial-exclusion 181-key evidence packet

This standalone packet preserves the exact territorial-exclusion held runs and all raw whole-target feature-contact rows from the pinned source-evidence and provenance artifacts.

## Reconciliation

- The held ledger uses half-open runs `[x_start_inclusive, x_end_exclusive)`. The territorial-exclusion partition is 181 keys in 141 runs over 22 pixel indices.
- The source-evidence artifact contributes 23 target/atom rows for those pixel indices, including two distinct atoms for pixelIndex 5755. Joined to retained whole-target exclusions, these yield 163 raw contact rows.
- The provenance artifact yields the same 163 rows. Full row comparison matches across atom ID, target ID, pixel index, source ID, feature ordinal, negative ordinal, and geometry SHA256.
- There are 162 unique `(pixelIndex, source_id)` pairs. The repeated pair is pixelIndex 5755 / `gb:CHE:ADM1:70761945B73326014959541`, feature ordinal 19, geometry SHA256 `8866b671526a4192adce3ade13d1ca5d2dc12a683a01763d3895b0552ab77360`. It appears under two atom rows for the same multipart target; both raw provenance rows are preserved.
- Family totals are recorded in the JSON as both raw row totals and de-duplicated pixel/source pair totals.

## Scope and limits

The contact records are whole-target geometry evidence retained in the pinned artifacts. They are not per-cell intersections and cannot show that each of the 181 held cells individually intersects a listed feature. They do not establish current source applicability, source vintage adequacy, legal or current boundary status, sovereignty, source authority, or repair eligibility. This evidence packet assigns no repair credit and does not change the issue or PR state.

## Pinned inputs

See `territorial-181.json` for exact refs, paths, Git blob IDs, and content SHA256 hashes.
