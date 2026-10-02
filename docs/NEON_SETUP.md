# Neon project setup and pending migration

The user created PostgreSQL project `weathered-lab-37571695`, production branch shown as `br-summer-butterfly-ar8qikk5`, with requested database name `worldatlas` and PostgreSQL 18. Provider metadata has not yet been authenticated/verified from this workspace. Do not assume the displayed branch ID/name, database settings or free plan have been verified merely because they were provided in conversation.

## Workspace setup completed

- Global Neon CLI 7.0.6 installed from the official `neon` package.
- `neon skills -y --agent codex` installed the official agent guidance under `.agents/skills`, with `skills-lock.json`.
- Project-level OAuth MCP setup in `.codex/config.toml` pins `https://mcp.neon.tech/mcp?projectId=weathered-lab-37571695`. It contains no credential; the client needs its own OAuth authorization. Installation does not prove callable/authenticated MCP access in the current session.
- `neon config init --services none` installed `@neon/config` and `@neon/env`. The generated policy was replaced with the user's requested bare `defineConfig({})` in `neon.ts`, with no Auth, Functions, buckets or branch-expiry policy.
- Local `.env` files are Git-ignored before any credential pull.

The CLI's attempted browser login timed out. Its redirect targets localhost on this remote workspace, so it cannot be treated as a completed login on the user's desktop. Current cloud readiness reports no secret bindings/outbound identity. Required next input is a project-scoped Neon API key bound as `NEON_API_KEY` through secure cloud environment configuration, or authenticated Neon MCP/CLI access available to this workspace. Never paste connection strings or keys into chat, tracked files, command arguments or receipts.

## Once access is available

Inspect actual current credential readiness; do not print secret values. Verify the project/production branch and database metadata, then link:

```sh
neon link --project-id weathered-lab-37571695 --branch production -y
neon config plan
neon deploy
```

Review the concrete policy diff before applying it. The empty policy must not unexpectedly remove existing services. `neon deploy` applies Neon service policy; it does not migrate the WorldAtlas SQLite schema or move its frontend. Preserve Sites authentication/frontend hosting and existing R2 archives. Check the database name/version/plan and retain nonsecret setup receipts.

Link/apply may pull connection variables into ignored `.env`/`.env.local`; inspect existing configuration before pulling and preserve unrelated values. Use the direct connection for migrations/dumps and pooled connection for normal application queries where appropriate. Server secrets must stay outside browser assets and Git. `.neon` local context is not a portable credential; this document and stable project ID are the restoration instructions.

## Engineering still required before the long-term handoff

Implement the PostgreSQL schema/backend adapter behind the stable API; test on an isolated branch using production-like evidence; migrate all existing stable identities/claims/corrections/receipts without source-byte changes; verify counts/hashes, temporal constraints, idempotent corrections, query plans, complete map snapshots and backups/restore; securely configure the Site's server and publish a verified cutover. `neon.ts` alone does none of this. Read `docs/LONG_TERM_STORAGE_PLAN.md`.

Current production remains D1 + R2 until those gates pass. Luna's generic research format/import tooling should remain unchanged. No PostgreSQL schema, claim migration, production cutover or successful `neon deploy` is claimed by the local setup above. This work remains with the technical maintainer; Luna should research and import supported historical evidence only.
