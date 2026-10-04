# Membership storage investigation

Issue: https://github.com/ChengshuLi/WorldAtlas/issues/754. This is an isolated measurement and prototype; production has not been compacted or switched.

The current representation repeats long release/source/entity identifiers in every row and multiple indexes, and embeds the same evidence text in many rows. The candidate keeps stable external identifiers in lookup tables, stores each byte-identical evidence string once, and retains a separate membership for every original release/entity pair. It preserves names, parents, active flags and original canonical evidence. No historical snapshot or factual claim is removed.

`result.json` records the actual independent PostgreSQL/PGlite relation, TOAST and index measurements, complete per-release membership/raw-row hashes, bounded query probes and resource samples. `inputs.json` lists whole original batch hashes, source batch pins and the verified immutable extension chain. All original prepared files remain in Git at the recorded baseline; original external archives have not been scientifically revalidated by this benchmark. The source dataset includes staged releases and must not be called the served geography.

The original prototype copies the frozen membership DDL, constraints and indexes. Shared entity/source/release registries are reduced to their identity columns; the candidate counts every lookup/dictionary relation and index. Consequently this is a membership-subsystem comparison, not a whole-production-database size forecast. The frozen production observation in `production-measurement.json` is separately dated and uses different physical/logical accounting.

Reproduce from the baseline with Node 24 and the locked dependencies:

```sh
node scripts/benchmark-membership-storage.mjs data/geographic-releases /absolute/new-output /absolute/new-isolated-target
node --test test/membership-storage-benchmark.test.mjs test/postgres-contract.test.mjs test/postgres-adapter.test.mjs test/geographic-releases.test.mjs
```

The tool refuses an existing target and uses only local disk-backed databases. Keep the output and targets from failed attempts. The first attempt failed before seeding because the runtime no longer exposes `lc_collate` as a configuration parameter; its original source and full log are preserved. Later result/source vintages retain the transaction-ownership correction, broader query probes and predecessor-chain review. The final implementation owns the candidate transaction and installs client dictionary entries only after commit. Focused negative controls exercise rollback, duplicate memberships, digest collisions, damaged payloads, missing keys, invalid fields and immutable-history protection.

The measured reduction justifies a separate production migration. A live schema cannot simply be replaced with this prototype: current geography inserts use `ON CONFLICT`, the restricted runtime role expects the frozen tables, and temporal guards, exports, restoration and owner migration contracts depend on them. The follow-up must adapt these together and verify the full real application, including byte-identical retry behavior.

The preferred migration investigation stays on Neon and preserves the existing public API. It should first test a bounded maintenance sequence that drops only the two rebuildable non-unique membership indexes, then builds the compact replacement while retaining the original membership rows, verifies exact SQL row parity and existing facts, and atomically switches the compatible readers/writer. Index definitions must be pinned; if the copy cannot fit or validation fails, discard only the new candidate and rebuild the original indexes. Dropping original factual storage requires a recoverable current backup and verified replacement; never infer backup completeness from these prepared inputs. Recheck actual logical capacity after each committed preparation step, since estimated local savings cannot authorize a quota gamble.

If that measured sequence cannot retain adequate peak-space/rollback reserve, an authorized separate free Neon project is an alternative staging target; availability and account-wide allowances must first be confirmed. A paid Launch switch is the fastest way to remove the immediate hard cap, but billing applies to the organization and compute can cost more than storage. No payment or provider provisioning occurred here.

`alternatives.json` retains dated public rates, illustrative Neon compute/storage costs and compatibility limits. Supabase Free and D1 Free have smaller per-database limits. Turso offers more free space but changes the engine/API and requires a migration with parity, transaction/trigger and recovery validation. Given the measured redundant representation, switching providers should not substitute for fixing the storage model. A future increase in unique factual data may warrant paid Neon or another backend after measuring actual growth and workload.
