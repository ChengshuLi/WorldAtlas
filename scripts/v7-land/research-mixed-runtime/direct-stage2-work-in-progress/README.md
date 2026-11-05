# Direct stage-2 integration work in progress

This patch preserves an isolated research prototype; it is not the active
pipeline, a reviewed executable freeze, or a production release. Fresh v2 seed
execution is not wired into the outer pipeline. The unconnected request,
invocation and fresh-proof helpers must not be enabled until the actual call,
source bindings and checkpoint/resume identity are independently reviewed.
The most recent external re-review request was not admitted because automatic
approval review failed; no approval or completed review is implied.

The direct prototype does not launch a supervisor or impose a total-process
memory cap. Its bounded tests cover selected contracts and core checkpoint
failure/resume; early failures before the derived manifest require a new work
path. The historical seed and its historical monitor artifacts remain distinct
from the new v2 producer. A new direct seed must bind the selected snapshot,
current witness and physical/component data, Panama archive, optional Caucasus
source gate, current closure proofs, code and request hashes, and the same
artifacts in resume and core identity. Historical route provenance must not be
represented as a proof from a new checker. Physical-mask producer lineage and
production closure remain unverified.

`work-in-progress.patch` is a source preservation artifact against the local
`stage2-rss-runtime-20261105` baseline; `file-hashes.json` records exact base and
candidate bytes. The independently reviewed v2 seed producer and its 14-file
freeze are separately committed under `scripts/v7-land/mainland-seed-l2/` at
PR4 commit `b2f4648f84825e8c19cc15d606ca6b278a263e09`. Applying this patch
alone does not assemble a working runtime: it needs the complete baseline,
the v2 producer in a separate directory, and source-specific dependencies.
No map or selected Neon data was produced by these bounded tests.
