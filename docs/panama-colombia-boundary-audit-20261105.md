# Panama–Colombia boundary: source and pipeline status

Read-only inspection of the `continent-review-v1` Neon branch on 2026-11-05.
This is a draft research decision, not accepted geography.

## Selected data

Revision `v2-land-mainland-boundary-draft-1` selects
`panama_colombia_osm_admin_boundary` using `stored_linestring_v1`.
Its 5,254-vertex CRS84 LineString has canonical binary64 sorted compact GeoJSON
SHA-256 `cfbfbb514d0f6efff1c0c803ae5f0f0835225015568747bb8b1164f3bb6d0e17`.
The database provenance reports that 33 historical OSM ways joined using
current OSM node coordinates reproduced this hash. That statement is not
itself a retained coordinate input or a reproducible build.

The two linked catalog entries are provider-original OSM API responses:

- `worldatlas/sources/osm/panama-colombia/historical-ways-versions.json`,
  SHA-256 `b101f03f55339f4dfe26118f6b88f71ac5cd5acd25281eb6adb12c9db8836e0e`.
- `worldatlas/sources/osm/panama-colombia/historical-relations-versions.json`,
  SHA-256 `2f1107e182aa1c06245068754b80bd632be84c13858b940c39d10f04bc2e7a29`.

Their catalog provenance records full R2 readback verification. This audit
read the catalog, not the objects themselves. Both are classified as
supporting membership evidence; neither contains the node coordinates needed
to rebuild the line. These membership files do not by themselves reconstruct the line. The current
coordinate bundle described below supplies the missing source coordinates. Do not infer historical coordinate versions
from historical way membership. Exact V7 reconstruction is not required.

## Land assignment

The selected `north_america_mainland_region_v1` consists of the entire
boundary in forward order and `americas_exterior_closure_v1` in reverse.
The latter is a selected 14,541-vertex water closure with terminal references
to the same line; its SHA-256 is
`36d72849f2677a2a31250451d81c614d5e00e6b3228635470167a30ef1dbb940`.
Its proof is bound to a specific physical mask and must be rechecked against
the actual generation. The region stores six inside/outside witnesses.

`scripts/v7-land/mainland-seed-l2/regions.py` checks line hashes, ordered
joins, closure proof, polygon validity and witnesses. `seed_producer.py` and
the rasterizer use current physical components and the assembled region to
assign mainland cell centers; see the adjacent README for the input contract.
These are research-stage code and the README states that the complete
orchestrator remains gated for independent review. The Panama direct cut-graph
experiment in `scripts/v7-recovery/land/panama-direct-split-research-20261104/direct.py`
is explicitly retired at its entry point and is not the selected workflow.

The selected seed producer now verifies the pinned OSM archive against the
saved structured line before region assembly. The outer orchestrator and
current-generation physical inputs still need end-to-end integration and
independent review. A matching line hash alone does not establish geographic
correctness or complete land assignment. No geography changed.

## Follow-up capture

A subsequent capture of 33 current OSM way/full responses reconstructs the selected line exactly: 5,254 vertices and the canonical geometry hash above. The current way node memberships match the queried historical way versions, and both historical country relations contain all 33 ways. This is current coordinate evidence, not proof of historical node versions. The checked assembler and archive verifier are in `scripts/v7-land/mainland-seed-l2/`; five bounded tests passed. The archive is stored at `worldatlas/sources/osm/panama-colombia/way-full-20261105-04fe1adb295e.zip` (SHA-256 `04fe1adb295e93d78ee029b48351d2b0380d69ac631b47c909dffd538bbaf6c1`, 110,336 bytes); authenticated R2 readback matched byte-for-byte. Neon catalogs it as `osm-panama-current-way-full-bundle` version `capture-20261105-04fe1adb295e` and links it to the selected boundary as supporting evidence. It is a ZIP of 33 unmodified provider responses and a manifest, not one provider-original response. The verifier is wired into the direct seed producer; its real-source test uses a synthetic grid and closure. No map rebuild was run.

