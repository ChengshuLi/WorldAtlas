# Ural mismatch exception evidence inventory

This handoff provides historical diagnostic spans and input pins. It does not
authorize an exception or define a complete current mainland-boundary allowlist.
No map was rebuilt and no geometry was selected or changed.

## Verified sparse result

`exact-historical-spans.json` records zero-based, half-open row spans, preserving
event labels, V7 reference labels and the independently validated qualified seed.
Its producer authenticated every listed input before and after processing and
checked each historical event against the actual pinned grid files.

* The 3,391 historical draft-82 northern Ural corridor mismatches occupy 2,180
  spans. All have physical land code 17 and qualified seed 18 or 19; these seed
  categories identify the selected physical Eurasian mainland root 650207 for
  this exact component generation. They are not a complete current Ural mismatch
  set and have not been approved as exceptions.
* The 57 historical draft-136 delta overlay changes occupy 15 spans. All have
  physical land code 17, V7 reference 19 and qualified seed 0. They are outside
  the selected physical Eurasian mainland root. Thus a mainland-only exception
  predicate excludes all 57, despite their proximity to the selected river.
  Their downstream classification may have a separate source-based rationale;
  that does not turn them into mainland-boundary exceptions.

The selected seed report has SHA-256
`8e2062312b1988af8eb4cd1a7fcba5b0f42fb765adc05b7cec4fa8a78a1cff77`.
It binds seed rows/runs, physical rows/runs, selected snapshot
`615bc1aaa67d099ebd140dc172fd54885d66e82ef595a57a97e5a284f483f7cc`,
and component rows/runs
`4beda178bfc7beeb2d30cbdfa5901a48f9a41bb82c69e534d4c8cddfdb09aea7` /
`18d7f36fa22c5728662cdd40487bf684108da030c074fec6d22ac378d0df0961`.
The separately validated full seed coverage report, SHA-256
`5522de4831471789dbe6ae8ed0aa91c235a0860760633f96b500d6900d1bc458`,
checks all physical land and all four complete seed roots. Numeric root 650207
must never be reused with another component generation.

## Existing predicates and their limits

1. **Selected physical-mainland membership:** on the pinned qualified seed,
   `seed(x,y) in {18,19}` exactly identifies cells of the selected physical
   Eurasian mainland component. It excludes the nonseed delta cells above.
   It is a necessary filter, not an exemption for all Eurasian errors. It does
   not establish membership in a component of the physical/reference shared-land
   intersection: deleting physical-mask differences can split components.

2. **Delta side assignment:** the reviewed research overlay uses strict cell
   center inclusion in `[51.3,46.65,52.2,47.24]`, physical land code 17,
   candidate Europe/Asia categories, and the selected divider's global polygon
   side (Europe 19, Asia 18). The box and witnesses bound that operation;
   there is no mainland-component restriction. The draft-136 independent audit
   checked 43,575 physical-land centers and scope seams. Neither the box nor
   all of those land centers form an authorized exception mask.

3. **Historical northern corridor:** `/tmp/ural-draft82-mountain-corridor.json`
   selected both-land Europe/Asia disagreements within an approximately 1 km
   WGS84 sampled-source corridor; refinements and local tangent directions were
   diagnostic, with numerical and global-side limitations. The 1 km width was
   not an approved exemption tolerance. Its exact 3,391 cells can be studied
   individually; neither the corridor nor its broad discovery box is an allowlist.

4. **Shared-land comparison clusters:** the historical comparison report uses
   `shared-land-8-connected-wrap-v1` and counts physical-mask disagreements
   separately (305 candidate-land/reference-water, 369 reverse, totaling 674
   for its pinned inputs). It describes clusters as diagnostic, not executable
   corrections. No authenticated shared-mainland witness membership predicate
   or complete exception span set was found in the inspected Ural artifacts.

## Necessary current exception contract

A defensible executable predicate must combine a pinned, current sparse
candidate/reference land mismatch event with: the permitted label pair; verified
mainland membership for the chosen topology; and membership in an explicitly
reviewed line-relative changed region or exact reviewed row spans. The default
outside the reviewed set must remain rejection. Geographical distance alone,
label pair alone, component membership alone and a broad box are insufficient.

Current sparse mismatch inputs have not been supplied to this audit. A final
Ural definition also needs an explicit choice of exact changed region / spans
or justified line-relative tolerance and exact endpoint handling. Current
raw-source derivation still needs defensible mountain-gap and principal-headwater
joins, river-mouth interpretation and Caspian closure. The old V7 construction
and old V7 cell match are not requirements for choosing the new boundary.
These geographic questions do not permit exemption of unrelated island errors.

The selected Ural geometry hash observed earlier was
`5a6526344cacbc1a23be174f589cec9710a0f317360ec5c8737ba6956c3f7fe2`;
Caspian closure `6ee86cf4108b8622e01a4dd0be0b4ae19e809b4e04d8cceb25547425258ac62a`.
The earlier selection attestation is point-in-time and checks stored hash fields;
refresh and independently bind actual geometry before current use.

This Ural audit does not review or certify a Caucasus or Panama exception set.
The same old snapshot names Caucasus geometry
`9f4ae3bc778ebbcd0258a19868acf0fa655763f5e849361196160fb4289c0d52`
and Panama geometry
`cfbfbb514d0f6efff1c0c803ae5f0f0835225015568747bb8b1164f3bb6d0e17`;
those historical hashes are not proof of their current selection or approved
exception cells. The Caspian water closure joins Ural to Caucasus; it must not
be used as a broad land exception connecting both areas.

## Reproduction

`inputs.json` contains actual local paths and exact hashes. Remap paths only to
identical verified bytes. Run `python3 audit_existing_predicates.py inputs.json
NEW_OUTPUT.json`. It writes a new diagnostic file only. `python3 -m unittest -v
test_sparse_membership.py` passes three checks, including 100 randomized exact
span roundtrips and boundary tests for RLE lookups. No third-party libraries are
required. The code validates queried rows; the full coverage checks remain the
separately pinned prior evidence.
