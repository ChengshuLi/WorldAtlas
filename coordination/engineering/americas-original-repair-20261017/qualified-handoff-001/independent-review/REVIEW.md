# Independent original-to-actual qualification review

The actual five stock native-authority calls support **63,035 qualified native cells**, preserving **3,884 territorial-held original cells**. I found no mismatch in the original-to-supported/held partition, actual constructor ledgers, owner identities, declared land/water classes, retained source operands, or actual execution custody examined here. This is a review of completed qualification products. **Accepted cells remain zero in this review, and current owner-zero has not been established.**

| Country | Original cells | Actual qualified | Territorial held | Original / qualified / wholly held targets | Qualified land / inland-water |
| --- | ---: | ---: | ---: | ---: | ---: |
| MEX | 24,208 | 24,092 | 116 | 158 / 157 / 1 | 24,087 / 5 |
| ECU | 13,969 | 13,387 | 582 | 58 / 51 / 7 | 13,384 / 3 |
| BOL | 11,311 | 10,404 | 907 | 37 / 34 / 3 | 9,067 / 1,337 |
| PER | 10,371 | 8,922 | 1,449 | 55 / 55 / 0 | 6,714 / 2,208 |
| COL | 7,060 | 6,230 | 830 | 81 / 69 / 12 | 6,230 / 0 |
| Total | 66,919 | 63,035 | 3,884 | 389 / 366 / 23 | 59,482 / 3,553 |

Every held key retains its original owner and the diagnostic reason `territorial_exclusion_cells`. The holds contain 3,883 land cells and one inland-water cell (Mexico). Across the original scopes there are 63,365 land cells and 3,554 inland-water cells; qualification has not relabeled inland water as land. The 23 wholly held targets remain present in the retained original evidence and diagnostic custody. Narrowing the constructor's requested roster to 366 surviving targets has not removed their original records.

## What was actually reconciled

The task-side verifier `review-qualification.mjs` authenticated the pinned input blobs by commit, exact tree path/mode/OID, Git object bytes and SHA-256, then joined the original intervals, source roster, complete original requested patch, original diagnostic decisions, supported input partition, held originals and actual emitted constructor rows. `review.stdout` contains the complete resulting custody pins and country outcomes; `review.stderr` is empty. The initial harness assertion about a version/config field was corrected and its first-attempt logs remain retained separately; it was not an input or constructor failure.

Supported inputs are pinned at `db3801d77516795a6f9b09a241f1196cdc1ccd49`, under `coordination/engineering/americas-original-repair-20261017/country-supported-inputs-001/{mex,ecu,bol,per,col}/`. The original evidence and requested patches remain pinned at `b6900b2fe487f3971045b63fb51c39dd30e013f3`, under `country-source-evidence-001/`. The unchanged full diagnostic decisions are at `049a96969256c7a954b0d0d8b0b6f3a6a85ced87`, under `country-diagnostics-001/`. The roots share the preceding `coordination/engineering/americas-original-repair-20261017/` prefix. Exact per-blob OIDs, encoded/decoded sizes and SHA values are in `review.stdout`, rather than relying on a mutable checkout label.

The actual outputs are the author checkout's `.cache/delivery-handoff/americas-qualified-{mex,ecu,bol,per,col}-001/`. Each output preparation's complete file inventory and hashes match the emitted files. Actual `authority-binding.json` and `original-rule-preimage.json` bind the supported input descriptors; the canonical rule hash and component IDs match the real constructor. I used the unchanged accepted `verifyCompletedSourceTargetNativeAuthority` for completed-result joins and independently compared every interval key and class. This did not replay physical construction, native predicates, or source geometry scans.

For every actual ledger row, its assigned native rows and real cell count equal the supported patch for the same owner. Its base geometry equals the retained original stage's selected geometry, its geometry hash matches the canonical value, and the physical receipt remains the original receipt. All 63,035 actual qualified native keys are also unique across the five countries when compared without country prefixes: zero duplicate native keys. This is not a current ownership census.

Each surviving target retains all original noncoverage fields byte-for-value, including source identity, pixel owner, selected geometry, physical receipt, and territorial exclusion geometries. Only the requested roster and coverage rows narrow to the supported original keys. The top-level source evidence is otherwise unchanged. All positive and foreign family parts match the complete original catalogue part descriptors; the qualification input has not silently removed negative families or reconstructed smaller source atoms.

The actual execution records in `five-supported-authority-execution-001/` document five `native-authority` invocations, all actual wrapper exit 0, each `resumed:false`, and stdout qualified counts matching the actual ledgers. These are distinct from the earlier foreign-applicability scan wrapper's retained sysctl error; that earlier wrapper fact has not been relabeled. `accepted-code-comparison.json` shows all 11 materialized CLI/static dependency files equal the accepted `2d1fc6f430e756498908bf2c4e267356a13f5cc7` Git blobs, including the unchanged native-grid and selected-neighbor implementation. No issue-2428 code was used in this review or these identified calls.

