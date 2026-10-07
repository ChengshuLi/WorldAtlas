# Complete original GSHHG2.3.7 custody — issue1261, first PR

This packet retains the complete official binary ZIP as four ordered contiguous ordinary byte fragments. `catalogue.json` records whole original and member identities and each actual fragment. These are original ZIP bytes, without archive recompression or geometry changes. The complete ZIP includes every original archive member, including the lower-resolution shorelines and WDBII line datasets. Only `gshhs_f.b` is inventoried as the intended full-resolution nested polygon operand for the next PR.

`custody.py` reads immutable ordinary Git inputs, reconstructs the ZIP, verifies every whole member, then inventories every original native record in source order. Both complete executions at immutable `f778478cc6f4995b0e603dafb8560fce5436ab92` are retained separately and byte-identical. Original big-endian integer coordinate bytes remain in the complete member; the JSONL roster records source offsets, exact full-record and coordinate-byte hashes, all original header integers, native bounds, container/ancestor IDs and flags. `area_scale` is the retained raw high-six flag bits, without interpreting a geographic area or historical scale. No native polygon is dropped. The two unclosed original records are the Antarctic L5/L6 alternatives; they remain explicit and are not repaired or conflated with L1.

Reproduce with Python3.12.14, after fetching the immutable producer freeze ref shown in the PR. Use the exact full commit, not a branch or abbreviation:

```
python -B coordination/engineering/global-physical-sources-20261006/custody.py --repo . --commit f778478cc6f4995b0e603dafb8560fce5436ab92 --output .cache/gshhg-new-run
python -B coordination/engineering/global-physical-sources-20261006/controls.py --output .cache/gshhg-new-controls.json
```

The producer requires its actual executed module and imported existing `scripts/evidence/immutable.py` to equal immutable Git bytes. The original source is read from the frozen Git commit; no historical private capture directory is needed. The output directory must be absent. Each ordinary encoded/decoded descriptor stays within the original32MiB limit; the ordered original archive reconstruction is explicit, not declared as a single oversized evidence file. No size limit or gate is changed.

`LICENSE.TXT` explicitly grants use/copy/distribution with retained notices and states LGPL version3 or later. The historical2013 README paragraph says version3 or earlier. Both distributed original texts and `COPYING.LESSERv3` are preserved exactly; the conflicting version wording is not silently reconciled. `LICENSE.TXT` references `COPYINGv3`, which is absent from the actual18-member binary ZIP. This packet does not invent an original member or assert independently settled licence interpretation. The package author credits Paul Wessel and Walter H. F. Smith, University of Hawaii and NOAA; original notices remain inside the full original source and as exact ordinary documents.

This is original source custody, not physical approval. The2017 compilation contains older WDBII lake inputs, uncertain source dates and known registration differences from modern imagery. Rivers can have no polygon width, seasonal/current water remains unknown, and absence of recorded water never means dry land. Native coordinate storage precision is not accuracy. No geometry validity, mapped land/water membership, political assignment, repair, delivery or production claim is made here.

Issue1261 remains open after this PR. Its second PR must compare all95,173 complete current global components against nested original L1–4 polygons with source-relative complete footprint results and explicit date/precision/validity/container/seam/numerical unknowns. Parent1202 remains unfinished. The original component audit pins are retained as immutable baseline bindings; this custody PR does not rerun or relabel the candidate audit.
