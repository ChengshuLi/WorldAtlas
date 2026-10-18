# Togo discovery report wording correction

The frozen author report at `coordination/engineering/togo-original-repair-20261018-worker5/execution/FIRST-DISCOVERY-RESULT.md` says that “whole candidate features” remain in the actual output. The exact original output is `coordination/engineering/togo-original-repair-20261018-worker5/source-review/foreign-bounds-001/complete-foreign-bounds.json` in the author worktree; it is 457,291 bytes with SHA-256 `d0ede54cec455302cf50dce6bd593ff1920cfedf289c1c4eba3c7842e2c81e7d`.

The result records each candidate’s source identity/index/ordinal, owner list, whole-geometry SHA-256, whole-part bounds, and target associations. It does not embed raw candidate geometries. The complete original geometries are recoverable from the separately pinned whole-family source payloads listed in `result-pin-reconciliation.md`.

Suggested separate correction: “All per-family traces, complete source pins, target associations, candidate identities and bounds, and unsupported records remain in the actual output. Original candidate geometries are recoverable from the separately pinned complete-family payloads.”

This wording correction does not change the frozen result, counts, or interpretation. Candidates remain bounds-screen results, not polygon-intersection findings, source fitness, legal boundaries, physical/native qualification, or accepted repairs. The three Fiji invalid-coordinate records remain unresolved.
