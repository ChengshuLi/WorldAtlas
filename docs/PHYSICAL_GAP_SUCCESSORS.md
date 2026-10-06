# Physical-gap audit successors

`scripts/physical_gap_successor.py` is a fail-closed decision layer for a
future immutable-input audit adapter. It does not run a detector, infer that a
preview is installed, or make source, water, ownership, or geographic claims.
The archived physical-gap reports remain tied to their original source and
software vintages.

An adapter must provide a complete snapshot with an immutable execution
commit, every source commit, and a byte-keyed closure. Each closure row binds a
whole-file descriptor to its source commit and a role. At minimum the roles
include the full source roster, executed code, software, declared domain,
hierarchy, release, native-owner provenance, and a complete ordered tile roster.
Tile geometry and metadata operands are separately retained as whole byte
payloads and mapped to stable IDs in exact per-layer detector query order. This avoids treating equal
bounding boxes, matching counts, a new pointer file, or a caller-provided
`verified` flag as proof that the run used identical geometry.

Before reuse, the helper rehashes every declared file for both snapshots,
checks that the payload inventory has no omissions or extras, and verifies
that the ordered tile IDs exactly match the pinned roster. It also checks the
complete original output closure: checked tiles carry candidates, residues,
original physical shore, missing-geometry digest, and water diagnostics;
unchecked tiles carry their blocking sources. Tiny polygons and point/line
remnants remain part of the exact retained output bytes. Unknown states can be
reused only if the same exact unknown records remain, in which case the result
still reports `unchecked`.

Geometry reuse compares only the declared detector computation semantics,
exact executable/runtime/domain file bytes, tile bounds, each layer's ordered
member IDs, and the exact geometry and metadata bytes supplied to the run.
Layers remain distinct for land, locations, invalid-land blockers,
invalid-location blockers, invalid-water diagnostics, and physical shore.
Changes in hierarchy, release-pointer, or native-owner provenance remain fully
authenticated but do not by themselves force geometry-tile recomputation when
the detector does not consume those values. A separate native-context stage
must still reassess every legacy status under the selected native grid; this
tile reuse decision cannot carry old statuses forward. Global connectivity,
contacts, crosswalks, and priority outputs also remain fresh global
computations. A changed source commit alone does not invalidate a tile if the
complete closure is retained and the exact local operands are proven
identical. Explicitly forced recomputation always wins. Changes to a member,
query order, metadata, executable/runtime/domain semantics, or unknown
inventory force recomputation. Empty-area predicates do not certify geometric
equality, and this helper has no area threshold or geometry-repair path.

The checked-in controls use synthetic bytes, not the worldwide source archive.
Production adapters must pin exact per-feature bytes passed to the detector,
not hashes asserted by metadata; use `verify_decoded_relation` to bind whole
encoded gzip bytes, the exact number of gzip layers, and retained decoded
bytes; prove complete encoded and decoded source closure; account for every
tile and output; and run the committed producer twice before publishing any
new diagnostic packet. `decode_gzip_layers` accepts one to three explicit
single-member layers and rejects truncation, trailing bytes, and decoded-size
overflow. Evidence limits, original measurement vintage, and unresolved
source/physical-water questions remain unchanged.
