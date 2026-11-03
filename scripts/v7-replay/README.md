# V7 composition replay candidate

This is a proposed portable replay of the V7 final-grid composition, not a proven recreation of the historical run. It starts from the preserved V2/physical/V6 grids and prepared water layers; it does not regenerate those layers from original geography sources.

The compositor maps the historical workspace and /tmp input paths into a supplied recovery root. It checks RLE, manifest and tile hashes, and exclusively creates a new output directory outside the input tree. Never reuse or overwrite an existing intermediate or output. Preserve and verify the recovery archives before preparing an input tree; check extraction collisions and place the separately preserved Bering tile and ocean-adapter manifest at their original archive-relative paths.

The five water-layer manifest hashes are recorded in the original composition audit. The land-provenance manifest hash was observed from the retained local file and is not independently authenticated. The exact compositor source used in the historical production run is not established. The added manifest pins change the plan hash, so audit and downstream release metadata will differ even if scientific outputs match.

Focused synthetic tests cover path rejection, input hashes, a two-row composition, and refusal to reuse output. They do not establish full-grid equivalence. Before use, verify the source archives, required inputs, and dependencies in an isolated workspace. Compare a fresh result to the preserved rows SHA-256 `acc7a8f3d3ebfba3fea688154e93d3a1b577b9b6e6d2db4a6e1a16b32d9ece68`, runs SHA-256 `73819432f0e45ae52a4288985eaa570b3ab22cd20f68ade95f8adc17ace9a90c`, and V2-difference counts and contents. Investigate any mismatch without overwriting the preserved data.

Historical coastal v2/v3 script sources and an independently cited closed-water QA file remain missing. See the V7 recovery notes for further limitations.
