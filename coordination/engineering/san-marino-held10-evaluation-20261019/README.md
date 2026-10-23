# SMR original ten-key proposed disposition

This preserves team1's completed v11 proposal for `gb-SMR-ADM1--repair-evaluation`
and its unchanged supporting outputs. It is a durable evidence handoff for
[#1202](https://github.com/ChengshuLi/WorldAtlas/issues/1202) and the original
[queue delivery #1869](https://github.com/ChengshuLi/WorldAtlas/pull/1869), not a map change.

`interval-proposed-dispositions-v11.json` is the byte-identical 102,827-byte author
packet, SHA-256 `a0a4215e1c81cf4fee0e6db6bd7b361ab8f8815194d9b7a9a71bcf8df83f5a24`.
All six original intervals / ten keys remain held with `accepted=false`, zero
accepted credit, zero completion count and zero denominator change. The documented
unresolved/no-repair exception is proposed only; repository delivery does not grant
acceptance, source qualification, repair credit, import or publication authority.

## Retained references

The packet's original local path strings are historical provenance, not commands
to locate files in a reader's checkout. The following exact, unchanged bodies are
retained here; their SHA-256 values remain those recorded by v11:

- `evidence_pins.candidate_inventory`: `smr-original-10-candidate.json`.
- `evidence_pins.source_raster_matrix`: `smr-original-10-source-raster-membership-v4-20261019-001.json`.
- `evidence_pins.all_nine_center_relations`: `smr-original-10-all-nine-cell-center-pip-v1-20261019-001.json`.
- `evidence_pins.selected_owner_observation` and `selected_owner_observation_join`:
  `selected-owner-observation.json`, SHA-256
  `424cc6c62051327f9b8d2701dd72f257f056d24d5114235fcc76a60052de3e13`.

The packet also retains a hash of its historical `contract_assessment` v1. That
older assessment is not included here and is not normative support for the current
disposition: v11 quotes the original queue contract directly, and its explicit
exception/acceptance boundary supersedes that assessment. No missing body is
represented as reviewed or silently reconstructed.

The original queue/catalogue/lineage/block/mask/source bodies remain at the exact
repository commit, path and object/hash pins in these files. They are not duplicated
or recomputed here. The queue pin is `77609a1f159bfee954e52d48a883c5fe3e4b59f5`.
The original catalogue SHA-256 is
`d3da799558be1fcbe7f3ea90ba7033d312a65690984983cb008f2d72e32765f9`.

The selected-owner observation uses data `03b369b72d07dbcd086c2163d4406a521f517180`
and code `21a38f0b531c8c647467f3ddc75043b138e7608d`.
Its [independent full-body audit](https://github.com/ChengshuLi/WorldAtlas/pull/2536#issuecomment-6262148502)
verified the original ten-key scope, authenticated stored-owner and latitude inputs,
and zero base/additive/effective owners with no overlap. This observation does not
reread the ledger body or establish source/physical qualification.
The [original-mask clarification](https://github.com/ChengshuLi/WorldAtlas/pull/2536#issuecomment-6262318274)
identifies the six original intervals as retained mask class land, not present-day
physical truth or repair qualification.

## Interpretation and verification limits

V11 distinguishes owner-candidate index `[7129]`, source-feature contact, original
mask class and observed current ownership. The nine-feature comparisons are point
centres, not whole-cell geometric/exclusion qualification. Current applicability
under retained exclusions and current physical/source requirements remains unresolved.
The earlier supporting outputs retain their original status/limitations; v11 is the
current proposed disposition and does not silently revise predecessor bytes.

Publication checks verify byte preservation, JSON readability and unchanged held /
zero-credit flags. Existing factual reviews are reused, not represented as a new
raster, point-in-polygon, geometry or selected-owner execution. Independent review
must bind the complete final Git diff and exact public head before ordinary delivery.
