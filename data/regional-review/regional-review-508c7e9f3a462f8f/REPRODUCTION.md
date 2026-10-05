# Reproducing issue #431 evidence

All outputs are read-only assessments against the fixed baseline commit in `reproduce.py`. The reproduction checks exact SHA-256 pins for every retained original input before parsing them.

1. Use Python 3.12 and install the exact direct dependencies from `source/reproduction-requirements.txt` into a virtual environment.
2. Run from the repository root:

   ```sh
   python data/regional-review/regional-review-508c7e9f3a462f8f/reproduce.py --output-dir runs/new-run-id
   ```

   The `--output-dir` value must be a new path beneath the issue-owned packet. Existing run outputs are immutable; do not overwrite them.
3. Compare the generated files byte-for-byte with `runs/twelve/`. `runs/thirteen/` is a second independently invoked run from the same code and inputs; it should be identical.

`source/restore-geoboundaries.mjs` restores the two GeoBoundaries LFS objects using the exact original OIDs and refuses to replace different bytes. For Census inputs, use the original Texas API response bytes retained in the packet. `source/census-2018/cb_2018_us_county_500k.zip` is the original Census 2018 1:500,000 county archive; its official URL, retrieval time, response size, Last-Modified value and SHA-256 are in the adjacent `*-retrieval.json` file. The program checks this ZIP hash before use.

The row-level output contains every one of the 254 exact Atlas IDs, source IDs, Census GEOIDs, source role/vintage/license, parent, multipart details, individual classification, equal-area comparisons, and unresolved signals. The screening value is triage only. No output certifies legal boundaries, island completeness, region approval, historical imports, or production publication.
