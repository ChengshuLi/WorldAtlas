# Provider capacity and operator response

Inspected 3 October 2026 UTC for issue 50. Original official pages, sanitized account readbacks and application measurements are retained in `data/engineering/provider-capacity-20261003-7e91/`. Older receipts retain their original dates and values.

| Fact | Evidence | Meaning and limit |
| --- | --- | --- |
| PostgreSQL database bytes | 827,506,688, `pg_database_size`, 18:31 UTC, revision 2620 | Measured use, not a row-to-byte forecast or provider logical-branch measurement |
| Application guard | 800,000,000 bytes, warning fraction 0.8, `at-or-above-budget` | Planning guard, not Neon quota; measured database is 27,506,688 bytes above it |
| Configured logical branch limit | 1,024 MiB, management API at 18:38 UTC | 1,073,741,824 bytes; do not subtract differently defined physical database bytes to claim quota headroom |
| Production compute | 0.25–2 CU configured autoscaling range | Configuration, not monthly compute use or account allowance |
| Scale-to-zero setting | `suspend_timeout_seconds: 0` | Official API defines zero as the plan default; exact idle timeout is not established |
| Shared project history | 21,600 seconds (six hours) | Configuration, not a backup/restore rehearsal or recovery guarantee |
| Project consumption quotas | Five supported fields unreported (`null`) | Active/CPU time, write, transfer and logical-byte quotas are not invented; zero/empty project-quota semantics do not prove unlimited billing allowances |
| Organization plan | Unverified; organization GET returned 404 | Existing identity reads project/branches/endpoints; 404 does not distinguish missing organization from unavailable authorization |
| Registered media metadata | 414 objects, 236,228,730 bytes | Manifest total; PostgreSQL aggregate arrives as an exact decimal string, converted only within the safe integer range |
| R2 size readback | Separate `live-capacity-recheck.json` | One-byte ranged reads measure provider `object.size` through Content-Range; full coverage requires `completed:true`. No whole-object digest or unregistered inventory claim |

The original 512 MiB guard, later 800 MB runtime guard and 950 MB geographic review guard are dated application decisions, never provider free-plan quotas. This work does not raise the runtime guard or change a plan.

## Public allowances and account proof

The official Neon pricing page inspected at 18:31 UTC advertises Free with 1 GB PostgreSQL storage per project, 100 CU-hours per project/month and compute up to 2 CU (8 GB RAM). Its table describes history up to six hours or 1 GB of changes. These are published terms, not proof this organization uses Free. Do not replace advertised GB with GiB or equate CU-hours with an unreported project CPU-seconds quota. Neon's separate object-storage allowance is not the existing R2 bucket's allowance.

The official R2 pricing page inspected at 18:32 UTC lists Standard free tier as 10 GB-month/month, one million Class A requests/month and ten million Class B requests/month. It describes storage/operation charges and no Internet egress bandwidth charge. Infrequent Access has different retrieval/operation charges and does not inherit the Standard free tier. None of this proves this Site-managed account's storage class, remaining operations, billing allocation or quota.

Sites archive/per-file limits belong to publication issue 39 and deployment-budget receipts. They constrain packaged application/assets independently of PostgreSQL, R2, history and compute. The 20 MiB media-upload endpoint limit is an application transport limit, not a bucket allowance.

## Operator response

1. Read `/api/storage/capacity` through documented private access and retain timestamp/revision. Use actual `database.bytes`, `measurement`, `configured_budget_bytes` and `budget_status`; never multiply record counts by invented average bytes.
2. At `approaching-budget` or `at-or-above-budget`, pause planned bulk expansion for coordinator review of measured database/index/query growth, logical-branch usage and actual billing/compute allowances. Preserve current facts and archives. Do not delete evidence, rerun baseline transfer or upgrade a plan automatically.
3. Review guard changes explicitly after provider verification. A higher guard does not increase quota. Geographic approval/import gates remain separate; capacity checks certify no complete regional branch.
4. Treat unavailable measurement as unknown. Keep manifests, actual sizes, whole-object integrity and account-wide billable storage separate. Ranged reads do not verify SHA256; prior immutable whole-object preservation receipts remain intact.
5. Complete separately authorized isolated recovery before relying on backups. Never restore over production to test recovery.

## Access and reproduction

Manual-dispatch `neon-verify.yml` uses existing server-side `NEON_API_KEY` and `NEON_PROJECT_ID`. The capacity step is GET-only, bounded and project-scoped with a strict output allowlist. It requests no URI/password, performs no SQL, and provisions or changes nothing. Successful source-pinned execution and sanitized console JSON are retained because artifact blob egress is unavailable. Do not print signed artifact URLs or credential errors verbatim.

Account-plan completion needs an authorized Neon organization-read identity or secure console connection to the same organization; current project-read identity returned 404. R2 account/billing completion needs a supported read-only connection for the existing Cloudflare account/bucket or a Sites-managed quota readback. No such management connection is currently configured. Never paste credentials into chat. Inaccessible facts remain explicitly unverified, as this issue's acceptance permits.

Retrieve existing private access through native Sites `get_site` and supply it only on hidden raw-TTY stdin:

```sh
node --use-env-proxy scripts/verify-live-capacity.mjs data/engineering/YOUR-OWN-JOB/live-capacity.json
```

Use a fresh owned output path. The fixed production origin accepts supported GET routes only, bounds pages/requests/responses, records object sizes separately and compares immutable before/after snapshot markers. No token enters arguments, Git, browser input or logs. Failed attempts retain `completed:false` and are not acceptance or certificate evidence.
