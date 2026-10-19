# NLD original 208-key residual proposed disposition

This is a byte-preserving durable handoff of the completed v4 proposal for
`gb-NLD-ADM2--repair-evaluation`, following [#2432](https://github.com/ChengshuLi/WorldAtlas/issues/2432)
and the prior [accepted repair delivery #2459](https://github.com/ChengshuLi/WorldAtlas/pull/2459).
No source, geometry, raster, point-in-polygon or selected-owner calculation is rerun.

The original package contains 770 keys: 562 previously accepted repaired outcomes
are conserved, and all 208 residual native assignments remain held. The proposal
covers all 86 held intervals and 14 recorded owners, including the six wholly held
owners. Its status remains `proposed_unaccepted`, package completion remains false,
and accepted-credit and denominator deltas remain zero. Delivery does not by itself
accept these documented-unresolved outcomes, grant new repairs or authorize a map import.

## Complete retained bodies

- `interval-proposed-dispositions-v4.json`: unchanged 570,488-byte author packet,
  SHA-256 `752664893e7ac71fc1136f6f393f837a1f19074203b3e9225810078a81322278`.
- `original-contact-mask-witness.json`: unchanged 24,236-byte compact witness,
  SHA-256 `458c7b3049f2a9948c4eafb2c741d1aa1916d1becd84469c1add890fdea19692`.
  This is the actual body named by v4's `original_contact_mask_witness_pin`, despite
  that field retaining its original local path.
- `selected-owner-observation.json`: unchanged complete 239,247-byte observation,
  SHA-256 `2d78e58dd147cf95b3d809f4ae2a7510f48a1b0a659601cd2da8cd3e5ab0f2f6`.
  It contains all 770 original package keys, not a reduced 208-key witness.
  Data commit: `03b369b72d07dbcd086c2163d4406a521f517180`;
  executable commit: `21a38f0b531c8c647467f3ddc75043b138e7608d`.

The packet's `observation_body_public_pointer` links the
[independent audit](https://github.com/ChengshuLi/WorldAtlas/pull/2536#issuecomment-6262148502),
not the raw body. The complete body is retained above. The separately cited
[PR2536 code merge receipt](https://github.com/ChengshuLi/WorldAtlas/pull/2536#issuecomment-6262087299)
is not an ownership observation or package qualification.

The five original queue/held/source/physical/stage inputs remain at the exact
public repository paths, commit and Git objects in v4's `pins`. In particular the
full original source witness has 39 targets; the supported subset is not substituted.
Original bodies are not duplicated or repinned here. Earlier local contract/join
reports and run-log names remain historical provenance, not additional files a
consumer must locate or newly executed proof. V4 and the included witnesses retain
the current proposal and exact immutable references.

## Interpretation and verification limits

The compact witness records original source-relative contacts and retained land-mask
classification, not present physical truth or current source qualification. The
native observation records stored ownership and authenticated normative latitudes;
it neither rereads the ledger body nor establishes source/geometric qualification.
Its existing audit found 562 target-matching additive-owned keys and 208 unowned
keys, with zero base owners and zero overlap. No new accepted outcomes are claimed.

Publication checks verify exact input/output bytes, readable JSON and preserved
held/zero-credit accounting. Completed factual checks are reused and require the
distinct auditor's final exact-public-head review. The ordinary delivery and explicit
root acceptance remain separate from preserving this evidence.
