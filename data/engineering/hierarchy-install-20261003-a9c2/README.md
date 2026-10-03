# Offline installation of three reference hierarchy corrections

Issue #6, second permitted PR, worker `engineering-hierarchy-crosswalk-a9c25e14-20261003`. The actual same reservation was rotated after PR673 merged; `reservation-renewal.json` retains the accepted bot result. Original immutable data baseline is `277b8ecbb3199ae3d5fb07bab96353d17a049b1c`; concurrent storage PR671 is incorporated without changing this generation's source bytes.

The reviewed correction retains Monaco/Luxembourg area identities and names, consolidates Hancock into the existing West Virginia province, and preserves the retired province with its exact reference record and explicit same-tier merge. The complete original identity/source chronology is replayed through prior-v4/prior-v5 archives. Existing registered definitions, historical claims, source bytes and published releases remain preserved. No new location or factual assertion is introduced.

## Reconstruct from committed inputs

Use Node24, Python3.12 and the committed requirements in an isolated environment. Outputs must be fresh external directories; replace the example paths if they already exist. The old baseline-specific 49,589-location preparer is not used.

```sh
python scripts/rebase-reference-hierarchy.py --request data/engineering/hierarchy-crosswalk-20261003-a9c2/baseline-request.json --output /tmp/atlas-correction-crosswalk
python scripts/verify-hierarchy-install-baseline.py --inventory data/engineering/hierarchy-install-20261003-a9c2/baseline-inventory.json.gz --receipt /tmp/atlas-correction-baseline.json
node scripts/prepare-hierarchy-correction-release.mjs --candidate /tmp/atlas-correction-crosswalk --output /tmp/atlas-correction-release
node scripts/prepare-hierarchy-correction-install.mjs --candidate /tmp/atlas-correction-crosswalk --release /tmp/atlas-correction-release --stage /tmp/atlas-correction-install
```

Full historical proof replay invokes the existing geographic creation validators and therefore needs the pinned Python dependencies. Initial adapter field-name and missing-dependency failures are recorded in the execution checkpoint; they are not counted as passing validation. Intermediate stage logs are retained as distinct vintages. Final generation and preservation verification are still pending at this checkpoint.

## Evidence and approval limits

`baseline-inventory.json.gz` has3,307 exact whole-file descriptors. `baseline-verification.json` verifies each committed blob and checkout byte with the shared immutable preparation helper, split into ten bounded partitions without raising limits. Compressed identity-proof archives preserve whole-file bytes; replay separately hashes every safely extracted member. A larger archive's aggregate expansion is not represented as a single bounded JSON input.

The offline install composes both existing producer receipts through their actual archived predecessor bytes, retaining migration chronology and source/record/interval bytes. Existing legacy detached projection hashes remain explicitly limited; their archived `prior_revalidation` links govern the preserved generations. It does not assign dated memberships or transfer historical claims.

Macro compatibility proves all116 existing macro identities, memberships, geometry fingerprints and envelope bytes unchanged. Approval remains the original reporting-convention approval. Candidate certificate/publication state is explicitly pending, with no new semantic, source-completeness, physical-precision or regional approval. All regional location-attribute imports remain closed. Original certificate, review, handoff, gate and publication receipts retain their archived vintages.

This checkpoint has no live installation or publication. Local reversible preparation/apply validation does not verify served assets. Exact-head independent review, required CI and serialized accepted merge still precede publisher handoff. The designated publisher must recheck actual served release and serialize release/Site verification, including preserved claims and archive readback. Use a partial issue reference until complete acceptance is actually verified; if publication requires scope beyond the two-PR budget, propose bounded coordinator-reviewed follow-ups.

The complete generation is larger than one512-descriptor evidence contract. Repository evidence rules allow reviewed partitioning. Planned voluntary aggregate evidence binds bounded manifests and exact union of changed-file receipts; it will explicitly verify descriptor count, byte limits, baseline/original hashes and every preservation file. The current legacy queue does not automatically enforce this aggregate contract; do not claim it does. Final independent review must inspect every partition and unique hash.
