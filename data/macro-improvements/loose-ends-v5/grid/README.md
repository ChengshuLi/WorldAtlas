# Fixed-grid repair preparation

Issue #540. Source-backed stage only; no map, database or published release change.

`held-islands.geojson` preserves all three existing OSM dry-land rings for each
of Kingman Reef and Gardner Pinnacles. It verifies original compressed and raw
source hashes. One whole named island/reef is one location, not one location per
ring. Both keep their previously approved macro routes. Kingman uses the existing
Line Islands province instead of creating the previously proposed separate
province; Gardner uses the existing Hawaii province. This local grouping does
not certify regional interiors or change their fixed macro assignments.

Run `node data/macro-improvements/loose-ends-v5/grid/check.mjs` for the isolated
source-centre check. Add `--full` for the complete collision-resolved ownership
check covering the current published locations plus these two staged additions.
`--size=N` accepts an explicitly fixed candidate width, not a navigation setting.
The check changes only evidence files in this directory.

Run `python3 data/macro-improvements/loose-ends-v5/grid/prepare.py` to reproduce
`prepared/candidate-patch.json.gz`, its creation proofs and source wrappers.
The generic land-creation validator checks exact raw geometry, nonoverlap and
complete parents against all current locations. The retained v3 identity scan
is preserved as earlier archive evidence; a fresh private/live scan remains a
separate root publication gate.

## Bounded candidate

The existing 262,144-wide canonical grid hits neither held location. A fixed
266,240-wide grid is only 1.5625% finer and hits Kingman four times and Gardner
twice. A fixed 524,288-wide grid hits them six/four times but approximately doubles
the existing ownership memory and download. Source-centre hits depend on grid
alignment: a finer candidate cannot be assumed to preserve every earlier hit.
The full ownership check is therefore required for every proposed candidate.
266,240 is a useful tested candidate, not proof of the globally smallest possible
width or permission to skip the final v5 footprint audit.

Current published grid: 28,805,134 runs, 232,538,224 decoded ownership bytes and
47,586,913 compressed bytes. Current package files plus hosting configuration
total 263,541,551 bytes; the 256-MiB limit leaves 4,893,905 bytes. The preceding
native archive was 263,925,760 bytes; archive overhead must also be remeasured.
Those measurements predate all v5 repairs and are not a final package-fit claim.

## Integration requirements

- Declare `GRID_WIDTH` as the exact integer width and derive `GRID_ZOOM` as
  `Math.log2(GRID_WIDTH / 256)`. Do not derive the integer width by rounding an
  exponent after storing a fractional zoom. Leaflet accepts fractional project
  zooms; GPU rendering, canvas fallback, selection bounds and picking already
  use the shared zoom. Audit their consistency against manifest size.
- `scripts/audit-grid-resolutions.mjs` already rescales coordinates for fractional
  zoom but its CLI rejects zooms above 10 and assumes powers of two in world size.
  Add an explicit integer-size candidate option before final packaging. The
  compact ownership codec and shader accept arbitrary integer sizes.
- Recompile the final complete v5 footprints once, validate every location's
  collision-resolved cells, WGS84 area distortion and all source masks, then
  rebuild bounds, membership and hash-checked transport parts together.
- The small increase remains within the existing adaptive 4096 texture layout
  if measured run count stays near this candidate. A doubled global grid likely
  needs larger devices or new split-texture support; do not silently drop 4096
  devices. Check desktop/mobile viewport, canvas fallback and actual upload bytes.
- Navigation must keep using the one cached grid. Verify zero ownership
  recompilations and texture uploads while zooming, panning and resizing.
- Measure the complete hosted build/archive. Existing R2 serves registered
  evidence/media through `/api/media/:id`; ownership assets are currently bundled
  into the Site. If necessary, move noncritical report/evidence assets to R2 with
  checksums and compatible links. That requires build/router work, not merely an
  R2 bucket setting. Do not delete archived evidence to gain package headroom.
- Before creating identities, check live/current/archived registries and claims;
  preserve predecessors, historical claims, source bytes and modern-only dates.
