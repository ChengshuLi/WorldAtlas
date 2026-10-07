# Release membership request admission — issue #1266

Immutable membership transports can satisfy their byte cap while exceeding the
service's separate row cap. Bootstrap now authenticates and admits the complete
set of needed inputs and requests before its first write. It captures input bytes,
checks complete release identities and canonical record hashes, and consumes the
captured requests without reopening original files.

`geographic-release-admission.mjs` partitions only staging requests. Both membership
and change rows, plus the release definition when present, count toward 250 rows.
UTF-8 envelope, metadata and ingestion-ID bytes count toward 1 MiB. Original bounded
requests retain their bytes and identities. New child IDs bind the complete parent
bytes, route, path, child index and content. Full raw row objects, their key order
and their sequence are preserved. Source/entity registration precedes the release
definition and its ordered membership/change requests. Staging parents run serially
even when prerequisite concurrency is six; their child requests cannot interleave.

Source/entity admission reuses the service's actual field normalizer through an
internal read-only helper in `hosted/records.js`. Staging admission and the service
share `validateGeographicStageBatch`, including dates, text fields and creation
proof semantics; coherent hashes do not excuse invalid consumer fields. This adds no route and changes no
server gate. It prevents malformed later source fields or intra-batch parent cycles
from causing earlier prerequisite writes. Foreign keys, existing record conflicts
and provider availability still require the real transactional service. A failed
operation is not a completed publication.

The original v5-prefixed entity prerequisite is included in the existing tier
selection; prefix-only selection previously omitted two actual stable identities.
No source record, immutable transport, predecessor definition or archived producer
has been replaced. This repair grants no source authority or geographic approval.

## Verification and bounded scope

The retained full-store runs use the actual handler, original immutable transports
at `d7d209a18b96b5d86ba31795c422e6bf439cd72d`, and actual Node SQLite transactions and
schema guards. Original stable registry/source records are seeded in a separately
admitted phase. The successor-only phase stages release 7, with full expected
canonical hashes, and compares the complete ordered raw input/output records.
It does not pretend the six predecessors were already published.

An injected interrupted response follows a durable membership write; the same
captured inputs resume with duplicate receipts, without overwriting prior rows.
Meaningfully changed content under an existing ingestion ID is rejected. Original
registry/source rows are compared before and after staging. The unrestricted
all-predecessors-missing case must refuse its oversized descriptor inventory before
reading any batch or making any bootstrap write; a small compressed transport does not waive decoded budgets.

`verification-first.json` records the original implementation vintage.
`verification-second.json` records the optimized byte accounting vintage and
original registry preservation. Their complete request-body hashes are identical;
their execution/code provenance differs. Later receipts, rather than edited old
receipts, record subsequent safeguards. These are isolated results, not production
acceptance, deployment, source approval or history imports.

## Reproduce

Use Node 24 in a managed sparse checkout. No service token or network operation is
used. Replace `EXACT_EXECUTION_COMMIT` with the retained receipt's execution commit
or an independently reviewed corrective commit. Use a fresh owned output filename;
existing targets and symlinks are refused before calculation.

```sh
node --input-type=module -e 'import {execFileSync} from "node:child_process"; const commit=process.argv[1]; const code=execFileSync("git",["show",commit+":coordination/engineering/release-membership-admission-1150/verify-staging.mjs"]); await import("data:text/javascript;base64,"+code.toString("base64"));' EXACT_EXECUTION_COMMIT coordination/engineering/release-membership-admission-1150/verification-fresh.json
```

The verifier itself executes directly from Git. Its project-module loader supplies
the exact recorded Git bytes and captures the imported code closure. Inputs are
read from pinned Git blobs, checked against their authoritative indexes, and traced
in the result. SQL migrations use the execution vintage. No full dataset checkout,
new dependency environment or on-disk database is needed.

Focused regression tests are `geographic-release-admission.test.mjs`,
`geographic-bootstrap.test.mjs` and `geographic-releases.test.mjs`. Retained independent
fixtures exercise combined row counts, valid Unicode metadata, exact full-envelope
byte boundaries and raw-record preservation. Record-import and classification
regressions cover the adjacent shared normalizer. The complete cohort experiment
is an explicit engineering verification; it is not added to source-only research CI.

Whole-file and descriptor evidence checks remain separate from scientific approval.
The catalog and successor phases each retain their own complete inventory and
existing caps; splitting a manifest does not make an oversized single execution
phase valid. An unrestricted full bootstrap is rejected when its needed inputs
cannot fit the admitted phase. No request limit or evidence limit is raised.

Complete caller admission caps a needed phase at 512 descriptors before input reads,
as well as 32 MiB per file and 256 MiB for encoded, decoded and request bytes.
The catalog seed uses a separately validated existing-v1 manifest; the primary
manifest binds that manifest, but does not recursively execute or validate it.
Independent review must validate both inventories and the isolated experiment.
