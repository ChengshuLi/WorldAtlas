# Central India whole-input admission assessment — 2026-10-08

This packet answers the operating-limit question in #1497. It is an additive admission guard and a bounded refusal audit. It does not reproduce or approve the Central India geography analysis.

## Finding

At immutable data commit `950eb2188e5b66d88ea47a679936a02fe3eb1c40`, the 55 complete unique encoded inputs in the retained run ledger were individually retrieved from Git and matched against their declared sizes and SHA-256 values. They total **238,931,443 bytes**. The retained source is **13,794,274 bytes** compressed. Its gzip footer and ten prior chunk receipts both state **40,040,002 decoded bytes**. Those two historical size records agree, but they do not authenticate the decoded content, CRC, or full decoded digest.

The minimum complete input operation is therefore `238,931,443 + 40,040,002 = 278,971,445` bytes, **10,535,989 bytes above** the 256 MiB phase limit (268,435,456 bytes), before any output reservation or completion receipt. The single decoded source body is **6,485,570 bytes above** the 32 MiB per-file limit. The assessment also reads the exact seven output names from the pinned runner and reserves each at the 32 MiB file ceiling, plus the 4,096-byte receipt. The resulting conservative complete-phase reservation is **513,856,565 bytes**. The installed runtime closure is still incomplete. The full original run was refused before source decompression or analysis.

The assessment records the exact 229-subject, 35-province partial scope: Madhya Pradesh 144/422 and Uttar Pradesh 85/244. This confirms scope custody only. It does not validate the source’s legal boundaries or hierarchy.

## Implementation and controls

`admission.py` provides a fail-closed complete-operation planner. It counts exact logical identities once only when duplicate descriptors agree, retains distinct identities even when bytes hash identically, requires an expected inventory when supplied, counts decoded bodies and output reservations in the same phase, and refuses missing authentication, per-file overflow, incomplete runtime closure or total overflow. `decode_gzip_bounded` stops at limit plus one byte and does not return a partial body as success.

`run_controls.py` executes the actual admission entrypoint with synthetic bounded fixtures covering below/at/above the body limit, compressed-small/decoded-large data, combined source and geography inputs, duplicate identity behavior, output-inclusive overflow, missing descriptors, incomplete runtime, descriptor conflicts and an existing-output collision. The collision control executes the exact `NewVintage` helper bytes pinned at commit `950eb2188e5b66d88ea47a679936a02fe3eb1c40` in a disposable repository and confirms the existing sentinel bytes survive.

`preflight.py` rechecks all 55 immutable Git blobs, the exact scope partition, the retained execution ledger, gzip footer and chunk-receipt byte sum. It reads the compressed source bytes for hashing and footer inspection only. It never decompresses them. The resulting `admission-assessment.json` is a refusal receipt, not a successful science run.

`guarded_reproduce.py` is the packet's refusal-only command for operators. It refreshes and preserves the same admission receipt, and exits successfully with `status=refused` while the complete source closure is over limit. It never launches the historical reproduction runner. If the input plan were later admitted, this packet still refuses to run because it contains no reviewed geography producer with a complete runtime and output closure.

Reproduce from repository root:

```sh
python3 research/geography/central-india-admission-1339-20261008/run_controls.py
python3 research/geography/central-india-admission-1339-20261008/preflight.py
python3 research/geography/central-india-admission-1339-20261008/guarded_reproduce.py
node scripts/evidence-quality.mjs research/geography/central-india-admission-1339-20261008/evidence-quality.json
node scripts/check-handoff-scope.mjs --issue-file /tmp/worldatlas-1497-issue.json --pr-body-file /tmp/worldatlas-1497-pr-body.txt
```

The PR should use exactly `Closes #1497` after the issue's admission criteria and review gates pass. That closes only the bounded operating-limit work item; PR #1339 remains Incomplete, and this packet does not certify the underlying region.

## Engineering handoff

The retained runner must not be represented as a complete bounded reproduction while it admits 4 MiB decoded chunks into a separate source `Baseline` and later creates outputs with only the geography `Baseline`. A future owner should integrate a single complete input/output/runtime reservation before any body parsing or output creation, or report a refusal if a complete lawful method still exceeds the configured limits. That owner must preserve all original packets, IDs, source vintages and successful receipts. Source clipping, renaming chunks as separate bodies, or raising limits to force admission would not repair the evidence gap.

## Source and geographic limits

The preserved 2018 geoBoundaries ADM3 source is described by publisher metadata as Sub-District. Its metadata was updated 2023-01-19 and built 2023-12-12; the existing manifest records source retrieval on 2026-10-06. The metadata asserts ODbL 1.0; independent legal confirmation is not claimed. Retained receipts report 6,822 features while metadata declares 6,836. The discrepancy, effective current legal polygons, parent relationships, source completeness, license obligations and neighboring-tier correspondence remain unresolved. The gzip footer and old chunk receipts are size evidence only: RFC 1952 defines ISIZE as a modulo-2^32 value and includes a separate CRC32 trailer field ([RFC Editor, RFC 1952](https://www.rfc-editor.org/rfc/rfc1952.html)). No decoded source body, full source hash, CRC, refreshed upstream response, geometry overlay or historical comparison was run for this packet.
