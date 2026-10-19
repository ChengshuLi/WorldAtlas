# Namibia–Angola treaty findings integrity control

This additive successor checks the stable findings body before using a run's
semantic digest. It preserves the immutable #1545 validator and all original
publications. It binds historical findings to the original producer path and
source SHA-256; the successor comparator is never represented as their producer.
The comparator authenticates the complete three-file run output
inventory against each publication receipt, requires the pinned #1545 validator
source and matching real-format control headers, then derives SHA-256 from the
actual findings object. Canonical JSON uses sorted keys, UTF-8, compact separators,
and rejects non-finite values. Only `run_id`, `started_at_utc`, and the digest field
itself are excluded. A missing or stale declared digest rejects the run. Equal
derived digests can produce a new exclusive comparison file; different derived
digests are reported as `disagreed` without a success file.

From the repository root, run the focused controls:

```sh
python3 research/geography/namibia-angola-treaty-controls-1545-20261009/test_semantic_comparison.py \
  research/geography/namibia-angola-treaty-pages-1346-20261008
```

The tests read the retained final runs 5 and 6 and their own positive/negative
control files. Temporary fixture copies receive distinct run IDs and freshly
computed ordinary publication byte counts and hashes. They are control fixtures,
not new treaty producer executions. The matching case checks the actual stable
hash retained in both finals. The changed-body case changes only the second
fixture's printed-page finding and refreshes its publication descriptor while
leaving the declared semantic digest stale; the comparator rejects it. The
distinct-result case adds a synthetic limitation and recomputes its semantic
digest, so the comparator reports disagreement. An occupied destination test
confirms existing bytes remain unchanged. No fixture modifies retained source
files or implies a new geographic, legal, or sovereignty conclusion.
