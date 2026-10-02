# Hosted migration transport

Frozen primary-repository migrations remain immutable. `scripts/compile-hosted-migrations.mjs` produces a separate deployment derivative for a SQL transport that does not distinguish a trigger's final `END` from `CASE … END` inside that trigger. This is a packaging adaptation, not a schema migration or historical-data correction.

Native workerd/D1 reproduces the failure: original migration 0002 succeeds when its complete Drizzle breakpoint statements are prepared and batched. A BEGIN/END-only splitter truncates the first `geographic_release_insert` trigger immediately after its first `SELECT CASE … END;`, and D1 rejects that fragment with `incomplete input: SQLITE_ERROR`. This reproduces the reported deployment error and explains why the earlier migrations, whose trigger bodies use `SELECT RAISE … WHERE`, can succeed. The Site's private migration parser has not been inspected directly; this evidence identifies a compatible transport failure, rather than asserting access to its implementation.

Whole-file D1 `exec` is also unsuitable for these multiline migrations: it fails at the first multiline CREATE TABLE. Preparing complete statements and batching them is the supported control case used by the native tests.

The compiler is narrowly pinned to the immutable 0002 source SHA-256 `fc03e50b1c7053d9ffe89534395bcbb644e3192231122eca51a424fd14753c53`. It changes exactly 21 single-line trigger guards:

```sql
SELECT CASE WHEN condition THEN RAISE(ABORT,'message') END;
-- becomes
SELECT RAISE(ABORT,'message') WHERE condition;
```

Both forms raise the identical error when the condition is true. When false or NULL, the first form returns a NULL result and the second returns no row; the trigger discards either result. Every condition and error message is retained exactly. The derivative 0002 SHA-256 is `77459729e200a45e3c003333acbd2a30446acba1670138a4861f7315a4241e77`. Other SQL files and every Drizzle metadata file are copied byte-for-byte. The compiler rejects a changed source hash, an unexpected number of transformations, or an attempt to overwrite the raw source directory.

```sh
node scripts/compile-hosted-migrations.mjs --input drizzle --output <derivative-directory>
node --test test/hosted-migration-transport.test.mjs
ATLAS_DRIZZLE_MIGRATIONS=<derivative-directory> node --test test/geographic-release-preparation.mjs
```

The generated `transport-receipt.json` records the immutable source and derivative hashes for every migration, all metadata hashes, and the source line/condition/error hashes of each transformation. Retain both the raw source directory and this receipt in deployment source packaging. A Site mirror whose root `drizzle` directory contains derivatives must rebuild from its separately retained `drizzle-source`, rather than feed derivatives back into the compiler. Already applied 0000 and 0001 stay byte-identical; their migration identities do not change. This workaround assumes 0002 remains unapplied, as established by the deployment's table inventory.

The focused tests check compiler determinism, all source/meta byte hashes, all 21 conditions and error messages, and schema equivalence. Native workerd/D1 additionally checks the original whole-statement success, truncation failure, and derivative success over a populated fixture. Both original claims and the sourced retirement remain equal, all original indexes/triggers remain equal, and foreign keys remain valid. The exhaustive real-D1 service test can run all release preparation, staging, publication, profile, paging, crosswalk, original-evidence preservation, and future-release checks against the derivative using `ATLAS_DRIZZLE_MIGRATIONS`.

This local proof does not establish a successful Site deployment. Root deployment must confirm the new schema inventory and run the retained-record checks before claiming publication success. The preferred long-term upstream repair is a migration parser that prepares complete Drizzle statements or uses SQLite's trigger-aware statement-completion rules, retaining original SQL without adaptation.

Verified on 2 October 2026: all three focused transport/native tests and all 14 exhaustive release tests against derivative migrations passed, with no skips. The durable test-only receipt is `data/validation/hosted-migration-transport.json`. No hosted deployment success is asserted by these local results.

## Confirmed Site deployment

After local transport validation, the deployment controller reported a successful native private Site deployment on 2 October 2026 at 02:18:04 UTC: deployment `appgdep_6abf142287588191a4eb9546fc54903d`, Site version 13, source commit `282d0a0b0cec459db3341af61fed8236e8eb8ae0`. The native table inventory confirms all three geographic release tables exist. This confirms the derivative transport crossed the failed migration stage; publication of the geographic reference memberships is a separate bootstrap milestone.

The staging command checks the prepared derivative receipt against raw source and build bytes, preserves the immutable source as `drizzle-source` in the separate Site checkout, and copies derivatives into its deployment `drizzle` folder:

```sh
node scripts/stage-site-migrations.mjs <separate-Site-checkout>
```

Run this after the hosted build and before saving/deploying the Site source. It rejects the primary repository or a checkout lacking its existing hosting manifest. Source/meta hashes and copied source/derivative bytes are checked; credentials and existing historical claims are not touched.
