# Accepted selected-checkpoint handoff

A batch's provisional products become reusable only through the normal accepted
merge boundary. A locator, a candidate certificate, a local digest or an uploaded
ZIP alone cannot qualify a checkpoint. Scientific/source/publication limits are
unchanged.

## Authority and lineage

`acquireAcceptedCheckpoint` reads the existing bot `worldatlas-merge-result:v1`
receipt, checks the actual merged PR with the same verifier used by the queue,
checks the accepted/tested trees, and authenticates the originating geography
run, job and artifact. It returns an invocation-private handle. The selected
qualifier independently checks complete selectors, source/native bindings,
execution lineage, native outcomes, the applicable continuous result and the
complete present/absent route census before creating its own checkpoint capability.
Full-geometry artifacts still require their original strict Python success.

PR provenance uses `merge-integration-checks.yml` / `pull_request`; the workflow
head is the reviewed PR head. Queue provenance uses `worker-merge.yml` /
`workflow_dispatch`; its workflow head is recorded separately from the reviewed
PR head and tested candidate. Failed-job-only reruns retain the actual original
producer attempt/job/artifact. No result is relabelled as a new execution.

The handle stays inside the trusted joint Node invocation. It is never serialized
between the Python wrapper and a new Node child. Releasing it expires access.
Original predecessor acceptance remains lineage; it is not a request to reacquire
or rerun historical science.

## Authenticated artifact

`geography-check.json` remains the authenticated root, including complete native
and either the original strict Python result or explicit pixel-only applicability.
Its optional `checkpoint` object has version
`1`, kind `selected-checkpoint-products-v1`, and a `members` array. Each member
has a fixed `name`, exact `bytes` and `sha256`; gzip members additionally bind
`decoded_bytes` and `decoded_sha256`.

The historical full-geometry roster is:

- `derived-certificate.json.gz`, `derived-facts.json`, `derived-publication.json`
- `facts.json`, `operands.json.gz`, `publication.json`
- `checkpoint-routes.json`
- `operating.json` only when an actual producer emits it

An eligible visible native-pixel append-only comparison instead retains exactly
`derived-certificate.json.gz`, `derived-facts.json`, `derived-publication.json`,
and `checkpoint-routes.json` (plus optional actual `operating.json`). It sets
`validation_stage` to `native-passed-continuous-not-applicable` and
`continuous_publication` to null. Its continuous report explicitly says
`status:not-applicable`, `scope:visible-native-pixel-repair-v1`, and has no polygon
result. The complete coordinate certificate is derived arithmetically from the
unchanged admitted base and actual literal additions; it is not polygon overlap
approval. Do not add empty continuous files or fabricate a passing polygon test.

This scope requires a genuine authenticated transition and successful complete
native conservation, including every changed row and each newly selected
component's actual unowned-to-its-own-target cell witness inside its exact native
polygon. Empty witness lists are ineligible. An actual baseline-to-candidate Git
diff permits only selector/locator/package-input changes and newly added inert
engineering evidence. Code, base/source, old evidence or other geography changes
keep the original continuous checks. Cold comparisons retain those checks too.
The native and independent source qualification requirements remain unchanged.

The provisional derived publication keeps `accepted_checkpoint:false` and its
original validation stage. Acceptance is external custody, not an edited boolean.
The successful trusted job supplies terminal execution authority; the transport
does not fabricate an operating or cleanup measurement.

The in-memory reader verifies the trusted root hash before interpreting member
descriptors. ZIP entries must be ordinary fixed files, unique and exactly listed;
local records must tile the local-file area without gaps or overlap. ZIP64,
traversal, links/directories, contradictory sizes/CRCs, malformed descriptors,
compressed trailing bytes and excess decoded gzip output are rejected. Nothing
is extracted into the trusted checkout. Legacy one-member artifacts remain
reports and cannot provide checkpoint products.

The existing ordinary/report and archive limits remain 32 MiB and 40 MiB.
Checkpoint acquisition additionally admits the complete transport, decoded JSON,
metadata and live representation union before allocation, within the current
caller's allowance and a 256 MiB phase ceiling. Metadata pages and accumulated
metadata are bounded. Historical operating limits never grant a current memory
allowance.

## Durable next-batch input

After a genuine complete artifact is accepted, run the following from the next
batch's managed checkout with the existing authorized GitHub identity:

```
node scripts/accepted-selected-checkpoint.mjs ChengshuLi/WorldAtlas PR_NUMBER REQUEST_ID REVIEWED_HEAD coordination/engineering/BATCH/FRESH_DIRECTORY
```

The parent batch directory must already exist. The fresh child directory must
not exist, including as a dangling symlink. This writes the exact accepted
`geography-artifact.zip` and then `selected-checkpoint.json` last. The latter is
an untrusted locator suitable for the next batch's `data/selected-checkpoint.json`:

```json
{
  "version": 1,
  "kind": "accepted-selected-checkpoint-locator-v1",
  "acceptance": {"pr_number": 123, "request_id": "the-existing-queue-request", "head": "the-reviewed-40-character-head"},
  "retained_artifact": {"path": "coordination/engineering/BATCH/FRESH_DIRECTORY/geography-artifact.zip"}
}
```

Keep both files in that batch's ordinary evidence. No per-batch executable or
accepted-checkpoint catalogue change is needed. A retained ZIP is admitted only
as an ordinary bounded file and is compared with the artifact hash in the actual
accepted receipt. A newly computed local hash cannot grant authority. The exact
retained copy may replace a missing/expired original artifact; access denials,
contradictory metadata and corrupt copies do not trigger fallback.

The locator is excluded from scientific route equality but remains an explicit
applicability/admission dependency. Changes to it or its retained whole archive
force proper reauthentication, including baseline-only changes during an
otherwise source-only PR. Unchanged selectors alone do not waive this boundary.

## Initial reviewed seed

The first complete hosted artifact cannot depend on already having a hosted
checkpoint. The initial rollout therefore adds one typed
`accepted-derived-selected-checkpoint-v1` row to the existing executing trusted-main
catalogue, after the combined joint implementation and its retained clean proof
are actually accepted. This is a one-time bootstrap, not a per-batch registration
step. The row pins the original certificate, continuous operands/facts, native
and original strict result, successful operating receipt, exact executing policy,
and complete inherited-plus-candidate route census. Historical proof bytes and
provisional publications remain unchanged.

The seed uses the same private derived-state admission as accepted artifacts,
with `trusted-main-derived-selected-checkpoint-v1` lineage. It does not claim
a hosted job receipt or cold acquisition. Current selectors, complete routes,
consumed policy and current memory allowance are still checked. Candidate data
cannot register itself in the executing catalogue.

A selected batch using that seed must pass the applicable native and continuous
scope rules and the normal hosted job/merge boundary, which creates its complete
accepted artifact. The following selected batch uses that artifact's normal merge receipt
and locator through `acquireAcceptedCheckpoint`; it requires no catalogue or
executable change. Those two real batch handoffs establish bootstrap and generic
advancement separately.

Warm admission runs before any optional full-bank prefetch. Only an explicit
legacy-cold decision starts that prefetch and the existing cold route. An
authentication contradiction or access denial remains an error.

## Completion criterion

Synthetic transport/adverse controls establish the changed boundaries only.
Automatic advancement is complete only when a genuine accepted batch A supplies
batch B's actual baseline through the joint entry point, with original results,
lineage and measured timing retained and no cold authentication replay. The
initial reviewed seed and that actual adoption remain distinct from shipping
transport code.
