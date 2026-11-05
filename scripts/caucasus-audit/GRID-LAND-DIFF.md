# Windowed land-grid comparison

`grid_land_diff.py` compares two exclusive-end u32 row-run grids over a
user-supplied row/column window. It verifies each decompressed input against
its supplied SHA-256, checks row offsets and row-run coverage, and emits
exclusive-end spans where both codes are in the explicitly supplied land set
and their labels differ. It writes to a new private output file only.

Input hashes identify bytes, not the authority, revision or comparability of
the source grids. Verify their shared dimensions, coordinate convention,
physical mask and lineage before interpreting the results. Historical
comparisons are not current-build mismatch counts; run a new comparison using
the intended pinned grids. This tool does not judge geographic correctness.
Large windows may produce large in-memory span lists. Keep input and output
geographic data in the project's data stores.

Requires NumPy. Run `python -m unittest discover -s scripts/caucasus-audit
-p 'test_grid_land_diff.py'` for the synthetic span and fail-closed checks.
See `python scripts/caucasus-audit/grid_land_diff.py --help` for its parameters.
