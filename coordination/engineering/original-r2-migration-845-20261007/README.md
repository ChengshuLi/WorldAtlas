# Original Site R2 migration, 2026-10-07

This PR restores the three exact missing original README objects and prepares
lossless storage reconciliation. It does not claim complete old-bucket enumeration
or live transfer. Issue #845 remains open for its operator-run acceptance after
review/merge; no further implementation PR is presumed within its one-PR allowance.

The owner-authorized original Site media reads returned the recorded exact lengths
and SHA256 values. They cover only those three registered objects. The destination
API inventory is complete for worldatlas-archives at its recorded preflight vintage;
it cannot establish the old bucket's complete contents. The first raw-token
access probes returned401; adding the documented Bearer prefix succeeded.

`hosted/site-r2-export.js` is an expiring read-only wrapper, separately staged around
the original live Site24 compiled server. It is inactive in ordinary atlas builds.
It lists arbitrary keys with HTTP/custom/storage-class metadata, streams exact
objects with conditional ETag reads, delegates existing routes, and never writes
storage or Neon. Invalid/missing/expired credentials close the route before reads.
`prepare-site-r2-export.mjs` consumes the exact Git blob of Site24's server and
checks every other packaged original member (including drizzle). Two final builds
are byte-identical. Earlier narrower build receipts are retained as earlier checks.
The changed-frontend adverse control is rejected before server build output changes.

The separate temporary destination Worker accepts authenticated, expiring,
checksum-verified, bounded create-only uploads using R2's atomic conditional put.
It is not the public atlas Worker. It refuses collisions and supports full readback.
The reconciliation driver walks all pages, rejects duplicate keys/cursor loops and
unadmitted sizes, rereads stable inventories, verifies every existing object's full
bytes before writes, and verifies each new object's full bytes and metadata. It
retains complete origin/destination metadata. Extra destination HTTP policy such as
immutable caching is allowed only while every original metadata value is preserved;
a differing original value blocks copying. Provider-specific versions, ETags and
upload timestamps are recorded as separate origin and destination properties rather
than represented as identical new upload properties.

Run `node --test test/site-r2-export.test.mjs test/r2-migration.test.mjs`.
Run the provider driver by sending one JSON configuration object through stdin to
`node scripts/migrate-site-r2.mjs`. Required keys: `source`, `destination`, `copy`
(boolean), and an absolute fresh owned `output` directory. Each endpoint specifies
an HTTPS URL, token, and optional owner-authentication headers. Never put secrets in
CLI arguments, committed receipts or disk configuration. The dry run uses
`copy:false`; copying uses `copy:true` only inside the approved serialized operation.

Equivalent operating safeguards are deliberately used instead of the scientific
Python evidence helpers: live provider streams are not local scientific inputs.
Inventory admission limits the complete storage phase to20,000 objects/200 pages/
1GiB, with a32MiB per-object cap and bounded page responses. Existing-object hashing
streams without retaining the body. Missing-object transfer retains one bounded
body at a time. Each HTTP request has a120-second timeout; the live operator window
has its separate finite expiry. Fresh local run directories and exclusive files
retain partial failures. These limits do not widen premerge manifest byte limits.
The Site packaging phase is separately admitted through the managed publisher
checkout; it authenticates all original package members before building.

After normal review/merge: freshly verify all Site/Neon/Cloudflare operation
settlements and register one bounded #845 recovery operation. Preserve the current
Site24 deployment ID as rollback. Set temporary secrets/expiry, push/save/deploy
the reviewed wrapper through the Sites workflow, and preserve its audience and
bindings. Provision only the separate temporary Cloudflare migration Worker with
the destination bucket binding. Inventory and verify first; copy only missing
originals. Preserve complete inventories, metadata and per-object proof as durable
original-issue evidence. Confirm stable source and destination inventories and
unchanged Neon/public atlas markers. Restore Site24/remove temporary environment
keys, disable/remove the temporary destination Worker, and verify cleanup before
settling the operation. Preserve all old Site versions, buckets, objects, facts,
IDs/provenance and existing Cloudflare objects. No database registration or deletion.

Limits: local controls and package checks do not prove production permissions,
complete old storage inventory, production byte/metadata parity or cleanup. Those
are the original issue's remaining live acceptance. The public site continues
without login; the old Site remains preserved.
