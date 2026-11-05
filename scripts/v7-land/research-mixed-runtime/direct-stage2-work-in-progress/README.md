# Direct stage-2 integration work in progress

This patch preserves an isolated research prototype; it is not the active
pipeline, a reviewed executable freeze, or a production release. A fresh v2
seed request, direct producer call, Panama core source replay, Caucasus gate
path and core/resume bindings have been wired in scratch, but both
`FRESH_DIRECT_EXECUTION_ENABLED` and `CAUCASUS_DIRECT_GATE_ENABLED` are false. Do not enable either until the
actual call path and source/checkpoint bindings receive independent review.
The latest requested external re-review was not admitted because automatic
approval review failed; no approval or completed review is implied.

The direct prototype does not launch a supervisor or impose a total-process
memory cap. It uses isolated Python and a byte-verified private code snapshot;
Python, GDAL, native libraries and the external environment remain trust
inputs. Bounded tests cover selected contracts, source replay, failure and core
checkpoint resume. Early failures before the derived manifest require a new
work path. The historical seed and its historical monitor artifacts remain
distinct from the new v2 producer. A new direct seed must bind the selected
snapshot, current witness and physical/component data, Panama archive,
Caucasus source gate, current closure proofs, code and request hashes, and the
same artifacts in resume and core identity. The core now checks that the
Caucasus configuration exactly matches the pinned outer configuration, and
repeats that complete binding before publishing output. Historical route provenance must
not be represented as a proof from a new checker. Physical-mask producer
lineage and final production closure remain unverified.

`work-in-progress.patch` is a source preservation artifact against the local
`stage2-rss-runtime-20261105` baseline; `file-hashes.json` records exact base
and candidate bytes. The independently reviewed v2 seed producer and its
14-file freeze are separately committed under `scripts/v7-land/mainland-seed-l2/`
at PR4 commit `b2f4648f84825e8c19cc15d606ca6b278a263e09`. Applying this patch
alone does not assemble a working runtime: it needs the complete baseline,
the v2 producer in a separate directory, the Panama core validator from PR4
`56af1a0`, and the pinned Caucasus source-specific dependencies.
No map or selected Neon data was produced by these bounded tests.

For the bounded test paths, put top-level `test_*.py` files beside `runtime/`;
copy the separately published seed source into `runtime/seed-producer-direct/`
without overwriting its tests, and assemble the seven Caucasus modules in the
sibling `caucasus-audit/` directory. Some historical-handoff tests also require
their existing local qualified fixtures. These instructions do not enable the
review gates or establish a complete reproducible production environment.
