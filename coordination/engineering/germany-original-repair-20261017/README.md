# Germany original ADM3 repair: source checkpoint

Issue: https://github.com/ChengshuLi/WorldAtlas/issues/2410

This checkpoint is **unqualified**. It preserves complete original inputs and
source screening after the recovery interruption. It contains no accepted
native authority or selected-delivery proposal.

## Exact original scope

The unchanged stock `source-batch-intervals.mjs` at accepted
`282d14b4682f738fed6a0e6f3ee0d0e4b775d611` extracted
`gb-DEU-ADM3--repair-evaluation`: 27,555 cells (27,043 land, 512 inland
water), 7,499 intervals, 82 owners, 21 localities, native blocks 20–22.
Its complete original outputs are in `original-intervals-001/`.
All eight shared queue hash inputs and the nine block bodies were authenticated.
Exact original interval comparison found no overlap with the accepted
6,028,236-cell additive patch or Sweden's entire 18,381 original and 18,380
supported cells at `a1a8c3060a97cfc0648a7412c1662e19fde83f76`.
The comparison receipt pins each full input body. This does not replace the
later canonical native-base zero-owner check.

## Sources and identities

All complete retained German ADM1/2/3 sources were reconstructed from the
original-source corpus and checked against their full decoded hashes.
Their 16, 38 and 428 geometries are valid, nonempty and explicitly CRS84.
All original 82 owners join to exactly 100 ADM3 shape identities: 64 owners
have one atom, 18 have two. Preserve every existing city/multipart owner ID
and all atoms. No name-only join or one-feature-per-owner assumption is valid.

The source ZIP at geoBoundaries ref `9469f09` matches its Git-LFS pointer:
6,515,218 bytes, SHA256
`20b6aad172dbbf1cfa45805ebffad5cb16062b414393d7f08a3845c9d167dea8`.
The separately retrieved official BKG archive is explicitly the 31.12.2021
version. Both original ZIPs, historical license evidence, source metadata,
projection history and documentation are preserved in
`source-review/upstream-provenance-001/`.

Source: [BKG NUTS250 2021 archive](https://daten.gdz.bkg.bund.de/produkte/vg/nuts250_1231/2021/).
License: [Data License Germany Attribution 2.0](https://www.govdata.de/dl-de/by-2-0).
Attribution: © GeoBasis-DE / BKG 2026 (Daten verändert), with provider,
dataset URI, license link and changed-data notice. The consumed derivative
also requires geoBoundaries attribution. This checkpoint does not apply the
newer 2024-and-later terms PDF retroactively.

### Important physical/source distinction

There are 428 ADM3 records, but 401 distinct district names. Official NUTS3
has 401 GF=4 land records and 27 GF=2 extensions into the North/Baltic Sea or
Lake Constance. The geoBoundaries conversion deleted GF and NUTS codes.
Ordered names and vertex/part counts agree with the official archive, but
80 records have reordered polygon parts; this is not exact coordinate or
water-role equivalence. The full all-atom geometry and physical roles still
need reconciliation. Do not treat duplicate names as interchangeable shapes,
or historical source membership as proof of present legal/physical truth.

## Resume

1. Authenticate current selected footprint/owner joins for all 82 owners and
   their complete 100-atom unions; preserve original feature IDs.
2. Reconcile source water extensions, complete foreign-original exclusions
   and native frames without substituting a country-only classifier.
3. Assemble complete original physical inputs and runtime custody, then use
   the existing stock physical/source producers. Retain every unsupported
   original cell explicitly.
4. Construct genuine stock native authority only for supported cells; run
   meaningful writer controls and focused tests.
5. Obtain independent exact-head source review, then prepare a separate
   selected delivery against actual accepted main. Only acceptance changes
   delivered counts; held original cells keep the package unfinished.

The repository owns immutable source inputs; local dependencies and access
credentials are deliberately excluded. No previous Sweden or Tanzania
science was rerun for this screening.
