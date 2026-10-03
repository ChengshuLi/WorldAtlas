# Release 4: capacity gate and resume

The candidate has passed offline migration proofs. It is not published. The current installed geography and the three published releases remain unchanged.

The authorized read-only preflight measured 481,394,688 database bytes at revision 1754 against a configured 536,870,912-byte budget. This leaves 55,476,224 bytes. The configured budget has not been verified as the actual Neon plan quota. The subsequent official-pricing check in `capacity-plan-update.json` found that the Free plan now advertises **1 GB per project**. The old512MiB guard is not that provider allowance; a conservative800MB guard accommodates the modeled626MB post-import total without a paid upgrade. This does not turn the model into a physical growth measurement or verify account-specific/branch totals.

| New database rows | Count |
| --- | ---: |
| Stable entities | 42 |
| Reference sources | 1 |
| Geographic releases | 1 |
| Geographic memberships | 84,831 |
| Geographic changes | 768 |
| Bounded ingestion receipts, at most | 434 |

Existing entity IDs do not make the memberships duplicates: their primary key includes the new release ID. The publisher checks the already published baseline release and skips its 425 import batches (45,750,980 JSON bytes). The new reviewed payload remains 92,935,927 bytes.

The prepared memberships contain 89,452,281 bytes of uncompressed text, including 66,815,557 bytes of evidence. Their three B-tree indexes add storage too. A rough model of tuple headers, fields, alignment and page packing produces 144,127,810 bytes for the new heap/index data. This is a model, not a measurement. Almost all modeled membership rows are below PostgreSQL's usual 2 KiB TOAST threshold, so gzip transport or repeated evidence does not establish that the database will fit.

Use `capacity-assessment.json` for assumptions, exact prepared row counts, immutable input hashes and read-only SQL suggestions. `capacity-preflight.json` retains the authorized earlier capacity receipt without credentials. Recheck `/api/storage/capacity` and the storage marker immediately before an import. Verify the provider plan, and measure actual table, index and TOAST sizes through an authorized database path. The Site has no arbitrary-SQL endpoint; do not add one to inspect storage. Raising an application budget alone does not create provider capacity.

Reproduce this offline assessment from the same pre-release checkout:

```sh
python3 scripts/assess-geographic-release-capacity.py \
  --root "$PWD" \
  --release /tmp/worldatlas-macro-candidate/geographic-release \
  --capacity-receipt data/macro-improvements/combined-restoration/capacity-preflight.json \
  --output /tmp/worldatlas-capacity-assessment.json
```

Once storage is available, resume the root publication issue using the pinned candidate rather than re-researching or rebuilding source identities. Replay or safely extract `installation-proof.tar.gz`, verify its container and member hashes, and retain the separate reference metadata receipt. The installer receives the current-baseline replacement→creation descriptor. The full geographic release additionally uses the original repair and all prior metadata receipts in their explicit chronology.

Finish and preserve the grid, source-area and macro-envelope checks, ownership/reference applicability archives, derived unknown intervals for changed/new land, matched runtime/static assets and installer validation receipt before import. Then stage the exact release batches, check completeness and content hashes, and publish the matching assets and geographic release together under the established publication procedure. Recheck original historical claims and previously published releases afterwards. Geographic research issue scopes may be repinned only to the final published release/grid/envelope hashes.

If verified storage cannot support the release safely, preserve these artifacts and report the publication blocker. Infrastructure expansion, partitioning and map performance work belong to their separate engineering issues. Do not delete old releases, existing facts or source evidence to make this release fit.
