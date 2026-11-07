# Sequential tile integrity: research prototype

This is a synthetic-only experiment. It is not integrated into the map builder, does not satisfy the existing pinned source gate, and must not be used for production or a geographic result.

The prototype explores authenticated, one-file-at-a-time materialization with bounded reads and tests source order, pre/post-use hashes, failure handling and detached trace evidence using injected stand-ins. Thirty synthetic tests passed and an independent review found no remaining synthetic blocker in the reviewed bytes.

Real-data replay, raster processing, authenticated source-reader and runtime admission, resource limits, crash recovery, and integration remain unimplemented or unverified. Resource claims cover only owned scratch files at check boundaries, not total process memory or disk use. The original recipe and gate remain unchanged.

Files:
- `sequential_tiles.py`: research protocol.
- `test_sequential_tiles.py`: synthetic tests.

Run tests with `python3 -I -S -B test_sequential_tiles.py`.
