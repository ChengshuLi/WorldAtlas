# Read-only provider capacity inspection — 3 October 2026

GitHub issue 50 and its canonical claim are authoritative. Worker `engineering-night-20261003-7e91f438` owns claim `6737f393-7cdb-4186-be3f-793a64c0eb70` on fresh branch `engineering/provider-capacity-20261003-7e91`, based on actual main `8a22c155c114bf1ce4393a38e26535a74a3d7f32`. Previous issue23's actual merge and confirmed release are retained as serial-resume evidence, not current work claims.

## Outcomes and receipts

- `neon-project-readback.json`: existing project-only manual workflow37144379658 succeeded on main8a22c15, four GETs; PostgreSQL18, production/default branch, neondb, existing owner/runtime roles. No SQL or credentials requested.
- `neon-capacity-readback.json`: explicitly dispatched source-pinned workflow37144853024 at61c8b31ed428e1592e3df252ebf8dfc9143e614f. Project/branches/endpoints returned200. Configured logical branch limit1024MiB, shared history21600seconds, compute0.25–2CU, idle setting0 (plan default). Five consumption quota fields unreported. Organization GET404: account plan unverified, no inferredFree status or unlimited billing allowance.
- Artifact blob download was unavailable through egress; exact successful workflow console's deliberately sanitized JSON supplied the receipt. No signed URLs/credential values are retained here.
- `live-capacity.json`: failed first client inspection, all five API requests200; strict number-vs-PostgreSQL-decimal-string media-sum assertion failed before object scan. This is not a product/server failure or complete pass. Original failed outcome retained.
- `live-capacity-recheck.json`: complete corrected inspection. Capacity827506688 physical database bytes, application guard800000000 (not provider quota), revision2620. All414 registered R2 objects returned206/one byte with provider-reported sizes matching manifests, total236228730bytes. Six metadata GETs returned200;420requests total. Immutable before/after snapshot fingerprints equal. No whole-object checksum, unregistered bucket inventory or account-wide billable-size claim.
- `capacity-contract-tests.log`: nine focused tests passed, zero skips/failures. Existing capacity/catalog checks exercise actual byte warnings and revision safety; new controls cover GET-only/secret allowlist, denied organization proof, missing quotas, wrong project and invalid/lossy quota values.
- `capacity-summary.json` and `file-receipts.json`: technical outcome/whole-file hashes, not historical or geographic approval.

## Official sources and interpretation

Original HTML, source URL/status/time/whole-file SHA256 and visible-text derivatives are retained for current official Neon and R2 pricing. `neon-capacity-api-definitions.json` is a selected literal schema extraction from the retained official Neon API page, not account/example facts. Documented ProjectQuota/units, endpoint and organization fields drive the sanitized inspector. Public pricing cannot establish configured account plans or remaining monthly allowance. See `docs/PROVIDER_CAPACITY.md` for the exact distinctions and operator response; prior original measurements and archives remain unchanged.

No provider plan upgrade, resource provisioning, SQL connection, migration, baseline rerun, factual write, geographic approval, Site publication or token/audience change occurred. The application/API code is unchanged. Site24 and its Site23 rollback remain the last actual publication under issue39.

## Reproduction and serial resume

Manual `neon-verify.yml` uses existing GitHub server secrets only; never place them in chat or local logs. `scripts/verify-neon-capacity.mjs` performs at most four fixed-origin GETs and retains only allowlisted fields. Failed account proof remains explicitly unavailable. The private live inspector accepts existing Sites access on hidden raw-TTY stdin only and writes a fresh owned receipt; one-byte R2 reads verify availability/size, not hashes.

Read fresh issue50/39 checkpoints, current main, AGENTS.md and repository coordination rules before resuming. Confirm the same canonical active worker/claim/branch and avoid a competing writer; never recover an expired lease outside the recovery procedure. All work is read-only with `live_work=false`. Finish one permitted PR, request distinct exact-head review with honest account/object limits, pass required latest checks, use serialized squash queue, verify matching bot result and actual merge, then release the claim. Continue another ready unclaimed engineering item; the standing goal remains active. Inaccessible account facts are expressly allowed to remain unverified by issue50's acceptance; no credential pasted into chat is needed.
