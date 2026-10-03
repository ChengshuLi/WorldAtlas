# Offline v5 integration producer

`compose.mjs` owns no live data. It creates a fresh caller-selected directory outside the checkout, links unchanged geography read-only, and materializes changed parts there. No installation, content import, release approval or publication is performed. Do not pass this linked stage directly to the installer: its final geographic input must contain actual validated file bytes rather than symlinks.

## Inputs and commands

Use repeatable paired `--replacement-patch` and `--replacement-manifest` arguments in matching order. Replacement patches follow Cook's prepared contract: `input_hierarchy_sha256`, `input_world_index_sha256`, `input_part_sha256`, `existing_location_updates`, empty `existing_group_updates`, `added_features` and `added_groups`, and `history_transfer: false`. Each manifest must pin an independently validated migration receipt with exact original features, disjoint changed IDs, all reused IDs, inspected source evidence, no additions/retirements and no historical transfer. Names, parents and owners must remain unchanged; inspected footprint/source metadata may change.

Pure creation inputs use repeatable `--creation-patch`. Each JSON/gzip document must contain:

```json
{
  "history_transfer": false,
  "supported_from": 2026,
  "supported_to": 2027,
  "input_hierarchy_sha256": "<current v4 hierarchy SHA256>",
  "added_features": [],
  "added_groups": [],
  "creation_proofs": []
}
```

At least one added feature is required per creation input. Top-level support dates may be omitted only when every individual creation proof explicitly supplies the required `[2026,2027)` source interval; contradictory declared top-level dates are rejected. Use the existing `validate-land-creations.py` proof contract: one exact source GeoJSON wrapper, SHA256, inspected URL, license, attribution, modern support interval, distinct-territory identity review and complete five-parent chain per new location. Source paths are relative to the patch directory and their exact bytes must match their proof SHA256. New owners/attributes remain unknown. Any new groups must be local province/area units; no macro boundary is invented here.

```sh
node --max-old-space-size=4096 data/macro-improvements/loose-ends-v5/integration/compose.mjs \
  --root /workspace/WorldAtlas --output /tmp/worldatlas-v5-integration \
  --replacement-patch data/macro-improvements/loose-ends-v5/cook/prepared/candidate-patch.json.gz \
  --replacement-manifest data/macro-improvements/loose-ends-v5/cook/prepared/index.json \
  --replacement-patch data/macro-improvements/loose-ends-v5/chagos/prepared/patch.json.gz \
  --replacement-manifest data/macro-improvements/loose-ends-v5/chagos/prepared/index.json \
  --creation-patch data/macro-improvements/loose-ends-v5/grid/prepared/candidate-patch.json.gz

node --max-old-space-size=4096 data/macro-improvements/loose-ends-v5/integration/compose.mjs \
  --verify --root /workspace/WorldAtlas --stage /tmp/worldatlas-v5-integration
```

Composition and verification are separate so callers can inspect exact scope first. Verification requires a fresh `replacement-migration` and `creation-migration` directory; use a fresh output directory to retry after a failed verification. Never overwrite a predecessor stage.

## Outputs and independent gates

- `baseline/`, `replacement/`, `creation/`: sequential current v4, combined retained-ID correction, and pure-new-land geography.
- `composition.json`: input hashes, every source-part before/after hash, IDs and scope; no full-world archive is committed to Git.
- `replacement-inputs/<n>/`: byte-preserved independently validated child proof archives.
- `replacement-migration/index.json`: combined replacement receipt, exact originals and full-world before/after footprint hashes.
- `creation-migration/index.json`: the existing generic pure-creation producer's source-byte, geometry, identity, overlap and parent-chain proof.
- `geometry-proofs.json` and `aggregate-source-receipt.json`: ordered generic installer-compatible proof descriptor and exact combined source receipt.
- `integration-validation.json`: checked footprint pins and inventory counts, with `published: false` and zero historical transfer.

Each retained child is validated separately against v4 using `validateGeometryMigrations`; combined originals must reconstruct the complete baseline exactly. Creation validation scans the whole resulting world for overlapping land and rejects prior-identity/name ambiguity, geometry changes to existing features, altered owners and invalid parent chains. This does not replace independent replacement source replay, or prove historical environmental/ownership facts.

`cook-only-check.json` records the executed full-world Cook composition/verification: 49,623 retained locations, two geometry changes, zero removals/creations and exact reconstruction of the v4 footprint pin. Syntax checks passed; separate rejection checks confirmed overlapping replacement scopes, missing paired manifests and output inside the live checkout are refused. This receipt is a bounded integration check, not a complete v5 release or creation/grid/publication certificate.

`cook-grid-check.json` records the next executed full-world check: both Cook corrections followed by two pure Kingman/Gardner creations, 49,625 locations and zero removals. Existing generic source/overlap/identity/parent-chain creation validation and ordered geometry reconstruction passed. Chagos and canonical-grid/publication gates are still separate.

Before installation/publication, still run the reviewed installer gates: regenerate ownership/environment products only for changed footprints; verify retained database content and immutable original claims; compile and audit a canonical grid representing every final location; regenerate parent-envelope/macro handoff certificates; assemble the prior plus new ordered release proofs; materialize stage links; check exact production assets, deployment limits and live readback. Regional interiors remain unapproved, and historical imports stay gated. New footprint support is modern-reference-only; no old record interval is widened or redistributed.

`combined-check.json` records the complete Cook + Chagos + Kingman/Gardner check: 49,623 to 49,625 locations, three retained-ID footprint corrections, two pure creations, zero removals and no historical transfer. This source-stage result is not a final grid, derived-attribute, live identity or publication approval.
