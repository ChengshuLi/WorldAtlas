# Unreviewed shared-edge investigation checkpoint

This branch is a resume checkpoint, not a mergeable repair, evidence approval,
installed geography, or completed worldwide fix. No PR has been requested for it.
Issue #991 remains open; global audit work proceeds separately under #973.

Evaluation inputs are immutable Git blobs at
`06bf4087bf5aec0e7071830ba61e99105f2c3697` (merged PR993). The scripts currently
read `HEAD` for prior source packets: resume only at this exact evaluation commit,
or pin their read function explicitly and re-run all affected checks. Current main
is not an interchangeable baseline. Original OSM sources and prior immutable
packets remain in Git; no original coordinates, sources, world footprints,
canonical grid, location properties, releases or historical facts were edited.

## Actual results

- Twelve synthetic exact-arrangement controls pass, including disconnected
  nested rings, islands, shared edges, overlap, bridges, point-touching holes,
  missing-edge rejection, retained nonzero tiny faces and nonzero tiny bends.
- Exact all-pair bounding-box reference examines all 6,109,260 segment pairs,
  finds 9,103 intersecting-box pairs and agrees with indexed exact noding.
- All eleven original complete neighbor footprints reconstruct with equal exact
  area and valid floating-point polygons topologically equal to originals.
- Raw exact exports and exact-collinear-only exports failed; their complete
  geometries are retained. Point-touching cycles must be separated while
  preserving every directed edge, not converted into one self-crossing ring.
- The latest *diagnostic* floating-point derivative is valid on both subjects.
  Each subject also has one collapsed, exact-zero-area rounded walk. Complete
  source-rational rings and those collapsed walks remain retained explicitly.
  This has not established acceptable source-rounding or boundary-tie semantics.
- The unchanged geographic detector checks all 49,625 immutable world locations:
  zero lost-coverage/new-overlap findings and zero geometry errors.
- The unchanged application compiler checks 4,257,008 cells: 953 changed cells,
  all inside the component, zero outside changes/lost owned/new multiple cells,
  and complete changed runs equal the prior reviewed PR990 candidate.
  Original encoded-grid parity is inherited from merged PR993, not re-decoded.
- Actual application-projected polygons remain invalid in BOTH baseline and
  candidate at `[177182.43908484, 110548.801388677]`. This finding is preserved;
  no projection repair or blanket validity exception has been accepted.
- The official State Department LSIB WFS endpoint returns a retained XML error:
  `Service WFS is disabled`. It supplied no usable independent border geometry.

## Resume

Read AGENTS.md, workspace/claim coordination and evidence review requirements.
Allocate an owned sparse author slot and check storage before reproduction.
Retain this branch/commit; restore prior inputs via immutable Git blobs. Copy only
these experimental `.py`/`.mjs` scripts into owned `.cache/shared-edge-991/`;
keep recorded JSON results immutable and generate new outputs in fresh scratch.
Dependencies actually used: Python3.12, Shapely2.1.2, NumPy2.3.5, pyproj3.7.2,
Node24. Never use another worker's mutable dependency environment.

Useful entry points: `test_exact_faces_v2.py`, `exact_world_v2.py`,
`exact_baseline_reconstruction.py`, `rounded_walk_diagnostic.py`,
`rounded_world_regression.py`, `rounded_grid_check.mjs`. Source packet initializer
`prototype.py` and `exact-world-case.py` are required. These exploratory programs
contain fixed scratch names and some overwrite their scratch products; preserve
recorded outputs and review/replace this behavior before any mergeable generator.

Next repair obligations: evaluate source/county identity/date/authority and
physical-water/registration limits; establish acceptable rounding and boundary
semantics with independent review; resolve or explicitly coordinate the old
projection failure under the complete affected scope; then full-world, native
encoded-grid, geographic/release/certificate/content revalidation before any core
integration. Do not turn this checkpoint or grid success into factual approval.
Worldwide detection, Portugal-Spain and other regional repairs remain open.

No browser, provider/database writes, deployment or publisher-chat message occurred.
