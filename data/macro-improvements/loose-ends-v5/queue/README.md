# Read-only v5 queue preparation

`plan.py` streams candidate parts and retains IDs, parent chains and two new source-property records, rather than keeping the world's geometries. It has no GitHub/API mutation capability. Existing 273 packet memberships/owned paths stay exactly unchanged; two one-subject supplements account for Gardner and Kingman. Their shared Hawaii/Line Islands parents remain regional integration work.

Preview command:

```
python3 data/macro-improvements/loose-ends-v5/queue/plan.py --candidate CANDIDATE_DIRECTORY --issues FRESH_ISSUES_JSON --output PLAN.json.gz
```

An issue snapshot must include number, state, body, updated_at and labels. Optional `canonical_claim` contains the verified current claim. Closed issues and observed active claims are preserved exactly. Other planned updates still require a fresh canonical comment-claim check before every eventual write.

Publication requires `--handoffs FINAL_HANDOFFS --live-confirmation ROOT_RECEIPT`: release5 IDs/hashes/certificate/count must match; historical imports stay blocked. Preview supplements are blocked. After idempotent creation, pass their key→number map as `--created-issues` and regenerate numeric approval dependencies. Optional `--changed-ids` supplies retained subjects needing evidence revalidation.

The root publisher alone applies the plan using the established fresh body SHA, updated_at, exact labels and canonical claim guards. Preserve issue IDs, states, comments, claims and PR links; replan late edits. Do not apply an unverified plan or one with unresolved numeric links. Then verify every packet and dependency by GitHub readback. Tests: `python3 data/macro-improvements/loose-ends-v5/queue/test_plan.py`.

Root-only application helper: `node data/macro-improvements/loose-ends-v5/queue/apply.mjs --plan=PUBLISHED_PLAN.json.gz --repo=ChengshuLi/WorldAtlas --output=APPLICATION_DIRECTORY --create`. It discovers existing issue markers before creating supplements and saves `created-issues.json`. Regenerate the published plan with that map and a fresh issue snapshot, then run the same helper with `--apply` instead of `--create`. Without either flag it only prints counts. Creation and application are separate; unpublished plans and unresolved numeric dependencies fail before writes. Closed or active-claimed issues are skipped, late body/date/label edits stop the queue, and successful body-only writes are read back and journaled. Resume by rerunning: matching bodies are idempotent; never blindly trust earlier log entries. Tests: `node --test data/macro-improvements/loose-ends-v5/queue/test-apply.mjs`.
