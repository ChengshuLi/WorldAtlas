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
dissolve an invalid overlap or shared edge. The shared `canonical_land` entry point
retains strict original-source semantics, including exact ±360-degree comparisons
between distinct source members. Its original periodic shared-edge rejection is
unchanged.

The trusted prepared-footprint consumer explicitly uses
`worldatlas-prepared-antimeridian-cut-v1` through `canonical_prepared_land`.
GeoJSON may represent one feature footprint as pieces cut at opposing ±180 edges
(RFC 7946 §3.1.9). In this declared representation domain, a periodic contact is
permitted only when its entire intersection lies exactly on a world seam, the
members occupy opposing sides and their interiors do not intersect. There is no
near-seam tolerance or geographic ID exception. Every member and the unshifted
short-edge combination must still be valid before clipping or union; positive
overlap of any size, real non-seam shared edges and mixed defects remain errors.
Disjoint members and valid point contacts remain supported. Naive flat-longitude
validity is not substituted for the short-edge method.

The consumer configuration is committed code, not feature metadata or a source
approval. Differential reports bind the same prepared domain to both complete
immutable inventories, their containing-file descriptors, release/hierarchy pins,
feature counts and sorted identity/geometry hashes. Unknown or altered bindings
fail closed. This representation decision changes no stored location pointset and
does not certify source authority, historical preparation, water or ownership.
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

### Selected native assignment conservation

The same trusted wrapper also compares `data/ownership-selection.json` when
present on either side. It reads immutable selected manifests and registered
comparison receipts, authenticates the independent original bounds identity and
parent roster, and compares complete affected native rows by stable owner ID.
Candidate code is never imported. The accepted v8 bank's retained whole fragment
transport is read as data; raw historical geography is not substituted for a
restored selected native asset.

Affected rows come from all changed whole native run-part ranges and changes to
the complete row table. Both whole containing parts are authenticated, including
canonical unshuffled words; full row width is compared. New unowned cells or a
transfer to another owner fails the gate. New assignments remain gained coverage,
not physical source approval. Whole decoded part cohorts are discarded before
the next genuine bounded acquisition; metadata, row tables, runtime and live
representations count toward the complete phase.

This native test does not detect sub-cell polygon gaps. The existing polygon
detector remains unchanged. Selected pointset comparison and a complete current
effective-neighbor exclusion index are the second deliverable of #1569; historical
native camera bounds do not supply that proof.

There is currently no committed additive ownership selection. Extra/unknown
selection fields, removal of a native selection and changed native grid domains
fail closed rather than select a staged proposal or ignore unsupported effective
geometry. The full repair-ledger preservation comparator retains zero-cell
primitives as well as assigned primitives, but its active selection hook must be
integrated with the normal reviewed additive activation contract before use.
No files in coordination namespaces are automatically selected or activated.

Focused controls live in `test/effective-geographic-regression.test.mjs` and invoke
both the immutable reader and real trusted wrapper with complete small synthetic
Git fixtures. They are safeguards, not new geographic source approvals.

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

### Complete selected-source prevention certificate

The selected continuous gate reads complete ordinary source bodies from the
committed world index and any explicit, whole-byte selected overrides. Its
`complete-selected-source-pointsets:v1` certificate covers the full unique owner
roster, original record order, containing-body hashes, complete per-record
geometry hashes and coordinate-derived conservative exclusion bounds. Camera
bounds cannot exclude a neighbor. Both baseline and candidate certificates are
required; changed targets are compared against each other and every possible
unchanged neighbor using complete original pointsets.

The geographic release's previously qualified footprint digest is separately
recorded as historical authority with `recomputed:false`. Source-file traversal
is not the legacy global `localeCompare` digest order. The certificate does not
claim to recompute that scientific output; it authenticates the whole selected
source bank and every actual pointset under its own explicit domain. Altered,
omitted, duplicated or misjoined source bodies fail closed. This separates
once-qualified scientific custody from normal provenance enforcement.

A future committed `additive_release` hook names one whole typed sidecar, never
scans proposal files. It preserves the complete native base selection and binds
the exact runtime envelope, ordinary ledger/delta/owner assets and append-only
original authority registry. Each authority retains its original issued source
and native requests, preimage, complete publications/inventories, operating
receipts and code/runtime/input provenance. Batch hashes are not stable policy
identities. Per-component authority and zero-cell geometry must remain unchanged
when additional independently authenticated authorities are appended.

Effective coverage means literal BASE OR complete ADDITION primitives. The
trusted wrapper passes those separate, unchanged polygons to the original
preparation/comparison functions; it does not persist a dissolved OGC polygon,
round coordinates, use MakeValid or suppress coverage loss. Internal intersections
between primitives of the same stable owner are not competing-owner overlap.
All other loss/overlap/invalid-geometry findings remain failures. Native checks
compare virtual combined rows against every original owner and reject delta
cells that were previously assigned. No repair or release is activated by this
checker, and source-relative qualification does not establish physical water,
administrative or historical truth.

The cold certificate retains one conservatively merged coordinate rectangle per
owner and complete identity/index/parent tuples. It does not repeat camera fields
or substitute bounds for actual source geometry. All original whole owner/camera
custody and carried metadata remain authenticated and charged to the acquisition
phase. A seam-spanning original member expands the merged longitude interval;
merging never excludes a neighbor. After each whole containing body leaves its
helper frame, the trusted cold child uses authenticated native GC (`--expose-gc`)
to reclaim dead source objects. Missing or replaced GC refuses; this changes
acquisition lifetime only, without changing source pointsets or polygon methods.
