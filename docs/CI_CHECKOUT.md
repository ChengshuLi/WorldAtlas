# CI candidate checkout

The final queue uses pinned `actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803`
to acquire the exact candidate emitted by trusted preparation. The job keeps
read-only repository access, disables persisted credentials, LFS and submodules,
and closes system/global Git configuration, hooks and credential helpers. No
candidate programme runs during checkout. Evidence-only and geographic checkout
roles remain separate.

Trusted preparation already authenticates the candidate's parents and complete
tree and compares reviewed bytes. It now emits that tree identity and the
existing sparse selection directly, removing the separate helper authentication,
custom Git executor, staging/promotion protocol and legacy fallback branch.

Complete regressions retain every discovered test across the existing three
shards and the actual hosted build/parity/runtime checks. In addition to the
existing `data/regional-review/` and `research/campaigns/` exclusions, ordinary
full checkout omits eight historical archive roots:

- `coordination/engineering/global-source-comparisons-b-package3-20261006/`
- `coordination/engineering/global-source-comparisons-a-20261006/`
- `coordination/engineering/global-source-comparisons-a-001-20261006/`
- `coordination/engineering/global-source-comparisons-b-20261006/`
- `coordination/engineering/reference-source-custody-20261007/`
- `coordination/engineering/complete-numeric-closure-diagnosis-20261007/`
- `research/geography/lithuania-latvia-gap-source-fitness-20261007/`
- `research/geography/shared-seam-prt-esp-20261006/`

These are exact whole-directory exclusions, not broad research or engineering
namespace filters. Their original files and history remain in Git; neighboring
roots remain checked out. Trusted preparation reads the authenticated candidate's
package definition and retains an entire archive root when any declared package
or verification path intersects it, including directory ancestors. Unavailable
or malformed definitions fail preparation. New actual regression consumers of
these archives must restore the needed checkout inputs through review.

Selected-data requests retain
the existing package/verification roles, ordinary engineering execution files
and exact reviewed expectations. The existing selector is evaluated against the
authenticated candidate tree; it grants no package, scientific or publication
authority. Unknown or malformed selection inputs still fail before acquisition.

The following canonical verification step independently checks the exact commit,
tree, detached HEAD, ordinary origin URL and absence of credential environment,
headers, helpers, include pointers and leftover action credential files. It then
disables origin promisor behavior and removes the partial-clone filter before
candidate commands run. Required historical regression inputs keep their
existing explicit acquisition. A failed checkout or verification cannot run the
build/tests or select a fallback workflow.

The pinned action owns Git transport and its existing fetch retry behavior.
Normal runner cancellation and the integration job's existing timeout own the
operation lifecycle. This does not retain the deleted helper's custom process
session or atomic directory promotion claims; the action operates in its normal
fresh isolated runner workspace. No new supervisor, cache or proof product is
introduced.

The accepted custom-helper runs spent roughly four to seven minutes in one Git
materialization command, with most time preceding file-update progress. Those
logs do not distinguish network transfer, packing or filesystem work. Replacing
the executor does not prove a speedup or diagnose the active Papua straggler.
Measure the next ordinary adopted run honestly. A duplicate local full Papua
checkout was declined because its exact retained files alone total 10.64 GB,
which would breach the local storage floor before Git object storage.

Earlier custom-helper rollout failures at a fixed 420-second cutoff, and the
later removal of that cutoff, remain historical evidence; they are not evidence
of a supported maximum acquisition duration. Source/scientific execution and
publication gates remain unchanged.

Focused controls use Node 24:

```sh
node --test test/ci-checkout.test.mjs test/merge-integration.test.mjs test/merge-integration-entrypoint.test.mjs test/package-inputs.test.mjs
node --test --test-name-pattern='stock checkout|canonical verification' test/trusted-workflow-checkouts.test.mjs
```

The first suite exercises the existing sparse role boundary with tiny real Git
trees, exact tree preservation, directory ancestors and adverse input layouts.
The second checks the actual workflow declarations and executes its real
candidate/credential verification against positive and adverse repositories.
Complete-profile controls also exercise every archive exclusion and neighboring
root with stock non-cone Git, declared package/verification overrides, actual
prepare outputs and all discovered three-shard test paths. They establish sparse
selection and identity, not full-size action throughput or execution of those
entire suites. Ordinary full hosted integration and the real package build remain
required before accepting this checkout change; measure that run before claiming
wall-clock savings. Preparation executes trusted main, so the omission change's
own integration uses the previous patterns; its first subsequent ordinary full
run establishes actual adoption. The earlier selected-data omission diagnostic was a bounded
check, not exhaustive proof that no process could read an archived Git body.
