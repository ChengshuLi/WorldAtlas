# Deployment package accounting

`npm run build:hosted` measures the complete upload layout and enforces reserves.
Its `.cache/deployment-budget.json` report has every file path, byte count and
SHA-256, category totals, actual tar size, compressed size and archive hash.
Reports are outside deployment assets. CI runs the same build and retains the
report on success or a budget failure. Neither command publishes or runs live
migrations.

All sizes are bytes; **1 MiB = 1,048,576 bytes**. The known Sites package ceiling
is **268,435,456 bytes (256 MiB)** of uncompressed archive, including tar headers,
padding and directory entries. The individual asset ceiling is **26,214,400 bytes
(25 MiB)**. A smaller gzip upload does not establish compliance with either limit.
The policy reserves **4 MiB per package** and **1 MiB per asset**: the gate permits
at most **264,241,152 tar bytes (252 MiB)** and **25,165,824 file bytes (24 MiB)**.
These reserves leave space for packaging/code growth without deleting evidence;
they are application policy, not provider quotas. Larger future map growth needs
the separately reviewed immutable delivery work, not automatic reserve removal.

Historical Site 19 observations remain unchanged in
`data/validation/global-macro-publication.json`: **261,275,557 dist file bytes**
and **262,225,920 saved archive bytes**. Those receipts used their recorded
publication layout and packaging metadata. A new reproducible tar can have a
different size/hash; do not substitute its result into the old receipt.

## Layout and publisher check

The primary build audits `.openai/hosting.json`, `dist/client`, `dist/server`
and the compiled migration transport. The archive maps `dist/drizzle` to root
`drizzle`, preserving the server's separate required transport copy. It never
packages the primary repository's raw root SQL as the deployment derivative.
POSIX tar uses fixed timestamps/ownership and excludes atime/ctime metadata;
gzip uses level 9. Directory headers and tar padding are measured by streaming
the actual tar, rather than estimated from file sizes.

Source SQL/metadata, source archives, research, SQLite, credentials, dependencies,
Git and caches stay outside the upload. They remain in their existing source
repository/storage locations. The prior-lineage omission contract remains in
`ownership-history/archive-delivery.json`; accounting does not assert any upload
of those retained archives.

After staging migrations in the separate Site mirror through the existing
`scripts/stage-site-migrations.mjs` protocol (and removing redundant
`dist/drizzle`), the designated publisher must audit that **final** layout:

```sh
node scripts/deployment-budget.mjs --root /absolute/site-checkout --layout site --out /tmp/site-package.json --archive /tmp/site-package.tar.gz
```

The archive output must be new and outside deployment inputs. Upload that exact
archive only if the gate passes and all other publication checks pass. Any
subsequent staging/build change needs another audit. Source-only changes that do
not affect the packaged files do not require repackaging. Symlinks and special
files in deployment inputs fail closed. Do not include the generated report in
the archive.

## Failure response and immutable delivery candidates

A failed gate prints package excess, category totals and the ten largest files;
asset violations also name every offending path and excess. Read the complete
report before changing packaging. Preserve evidence and split or move immutable
assets only through the reviewed delivery protocol. Package/file budgets are
independent of Neon database bytes, the 512 MiB database planning guard and
unverified R2 account/storage/egress allowances.

`immutableAssetCandidates(report)` selects fixed ownership, geometry/catalog,
reference-attribute and prepared-evidence assets with exact byte hashes and
proposed content-addressed object keys. The retained candidate receipt is a
proposal for the next delivery issue, not a deployed manifest or upload proof.
It includes the private authorization/cache and complete-manifest rollback
requirements. Public CDN access is not permitted by the current owner-private
audience. Account limits, object metadata/read-back, authenticated cache behavior
and the eventual client delivery implementation still require independent proof.
