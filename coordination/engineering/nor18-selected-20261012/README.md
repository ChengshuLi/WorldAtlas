# Norway eighteen-component delivery

Issue #1796. The accepted source is PR #1738, merge fd7e242f3659cc258a48867294abb19587747653. Exact component and target mappings are in delivery-scope.json.

## Genuine producer results

- South5 SOURCE: all five compatible, 109.633 seconds, 521,617,408-byte conservative combined peak.
- South5 NATIVE: three assigned and two zero-cell components, 56 new cells, zero conflicts/exceptions; 60.508 seconds, 497,041,408-byte combined peak.
- South5 current-bank rebind: 190.691 seconds, 374,210,560-byte child lifetime peak; complete prior custody and target/native conservation.
- South5 assembly: qualified, 75.121 seconds, 454,463,488-byte combined peak. Unchanged prior 1,123 cells plus 56 equals 1,179 cells.
- North13 SOURCE: all thirteen compatible, 73.381 seconds, 608,817,152-byte combined peak.
- North13 NATIVE: ten assigned and three zero-cell components, 125 new cells, zero conflicts/exceptions; 61.116 seconds, 571,052,032-byte combined peak.
- Every successful producer terminated normally with no surviving owned processes. Failed setup/publication attempts remain in preserved-refusals.

## Sequential selected acceptance

This first candidate selects only south5 and has no selected-checkpoint locator. Its real selected validation must use the accepted #1788 trusted seed implementation. No hosted selected acceptance or repaired-gap credit is claimed by this preparation.

North13 producer evidence is reusable, but its final current-bank rebind and selected delivery must follow the actual accepted south5 receipt/artifact. Its two unselected native run files are retained at exact Git pins in north13-prepared-operands.json and excluded from the first candidate tree. Restore them byte-identically for the successor. Shared immutable acquisition caching does not expand a delivery's selected file projection.

All additions remain source-relative to the approved retained administrative vintage. No new physical/legal/water/date truth is inferred. All original held, incomplete, mixed, and serialization-failed Norway cases remain excluded.
