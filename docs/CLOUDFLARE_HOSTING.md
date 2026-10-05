# Cloudflare hosting with existing Neon

For a public website, explicitly build with `ATLAS_PUBLIC_READ_ONLY=1`. This permits anonymous reads and forces read-only behavior even if `ATLAS_READ_ONLY=0` is accidentally configured. Private JWT protection remains the default for every other value. Deploy the reviewed public package before removing the corresponding Cloudflare Access application; otherwise the edge login still applies. Preserve the previous private configuration for rollback.

Before accepting either access mode, compare the static `atlas-geography.json` reference release with the live temporal snapshot's release ID, hierarchy hash and footprint hash. Exercise the combined historical loader, including inline temporal pages. HTTP 200 responses alone do not establish matching releases; staged static release6 and published Neon release5 are incompatible. Serve the verified published release's matching assets or complete its separately authorized publication; never weaken the loader's pin checks.

The alternative build deploys the hosted atlas API and fixed map assets to the user's Cloudflare account. Neon remains the existing PostgreSQL project, with the existing runtime role and schema. No database provisioning, schema migrations or content imports run during this build or deployment. The Sites build remains available for rollback.

## Build and private access

Use Node 24, `npm ci`, and the pinned Python preparation dependencies in `requirements.txt`. Configure a Cloudflare Access self-hosted application covering the entire Worker hostname and an explicit owner email allowlist. Email one-time PIN is supported. Preserve the old Site's owner-private audience; code collaborators use GitHub, and do not automatically receive visitor or database access.

Set `ATLAS_ACCESS_TEAM_DOMAIN` to the team's host (for example `atlas.cloudflareaccess.com`) and `ATLAS_ACCESS_AUD` to the application's exact audience, then run `npm run build:cloudflare`. The result is `dist/cloudflare/wrangler.json`, its Worker entry and `dist/client/` assets. The build reuses the prepared static asset pipeline, but does not package D1 migrations or apply Sites' whole-archive transport budget. Wrangler's dry-run and deployment must verify the actual account's Worker and asset limits before release.

The Worker verifies Access JWT signatures, issuer, audience, expiry and required claims through the team's published keys. Missing or invalid configuration denies all requests. `assets.run_worker_first: true` is essential: authentication covers static assets as well as API routes. Preview URLs are disabled. If additional domains are introduced, protect them with Access too; JWT verification must remain enabled at the application boundary.

## Secrets and deployment

Use a scoped Cloudflare API token, restricted to the intended account, with Workers Scripts Edit, Workers R2 Storage Edit, Account Settings Read and Access Apps and Policies Edit. Initial organization/identity-provider setup also needs Access Organizations, Identity Providers, and Groups Edit. Keep the token outside Git and pass it through `CLOUDFLARE_API_TOKEN` in the deployment process environment, with `CLOUDFLARE_ACCOUNT_ID`. Never put credentials in command arguments or logs.

Activate R2 in the account, and create a private `worldatlas-archives` bucket. The build binds it as `BUCKET`. Keep public bucket URLs disabled. Before deployment, configure Access protection for the destination hostname. Deploy the reviewed package with `npx wrangler deploy --config dist/cloudflare/wrangler.json`. Store the existing runtime-role Neon URI as the `DATABASE_URL` Worker secret using Wrangler's hidden prompt or stdin. Do not substitute an owner-role URI. Keep secrets out of generated configuration, source files and evidence.

The build selects `ATLAS_CONTENT_BACKEND=postgres` and `ATLAS_READ_ONLY=1`. The wrapper also denies mutations when the read-only flag is missing or malformed. Enabling writes requires an explicit `ATLAS_READ_ONLY=0` publisher cutover after database maintenance is settled. A read-only app flag is not a database-wide SQL maintenance lock.

## Archives and cutover

Sites-managed R2 belongs to the existing Site's storage context. It is not the new account's bucket. Retrieve an actual complete inventory/export using the owning Site account or a preserved verified export. Copy original object bytes under the same keys, retaining content types and checksums. Compare every copied object's byte length and SHA-256 with its authoritative inventory, and resolve any collision before proceeding. Tracked reference archives alone do not prove completeness of later uploads. Do not silently regenerate archives, rewrite database object keys or declare migration complete from an empty bucket.

The current database recovery/compaction publisher operations own their production windows. Coordinate with their original issues and the durable publication registry before any shared-data operation or write restoration. Migration preparation does not supersede their read-only state or authorize another publisher.

Before cutover, pin the reviewed code, current geographic release, prepared assets and database state. Verify anonymous requests cannot retrieve assets, API responses or media; verify owner login, map modes, dates, search, current content reads and archive/media checksums. A Worker deploy receipt only proves deployment, not data parity. Exercise import/idempotency checks only in the designated publisher window after explicit write restoration.

Keep the old Site and its storage until the new host's acceptance is verified. Rollback changes the website destination back to the old Site; it does not restore or overwrite Neon. Preserve receipts and original archives. A CI integration should deploy only reviewed merged code, use a protected environment and its scoped secrets, and avoid concurrent publishers or automatic database migrations.

References: [Access for Workers](https://developers.cloudflare.com/workers/configuration/cloudflare-access/), [JWT verification](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/), [external CI](https://developers.cloudflare.com/workers/ci-cd/external-cicd/).
