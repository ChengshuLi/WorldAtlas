# Fresh provisional regional rerun

This prepares the exact v24 mixed/regional request against a **completed** fresh
Stage 2 provisional output. It does not publish a map or change the original
regional decision snapshot, policy, or historical route provenance. Pending
inventory and geographic-source interpretations remain incomplete.

First stage the source files named in the original request and its point
request; the driver rehashes the staged local bytes against the pinned source digests.
R2 custody is established separately; the driver does not re-download from R2. The runtime
uses the exact historical v24 point resolver beside its dependencies. The
provisional regional hook isolates its pinned historical WGS84 run-pair module
from the newer Stage 2 module without replacing the latter.

Run with Python that has the project GDAL, NumPy, SciPy and PyProj dependencies:

```
python prepare_fresh_handoff.py \
  --template /path/to/provisional-diagnostic-handoff-v7/config.json \
  --outer /path/to/fresh-stage2-outer-config.json \
  --work /path/to/fresh-stage2-work \
  --stage2-output /path/to/completed-stage2-output \
  --destination /path/to/new-preparation-directory \
  --regional-output /path/to/new-regional-output
PROJ_NETWORK=OFF python apply_selected_mixed.py /path/to/new-preparation-directory/config.json
```

The exact template SHA-256 is `4668cac041f0dee1257c95a9e60c46d34fff53ffb5ab0010ec3647e114d909d0`.
For a moved source tree, add `--source-prefix /old/source/root /new/source/root`;
stage the same files under the corresponding relative paths. Executable pins
are resolved to exact matching tracked PR4 bytes. The preparer verifies the
same-run outer/core/config/report bindings and independent provisional Stage 2
validation before creating new inputs; the mixed driver rehashes and validates
its source files and code again. Use fresh, non-overlapping work/output paths
with at least the configured disk reserve. A failed preparation may leave a
partial destination and must be inspected before retry.

Successful preparation or output is a profiling candidate, not an accepted
Neon geography, an independently authenticated source, or a final map rerun.

## V24 regional input custody

The following consumed regional inputs were preserved at
`worldatlas/sources/derived/v24-research/<sha256>.json` in R2 and as the
corresponding `atlas.source_assets` records in the Neon research branch.
Each R2 object passed full-byte readback, and each Neon JSON value matched the
input JSON. These records are unverified research evidence, not accepted
geography.

- Mixed request: `v24-regional-request`, SHA-256 `4668cac041f0dee1257c95a9e60c46d34fff53ffb5ab0010ec3647e114d909d0`.
- Point request: `v24-regional-point-request`, SHA-256 `b0751dc93eff424ebe440d794e33b2ca5b0e6677bfc5fee1807468044ed3f192`.
- Local-derived policy: `v24-regional-policy`, SHA-256 `1cae6df25a1f33ff557a4d93c90c4fdc3724983a3268801ae9621fe3f757840d`.
- Regional line: `v24-regional-lydekker-line`, SHA-256 `cbb4508245942a2586bf37279570b55c7b2382c15268b311c0c2ddf3d96dbcd2`.
- Empty pending stand-in: `v24-regional-pending-standin`, SHA-256 `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570`. Its emptiness does not establish that there are no pending claims.

The regional Bering calculation requires PROJ network access disabled and the
exact pinned active PROJ database. For the recorded v24 environment,
`/usr/share/proj/proj.db` has SHA-256
`8bbb2ea3a88c44383f51e205755c32bff09b8aff7937eca001a1cd519714be60`.
