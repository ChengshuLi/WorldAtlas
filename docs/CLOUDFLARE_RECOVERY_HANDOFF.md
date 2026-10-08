# Cloudflare serving and retained recovery

Cloudflare is the normal public serving and publishing destination:
https://worldatlas-explorer.chengshu-worldatlas.workers.dev/ . Follow
[PUBLICATION_HANDOFF.md](PUBLICATION_HANDOFF.md) for subsequent publications.
The original ChatGPT Site is an owner-private, read-only recovery copy; do not
send ordinary publishers or visitors there. Historical deployments remain readable
in the complete cross-provider registry. The #907 application delivery hold still
applies: this handoff does not make latest main eligible for a new application build.

## Current destinations and proof

Neon remains project weathered-lab-37571695, branch
br-summer-butterfly-ar8qikk5, database neondb, with the existing compact schema and
worldatlas_app runtime role. No migration, factual rewrite, credential rotation or
provider deletion accompanies retirement. The public Worker blocks mutations.
R2 bucket worldatlas-archives contains the actual registered archive/evidence bodies.
Website HTML, JavaScript, CSS and prepared map drawings are Cloudflare Worker ASSETS;
they are a separate part of the deployment, not this archive bucket.

Archive preservation is complete under #845: the complete original bucket and
all three missing README originals were compared and preserved. The old bucket
and every pre-existing destination object remain. Full original/destination
inventories, metadata, individual byte checks and cleanup are retained at
https://github.com/ChengshuLi/WorldAtlas/issues/845#issuecomment-6050922276 .
Independent acceptance:
https://github.com/ChengshuLi/WorldAtlas/issues/845#issuecomment-6050954579 .

The actual bounded Cloudflare publication under #846 retained application commit
4a1fc6777fe766dca2c0698362a06f06a44f9344 and Worker version
f46f5cdd-58f5-41cd-abee-cb5b41c2106d. Provider deployment
1c783313-6d1b-46d0-9086-6b0660ed37f2 is tracked by GitHub deployment 6926837015.
Matching release, database marker, assets, anonymous browser behavior and blocked
writes passed. Complete actual proof:
https://github.com/ChengshuLi/WorldAtlas/issues/846#issuecomment-6051902257 .
Independent acceptance:
https://github.com/ChengshuLi/WorldAtlas/issues/846#issuecomment-6051986479 .
This was a real re-publication of the existing immutable version, not a new main build.

## Tested database recovery and current coverage

The actual native PostgreSQL backup/isolated restore is preserved at
https://github.com/ChengshuLi/WorldAtlas/issues/51#issuecomment-5988399376
(workflow 37265153024). It includes logical facts, releases and metadata, the
compact physical tables, migration registry, schema, sequence state and the stated
owner/ACL scope at capture. Restore ran in an isolated network-none PostgreSQL18
target and matched original ordered row digests; source writes were zero.
Retained SQL restoration uses the documented target-only session-header and
constraint revalidation in [CURRENT_POSTGRES_RECOVERY.md](CURRENT_POSTGRES_RECOVERY.md).
Do not load a raw dump directly into production or change the frozen source catalog.

The retirement packet at
../coordination/engineering/cloudflare-retirement-847-20261007/ retains the original
native receipt and fresh read-only comparisons. Every current logical collection's
count and ordered digest equals that tested backup, and the complete marker was
unchanged before/after and equal to its captured marker. Both current catalog
bodies reproduce their public/private definition hashes and match the backup.
Every registered media entry was joined to the complete migrated inventory, and
its full current download was checked for exact length and SHA256. The recipient's
existing private key successfully authenticated/decrypted the retained encrypted
backup in memory; its plaintext digest matched the previously restored archive.

These are current logical facts/releases/metadata and archive-byte checks. Private
unused dictionary rows, current private sequence values and private registry rows
were previously restored and verified at capture; they were not freshly compared
with the runtime role, which cannot read them. Catalog equality proves definitions,
not those private values. This is not a server-global/provider physical backup,
password or role-membership recovery, permanent offsite-retention guarantee or new
SQL restore. Preserve the existing provider/credential setup separately.

## Recovery procedure and custody

Keep the original encrypted custom archive, backup-envelope.json, expected-context.json,
receipt.json and recipient acknowledgment in the existing private recovery directory
outside Git. Preserve recipient-private.pem separately with mode0600. The operator
has verified the existing local custody; another worker must obtain authorized
private access rather than assume these files exist in its checkout. Never commit
or print the key, database URL or plaintext dump. Actions artifacts expire; the
independent local copy must remain retained.

Verify raw hashes against private-custody-descriptors.json and the original receipt.
Use the reviewed CLI outside Git with a fresh exclusive output:

    node scripts/recovery-backup-envelope.mjs decrypt ENVELOPE CIPHERTEXT PRIVATE_KEY EXPECTED_CONTEXT NEW_OUTPUT

The CLI verifies exact recipient/context, ciphertext hash, AEAD authentication,
plaintext size/hash and restrictive key permissions. Restore the verified custom
archive only into an isolated PostgreSQL18 target with the exact native procedure
in CURRENT_POSTGRES_RECOVERY.md and its pinned original schema inputs. Recompare
all logical rows, compact state/catalog/ACLs, and prove target/source-lock cleanup.
Any later production restore requires a new scoped reviewed operation, current
source comparison, rollback and serialized provider window; this retirement does
not authorize overwriting Neon. Reuse current verified source reads if preparing
a new current-source backup; do not substitute an old marker for a live one.

Recover archived files from the retained original bucket or the verified current
worldatlas-archives bucket using their original object keys. Obtain the complete
inventories from #845's durable proof and compare whole bodies/metadata before any
copy. Use create-only copies, resolve collisions explicitly, and never overwrite
or regenerate a differing original. Neon media rows are the index/pointers; their
presence alone is not a backup of R2 bytes.

## Safe retirement and rollback

The old Site is appgprj_6abdf87277c08191bce4a22b8dfb25db at
https://worldatlas-explorer.chengshu-li-2013.chatgpt.site . Its retained live version24,
original repository, versions, bucket, owner-only access, database binding and
read-only setting remain. Native automations were empty; the two inspected local
jobs were paused and contained no old Site publishing destination. No new schedule
or saved-chat goal is created or silently rewritten. Omitted connector settings
are not proof that an unobservable external integration does not exist.

Issue #847 records the actual post-merge metadata operation/readback: label the
private Site as retired from normal publishing, preserving its URL/access/version,
all environment bindings and storage. No unpublish, redirect, bucket deletion or
application deployment is needed for this retirement. Its prior display title is
WorldAtlas; title rollback uses update_site_metadata with the same project ID and
that exact title, under a newly serialized recovery operation. The metadata change
is complete only when the native result on #847 proves it; merging this document
alone is not production acceptance.

For serving rollback use an explicitly verified retained Cloudflare immutable
version whose code/assets and data pins match the current Neon release. Preserve
current/previous provider deployments and register/settle the real operation.
The old Site is retained historical recovery, not an automatically compatible
current-release serving fallback. Keep original source/history and all recovery
credentials/receipts; retirement grants no deletion authority.
