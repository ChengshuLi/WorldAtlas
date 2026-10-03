# Read-only v5 macro metadata preparation

`prepare.mjs` refreshes the existing bottom-up macro certificate using completed source-backed integration, geographic release 5 and independently verified parent envelopes. It never changes live geography, installs data, imports facts, approves regional interiors or publishes a Site. Do not execute its full-world preparation concurrently with other heavy preparation jobs; the coordinator schedules that execution.

```sh
node --max-old-space-size=4096 data/macro-improvements/loose-ends-v5/macro/prepare.mjs \
  --root /workspace/WorldAtlas \
  --geography /tmp/worldatlas-v5-integrated/creation \
  --release-index /tmp/worldatlas-v5-integrated/geographic-release/index.json \
  --envelopes /tmp/worldatlas-v5-envelopes \
  --integration /tmp/worldatlas-v5-integrated \
  --output /tmp/worldatlas-v5-macro-candidate
```

The fresh output contains archived byte-identical `prior-v4/` certificate, decisions, review index, regional handoffs and membership inventory; refreshed candidate equivalents; and `preparation-receipt.json` with exact predecessor/new hashes. Original continental inspections and policy profiles stay intact. Macro names, IDs, parent links and conventions must remain the same: **6 continents, 29 subcontinents, 81 regions, 116 macro units**. Candidate membership/envelopes must account for exactly **49,625 locations**, three retained footprint corrections, two genuine additions and no historical transfer.

Every membership and footprint fingerprint is recalculated from locations, then compared with the independently checked envelope and release pins. Only finite reviewed land changes are accepted. Kingman Reef updates its existing named route; Gardner Pinnacles receives an explicit route and joins its already fixed Hawaiian family routes. Reviewed Manuae, Aitutaki and Chagos identities update their existing routes. Stale v4 route references are corrected: Manuae is `COK-4951`, Aitutaki is `COK-4956`, and `COK-4956` is removed from Palmerston's named reference list. Original erroneous routing remains archived; this is not a historical name assertion or an identity migration.

Candidate status is explicitly **publication pending**, with regional interiors/import readiness false. The source summary pins the inspected integration artifact and carries underlying source URLs/hashes; its temporary proof archive must be durably retained before publication. Existing geographic conventions remain approved in their original scope; the new installed coverage and grid are not declared verified until installer and live publication checks finish. Global shoreline completeness and surveyed physical-divide accuracy are not asserted.

The separate `installer-macro-receipt.json` satisfies the installer's macro pass contract: exact source-repair receipt hash, no historical transfer, all candidate IDs as geometrically unchanged by this membership pass, and counts for all six tiers. Those footprints can differ from v4 through the separately validated source stage. `preparation-receipt.json` remains the metadata audit receipt.

Light verification performed: JavaScript syntax passed; all 116 current v4 macro names/identities/parents pass the frozen-convention check; changed-name and changed-parent fixtures are rejected. Full-world candidate generation is deliberately not claimed before the coordinator provides completed v5 release/envelope proofs and schedules execution.
