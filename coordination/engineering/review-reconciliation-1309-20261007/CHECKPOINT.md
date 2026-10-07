# Review reconciliation and safe controls

Refs #1309. The two earlier prevention and author-guide PRs remain preserved.
This third, documentation-only PR clarifies the existing queue semantics after
actual rollout showed repeated requests despite another reviewer’s objection.
It also applies fresh-run admission and preservation to the control writer, not
only the main producer. No gate, CI routing or scientific result is changed.

The active Fiji repair remains owned by #1361 / PR #1375. The shared writer was
corrected, but an independently reproduced control-fixture overwrite still
requires its owner’s repair and renewed relevant review. Full goal completion
requires actual-main verification and final rollout disposition; this PR does
not close #1309 or approve geography.