A read-only run of `scripts/v7-land/mainland-l2-draft/query-stage2-selected.sql` against the selected research revision returned the bundle once in `sources`, once in `source_lineage_assets`, and in the Panama boundary's source relationships. This verifies export availability; it does not mean the selected seed producer has consumed the archive.


## Selected closure against the stage-1 research mask

The exact water-only and terminal-aware checkers both accepted the selected
`americas_exterior_closure_v1` line against the available November 3 stage-1
research mask. Each checked 198,846 closed-cell visits, all water, including
both terminal cells. The terminal checker bound the first and last closure
points to the corresponding endpoints of the selected Panama line.

The physical rows SHA-256 was
`6cf4b928b6609b4d9c8fdd9264bb6f463a38a5d7376d6ffb0ffc43502284a468`,
the runs SHA-256 was
`1396fe9dfde48b65b6e5884089a5445682511fb47f9560ce06edd53c95d928d7`,
and the candidate physical report SHA-256 was
`8e8d7eb6514055a788c93055c825a0cfe103736c8221f21744f9e231ebcafa2e`.
The route and line hashes are recorded above. The water checker SHA-256 was
`5b01e11908293df6f941adbc391d4c9e7709f49c1b8ad60d46be0558d66ca6b3`,
and the terminal checker SHA-256 was
`08fd855bddd47dd2152ae0ac0fabd1e23e1d75db9e337a0af3a840a6787e1cb2`.

This was a **research screen**, not an approved production closure proof. The
physical report says candidate-only, and its use by the final selected outer
request has not been established. The v2 closure contract was assembled for
this screen; the pinned encoding-evidence file was taken from the current
checkout and has not been established as the historical mask producer. The
checker output's generic wording about an externally reviewed contract must
therefore not be read as a claim of such review. The screen does not establish
full-ring validity, original physical-source lineage, geographic authority,
or any historical V7 result. The actual selected generation must re-run its
closure verification against independently verified inputs.

The same physical rows and runs hashes appear in the earlier
`stage2-executable-pins-v1` runtime metadata for commit `267f7ef`. That is
evidence of reuse in that earlier qualified candidate, not confirmation that
the eventual direct-run outer request selects those inputs. The candidate
physical report pins its configuration (`c215b7b201d4c6b8c7fc54bd3e3a6cf69032c4e2a01f79c123f9954e8ca88668`),
land mask (`f7e3ca1067aed2814ce641f813da6d807b6d18eaffa0a42cac2782c699671463`)
and water mask (`0b632fe6dfb44b07b7df51b4b0e2c823e04c4858d70a2a05033ee76a81`),
but has no producer-code hash. Therefore the current `compose_physical.py`
bytes cannot be authenticated as the original producer from this report alone.
The builder must verify the actual selected snapshot, physical lineage request
and all pinned report-chain inputs against the final outer request, and seek
the original configuration and independent producer-code or execution record.
The existing `verify_physical_lineage.validate_combined` checks reported-chain
and selected-source consistency; it explicitly does not rerasterize or prove
which program produced the mask.

The selected region consumes the closure in **reverse**. A further run of the
v2 terminal checker used that exact orientation (canonical geometry SHA-256
`43845a84151c9debfca819d1f73975a6c9f5ba9c6ab75dc03303db4a0c676a16`)
and bound its start to the boundary's end and its end to the boundary's start.
It again visited 198,846 cells, all water. Its physical pins, encoding-evidence
hash, endpoint coordinates, terminal policy and complete contact result match
those recorded in the earlier qualified seed report (SHA-256
`8e2062312b1988af8eb4cd1a7fcba5b0f42fb765adc05b7cec4fa8a78a1cff77`).
The old and new checker and contract hashes differ, and the prior report's
encoding-evidence hash is not an independent execution record for the original
physical mask. The new proof remains a research screen under the limitations
above, not a promoted or final-generation proof.
