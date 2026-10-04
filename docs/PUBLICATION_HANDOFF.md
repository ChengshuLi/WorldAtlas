# Independent implementation and publication

Ordinary engineering workers validate implementation without depending on the production publisher. Local or deployed previews identify their exact code, dataset and runtime. Read-only features may use an authorized production read-only API/connection; ordinary bounded reads need no deployment appointment. Writes, imports, migrations or destructive tests use isolated data/database, and heavy load tests require coordination. Never give a preview production write credentials or silently run its startup migrations against production. Functional checks must exercise the real changed behavior rather than only mock its implementation. A preview proves its stated scope; it does not prove current production credentials, bindings, real database recovery, deployed geography certification or production performance. Remote preview access/hosting must be authorized; this protocol provisions no services or credentials.

## Performance acceptance

A worker may verify a loading-time target in its own preview using a full authorized snapshot of the real atlas in isolated storage, or authorized production read-only access. Record exact code/data pins, dataset size, hosting/database configuration and region, browser/device/network, measured start/end event and cold/warm cache/connection conditions. Exercise the real API/rendering path and repeat enough runs to expose variation; report the stated statistic and failures rather than the fastest run. A tiny fixture, localhost-only speed or a different backend cannot establish an equivalent hosted target. If a preview calls the existing production API, it exercises that deployed backend version; changes to API/server code must also execute the changed code under test rather than silently benchmark the old handler. Shared production cache/traffic effects must be recorded. These measurements can satisfy implementation acceptance when the issue agrees on those conditions; identify any production-only residual separately. The publisher later verifies actual delivery/deployment regressions without holding the implementation worker idle.

## One durable handoff

After reviewed, validated merge, the implementation worker posts one request on #714:

- Request ID and originating issue/PR links; exact merged commits, release/data/assets pins and preservation evidence.
- Desired publication action, affected services and acceptance checks; independent preview/test results and their limits.
- Required permissions/dependencies, rollback plan/receipt and any production-only checks still outstanding.
- State `ready` or a concrete blocker. Prefer `start when eligible`. Specify a future start only for a stated coordination reason or user request.

Do not add another confirmation round merely to toggle the implementation holder’s flag. A complete durable handoff permits normal issue-claim release when all PRs are merged/closed and no holder-run live operation is active. Record that implementation is handed off and link the request before releasing. The publisher does not require an active implementation claim solely for delegated Site publication. Preserve the worker’s branch, receipts and original source history.

An issue whose acceptance is entirely implementation can close after that acceptance is verified. An existing issue requiring actual publication stays open with its remaining acceptance explicit. Record its publication-only remainder as blocked from duplicate implementation claims, or split it into a bounded publisher-owned follow-up retaining the original criteria/history. Do not close or rewrite the original scope to pretend delivery occurred. If later implementation is needed, create/reopen an appropriate reviewed work item rather than silently modifying a released branch. Workers can claim other eligible issues after their safe handoff/release.

## Publisher-owned operation

One designated publisher records and owns one operation on #714:

- Operation/request ID, publisher worker ID, originating issues and exact approved commit/release/data/assets pins.
- State `active`, start/last-check time, bounded expiry/timeout, rollback reference and required access/read-only/drain context.
- Fresh checks: current request still eligible, exact review/CI/pins valid, no competing or unsettled operation/process, preserved records and valid rollback.

Read all unresolved operation records and originating receipts immediately before starting. A newer quiet comment does not erase an older unsettled operation. Start when eligible; do not introduce an arbitrary future appointment. Timeout/expiry bounds work and is not permission for another operation to overlap or a requirement to sleep. Expiry alone never proves cleanup or safe settlement.

Publish, immediately perform the actual served acceptance checks, then append a result with state `verified`, `failed-settled` or `unsettled`; exact deployment/release/asset identifiers, evidence, limits and rollback/cleanup outcome. Only verified applicable acceptance supports issue closure. `Unsettled` blocks the next live operation until explicitly resolved. The publisher updates the operation record itself, not another worker’s claim/identity. It does not need an extra confirmation from an implementation worker whose complete handoff remains unchanged. Material scope/input changes require renewed evidence/authorization as appropriate.

This reuses the existing cooperative single-publisher queue. It does not create an atomic/server-enforced lock, change provider permissions or serialize unrelated repositories. The GitHub merge queue remains independent. Validated publications may batch compatible merged changes if all requests, exact combined pins and acceptance remain traceable; do not mix incompatible migrations or conceal a failed request.

## Production-specific exceptions and transition

A current production database backup cannot be certified by a synthetic restore; production bindings/migrations and actual served release claims also require production evidence. The CURRENT_POSTGRES_RECOVERY.md workflow supports the same handoff through a bounded publisher-owned production-only child after explicit release of the original implementation claim. The publisher holds/toggles its own child reservation; the implementer can move on. The legacy original-claim path remains for already-agreed operations. Follow that workflow's exact child/scope/recipient/read-only/drain checks; never bypass them, impersonate another holder or release an unsettled operation. Ordinary preview acceptance does not open geographic certificates or historical-import gates.

Before switching an already agreed operation, reread its current claim/process/outcome. Safely finish or explicitly amend and settle it under the original rules; never clear another worker’s active flag. A scheduled start changes only through an explicitly recorded authorized amendment. This protocol’s start-when-ready default applies to new eligible requests.

The publisher and existing worker chats must reread this document and update their saved goals/automation instructions. Repository prompts do not alter a running chat’s saved instructions automatically. No Site deployment or credential change is needed to install this coordination guidance.
