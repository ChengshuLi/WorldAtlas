# Durable checkpoint — 2026-10-03

Issue #497; active reservation worker `codex-20261003-peru-6b28c076-1c52-4fc7-98fb-58336e73a862`, claim `e9a469f0-fa33-4157-9676-e3dd7da32439`, request `ea6b73d6-32b8-4185-a95d-d6e577ddb0c7`. Branch `geography/regional-review-d2dae235991eaa49`; reservation expires 2026-10-04T09:09:39Z. Owned path is this directory only.

Completed: 89 individual subject assessments; 78 of 78 ADM2 identity matches; 11 of 11 ecological fragments mapped to retained RESOLVE IDs and source province links; published parent ancestry; Peru-area sibling partition (89 + 115 = 204); retained official sources, hashes, dates, license/restoration facts; role/grain, legacy parent-source, multipart, settlement, and spatial exactness findings. `python3 .../reproduce-audit.py` passes. Actual issue metadata and `Closes #497` scope validation passed using `scripts/check-handoff-scope.mjs`.

Open findings are explicit: exact topology/partition of Loreto, Maynas, Requena not proved; 11 ecological intersections are misleadingly recorded as province locations; legacy ADM1 parent source is 2009 OSM-derived; identity/classification of multipart components and complete settlement evidence are unresolved. Recommended coordinated follow-up with sibling #496 and parent #489; no boundary or hierarchy edits made.

Next: rebase on current `origin/main`, commit/push this evidence packet, submit through serialized merge queue, verify merge and release claim. Then select another ready unclaimed `type:geography` issue from current main.
