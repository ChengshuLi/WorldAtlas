# Coastal #1160 fresh-run erratum

This additive packet makes the retained eight-county comparison reproducible under two new, exclusive output-vintage names. It reads only immutable Git objects from the exact #1160 merge (`a37ad37b94168f9b458617489a702bbb72afbd3d`), verifies the issue's 57 raw input pins and the original program/inventory pins, and imports the exact retained comparison program and geometry helper bytes. It does not overwrite or relocate any #1152/#1160 source, receipt, result or metadata file.

The author branch was cut from fresh `origin/main` at `bd3b4ab860f11320717c354b10378c9972726373`. Some of the 57 historical data paths have since advanced on `main`, so the runner deliberately reads the immutable #1160 merge objects by hash instead of silently consuming newer checkout files. Its source vintage, current branch base and per-run creation time are recorded separately.

## Reproduce

With Python 3.12.14, Shapely 2.1.2 and pyproj 3.7.2 available, run from the repository root:

```sh
python3.12 data/regional-review/coastal-fresh-run-1160-erratum/fresh-reproduce.py --controls-only
python3.12 data/regional-review/coastal-fresh-run-1160-erratum/fresh-reproduce.py --run-id coastal-20261006-g
python3.12 data/regional-review/coastal-fresh-run-1160-erratum/fresh-reproduce.py --run-id coastal-20261006-h
python3.12 data/regional-review/coastal-fresh-run-1160-erratum/fresh-reproduce.py --verify-pair coastal-20261006-g coastal-20261006-h --summary-id two-run-summary-partial-write-final
```

Each new run writes four product files and an execution receipt under `runs/<run-id>/`. Output names must be safe, distinct single path components and unused. Output publication refuses an existing file, directory or symlink; a failed write removes only exact file inodes created by that command, including partial product or summary writes. The pair receipt is written once and refuses replacement.

`input-pins.json` contains the issue's exact 57 input path/hash/length rows, the old runner/inventory pins and the eight retained product hashes from both historical run directories. `program-pin.json` binds the fresh runner's bytes. Before calculations, the command resolves every input from the pinned immutable merge, checks exact bytes and full gzip sizes, checks the exact 36-member world-index registry against pinned members, and bounds the complete phase to the existing 256 MiB/32 MiB limits and 200,000-byte reserve. The historical runner and geometry helper are executed from those verified bytes; its repository reads are confined to the verified input set.

The documented original `run-one` and `run-two` names still fail with `FileExistsError`, and `auditor-fresh` remains an invalid argument to that old CLI. Those retained names are not changed. Both new runs match all four historical products byte-for-byte; the final pair summary records the exact run commands, environment, timestamps, output hashes and comparisons. The earlier A/B and C/D attempts are retained separately; E/F are retained intermediate runs; G/H execute the final pinned runner after hardening both product and summary partial-write cleanup.

## Geographic scope and limits

The exact subjects are the eight IDs declared by #1218 and preserved in `input-pins.json`. Five are the coastal comparison cases (Camden, Chatham, Glynn, Liberty and McIntosh); Schley, Pike and Terrell are retained interior comparison controls. The inherited Atlas records identify all eight as USA ADM2 with Georgia parent `framework:province:georgia:99c5fb82481b`. The source assessment records how the retained Census GEOIDs, STATE code, names and LSAD county tier support that scoped parent/tier crosswalk.

The 2018, 2025 and 2026 Census geometries are dated statistical references, not adjudicated legal lines. The 2026 response is an exact query for these eight GEOIDs, not a complete Georgia county inventory. Equal-area IoU, county codes, roster checks and successful reproduction do not establish shoreline/island treatment, full-state or adjacent-county completeness, legal jurisdiction or the correctness of either competing geometry. The inherited 2018 geoBoundaries reuse conflict remains unresolved. This packet makes no geographic correction, regional approval, import or deployment recommendation.

See [source-assessment.md](source-assessment.md), [two-run-summary-partial-write-final.json](two-run-summary-partial-write-final.json), [validation/fresh-run-controls-final.json](validation/fresh-run-controls-final.json) and [evidence-quality.json](evidence-quality.json). The original source bytes, retrieval receipts, license notices and older evidence remain pinned in their existing packets and Git history; restoration references and precise limits are recorded rather than copied over.
