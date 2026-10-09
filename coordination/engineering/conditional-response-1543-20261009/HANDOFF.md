# Conditional response repair

Refs #1578. This repairs the shared queue regression introduced by #1571; it does not complete #1543 or #1544.

Native Node fetch receives a weak ETag on the Git commit 200 response and the same opaque validator without W/ on the conditional 304. Strict string comparison incorrectly rejects it. RFC 9110 section 13.1.2 requires weak comparison for If-None-Match: https://www.rfc-editor.org/rfc/rfc9110.html#section-13.1.2 . The change accepts only valid tags with identical opaque values. Different and malformed validators still reject. Every reuse still makes the authenticated network request and parses an independent value; bounds, credentials, routes, capacity and final authority checks are preserved.

`live-reproduction.json` retains the actual two-response native Node observation through the patched githubAPI entry point. `controls.log` retains focused shared API, capacity, claim-observer, Git transport, PR-gate and merge-entry controls. The added tests cover both weak/strong directions, fresh objects, exact request counts and malformed/different identifiers; existing authority-loss and changed-response controls remain.

No additional request, sleep, FIFO queue, candidate execution, scientific data change, workflow change or new worker procedure is added. This is correctness recovery, not a claim of global quota prevention or CI speedup. Full historical/scientific performance acceptance remains with #1543/#1544.

## Exceptional rollout ownership

The ordinary #1543 release request `c78542b2-4120-49fa-a410-b008f263f3cd` was terminally rejected by this same trusted-main defect. Its canonical claim remains with Main; no other worker's claim was taken. The complete readiness investigation of #1578 also fails with this error, so it is not claimed or falsely marked ready. Implementation uses Main's admitted owned workspace. Normal claim/readiness gate success must not be asserted for this incident.

The human explicitly authorized bypassing the queue/checks for urgent hotfixes where chicken-and-egg dependencies prevent recovery. Obtain independent exact-head review, preserve actual hosted results, and inspect a terminal queue/gate failure before applying that narrow exception. Do not claim full CI passed unless its actual runs did. Do not retry an uncertain merge. Verify exact actual-main objects and subsequent real queue recovery before closing #1578; preserve each affected PR's evidence and renewed review requirements.

After verification, release the preserved #1543 claim through its restored normal interface and resume its original setup acceptance. Keep the original performance goal active. Completed owned checkout cleanup remains required.
