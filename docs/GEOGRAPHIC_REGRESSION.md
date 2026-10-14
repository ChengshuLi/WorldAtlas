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

Selected repair validation is map-cell scoped. Both warm checkpoint reuse and
cold fallback require complete native conservation and source-supported target
identity. Every new component must produce its own actual current-gap-to-target
cell witness. Continuous polygon overlap and sub-cell gaps are outside this
scope; the wrapper does not run the polygon detector or import Shapely for a
selected comparison. The raw detector remains available for nonselected source
geometry checks.

Focused controls live in `test/effective-geographic-regression.test.mjs` and invoke
both the immutable reader and real trusted wrapper with complete small synthetic
Git fixtures. They are safeguards, not new geographic source approvals.

The PR and serialized queue workflows run a separate read-only geography job.
It checks out the immutable trusted baseline, fetches the proposed commit as
Git data, and executes `python -I -B scripts/run-geographic-check.py --fetch
--out geography-check.json`. Candidate scripts and reproduction commands never
run. The complete scripts namespace must match baseline bytes; untracked import
shadows, symlinks and cached bytecode are rejected. Dependencies come from the
trusted baseline requirements for general regression tests. The selected geography
job uses only Python standard-library code and Node; it does not install the
polygon dependency set.

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

### Selected checkpoint identity and source support

An accepted checkpoint retains the complete stable owner/index/parent roster,
whole source identities and actual native result. Append-only transitions derive
the next complete certificate arithmetically from unchanged accepted base rows
and actual literal additions. New target geometry is still projected from its
pinned source body and independently joined to the approved target; unchanged
neighbors are not projected for a polygon-only overlap check.

A committed `additive_release` sidecar binds the exact runtime envelope, complete
ledger/delta/owner assets and append-only original authority registry. Each
authority retains its issued source/native requests, preimage, publications,
operating receipts and executed code/runtime/input provenance. Existing records,
including historical zero-cell components, cannot be omitted or rewritten.

The current joint producer emits four native checkpoint products. See
[accepted checkpoint handoff](ACCEPTED_SELECTED_CHECKPOINTS.md). Original polygon
reports stay archived; they are not a second active acceptance format.

The optional `artifact_consumption` selection binds an ordinary whole qualified
product certificate and an independently registered whole review API capture.
The renewed Arctic interface includes a complete gzip release-product catalogue:
the complete certificate's inline roles plus 343 ordinary product roles, with unique space/path keys and
ordered registry path, compressed hash and decoded payload hash joins. Both full
catalogue and registry inputs are prospectively admitted before decompression.
This authenticates the once-qualified application provenance; the prevention gate
still reads its own selected native/source inputs and never executes a candidate
installer or claims it has installed all catalogue products. Original authority
captures remain historical evidence; each renewed certificate needs its actual
independent review binding.

Role counts are derived from that authenticated union, rather than fixed to an
older certificate. The original registered interface has 137 inline roles (480
total); the independently registered application-representation successor has
190 inline roles (533 total). Its ordinary descriptors without a `space` field
retain the original consumer's root-space interpretation. Explicit `prior` and
`image` references remain distinct. These are custody references, not a claim
that the prevention gate opened or executed 533 files. The same 512 actual-input,
32 MiB whole encoded/decoded member and 256 MiB complete-phase caps still apply.

The gate also admits and reads both complete code and qualification inventories
before validating their source-policy and original operating joins. Historical
grouped entry declarations stay historical; newer shared and entry-specific
critical pins must match the complete application input roster. All entry
profiles remain source custody here: the trusted prevention reader executes no
candidate code and does not label another application's entry as its own
execution. Actual application callers still authenticate their current execution
closure separately. This compatibility change neither repeats scientific
qualification nor approves source facts, selection activation or deployment.


The normal PR and combined-tree package checks target Cloudflare through literal
`npm run build:cloudflare` workflow commands. This target is immutable workflow
content, so an unbound repository variable cannot change the target after a
successful proof. The separate deployment-budget workflow keeps the explicit
Site builder and its existing reserve gate. The historical `Build hosted assets`
step name remains for the unchanged integration-proof contract; it does not
claim a live-host migration or deployment. The earlier mutable package-profile
routing draft was superseded before publication.

