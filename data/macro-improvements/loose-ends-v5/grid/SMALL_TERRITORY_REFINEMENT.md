# Exhaustive small-territory resolution check

The complete final-v5 ownership check at 262,162 represented all locations but failed area distortion for Necker Island and Bajo Nuevo. Rather than patch these examples alone, the follow-up tests every one of the 112 staged territories with less than 64 source cells at that grid width.

All 112 pass both projected and WGS84 25% area-error limits and contain genuine source-centre cells at **262,166**. The maximum absolute area error is 24.09%. The next passing candidates are 262,276 and 262,307. No rings, water masks, grid origin or source footprints were changed, and no water cells were donated.

`small-resolution-refinement.json` records all 112 IDs and their per-candidate results, not only the previously observed regressions. The compressed fixture preserves their exact final-v5 source geometries, metadata and ellipsoidal source areas; its full-world footprint pin is `2ac42eeb9fef8af923a0d4c4e55af49ca0a103de891ffbfb2c1181ad75950286`.

Replay with:

```
node --max-old-space-size=128 data/macro-improvements/loose-ends-v5/grid/probe-small-resolution.mjs
```

The replay writes only `/tmp/worldatlas-small-resolution-replay.json` by default. It completed in under one second with about 66 MB peak RSS. The initial fixture collection streamed source parts individually and retained only these 112 units.

This is an exhaustive **small-unit source** check. It does not resolve competing location pixels, certify the other larger units, or activate a grid. Root must serialize the complete final-v5 collision-resolved audit at 262,166 and verify the remaining packaging, source pins, device and fixed-navigation gates.
