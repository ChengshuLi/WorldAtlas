Ural delta and land comparison checks, prepared before completed stage-2 output.

1. Authenticate the freshly selected Ural divider and Caspian closure in Neon,
including their geometry hashes, and verify the physical-grid pins have not
changed. The prior 136 closure proof and this template are point-in-time; repeat
the closure check if the selected geometry or physical grid changes. Do not
apply a divider based on a stale selection.

2. For stage-2 against V7 baseline (or the current comparison grid), hash both
rows/runs and the physical rows/runs before AND after, pinning all six files
and this source code in a report. A separately monitored guardian should bound
runtime, process-group RSS and disk; no host-memory floor is required.

  c++ -std=c++17 -O2 -Wall -Wextra -Werror compare-land.cpp -o compare-land
  ./compare-land 131072 54614 "$PHYSICAL_ROWS" "$PHYSICAL_RUNS" \
    "$REFERENCE_ROWS" "$REFERENCE_RUNS" "$STAGE2_ROWS" "$STAGE2_RUNS"

The stage-2 candidate's water code is 0; the physical mask's water is 1 and
land is 17; the reference is assumed to use water 1..10 and land 17..22.
The program checks candidate land/water coverage against the physical mask.
It counts same/different continent only when both grids have land. It reports
candidate-land/reference-water and candidate-water/reference-land separately,
plus a 6x6 reference-to-candidate land matrix (categories 17..22). This does
not validate an ocean assignment, island overrides, historical construction,
or the geographic correctness of the selected line. It requires a full-width
row RLE pair stream and validates row offsets, stream lengths and codes.

This comparator's synthetic 4-cell case passed locally; it has NOT been run on
the full stage-2 output or on the builder's Linux host. Its stdout is not itself
an authenticated report; bind it to the pre/post hashes and monitored run.

3. Apply the source-driven delta overlay only after validating its actual inputs
and scope. Populate delta-manifest.template.json with independently verified
actual file paths and hashes for the raw base, overlay, physical mask and
selected divider, and fresh point-in-time selection attestation. Scope/witness
and code orientation reflect the prior reviewed Ural rule (Europe 19, Asia 18):
verify them against the current selection before using them.

  PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 delta-seams.py \
    --manifest delta-manifest.json --output NEW_REPORT.json

This independently counts source-divider side agreement for every physical-land
cell in the scope and checks adjacent scope-edge pairs; inspect nonzero mismatch,
other-label and divider-contact counts. It uses GEOS floating-point intersection,
not a surveyed boundary or certified topology at tangencies/vertices. Do not
interpret the ray check as independently proving source geography. It also hashes
all six RLE streams and divider before and after. A prior run on draft-136 found
43,575 scoped physical-land cells, no side mismatches, and zero eligible edge
mismatches; the prior result is not a claim about the new stage-2 output.

All selected boundary construction lineages remain incomplete. Perform independent
full output/physical-mask coverage and monitor validation before promotion. The
fresh selected seed requires a complete geographic comparison, including downstream
delta; the current stage-2 candidate has not yet been supplied for this check.
