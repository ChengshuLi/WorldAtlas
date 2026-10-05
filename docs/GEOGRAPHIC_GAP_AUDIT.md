# Geographic coverage gap inventory

`scripts/audit-geographic-gaps.py` detects physical-reference land covered by no
location polygon. It complements `complete-coverage.py` (missing named territories)
and `audit-pixels.mjs` (representation of supplied polygons). Neither older check
establishes that neighboring location footprints meet.

Run with the committed Python requirements, an exact immutable input commit, and
a new output directory in the engineering job's owned evidence namespace:

```sh
python scripts/audit-geographic-gaps.py \
  --commit 5f6ab02338a07fd4b3d1cf82d58b96bc84b70312 \
  --output coordination/engineering/YOUR-JOB/global-vintage
python test/geographic-gaps.py
```

The default declared domain is longitude −180 to 180, latitude −60 to the Web
Mercator north limit. Antarctica is excluded. Five-degree tiles keep clipping and
union work bounded. `--bounds WEST SOUTH EAST NORTH` and `--tile-degrees` support
regional pilots. Original inputs are read from Git blobs, not mutable checkout
files. Output never overwrites an existing vintage. Run the local workspace storage
check before reproduction, as required by `LOCAL_WORKSPACES.md` on current main.

The land reference is the retained Natural Earth 1:10m physical layer at revision
`ca96624a56bd078437bca8184e78163e5039ad19`. Its nested retained bytes and original
hash are verified against the original source receipt. It is public domain. This
coarse physical reference does not certify detailed inland water, coastal boundaries,
small islands, present-day conditions or political affiliation. A candidate can be
a river or reservoir omitted by that reference, a coastline/vintage mismatch, or
a missing geographic seam. No outside-reference cell is certified as water.

The bounded gzip GeoJSON bundles retain every positive planar-area polygon, including thin
strips and small islands. Each fragment retains its tile ID and bounds. Tile
intermediates are consolidated losslessly into bundles before completion. There
is no area cutoff, simplification, nearest-location
fill or source geometry repair. The report inventories input/output hashes,
software, bounds, invalid locations, blocked tiles and measurement errors.
Invalid location geometry blocks affected tiles; invalid physical reference stops
the run. The shared WGS84 source-edge area helper measures candidates in square
metres. Measurement failures retain the geometry with null area; totals include
only successfully measured fragments and do not imply a complete error-area total.

`touches_reference_shore` removes artificial tile edges from the clipped physical
reference boundary before checking contact. It is a triage indicator, not a proof
that a fragment is water. `touches_tile_edge` records where the same connected gap
may continue into another tile. IDs are tile/fragment IDs, **not globally connected
gap IDs**. Nearby locations are those intersecting a 0.02-degree diagnostic buffer;
that angular buffer is not a physical distance, proof of adjacency, or ownership
claim. The nearest-location label also uses planar degrees only for identification.

The initial global inventory is the first detection stage. Joining fragments across
tile boundaries, detailed hydrology checks, overlap/edge/parent-tier audits and
comparison with the actual canonical integer grid remain distinct checks. Review
interior multi-neighbor seams first, then source provenance and water evidence.
Actual footprint corrections require a coordinated reviewed release covering the
affected neighbors and revalidation; the detector never edits the map or database.
