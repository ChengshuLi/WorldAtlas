# Release 5 publication inputs

`prepare-release.mjs` replays the complete original identity and migration chronology, rather than rebuilding the identity registry from current geography. It verifies the retained v4 proof archive and each member, appends the two v5 geometry proof steps, and invokes the shared release preparer in a fresh external directory. It performs no live import, installation or publication.

```sh
node --max-old-space-size=4096 data/macro-improvements/loose-ends-v5/publication/prepare-release.mjs \
  --root /workspace/WorldAtlas \
  --stage /tmp/worldatlas-v5-integrated \
  --output /tmp/worldatlas-v5-release
```

The completed source stage must have exactly three retained-ID corrections, two additions, zero removals and no history transfer. `release-preparation.json` pins the source-stage validation, original archive, complete ordered identity sequence and resulting release. Source preparation alone does not approve the canonical grid or live deployment.

The coordinator runs large geography, derived-attribute and grid jobs sequentially. Whole-world representation and both projected/WGS84 area errors must pass; an isolated small-island probe cannot replace collision-resolved validation. Activate only matched geography, ownership, environmental references, runtime, macro envelopes and fixed-grid assets through the shared installer. Retain its rollback and source-proof archives, then verify live release pins and unchanged existing facts/media before recording completion on issue #540. Preserve the Site's existing audience.

`new-identity-preflight.json` is the read-only exact-ID registry check for the two additions. It contains no credential. A consistent registry snapshot establishes absence of duplicate IDs; source identity and spatial evidence are checked separately.

`extend-manifest.py` preserves the original index and every prior release/batch byte, then appends the v5 package through the shared gzip manifest pointer. It accounts for 42 already-registered v4 identities and creates only Kingman and Gardner. The original preparer reports its difference from the original registry; this extension records the actual difference from the published predecessor. `manifest-extension-receipt.json` pins that distinction.

The first live attempt rejected a previously registered area identity (SQLSTATE 23514); existing identities were preserved. A subsequent guarded staging attempt paused at the initial 780 MB application guard. The remaining import resumed idempotently with a measured 950 MB guard and finished at 827,506,688 bytes. These are application review budgets, not a verified Neon provider quota; no plan upgrade was requested.
