# PR #1411 standalone-writer integrity repair

This is the additive, bounded follow-up requested by #1557. It leaves all 198
original files and both original writers in
`indonesia-borneo-source-fitness-20261007` unchanged. The two new entry points
make safe, exclusive outputs under this owned packet's `runs/<run-id>/`
directory.

## Identity inventory

`identity_writer.py` authenticates the original family row, complete 45-ID
roster, both original products, and the historical writer bytes before deriving
the same 45 native identity values and null-geometry registry. It checks both
whole output byte streams against the original files before publishing either.
The dated runs `run-20261009-identity-c` and `run-20261009-identity-d` are
fresh, exact byte matches. Each run has an output-hash inventory and a final
completion receipt.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 research/geography/indonesia-borneo-writer-integrity-1411/identity_writer.py --run-id run-YYYYMMDD-a
```

Run IDs are one component and must be fresh. The program chooses every output
path itself; it cannot be pointed at the original packet or an arbitrary path.

## BIG KSP assessment

`big_writer.py` admits its full fresh run before reading the supplied BIG file,
any retained records, or importing Shapely. It requires a caller-supplied local
17,648,743-byte response whose SHA-256 is
`d45aedf8f0f70031804a2666e1a6061cb5c67c1a36add6fee51ed3dd273ee94e`.
It has no network client. The saved 138-byte selection response at
`inputs/big-selection-response.json` is authenticated against SHA-256
`f270c1c04cf8a53bf48ec5c9b632d6642680ce67c3f07b3a0b0f47477a0e517c`, parsed
offline, and checked against the exact ordered 12 IDs and selection envelope.
The local exact-hash geometry was already preserved outside the repository at
`preserved-ignored/issue-1355-big-source/big-2022-ksp-features.geojson`; it
was read without copying it into this packet. The assessment source declares
no open redistribution license, so no raw BIG geometry is committed.

The final runs `run-20261009-big-offline-c` and
`run-20261009-big-offline-d` match each other and match the retained historical
assessment's scope, 45 component rows, and summary. The reproduced historical
summary is 47 positive-area pairs across 43 of 45 components; two have no
intersection in the selected source subset. This reproduction demonstrates
the writer's deterministic output boundary against exact retained bytes. It
does not reverify or certify the geography: territorial meaning, administrative
parents, legal authority, effective date, current completeness, positional
accuracy, water/physical class, source rights, and whether non-intersections
are gaps remain unresolved. The eight current Indonesian ADM2 contact features
were hash-pinned and identity-checked read-only; they were not edited or treated
as territorial approval.

Run offline when the exact local source is lawfully available:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 research/geography/indonesia-borneo-writer-integrity-1411/big_writer.py \
  --run-id run-YYYYMMDD-a \
  --source-file /path/to/the/exact-local-BIG-response.geojson
```

The source argument is never fetched, followed through a symlink, or copied to
the packet. The code authenticates its bytes, the 45 component comparison file,
the eight current contacts, the retained selection response, original run
assessment, source receipt, and old producer code. Shapely is imported only
after those checks and output admission.

## Safety reproduction

`test_writer_integrity.py` exercises 11 focused controls. It covers fixed
output publication, ordinary sentinels, a dangling run-path link with literal
target `run-missing-target`, a symlinked `runs` ancestor with literal target
`../ancestor-target`, traversal, tampered pins, missing/duplicate/fabricated
identities, changed comparison products, and zero source/computation callbacks
on BIG output refusal. Synthetic BIG fixtures test publication and receipt
integrity only; they make no geographic claim. The original corrected CLI was
also run twice for identity and twice for BIG using the exact local source.

The first BIG attempt, `run-20261009-big-offline-a`, is preserved as an empty
failed unique run with its original `FileNotFoundError` in
`failed-attempts.json`. It stopped at a selection-snapshot path mismatch before
opening the BIG source or importing/using Shapely; no output or completion
receipt was created. The path defect was corrected before the final two BIG
runs.

See `evidence-quality.json` for all 53 exact scope identities, original
historical file pins, execution/output hashes, source limits, and numeric
bindings. This repair proposes standalone research tools only; it changes no
core geography, imports, deployment, publication, source certification, or
regional approval.
