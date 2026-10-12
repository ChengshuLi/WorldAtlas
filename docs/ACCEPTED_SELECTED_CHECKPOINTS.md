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
execution lineage, native and original strict Python outcomes and the complete
present/absent route census before creating its own checkpoint capability.

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
and original strict Python results. Its optional `checkpoint` object has version
`1`, kind `selected-checkpoint-products-v1`, and a `members` array. Each member
has a fixed `name`, exact `bytes` and `sha256`; gzip members additionally bind
`decoded_bytes` and `decoded_sha256`.

The complete supported roster is:

- `derived-certificate.json.gz`, `derived-facts.json`, `derived-publication.json`
- `facts.json`, `operands.json.gz`, `publication.json`
- `checkpoint-routes.json`
- `operating.json` only when an actual producer emits it

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

## Completion criterion

Synthetic transport/adverse controls establish the changed boundaries only.
Automatic advancement is complete only when a genuine accepted batch A supplies
batch B's actual baseline through the joint entry point, with original results,
lineage and measured timing retained and no cold authentication replay. The
initial reviewed seed and that actual adoption remain distinct from shipping
transport code.