An independently registered authority may explicitly declare the fourth
`build-cloudflare-inner.mjs` entry profile. Its complete critical custody and
entry-wrapper roster must be authenticated alongside the existing profiles.
Historical authorities retain their exact two- or three-entry schemas; no new
review anchor is inferred from a draft certificate.


### Whole native side acquisitions

The trusted selected-native comparison acquires baseline and candidate containing
parts in separate completed helper frames, including independent whole-member
frames within each side. A row crossing a native-part boundary joins exact interval
ordinals from both whole members without retaining both native buffers. Each frame
authenticates whole ordinary
or packed transport files, encoded/decoded pins and canonical unshuffled words.
It returns a compact, complete ordered interval projection for the admitted rows,
plus their whole input custody. It returns no containing transport or whole native
word buffers. The candidate phase charges that entire baseline projection together
with both selected metadata views, rowtables, code, installed runtimes, custody and
output reserve before opening candidate bodies. The original interval conservation
function then compares every admitted row.

Rows sharing both containing-part rosters are grouped. If a group cannot fit the
complete prospective side/carry cost, it is split into smaller exact row groups;
repeated whole-part acquisitions are recorded in their genuine phases. No affected
row is omitted or compared twice. An individually oversized complete row refuses.
All 32 MiB whole encoded/decoded member, 256 MiB phase and 512 opened descriptor
limits remain. A prior oversized paired attempt stays refused. This changes buffer
lifetime and admission, not scientific geometry/native reconstruction, ownership
selection, source approval or activation.


## Permanent visible-gap repair eligibility

Every new gap repair must change an actual displayed ownership cell. All thematic
and hierarchy modes use the same fixed native ownership grid; changing a mode
only changes its presentation. Eligibility is visibility at a supported close
zoom, not guaranteed visibility in the initial world overview.

The historical 95,173-component source-relative geometric inventory is not a
visible-gap or repairable-gap denominator. Preserve it as geometric evidence.
Its older one-cell probes include 65,032 positive witnesses, but the remaining
30,141 failed/unknown probes are not proven invisible, and none of these counts
is a current selected-map census. A current complete visible inventory has not
been established by this implementation.

Use `screenNativeGapCandidates` in `scripts/check-effective-geographic-regression.mjs` before
expensive source/native repair work. Supply the exact candidate geometries,
pinned normative latitude bytes and complete current effective owner rows,
including the selected cumulative patch. It calls the renderer's exact native
sampling operator. A positive result requires an unassigned native cell inside
the candidate; neither area nor bounding-box size substitutes for that witness.
No minimum island fill or separate thematic-mode rasterizer is introduced.

- `visible`: at least one current owner-zero witness. Partial scans retain a
  lower bound and null full counts.
- `invisible`: the complete relevant native row scope was checked and yields no
  current owner-zero cell; distinguish no native sample from already covered.
- `unknown`: an incomplete negative scan. A failed representative probe stays
  here until a complete relevant scan establishes otherwise.

Rows bind `current_selection_sha256` (canonical sorted-key JSON plus newline,
including the additive selector), `patch_sha256` (the pinned whole patch bytes),
`geometry_sha256`, source family/product, native containing assets, bounds and
required/checked half-open row extents. Share <=4096-row native blocks across
candidates and group by source and containing assets; do not rescan all 262,166
latitudes separately for each global inventory component. Visibility is an
execution prerequisite, not source/target approval.

At the actual requested baseline-to-candidate native comparison, both the cold
and checkpoint paths refuse new zero-cell primitives. Each new positive
primitive must have a literal native sample changing from owner zero to its
approved target in the actual complete before/after rows. A positive total or
an unrelated sibling's cell is insufficient. Existing accepted zero-cell rows
and historical checkpoint traversal are preserved unchanged. The result's
`repair_visibility` lists the new components and exact cell witnesses.

Current rebind validation authenticates the original executed code, request,
issuer and output bytes, then independently reacquires current source/native
operands and recomputes the complete result. An unrelated change to today's
validator or wrapper does not require a historical generation registration.
Original source authority, numerical schemas, full result equality and owner
conservation still apply.
