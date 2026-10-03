# Current-review projection refresh

If the current projection has already advanced, the helper locates the exact v4 predecessor through byte-pinned archives and restores it only in its temporary overlay. Shared validation follows immutable predecessor projections recursively, checking every source migration against the original inspection baseline. Earlier v4 additions/groups remain accounted for; v5 is not falsely treated as a standalone change to the original inspected world. Future archive directories use the predecessor projection hash, preventing different migrations with identical hierarchy hashes from overwriting one another.

Executed checks: v5 passed shared preparation/geometry gates and the original-baseline global semantic inventory/provenance gate at 49,625 locations and 5,734 groups. All 22 focused projection/semantic tests pass, including successive additions, retained created groups, corrupted archives, wrong release order and false approval rejection. This establishes provenance and structural consistency, never complete regional semantics.

The helper uses the shared strict projection producer/validator against a read-only temporary overlay: installation-backup geographic files supply v4 while unchanged current inspection artifacts supply preserved sources. It emits a complete v5 projection, world dashboard, location chunks and byte-preserved inspection/predecessor archives to a fresh external directory. No core files are changed. Regional semantics stay open.

```sh
node --max-old-space-size=4096 data/macro-improvements/loose-ends-v5/projection/prepare.mjs \
 --root /workspace/WorldAtlas \
 --before /workspace/WorldAtlas/.cache/geography-install-backups/4208e8a4-981c-4bc8-a9cb-fddfd2d448fa \
 --after /workspace/WorldAtlas/data \
 --geometry-proofs /tmp/worldatlas-v5-integrated/geometry-proofs.json \
 --source-receipt /tmp/worldatlas-v5-integrated/aggregate-source-receipt.json \
 --output /tmp/worldatlas-v5-current-review-projection
```

The coordinator schedules this as the sole heavy world job. Accept only exact 49,623 → 49,625 identities, three sourced footprint corrections, two additions, zero retirements and unchanged original inspection context. `preparation-receipt.json` pins every output; root installs those bytes separately after reviewing validation. Disk space is checked before writing assets. Local backup paths are execution inputs, not future recovery dependencies: emitted predecessor archives and immutable source proofs must be retained durably with the release.
