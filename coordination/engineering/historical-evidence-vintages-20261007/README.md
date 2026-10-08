# Historical evidence vintages: #1448

The original #1381 pins require input files from a37ad37 and later retained
outputs from a1cf4cd. No single baseline commit contains all the promised bytes.
The opt-in baseline version 2 resolves files by immutable commit and path, while
keeping result evaluation distinct. Legacy valid single-baseline manifests remain
supported. New versioned declarations cannot be silently ignored.

The compact fixture retains issue pin metadata, not datasets. The read-only
`check-1381.mjs` reads immutable Git objects at the recorded geography PR head,
expresses every original pin at its original commit, adds the actually executed
helper without replacing its old pin, and selects retained metric inputs explicitly.
Some identical-hash pins originally shared one manifest path; the conformance
check restores each original issue path and verifies its own bytes. It changes
neither GEO 1's branch nor its issue contract.

Run from the repository root with the fixture commits available in Git:

```sh
node coordination/engineering/historical-evidence-vintages-20261007/check-1381.mjs
node --test test/historical-evidence.test.mjs test/evidence-quality.test.mjs test/premerge-evidence.test.mjs
```

`conformance-1381.json` retains all reported source limitations. It proves local
representation conformance only. No packet runner or full GIS calculation was
executed. It does not establish factual correctness, hosted gate acceptance or
which helper executed independently of the runner's code. GEO 1 remains stopped
until the repair is reviewed, merged and verified on actual main. GEO 1 then owns
updating its manifest, renewed review and real trusted hosted validation. #1448
remains open until that final acceptance has been proven.
