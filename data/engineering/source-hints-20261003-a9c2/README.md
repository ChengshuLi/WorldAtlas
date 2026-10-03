# Supplemental source-profile instruction repair

Issue [554](https://github.com/ChengshuLi/WorldAtlas/issues/554), worker `engineering-continuous-a9c25e14-20261003`, baseline `58a4f380c99bb2bcbae5df021acb1881245cbba9`. GitHub holds current progress and canonical reservations; these files preserve reproducible inputs and receipts.

The original eight supplemental issues (520–527) advertise 34 distinct entries. Their entry digests all match the retained source-profile array. The broken pointer is an instruction error; source loss is not established. Exact original issue responses are retained in `issues-before/`; their bodies, dates, completion state, work contracts, owned paths and release/subject pins are preserved by the repair plan. No other worker's evidence directory is edited.

The correct artifact is `data/reference-migrations/macro-improvements-v4/queue-checkpoint/new-location-source-profiles-v4.json.gz`:

- Compressed whole-file SHA-256: `f13cb0b2a023c5bce5abdb3223f99148685961d4608b4acb81c3c2ea800d680e`.
- Uncompressed whole-file SHA-256: `b1f86acef46ac0c4fd04c275774294809b89eef2ae1d656a78c2e0ba4980167b`.
- Each original `full_source_profile_canonical_sha256` is an **entry** digest: select exactly one record by `location_id`, then hash Python sorted compact UTF-8 JSON without a trailing newline (`ensure_ascii=False`, `allow_nan=False`). It is neither whole-file digest.

The Inaccessible Island entry (`atlas:island:geonames:3370905`) retains digest `9b4939f3ae40a17866f2e082dd804b72ae57f778148beab10c7673474fe8a36e`. Every advertised entry is verified, not just this example.

The earlier planner remains immutable inside `queue-checkpoint/reproduction.tar.gz`; its portable planner SHA-256 is `12c98e76dc5fee75e82c86b7e8952dda9a7f579880f4397d8f8e5447a70af2d0`. It generated the obsolete `data/macro-foundation/` pointer. The new planner is a bounded post-planning instruction repair, not a rerun of historical geography preparation or an overwrite of that archive. Apply it to reconstructed hints before using the old planner's output as current instructions.

## Reproduce and inspect

```sh
python scripts/repair-supplement-source-hints.py --baseline 58a4f380c99bb2bcbae5df021acb1881245cbba9 --issues data/engineering/source-hints-20261003-a9c2/issues-before --out /tmp/new-source-hint-plan.json
python test/supplement-source-hints.py
node --test test/supplement-source-hints.test.mjs
```

The output path must be new. The shared immutable-baseline helper verifies actual committed source bytes before planning. `repair-plan.json` and an independent second run have identical SHA-256 `a6a1fab3f329cb82751847db6338656b86cf5a21ecc5a1b62a95be9ddf011d55`. Positive/negative controls cover entry/file/newline distinction, Unicode, duplicate/missing subjects, bad source pins, unexpected pointers, unrelated field/prose changes, active workers/PRs, stale concurrent body changes, idempotency and failed readback journals. Fixtures are synthetic, not geographic evidence.

The apply helper defaults to **read-only** preflight:

```sh
node scripts/apply-supplement-source-hints.mjs data/engineering/source-hints-20261003-a9c2/repair-plan.json a6a1fab3f329cb82751847db6338656b86cf5a21ecc5a1b62a95be9ddf011d55 /tmp/new-source-hint-preflight.json
```

Only the confirmed issue-554 holder may execute its authorized body repairs with `--apply` and a fresh owned receipt path. Preserve all original inputs first. The helper checks the entire target batch before any write, then rereads canonical reservations, linked PRs and body hashes immediately before each write. It changes body only, verifies state/labels/assignees and exact readback, and journals settled writes. A failed or partial run is not completion; inspect the receipt and current GitHub bodies before retrying. Replan changed instructions rather than overwriting another worker's edits. New plans need review and a new receipt/vintage.

## Limits and retained failures

This repairs pointers and hash terminology only. No source inspection, historical assertion, geographic migration/approval, Site publication or import permission follows from a matching hash. All complete-regional import gates remain in force. The source artifact and archived planner remain byte-identical.

Initial restricted Node test execution and an incomplete synthetic claim fixture failed and are retained separately. The first actual read-only preflight also failed because a JavaScript serialization-order comparison mistook differently ordered object keys for changed scope; it wrote nothing. The guard now compares object values independently of key order, with a regression control. Successful control/preflight receipts are separate from failed attempts. GitHub application/readback and final merge records belong to the linked issue and owned receipts.

Final GitHub readback verified all eight bodies and all 34 entries; rerunning the planner against `issues-after/` changes zero rows. A transient HTTP 503 stopped the first apply after five verified writes; its partial journal is retained. A fresh guarded replay skipped those five and settled the remaining three. PR 551 clarification: https://github.com/ChengshuLi/WorldAtlas/pull/551#issuecomment-5972760328. These receipts establish instruction correction, not source truth or live publication.