The five actual constructor bodies also match the committed copies at `673b20c77c5b1fd346bb0c846090c3661f8d1ddd:coordination/engineering/americas-original-repair-20261017/country-qualified-authorities-001/{mex,ecu,bol,per,col}/constructor-result.json`. `committed-constructor-custody.json` records their authenticated Git blob OIDs, sizes and SHA-256 values. This establishes the reviewed actual-to-committed constructor custody without asserting a push outcome.

Actual `constructor-result.json` SHA-256 values:

- MEX: `a508e84bb2c44debe935cae2cbfacbf0efd58e26837fef48ad2f569db690e4c5`
- ECU: `135f6037be17457b1771a97efaa42d6e559a81910e1dd68352d75ac64f355a12`
- BOL: `ee5e9afb02c515939ac7de31cbcea7ac53a56e495f6efd853f790fc82bc64e3a`
- PER: `54572467848b9422089cc47844229b235cf98bb7cc2ae7c4e4435e62cdfaba24`
- COL: `a438fb363bb15590a9d897a0e08b7b2e117e3cb57faa81fd05f2cdc018ea3bdc`

## Meaning of the physical and foreign evidence

This review reuses the independent completed physical review at `peru-worker-001/actual-physical389-review-001/REVIEW.md` and my completed foreign review at `foreign-adapter-result-review-001/REVIEW.md`; it does not replace or rerun them. The complete 389-target physical input remains pinned at `29e570dee104b096535f2388e240c119c8517012:coordination/engineering/americas-original-repair-20261017/five-country-physical-001/source-stage-001/original-stage-inputs.json` (OID `e8a3c7ae7384190a9a3c3524da1ef98f62c391c7`, SHA-256 `20703286b02761499790a8e219edc570862a47355d123ccb685acc8ae92d4091`). Every supported evidence set retains physical result SHA-256 `48a9748e5ca358808c6b7125b8ccbe156b4613d8c8a2f41074f047dc09a6dc9b`.

The physical run was a complete diagnostic with real residuals and hierarchy issues: 121 targets had issues, 59 had nonempty mapped-water support with overlap witnesses, and 212 were outside mapped L1 context. Whole original and selected geometries differ for all 389 targets. Qualification does not erase any of these findings or certify a whole parent. The unchanged accepted constructor evaluates requested native centres against the retained residual/conflict witnesses, source coverage, declared class support and territorial exclusions. Its actual completed products apply to the requested keys only. The retained original diagnostic found territorial exclusion to be the reason for all 3,884 held keys; none were reassigned to an adjacent owner.

The five foreign lists equal the independently reviewed complete bounds-method outputs over 368 families and 73,567 feature outcomes, including retained Fiji periodic proof. They retain 5 / 4 / 11 / 11 / 10 foreign families for MEX / ECU / BOL / PER / COL respectively, and surviving targets retain 131 / 111 / 150 / 182 / 123 explicit negative constraints (697 total). Brazil is an existing foreign operand where applicable, not a hardcoded positive selection. Colombia retains both Panama ADM1 and ADM2 negative families. The prior review establishes completeness within the recorded bounds method, not a new universal predicate or rights approval.

## Historical source meaning and remaining limits

The retained original administrative metadata describes the following source vintages and rights claims. These are the historical records carried through the inputs, not fresh grants or a present-day legal-boundary determination:

| Positive family | Retained represented year and provider meaning | Recorded rights |
| --- | --- | --- |
| MEX ADM2 | 2012 World Bank municipios; 2,457 whole-source units | CC BY 4.0 |
| ECU ADM2 | 2019 INEC / OCHA ROLAC cantons; 224 units | CC BY 3.0 IGO |
| BOL ADM2 | 2015 GeoBolivia, derived from ADM3; 110 units, canonical role recorded Unknown | Public Domain / free use and access recorded |
| PER ADM2 | 2020 IGN / OCHA ROLAC provinces; 196 units | CC BY 3.0 IGO |
| COL ADM2 | 2020 DANE; 1,122 units, canonical role recorded Unknown | CC BY 4.0, metadata says noted by CC icon |

The retained source release locators point to geoBoundaries `9469f09`; January 2023 source-update and December 2023 build dates are custody/build dates rather than substitutes for the represented years or contemporaneous provider grants. Counts and modern country labels do not establish administrative meaning. Bolivia's derivation and Colombia's unspecified canonical role remain explicit. No geometry substitution, coordinate transformation, provider-policy change, or licensing reapproval was performed.

Panama's positive original scope remains rights-blocked under issue 2437; the numerical success of the five calls and retention of Panama as a foreign negative operand do not resolve that conflict or authorize publication of Panama geometry. The six-scope accounting remains 89,588 originals = 63,035 qualified + 3,884 territorial held + 22,669 Panama blocked. Honduras future preparation remains outside that accounting.

The actual constructors explicitly limit their result to the requested native centres and retain original whole-source physical/hierarchy and historical source/resource limits. They delegate current owner-zero enforcement to native consumers. This review therefore supports the stated qualified products and preserved holds, while leaving acceptance, current ownership checks, integration and Panama rights resolution unclaimed. No shared branch, source data, geometry, or execution product was changed.
