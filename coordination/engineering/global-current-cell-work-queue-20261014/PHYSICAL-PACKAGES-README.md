# Executable physical investigation packages

Accepted snapshot: a61b6f9e7f88b1da380e3a834f89d7509132ed71.

`physical-package-queue.json` contains 14 disjoint geographic/source-disagreement packages covering every one of the 100,304,914 unassigned physical-land cells outside the retained territorial-source footprint. It also contains two supplemental tasks: malformed GSHHG source 2380 and Antarctic excluded-domain policy. These do not add cells to the counted global workload. Combined with the 644 territorial packages, the handover has 658 counted-domain packages plus two supplemental investigations, 660 tasks in total.

A physical-versus-retained-territorial disagreement is not an established repair error. Broad Arctic source sessions are kept together because they share source-comparison work. Native Web Mercator counts overweight high latitudes relative to ground area; package priority depends on available source evidence, common discrepancy cause, qualification cost and readiness, never cell count alone. Geographic rectangles schedule work without assigning countries or sovereignty.

## Execute a package

Put the helper and queue beside the retained source/physical block files, then run:

    python physical-batch-intervals.py PACKAGE_ID NEW_OUTPUT_DIRECTORY

For a separate artifact directory:

    python physical-batch-intervals.py PACKAGE_ID NEW_OUTPUT_DIRECTORY --data ARTIFACT_DIRECTORY

Only the Python standard library is needed. The helper never edits repository or ownership data. It reads whole hash-pinned blocks, derives physical-only intervals by subtracting the complete territorial interval union from physical land support, applies the package's exact integer row/column bounds, and verifies the selected count. It writes compact interval triples, the package instructions, and a completion manifest with output hashes. Existing output directories are rejected. Partial failure produces no completion manifest.

Source block 014 is transported as two complete JSON arrays; the helper verifies each encoded and decoded part, row order and original reconstructed canonical hash. No duplicate physical-only block copies are needed in the portable bundle.

    python physical-batch-intervals.py --verify-all

The full verification independently derived all 45 nonempty physical-only blocks, checked their canonical hashes and every package count, and confirmed exactly 100,304,914 disjoint selected cells. The other 20 native blocks have no physical-only cells. The independently reviewed package rectangles form a disjoint complete-world partition. Reviewer tests also covered relocated execution, unknown-source and Antarctic exports, collisions and corrupted input hashes.

`source_bbox_candidate_ids` are conservative physical-source candidates, not asserted exact memberships. Whole original geometries, container hierarchy and territorial exclusions remain mandatory in the investigation. The optional full local source-roster cache is not required by the portable helper: exact source IDs, accepted commit, repository prefixes, native custody descriptors and metadata receipts support source acquisition. The two supplemental tasks include their small source-record set in `physical-package-special-source-records.json`.

## Supplemental accounting

- Invalid source 2380: 948 owner-0 cells in its conservative envelope. Of 938 outside valid physical support, 63 already overlap the territorial-source workload and 875 lie outside the counted global union. This is unknown coverage, not 948 confirmed repair cells.
- Antarctic policy: 673 retained alternative level-5/6 source records. Native repair-cell count remains unmeasured, not zero. Export returns source metadata and the policy-review task, without inventing a repair interval scope.
