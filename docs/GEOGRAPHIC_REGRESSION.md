# Differential geographic regression detector

`scripts/check-geographic-regression.py` compares two immutable Git commits. It
reads the complete location inventory through `data/world-index.json`, preserves
whole-file SHA-256 pins for every input part and the hierarchy/grid/release files,
and verifies the current release pointer against the actual retained file.
Uncommitted checkout changes cannot replace its inputs.

The detector is the first part of #920. **It is not yet wired into the PR or merge
queue as an enforced gate.** Source review, hierarchy/crosswalk/certificate checks,
derived-product validation and publication remain separate requirements.

```sh
python scripts/check-geographic-regression.py \
  --baseline BASELINE_40_CHARACTER_COMMIT \
  --candidate CANDIDATE_40_CHARACTER_COMMIT \
  --out NEW_REPORT.json
```

Install the committed Python requirements. The output must not already exist and
must have no symlink ancestor. Exit status zero means no new detected regression;
one means new lost coverage, new overlap, or invalid/unsupported geometry. Input,
hash, size and output errors fail closed. A report is diagnostic evidence, not a
geographic approval or proof that mapped land belongs to a particular province.

The comparison follows short, straight longitude/latitude source edges. It uses
the versioned shared geometry helper to align holes and split the date line.
There is no snapping, simplification, implicit MakeValid or area cutoff. Positive
areas are compared in source-coordinate space; the report labels square degrees
explicitly and does not describe them as square metres. Unsupported geometry is
reported rather than silently reinterpreted.

An unchanged inventory still passes geometry validation before success. Already
validated baseline shapes can be reused for byte-identical candidate geometries;
invalid shapes are never reused as valid results.

For changed footprints, all locations enter the neighbor index. The detector
compares the union of affected baseline and candidate locations, reporting each
piece of previously covered geometry that becomes uncovered. It also compares
each changed location's pairwise overlaps with all relevant neighbors, reporting
only overlap newly added relative to the baseline. Existing unchanged gaps and
overlaps do not become new regressions. Gained coverage is reported separately;
it still needs source review. Changed stable IDs and source metadata alone do not
establish a valid identity migration.

Each finding retains its full GeoJSON shape, representative coordinate, bounds,
changed and neighboring stable IDs, and their before/after normalized geometry.
The report also retains their original geometry hashes, containing-file pins and
original metadata. The representative coordinate locates the finding; acceptance
must review the entire shape, including all pieces and holes.

Engineering should repair a shared boundary jointly using reviewed sources, or
document an intentional shoreline/water correction with exact source evidence.
A lake enlargement therefore still produces a review blocker: geometry alone
cannot certify water. This first detector has no exception or automatic repair
path. Unknown hydrology stays explicitly unverified. The global gap inventory in
`GEOGRAPHIC_GAP_AUDIT.md` remains the separate inventory of existing candidates.

Controls in `test/geographic-regression.py` cover isolated and combined neighboring
changes, valid joint repairs, unchanged gaps/overlaps, newly added overlap,
islands/lake holes, deletions/replacement, thin gaps, tile edges, the date line,
invalid polygons, immutable input reads, release hashes and exclusive outputs.
The Node test wrapper includes them in the existing full regression inventory.
The next part of #920 must invoke trusted detector code against the exact PR and
combined merge candidate; passing these controls alone does not install that gate.
