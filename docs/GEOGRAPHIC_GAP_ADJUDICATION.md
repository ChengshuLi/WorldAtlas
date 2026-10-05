# Differential geography and reviewed physical-water losses

The trusted geography job reads immutable baseline and candidate Git blobs. It
never imports candidate code. Unchanged geography blobs establish applicability
only; they do not clear existing gaps. Changed footprints are checked against
whole affected locations and their neighbors. Newly lost coverage and newly
introduced overlaps remain raw findings, even when an exception is accepted.

A physical-water exception is limited to a measured `lost-previous-coverage`
finding in current reference geography. It does not assign a province, approve a
historical shoreline, certify a regional branch, or authorize publication.
Overlaps and malformed geometry cannot use this exception. Unknown physical,
temporal, resolution or target uncertainty blocks it. Existing release,
identity, certificate, content and publisher checks continue to apply.

## Preparing a proposal

First run the trusted checker against the proposed immutable geography inputs.
Retain its raw findings. A candidate's evidence manifest may declare
`geographic_adjudications`, an array of `{path, sha256}` descriptors, each also
listed in its owned outputs. Each dossier has exactly these fields:

- `version: 1`, `method_id: "worldatlas-geographic-water-adjudication-v1"`,
  `target_context: "current-reference-geography"`.
- `context`: the raw check's `trusted_code_inventory_sha256`,
  `baseline_input_inventory` and `candidate_input_inventory`. These bind the
  consumed input bytes and trusted scripts/src namespaces and package/policy bytes without a self-referential
  candidate commit digest. Changes to neighbors or trusted code require a fresh
  dossier/review; adding evidence alone leaves geography input inventories intact.
- `findings`: exact raw `{sha256, feature}` rows. Feature digests use shared
  Python `canonical_json`, including its final newline. Retain all geometry and
  before/after neighbor metadata; a centre point or bounding box is insufficient.
- `source_refs`: exact retained source/native feature references.
- `rationale`: explain the specific proposed loss and actual source limitations.

A source reference contains `source_id`, `path`, whole-original `sha256`,
`decoded_sha256`, `native_identity: {property, value}`,
`native_role: {property, value}`, and `native_geometry_sha256`. Keep original
source bytes and native properties. The native feature must be unique, valid,
and physically water; no geometry repair, invented label, buffer or tolerance
can create support. The union of selected original water polygons must cover the
**entire** loss. Natural Earth's coarse current lakes are not automatically
suitable for a narrow border stripe or a particular historical year.

The manifest source must declare retained, verified, licensed physical surface
water (`role: "physical-surface-water"`, `temporal_status: "reference"`). These
are author declarations checked against retained bytes, not independent factual
authority. The independent reviewer must assess provenance and target suitability.
Source restoration instructions, political outlines, unknown suitability and
legacy/report-only evidence cannot authorize this exception.

## Independent decision and same-head rerun

The normal exact-head `worldatlas-review:v1` receipt must substantively accept
both source and geometry domains. Its additive `geographic_adjudications` field
has `version: 1` and one `decisions` row for every dossier. Each decision records:

- `dossier_path`, exact `dossier_sha256`, and the same `target_context`.
- `target_water: "supported"`, `physical_provenance: "accepted"`,
  `temporal_suitability: "accepted"`, `resolution_suitability: "accepted"`,
  `target_uncertainty: "resolved-for-this-target"`.
- Explicit `source_limits` and `source_refs_sha256`, computed using shared
  canonical JSON including the final newline.
- Sorted, unique `finding_sha256s` covering every complete supported finding.

The read-only adapter validates the actual issue contract, canonical claim,
whole-file evidence and latest distinct review from GitHub. Candidate-local
approval files cannot replace these authorities. Request a same-head geography
rerun after a valid decision; the adapter does not require its own geography
check to be green, avoiding a review/check cycle.

The combined candidate must still match the dossier's consumed inputs and bytes.
Every actual raw finding must be covered exactly once. Additional combined gaps,
changed sources or newly unresolved uncertainty fail. The report retains raw
`status: "regressions-found"`, plus a separate scoped adjudication and gate result.
It never becomes global source approval or publication certification.

## Final queue check and rollout

The trusted geography step outputs the SHA256 of its exact JSON report. Artifacts
are named per attempt so reruns retain earlier findings. The merge job downloads
only that run's named artifact, inspects its bounded single JSON entry in memory,
and verifies the trusted output digest before parsing. It never extracts archive
paths into its privileged workspace. A green job alone is insufficient.

Immediately before the guarded merge, the queue rereads the actual latest source
decision and compares its authority digest, full review body binding and findings
to the combined report. Withdrawal or replacement requires a fresh check. Main,
reviewed head, claim, issue, evidence and application checks remain guarded.
Older in-flight queue workflows without the new trusted report outputs fail
closed after rollout and must be resubmitted. Local synthetic controls do not
establish hosted execution, real source approval, a repaired map or delivery.
