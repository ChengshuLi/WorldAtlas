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
and original geometries, and no interior territorial holes.

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

Preparation began 2026-10-14T04:42:26Z. Exact queue extraction took 0.970 seconds;
current-source/current-owner acquisition and candidate subtraction took 4.807
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

Run `node coordination/engineering/myeik-native-followup-20261014/reproduce.mjs`
to authenticate whole consumed sources and the literal proposed native patch via
the unchanged source-native constructor. The original physical reproducer is
retained byte-for-byte as evidence/physical-reproduction.py. In a fresh bounded
workspace place original-stage-inputs.json at .cache/full-census/all-stage-inputs.json,
create .cache/full-census/gshhg-direct, and place the pinned comparison.py module
beside the reproducer. Run with Shapely 2.1.2/GEOS 3.13.1. It authenticates complete
original native-member and metadata parts, then selects the relevant whole source
hierarchy; it does not use old gap polygons as physical truth.

The compact evidence manifest binds source catalogue/native member/metadata indexes,
exact current-selection inputs and actual result bytes. The physical reproducer
owns full original-body authentication; this compact manifest does not pretend to
independently re-execute that science. Retained source and authority limitations
remain explicit. The independent review script and its complete pinned receipt are
under independent-review/. Later unrelated main changes do not invalidate these
unchanged scoped sources or selected bytes; actual integration still checks the
accepted main plus exact reviewed head.
