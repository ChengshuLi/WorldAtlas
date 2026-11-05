# Draft-24 reduced-memory runtime overlay

These three exact Python files were used in the draft-24 research build. They change only the coordinator's point-runtime path and minimum host-memory floor, the point parser's floor and startup cushion, and the identity watchdog's floor and startup cushion. The group and child RSS caps remain in force. This is a resource-policy overlay, not an accepted geography release.

To reproduce the directory layout, copy the preserved `stage3-mixed-leeward-full-20261105` directory to `stage3-mixed-draft24-reduced-floor-20261105` and replace its coordinator with the one here. Copy the preserved `osm-island-group-integration-v3-prototype-20261104` directory to `draft24-reduced-floor-point-20261105` and replace its point resolver and identity watchdog with the files here. Other sibling dependencies remain as in the preserved mixed runtime. Verify all hashes against the independently authorized build request before running.

These files do not include geographic data, decisions, snapshots, sources, credentials, or output grids. A successful execution requires separately obtained and validated private inputs and guarded process supervision.
