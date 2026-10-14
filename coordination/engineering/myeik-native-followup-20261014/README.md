# Measured Myeik locality follow-up

Issue #1874; scoped continuation of the accepted #1866 delivery path. Proposed
repository delivery adds 1,109 native map cells to two existing locations:
Palaw 1,055 and Myeik 54. It preserves all 15,269 previously selected additive
cells, for 16,378 cumulative cells, and every occupied native owner. Deployment
and complete regional/historical approval are separate, not requested here.

## Qualification and withheld cells

The frozen queue's complete locality candidate set contains 2,067 cells. Current
ownership was reread at accepted main aaad1215c1b215b415d219b682bc0ff0380d8c73;
none of the initial 1,165 unique land candidates had already been assigned.
Independent complete Myanmar/Thailand source-family membership checks reproduce
the stored candidate memberships without mismatch. Palaw and Myeik have unique
source membership, no retained Thailand reference-country overlap, valid current
and original geometries, and no interior territorial holes. Of these cells, 777
lie outside both coarse Natural Earth country polygons (730 Palaw, 47 Myeik).
That is retained coastline-resolution disagreement, not competing country
ownership: the topology reconciler preserved non-overlapping coasts and only
split shared coverage. Neither target carries a topology-reconciled flag.

Queue uniqueness alone failed to capture Tanintharyi's accepted country-border
reconciliation: 50 of its 56 nominally unique land candidates lie in the retained
Natural Earth Thailand polygon. The current topology reconciler used this exact
country reference. All 56 are withheld for coordinated territorial review,
including the remaining six; they are not repaired or resolved. Five additional
Tanintharyi cells conflict with mapped Thai administrative owners. Another 897
source-relative cells (Palaw 835, Myeik 62) lack supported physical interpretation.
All 958 withheld cells retain exact selectors in evidence/queue-disposition.json
and independent-review/source-qualification.json. They remain work under #1202.

The original Myanmar township source represents 2019, from Myanmar Analytics
Project/USAID through geoBoundaries, CC BY 4.0. Complete original product custody
is unchanged. GSHHG 2.3.7 uses heterogeneous historical observation dates; physical
source support does not establish perfect present-day ground truth or historical
jurisdiction. No inland-water candidates occur here. Physical water and territorial
identity remain independent; no nearest-bank inference is used.

## Verification and measured phases

Preparation began 2026-10-14T04:42:26Z. Exact queue extraction took 0.968 seconds;
current-source/current-owner acquisition and candidate subtraction took 4.806
seconds. Unchanged complete GSHHG source-hierarchy interpretation took 5.520 seconds
and had no target interpretation issues. The final two-target immutable authority
constructor took 1.158 seconds. These overlap with independent review and are not
end-to-end throughput claims.

Actual cumulative selected-reader/readback at dc89b511a015fd7fd7f77e122fb625e6a53f4992
validated all 16,378 selected cells against complete affected owner rows in 98.093
seconds, with 436,318,208 bytes peak RSS. The source-target native/runtime suite's
nine tests passed after materializing its pinned latitude input and using the
existing installed locked @noble/hashes 2.0.1 dependency. Actual CI, emitted-package
validation and ordinary integration/merge timing remain pending.

## Reproduction and retained evidence

Use the existing `constructOriginalAuthority` export in
`scripts/delivery-handoff-advance.mjs`, an `ImmutableReader` pinned to the candidate,
and the two commit/path locators in this packet's `authority-binding.json`.
This authenticates the full consumed sources and literal native proposal through
the admitted constructor. The unchanged physical reproduction program is retained
at `coordination/engineering/source-target-native-delivery-20261014/evidence/physical-reproduction.py`.
In a fresh bounded workspace place this packet's original-stage-inputs.json at
.cache/full-census/all-stage-inputs.json, create .cache/full-census/gshhg-direct,
and place the pinned comparison.py module beside the retained reproducer. Run
with Shapely 2.1.2/GEOS 3.13.1. It authenticates complete original native-member
and metadata parts before interpreting the relevant source hierarchy.

The independent executable probes remain preserved in the reviewed engineering
history at f3877cd164d0b143c556fe7ed6b4bec06622e02f under this packet's original
independent-review/ paths. Their actual source and ownership result receipts stay
in the data-only final packet. New copies of those helpers are unnecessary for
this delivery and have been removed from its final diff. No evidence is concealed
by renaming code as data. Later workers can inspect or reproduce the reviewed
engineering evidence at its exact historical commit.

The compact evidence manifest binds source catalogue/native member/metadata indexes,
exact current-selection inputs and actual result bytes. The physical reproducer
owns full original-body authentication; the compact manifest does not claim to
independently re-execute that science. Actual integration still verifies the
accepted main plus exact reviewed head.

## Qualification instructions for later family workers

Trace accepted topology reconciliation to its retained country-border authority,
not only unique administrative-source lineage. Check candidate cells against
competing countries and explicit territorial exclusions. A lack of interior holes
does not establish absence of territorial exclusions. Distinguish competing-country
coverage from absence in coarse coastline polygons: the accepted reconciler
preserved non-overlapping coastlines. Keep the Tanintharyi discrepancy and exact
withheld intervals unresolved until coordinated territorial review. Physical river
water remains independent of territorial identity; never assign by nearest bank.

For later data-only packages, use existing admitted constructors and retained
engineering reproductions instead of adding standalone executable helpers to the
batch. The first author run here conservatively selected the full suite because
copied helpers and a modified earlier queue README made the diff more than inert
selected data. Removing those unnecessary copies restored file-level data-only
eligibility. The unchanged classifier still rejects accepted source-native .py,
.bin.gz and .f64le.gz role extensions at its inert-pin boundary, so this delivery
uses conservative full CI. No classifier or source-role disguise is introduced.
Record this packaging overhead and dependency wait separately from computation,
warm geography and end-to-end delivery timings; no fast-route claim is made.
