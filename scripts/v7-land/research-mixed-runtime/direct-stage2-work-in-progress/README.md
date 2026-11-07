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

This later local snapshot additionally rejects altered or omitted Caucasus
outer/core bindings and compiles verified Caucasus source bytes directly, rather
than accepting shadow modules or cached bytecode. These changes have bounded
unit tests; the real full outer and post-return source replay remain untested.

This local successor additionally includes dependency preflight and the atomic
no-replace portability change. Linux uses renameat2(RENAME_NOREPLACE); macOS
uses renamex_np(RENAME_EXCL), with no unsafe fallback. Twenty-three bounded
Linux/core tests and an independent review passed. A separate Darwin arm64
syscall test verified success, EEXIST and ENOENT, but did not test this complete
patch. The combined patch was reapplied to its listed baseline and all 30 file
hashes matched. It remains local, unreviewed as a whole and unpublished; the
separately denied invocation-helper review has not been admitted. The Ural
source-gate candidate and newer Ural freeze updates are not included.
The separate Caucasus gate code is not included in the patch. The local runtime
now stages the PR4 d186571 isolation changes; the 158-test bounded suite passed
against them. Actual-source replay under those exact pins is still needed.

This later local snapshot includes the independently reviewed Ural core source
crosswalk. It requires all seven construction roles exactly once; synthetic
manifest tests and the combined 168-test bounded suite passed. It does not
include the Ural replay gate or producer integration, which remain separate.
This is not an end-to-end validation or a selected global revision.
