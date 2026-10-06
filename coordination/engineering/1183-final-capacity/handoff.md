# Final capacity pacing, issue1183

Author: 01a111d7-4e3b-7d22-b94d-09dd77f60e3f. Branch:
engineering/1183-final-capacity. Immutable baseline:
8ec1e31a451541af8b4cd5e09cc74d4325fe3b62. Raised/checked2026-10-06.

The existing final job now observes same-token authenticated capacity before
repository reads, obtains a complete tree/path/vintage-bound cost inventory and
waits on an actual deficit while retaining its live FIFO ticket. Three planning
attempts share one monotonic61-minute deadline. Final validation has13 minutes
plus1 minute job setup inside75. No quota reservation or token swap is possible.
The original full validators and SHA-guarded merge remain mandatory.

Actual local validation:180 controls passed,0 skipped, including23 capacity
controls and17 real Git/native geography controls. The retained transcript
contains actual results. The source input required for geographic API controls is
coordination/engineering/coverage-gaps-907-20261005-local01/sources/natural-earth-lakes.geojson.gz,
plus data/research-geography-gate.json. Python3.12.14/Shapely2.1.2/GEOS3.13.1
was reused read-only from an existing pinned runtime; no install was performed.

Read-only root1150/head405f75ce2280dc44172ba596b9ee08513abe437c
metadata planning found400 descriptors,92 originals and474 unique bound blob
OIDs with cache fit. Planning used22 metadata requests; with2 cheap guards,
12 illustrative admission requests,1 artifact page and48 overhead calls, the
ordinary final estimate is583. These are workload accounting observations;
they are not same-job-token capacity or geographic approval. Concurrent API
consumption and changed pagination can still reject safely. Missing/invalid
observations, unknown cost and bounds exceeding observed limits fail closed.

Remaining: independent exact-head implementation/release review, hosted CI,
normal FIFO integration/merge, actual main byte readback and claim/slot release.
Actual large-workload hosted quota recovery remains conditional and unverified;
do not force exhaustion or label local fake-clock controls live recovery.
No production/provider/database writes, deployment or source approval occurred.

Own canonical claim ba018853-5926-4f0e-b9b4-2bb89b1fb0de was accepted
at6021553913 with canonical6021553335, expires2026-10-07T17:16:12Z.
Keep it active until verified completion/release. The managed author slot is
/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/8c86b01772c1c827/dc0aba6f12fd593f6c65354c20e98fbba0361ab9f3b6026689f1b6d197e1503e/work.
Root owns exact-head review and coordination of larger1150 admission.
