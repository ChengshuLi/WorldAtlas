# South America #1349 manifest builder repair

**Issue:** [#1506](https://github.com/ChengshuLi/WorldAtlas/issues/1506)
**Claim:** worker `01a10947-b3d7-7812-8b2f-c5a47e88ccb2`, reservation and workflow receipts in `claim-receipt.json`.
**Branch base:** fresh `origin/main` `515c6e66cea72f0f2357826950692b719d0c89ce`.
**Scope:** manifest-builder custody and complete-output admission only. This directory is the sole owned path.

The earlier #1332 packet remains intact. Its 65 original files, six historical vintages, declared scope, pins, successful producer runs and unresolved source findings remain unchanged. The accepted immutable #1332 contract is SHA-256 `70e61fad77bb6b93376821cbe8b7c8c73439eac95ede07a45784758400ae23f6`; its 215 IDs equal this issue's declared roster and the exact 215 IDs in the inherited run-five audit. The complete immutable evaluation index is commit `e9190786dbf758524a3bde513fc4bb4d1ed6a3e7`, whose index declares 36 unique parts.

The inherited geography claims remain limited to retained Atlas identities, candidate crosswalk rows and parent/area rosters. Current source authority, original geometry, license/reuse, legal meaning, completeness, adjacent granularity and boundary quality remain unverified. No source acquisition, approval, import or deployment is part of this repair.

The actual producer writes run-nine/run-ten after binding each run to the exact producer script and captured immutable-helper hashes. Earlier run-seven/run-eight evidence is preserved unchanged. The corrected builder authenticates the accepted contract and reconciles every generated subject identity before preparing results. It validates every input and output destination before computation, holds every final result in memory, and publishes the success manifest last. The original builder and packet remain immutable historical evidence.

Run with the pinned Python runtime and from repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3.12 -B research/geography/south-america-batch4-manifest-1349-erratum-20261008/reproduce.py --vintage run-nine
PYTHONDONTWRITEBYTECODE=1 python3.12 -B research/geography/south-america-batch4-manifest-1349-erratum-20261008/reproduce.py --vintage run-ten
PYTHONDONTWRITEBYTECODE=1 python3.12 -B research/geography/south-america-batch4-manifest-1349-erratum-20261008/verify_controls.py
PYTHONDONTWRITEBYTECODE=1 python3.12 -B research/geography/south-america-batch4-manifest-1349-erratum-20261008/build_manifest.py
node scripts/evidence-quality.mjs research/geography/south-america-batch4-manifest-1349-erratum-20261008/evidence-quality.json
```

These checks establish only reproducible custody/integrity for the bounded repair; they do not certify source truth or the South America region.

The first actual builder output was rejected because its metric vintage used a producer run name instead of the required baseline/current/archived value. The second was rejected because metric hashes repeated across vintages without exact `input_file` paths. The third failed the trusted gate because the generated pin keys did not exactly match the issue-declared pin paths. All three exact drafts and findings are retained under `controls/failed-*-builder/`; they are described as failed drafts and are not accepted outputs. `cli-controls.json` keeps the original-builder reproductions and corrected CLI adverse controls. Earlier exact control receipts are preserved at `controls/first-control-receipt.json`, `controls/second-control-receipt.json` and `controls/third-control-receipt.json` as the final suite is rerun.
