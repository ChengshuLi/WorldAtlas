# No-host-floor research runtime overlay

This separately tested follow-up removes host-available-memory floor checks and per-child startup cushions from the research pipeline. Process and child RSS limits, timeout, disk reserve, and atomic outputs remain. The completed draft-24 map used the separate reduced-floor overlay, not these files. No completed global build has used this no-floor variant yet.

For a run, copy the previously preserved mixed-runtime directories to the sibling names shown here and overlay the matching Python files. The watcher directory is self-contained; reconciliation expects separately pinned input/output evidence. The included test files exercise the changed paths using synthetic data. Verify code and inputs before execution. No source geography, decisions, snapshots, credentials, or result grids are included.
