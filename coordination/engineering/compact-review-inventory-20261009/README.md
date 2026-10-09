# Complete review inventory commitments

This changes the existing normal exact-head receipt validator. A compact receipt
binds the complete changed/renamed path list and whole evidence hash list with
canonical count/SHA pairs. Literal receipts keep their behavior. Exact head,
manifest, distinct reviewer, issue/PR disposition, domains, limits and unresolved
changes-requested checks remain mandatory. The normal queue uses this same
validator; evidence descriptor/byte admission is unchanged.

The committed original input capture binds PR1593 at immutable 0d04 and its actual
base f0c44, all 470 paginated GitHub changed paths and the whole immutable manifest.
Its 481 unique evidence hashes produce 87,288 characters before review prose and
domains. `run-one/measurement.json` and `run-two/measurement.json` are two genuine
fresh metadata CLI outputs and are wholly byte-identical. This measurement does
not approve the geography described by that manifest.

The actual 21-test suite passed twice at the source commit in
`controls/execution.json`, including all original tests, compact schema/type
adverses, omitted/changed/renamed paths and hashes, authority/domain/limit refusal,
and the actual normal comment-selection route with a complete 470-file fixture
whose literal receipt exceeds 65,536 characters. A later unresolved review still
blocks. Fixtures are explicitly synthetic, not scientific executions.

Reproduce the metadata measurement with the pinned Node runtime:

```
node --test test/premerge-evidence.test.mjs
node coordination/engineering/compact-review-inventory-20261009/measure.mjs fresh-run
```

The CLI admits all complete metadata inputs, current executable bytes and the
actual imported module closure before reading input bodies, verifies their whole
hashes, and writes only a fresh ordinary directory. It neither runs source
preparation nor changes geography, an artifact selection or a map.

The subsequent real large review/normal queue admission for PR1593 is an explicit
remaining original-issue integration proof. It can occur only after that PR's
independent substantive review and required checks are complete; this packet does
not claim it happened. No scientific replay or geographic approval is requested.
