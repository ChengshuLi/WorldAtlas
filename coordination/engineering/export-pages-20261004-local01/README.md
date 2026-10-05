# Compact V4 export request budget repair

Issue #872 preserves the existing raw logical export contract while grouping
private catalog metadata SELECTs into ordered read-only PostgreSQL transactions.
The metadata SQL, guards, catalog hashes, private privileges, canonical cursors,
page byte bounds and fresh catalog checks at both ends remain unchanged.
Unbatched owner/native callers keep their existing default. An adapter without
batch support falls back to the original ordered reads. A failed transaction
rejects the export; it does not fall back to unchecked metadata.

The focused regression reproduces an external-request-budget failure in the
unbatched path and verifies an identical successful page in the batched path.
It compares every SQL statement count, exports first/intermediate/final pages,
and exercises invalid cursors, column privilege exposure, disabled guards,
transaction failures and privilege changes between page reads. Existing tests
cover both frozen base contracts, every original logical collection, restricted
app-role access, raw-text preservation and bounded interruption/resume.

Read-only diagnostics against current native Neon with the existing restricted
app role additionally verified byte-identical first media pages and complete
media paging. The dated private operator receipt is recorded on the issue; it
is not a public Worker deployment certificate. The observed public failure and
Cloudflare's documented Free request budget strongly support the request-budget
diagnosis, but no independent Worker-tail exception was captured. See
https://developers.cloudflare.com/workers/platform/limits/#subrequests .

Local validation uses PGlite and an injected request bound, not a Cloudflare
runtime. Full CI, exact-head review, serialized integration and actual deployed
Cloudflare readback remain necessary before issue closure. Native SQL recovery
already completed under #864; this change does not restore missing old archives,
modify facts or require new role grants. Release assets, database credentials,
R2 bytes and the public read-only setting must remain unchanged on publication.

Run `node --test test/compact-membership-profile.test.mjs` and the normal full
repository checks. Rollback uses the previously verified Cloudflare Worker
and its matching release package recorded in the publisher receipt.
