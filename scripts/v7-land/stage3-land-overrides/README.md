# Stage 3 land override research code

This partial, research-only package contains the selected-decision contract, a streaming land-only overlay, and focused tests. It preserves physical water as unassigned, rejects conflicting targets and mainland component claims, and emits attribution for changed spans. It does not claim a final map or V7 equivalence.

The runner uses the adjacent point-component and named-identity resolvers and the stage-2 candidate/lineage validator in the recovery package. It still requires separately reviewed components and an authenticated, revision-bound selection and source files before use. No datasets, decision selections, configurations or results are included here.

Run the local focused tests with `cd scripts/v7-land/stage3-land-overrides && python3 -m unittest discover -p 'test_*.py'`. The selected-point driver additionally requires the external dependencies above; the included tests are not an end-to-end production proof. The full mixed point/polygon integration is not yet complete.
