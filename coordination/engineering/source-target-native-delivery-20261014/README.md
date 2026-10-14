# Source-target native delivery

Issue #1866. This is an additive map-cell repair, with no synthetic addition
polygons and no claim that old geometric-gap counts define visible repair work.
The selected data is under independent review; repository merge and website
publication are separate outcomes.

The original consumed geoBoundaries products identify Kyunsu and Myebon (Myanmar),
Kolaka and Sumbawa (Indonesia), and Dam Ha (Vietnam). Their original retained
whole-product hashes and complete part rosters are in `source-evidence.json`,
joined to the existing original-source catalogue. Administrative identity and
physical water are separate facts. Reviewed territorial holes remain excluded.

## Measured scope

The five whole source targets contain 22,103 currently unassigned candidate cells.
Original GSHHG 2.3.7 level 1–4 interpretation supports 13,963 proposed assignments;
8,140 cells outside its mapped level-1 coastline context remain withheld. No
mapped inland-water candidate occurs in this five-target proposal. GSHHG's 2017
release and heterogeneous observation dates are a source limitation, not a claim
of present-day ground truth or absence of every unmapped water body.

- Kyunsu: 8,222 cells
- Myebon: 2,772 cells
- Kolaka: 704 cells
- Sumbawa: 2,090 cells
- Dam Ha: 175 cells

The proposal preserves every occupied cell, including 1,512 source-covered cells
with another existing owner. Whole-source replacement would also lose 12,930
current target cells outside the consumed source, so it is not used. The selected
cumulative patch retains all 1,306 previous cells and adds 13,963, totaling 15,269.
All 101 previous ledger rows remain literal; five source-target rows are added.
The old inventory denominator describes retained historical evidence only.

Complete source-family products were checked, with 26 original features relevant
to the proposed coverage. Every proposed cell has exactly one source-family owner.
The native operator, latitude bytes, hierarchy and owner identities are unchanged.
This route does not discover islands absent from administrative source products;
physical-land minus actual ownership remains a separate discovery route.

## Validation and reproduction

Run `node coordination/engineering/source-target-native-delivery-20261014/reproduce.mjs`
to authenticate the original consumed products and requalify the literal native
proposal through the shared delivery constructor. It reads immutable retained
bytes and does not repeat the physical-source research or fetch a newer vintage.
Run `node --test test/source-target-native-delivery.test.mjs` for the native-only
operator, current/default and affected historical-context controls.

`evidence/physical-support.json`, `original-stage-inputs.json` and
`physical-reproduction.py` retain the original measured physical comparison.
The latter ran with Shapely 2.1.2 / GEOS 3.13.1 and the unchanged
`coordination/engineering/global-physical-comparison-20261006/comparison.py`.
Its original scratch paths are retained honestly: a reproduction workspace places
`original-stage-inputs.json` at `.cache/full-census/all-stage-inputs.json` and the
original comparison module alongside the script before execution. The script
reads the committed original GSHHG metadata/record parts, authenticates them,
and reconstructs the complete relevant hierarchy; no old gap polygon masks are
used as physical truth.

Independent controls cover original source-family membership, actual current
owner-zero, occupied-cell preservation, wrong owner, shifted native output,
multiple territorial exclusions, source-vintage disagreement, lake/island nesting
and historical-context owner remapping. Physical river water does not veto a
source-supported territorial identity under #534/#528.

Measured local phases are distinct: physical comparison 91.873 seconds,
shared whole-target native operator 9.649 seconds, and immutable source/native
constructor 1.784 seconds. These are not end-to-end delivery times. Initial
integration and accepted-reader composition are reported separately from science.

Actual immutable selected-reader readback on the reviewed dependency composition
passed in 121.315 seconds at 458,149,888 bytes peak RSS: 15,269 cumulative
cells, including 13,963 new source-target cells and all 1,306 prior cells.
The exact tested candidate is retained in `evidence/selected-readback.json`.
This precedes actual emitted-package and ordinary integration validation.
