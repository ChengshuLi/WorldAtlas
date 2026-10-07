# Differential geographic regression detector

`scripts/check-geographic-regression.py` compares two immutable Git commits. It
reads the complete location inventory through `data/world-index.json`, preserves
whole-file SHA-256 pins for every input part and the hierarchy/grid/release files,
and verifies the current release pointer against the actual retained file.
Uncommitted checkout changes cannot replace its inputs.

The low-level detector and trusted workflow enforcement are separate components
of #920. The enforcement wrapper is described below. Source review,
hierarchy/crosswalk/certificate checks, derived-product validation and publication
remain separate requirements; scoped source-backed water adjudication is described
below.

```sh
python scripts/check-geographic-regression.py \
  --baseline BASELINE_40_CHARACTER_COMMIT \
  --candidate CANDIDATE_40_CHARACTER_COMMIT \
  --out NEW_REPORT.json
```

Install the committed Python requirements. The output must not already exist and
must have no symlink ancestor. Exit status zero means no new detected regression;
one means new lost coverage, new overlap, or invalid/unsupported geometry. Input,
hash, size and output errors fail closed. A report is diagnostic evidence, not a
geographic approval or proof that mapped land belongs to a particular province.

The comparison follows short, straight longitude/latitude source edges. It uses
the versioned shared geometry helper to align holes and split the date line.
There is no snapping, simplification, implicit MakeValid or area cutoff. Positive
areas are compared in source-coordinate space; the report labels square degrees
explicitly and does not describe them as square metres. Unsupported geometry is
reported rather than silently reinterpreted.

Original multipart members are validated together before clipping or union can
dissolve an invalid overlap or shared edge. This uses the declared shortest-edge
longitude domain, including exact ±360-degree comparisons between distinct source
members. A valid single polygon split at the date line is not mistaken for two
original members. Disjoint members and valid point contacts remain supported;
positive overlap of any size and invalid shared-edge contact fail without an area
waiver. Naive flat-longitude validity is not substituted for this periodic domain.
Baseline defects remain explicit, even if the candidate corrects the defect:
invalid baseline geometry cannot certify the differential comparison.

An unchanged inventory still passes geometry validation before success. Already
validated baseline shapes can be reused for byte-identical candidate geometries;
invalid shapes are never reused as valid results.

For changed footprints, all locations enter the neighbor index. The detector
compares the union of affected baseline and candidate locations, reporting each
piece of previously covered geometry that becomes uncovered. It also compares
each changed location's pairwise overlaps with all relevant neighbors, reporting
only overlap newly added relative to the baseline. Existing unchanged gaps and
overlaps do not become new regressions. Gained coverage is reported separately;
it still needs source review. Changed stable IDs and source metadata alone do not
establish a valid identity migration.

Each finding retains its full GeoJSON shape, representative coordinate, bounds,
changed and neighboring stable IDs, and their before/after normalized geometry.
The report also retains their original geometry hashes, containing-file pins and
original metadata. The representative coordinate locates the finding; acceptance
must review the entire shape, including all pieces and holes.

Engineering should repair a shared boundary jointly using reviewed sources, or
document an intentional shoreline/water correction with exact source evidence.
A lake enlargement therefore still produces a review blocker: geometry alone
cannot certify water. The low-level detector has no exception or automatic repair
path. Unknown hydrology stays explicitly unverified. The global gap inventory in
`GEOGRAPHIC_GAP_AUDIT.md` remains the separate inventory of existing candidates.

Controls in `test/geographic-regression.py` cover isolated and combined neighboring
changes, valid joint repairs, unchanged gaps/overlaps, newly added overlap,
islands/lake holes, deletions/replacement, thin gaps, tile edges, the date line,
invalid polygons, immutable input reads, release hashes and exclusive outputs.
The Node test wrapper includes them in the existing full regression inventory.
Passing detector controls alone does not install enforcement; the separate
workflow jobs below invoke the check on exact PR and combined merge commits.

## Trusted premerge enforcement

The PR and serialized queue workflows run a separate read-only geography job.
It checks out the immutable trusted baseline, fetches the proposed commit as
Git data, and executes `python -I -B scripts/run-geographic-check.py --fetch
--out geography-check.json`. Candidate scripts and reproduction commands never
run. The complete scripts namespace must match baseline bytes; untracked import
shadows, symlinks and cached bytecode are rejected. Dependencies come from the
trusted baseline requirements.

Unchanged live input blob inventories produce an explicit `not-applicable`
receipt, with no claim of fresh polygon validation or worldwide gap clearance.
Changes to indexed parts, the index or geography/release pins invoke the full
immutable detector. New loss, overlap or invalid geometry fails the job. The
queue requires fresh geography success even when application tests reuse an
exact-tree proof; an advanced baseline still requires a new integration.

Rollout has one bounded bootstrap exception: the specifically named activation
branch can report unavailable baseline code only after trusted API code verifies
its exact head and complete changed-file inventory, including rename origins,
and rejects every live `data/` change. The combined queue job has no fallback.
Already-running older queue workflows fail closed after the new final merge
condition becomes active and must resubmit.

The trusted wrapper's separate water-adjudication protocol accepts only retained
lost-coverage findings supported in their entirety by original native physical-water
geometry and an exact-head independent source/geometry decision. It requires
explicit target, temporal, resolution and uncertainty suitability, rereads the
authority before final merge, and rejects every additional unreviewed combined
finding. New overlaps and invalid geometry cannot receive this exception. This
does not establish global hydrology or approve administrative ownership. Existing source,
identity, crosswalk, regional certificate, content and publication requirements
remain in force.
