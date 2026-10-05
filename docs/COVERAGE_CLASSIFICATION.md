# Physical-reference classification

The classification is an independent diagnostic on the fixed canonical grid. It never changes a location ID, administrative boundary, political affiliation, historical fact or release. Natural Earth 1:10m land supports class 1; its major lake/reservoir polygons override land with class 2. Remaining cells are unknown, including tiles blocked by invalid original water shapes. Ocean background alone is not a water certificate.

An unassigned location cell with class 1 displays an orange/pale hatch and explains a **possible geographic coverage gap**. Smaller rivers/lakes, shorelines and source-vintage differences remain uncertain. Class 2 explains reference water. Missing, stale or corrupt products fall back to “No mapped location; water or geographic coverage is not verified.” Mapped locations take precedence in both GPU and Canvas. Click explanations include coordinates and physical-source links; these modern references do not change with the selected historical year.

Prepare the product offline from immutable Git inputs with the pinned Python requirements:

```sh
python3 scripts/prepare-coverage-classification.py --geography-commit EXACT_MAIN_COMMIT --out data/coverage-classification
```

The output directory must be absent. Preserve an existing product/evidence vintage before preparing a replacement. The optional `--water-commit` defaults to the selected geography commit, which must contain the retained original lake source and its receipt; source receipts verify the original bytes. A separately pinned source commit can be supplied when needed. The generator uses sparse row intervals and half-open cell-center sampling rather than a dense world bitmap. Water takes priority over land; blocked tiles take priority over both. It preserves polygon holes and the non-Antarctic declared domain. No invalid reference is silently repaired. Output timestamps and runtime diagnostics are excluded from product bytes, permitting deterministic reproduction.

The manifest pins the geographic release, footprints, hierarchy and exact canonical-grid manifest. Static packaging validates every compressed/decoded part and run before copying it. Hosted packaging also compresses the existing recovery receipt losslessly; the versioned ownership delivery manifest records its original and transport hashes, and verifies decoded equality. Original preparation/source bytes remain unchanged in the repository; portable exports retain them directly. The browser bounds allocations, transport/decompression and concurrency, verifies the same pins and hashes, and rejects invalid classes/overlapping runs. GPU textures and the Canvas worker receive classification separately from ownership; navigation/styles do not compile or upload additional ownership.

Run the classification and isolated renderer controls:

```sh
node --test test/coverage-classification.test.mjs test/coverage-browser.test.mjs test/pixel-ownership.test.mjs
```

These checks prove the implementation contract, not complete hydrological accuracy. See `GEOGRAPHIC_GAP_AUDIT.md` for the global candidate inventory. Detailed water evidence and source-backed coordinated administrative repairs remain necessary before closing confirmed geography defects. Issue #920 separately tracks the differential integration gate and actionable repair reports. This rendering change does not install that gate or fix boundary geometry. Deployment is deferred at the user's request.
