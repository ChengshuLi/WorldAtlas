# Reader adaptation — PASS WITH LIMITS

Reviewer: `/root/physical_remainder_source_limits` (Worker6).

**The corrected actual body is approved for the scoped source-reader adaptation.** `worker1-source/read_points.py` is 13,109 bytes, SHA256 `250bbdfe05bc55b1e2a19a3affce7d0ded10766508376e40a47a328a0595d12f`. No remaining launch blocker was found in this targeted review. Root controls the actual launch; this review creates no new permission gate or exclusivity requirement.

The initial actual body was 12,954 bytes, SHA256 `db486eebffdf898ffe78b5ebe353d540e2c19eb6abc0f8ed3e85cff97f6f5c09`. I read the complete body and parsed its syntax with Python `ast`; I did not import or execute the full reader, any native library, or any remote/raster access.

## Concrete finding corrected

The original first-tile HTTP 404 path spread each plan row, retaining its geometric `neighbourhood_complete:true` even though no actual tile, pixel or neighbourhood was observed. Its nested observation also omitted actual context and identity fields. Worker1 corrected this precise output-meaning defect: the actual missing observation now explicitly has false neighbourhood completeness and null codes, masks, nodata comparison, context, centre array and object identity. The original geometric flag survives only under `planned_neighbourhood_complete`.

I confirmed that this is the only change from the fully reviewed initial body by substituting the exact initial expression back in memory and recovering its exact original SHA256. I parsed the corrected body and executed only its two selected pure record-construction expressions from the AST against two synthetic plan rows, one geometrically complete and one incomplete. Both produce false actual completeness and all unavailable actual fields null at the top level and in the nested observation, while preserving their distinct planned flags. Both cases pass. The full reader, imports, native kernels, remote and raster access were never executed.

## Compatible actual paths

- The new plan and cache pins are distinct and fixed. Every result starts from fresh new-plan members. Old observation rows, old point indices and old plan identities are not promoted to new-key results; old array provenance remains separate.
- Each old pixel is read from actual NPZ `codes` and `masks` at saved window offsets, after array-byte verification. The supplier checks real containment, including one-pixel halos. New pixels come from their exact same-tile native block. Full neighbourhoods are assembled pixel by pixel, with both class and mask; no resampling, clamping, copied neighbouring label or vote occurs.
- Needed remote blocks come from the reviewed plan's missing-block union. The reader rejects a remote read of an old completed native core block. New reads use exact native blocks without a halo, with shortened frame-edge widths/heights. Old halos continue supplying their real saved pixels locally.
- For tiles extended remotely, the current HEAD identity must equal the old recorded object identity before cached/new data can combine. CRS, actual transform, dimensions, uint8 band and block shape are checked. The ten first-header tiles receive those same native-frame checks, and `ds.index` must agree with every planned member index before any block read. Index drift stops the tile rather than moving or clamping points.
- Valid values, mask-invalid centres and nodata are separate outcomes. A first tile's 404 is explicitly missing coverage rather than ocean. A 404 for an already cached source stops the tile rather than replacing retained source identity. Other exceptions yield an incomplete report. Actual outer-frame context remains incomplete and null; no cross-tile pixels are fabricated.
- Completed native block checkpoints bind new plan, reader and source object identity; completed tile checkpoints bind member indices and actual product bytes. Complete tile resumes avoid HTTP. Partial tile resumes reuse completed new blocks. These code paths were inspected, not executed in this review.

Plan coverage remains independently checked for all 80,712 rows in `cache-plan-verification.json`. This reader review does not rerun old observations, the source, or any native/scientific producer. It grants no body-location answer, per-key confidence, current truth, owner/parent repair, territorial acceptance or authority. Actual runtime/source outcomes remain pending until Root launches the reviewed body.
