# Reuse whole-component coverage within one build

The mixed resolver builds a transient all-root cell-count index at the first
all-center containment decision. It validates every physical/component row
once, then reuses counts for later decisions in that same resolver call. The
intended semantics preserve source geometry, selected decisions, boundary rules,
component IDs and output format. The existing non-indexed selector remains
available.

This is a research overlay, not a standalone runtime. Assemble it only with
matching reviewed dependencies; publishing this code does not deploy a map.

The index is trusted in-process caching, not an adversarially immutable
snapshot. Each use checks the resolved stream identities and file metadata;
the outer resolver must authenticate input hashes before and after resolution.
The caller must use an external process-group RSS guard, because index memory
scales with the number of distinct roots. If those conditions cannot be met,
use the existing non-indexed path. The index is not persisted across runs.

Synthetic tests check output and error parity and reject a changed generation.
A bounded benchmark compared 12 representative queries over four sampled
1,024-row windows of the pinned physical/component streams. It is not a full
map replay or a scientific validation. Full-map equivalence and performance
must be measured when a future map rebuild is authorized.
