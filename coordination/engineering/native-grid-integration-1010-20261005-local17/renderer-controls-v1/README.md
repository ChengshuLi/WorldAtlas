# Isolated native-grid renderer controls

Executed the actual GPU and Canvas layer implementations with synthetic source-native triangles, true holes and split dateline polygons. Original sparse feature indices are retained while the display grid uses an explicit dense ID mapping. The legacy projected triangle control is empty at the tested cell; the native grid assigns the cell to the left polygon.

Run `node --test test/native-renderer.test.mjs` with the committed Playwright dependency and its Chromium installation. `ATLAS_TEST_CHROMIUM` may name a separately installed test Chromium executable. The fixture creates a fresh disposable profile inside the owned checkout, permits only its exact localhost port and removes the profile afterward. It never attaches to the user's browser or accesses accounts or production.

The test checks recovered-cell RGBA and exact ID picking on both renderers; fourteen synthetic palette updates without grid recompilation; full-grid low-zoom picking; both sides of the dateline; true holes remaining unassigned; physical-water transparency; land-gap hatch colors; unknown-area transparency; coordinate/classification explanations; and GPU context loss, restoration and restored recovered-cell fill. Test failure is fatal, without skips.

Limits: software WebGL2 SwiftShader and Canvas2D are rendering correctness controls, not physical-device performance approval. Fourteen palette updates are not fourteen application-mode/content approvals. Physical classes are synthetic controls, not an independent global land/water audit. This does not certify source topology, factual boundary repairs, release certificates or deployment.
