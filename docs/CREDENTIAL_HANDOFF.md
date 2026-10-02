# Private PostgreSQL credential delivery

This is technical-maintainer infrastructure. Luna's research workflow does not need a Neon API key, an owner database credential, a recipient private key, or access to the Site's runtime secrets.

`scripts/credential-envelope.mjs` provides a bounded confidential transport for the restricted `worldatlas_app` PostgreSQL URL. It does not perform database migration, invoke Neon, change GitHub settings, install a Site secret, or publish the website. Importing the module generates no keys or credentials. The tests use synthetic accounts and isolated ephemeral keys.

## Trust and encryption

The implementation uses Node's standard crypto primitives: a fresh 32-byte AES key, AES-256-GCM with a fresh 12-byte nonce and 16-byte tag, and RSA-OAEP with SHA-256 to wrap the AES key. Recipient keys are RSA 3072 or 4096 bits; generated recipients use 3072 bits. The recipient identity is the SHA-256 fingerprint of its canonical SPKI public key.

The authenticated header includes the recipient fingerprint, suite, version, repository, workflow path, commit, run ID and attempt, project, branch, endpoint, role, database, source-manifest/schema/runtime-role SQL hashes and validity interval. Decryption requires an exact separately supplied expected context. Envelopes expire within at most 24 hours. Credential payloads are limited to 16 KiB, envelope files to 64 KiB and keys to 32 KiB. Owner-role URLs, another endpoint, a missing required TLS setting, unsupported algorithms, tampering and unexpected fields are rejected.

**Encryption does not authenticate the sender.** Anyone with the public recipient key can construct an envelope. Before decryption, the maintainer must authenticate the GitHub repository, authorized workflow path, event, head commit, successful run, attempt and artifact through GitHub. Obtain the envelope hash from that authenticated run's sanitized receipt. A matching hash prevents changing the downloaded file; a hash copied from an untrusted sender proves no origin. Expected context must be pinned independently, rather than copied wholesale from the envelope.

The utility trusts the authorized CI code and the local OS account. It does not protect against a compromised runner, modified authorized workflow, malicious code running as that account, or an administrator inspecting process memory. Node strings and provider request bodies necessarily contain the credential temporarily. Key and plaintext Buffers are cleared after file delivery where possible; this is not a claim of guaranteed memory erasure.

## Recipient setup

Generate a recipient only when the maintainer authorizes the handoff. The private key must be outside every Git working tree, owned by the current OS user and mode `0600`. Never upload it as an Actions artifact, add it to GitHub secrets, print it, commit it, or include it in chat. Commit or dispatch only the **public** recipient key through the reviewed CI configuration.

For example, after creating an owner-private directory outside the repository:

```sh
node scripts/credential-envelope.mjs generate \
  --private-key /workspace/private/worldatlas-handoff/recipient-private.pem \
  --public-key /workspace/private/worldatlas-handoff/recipient-public.pem
```

This command refuses overwriting either file. It prints only status, recipient fingerprint, algorithm and permission metadata. The public file can then be copied to the authorized CI input. Root must verify that the workflow uses this exact public-key fingerprint. This document does not establish that a production key has been generated or any credential has been delivered.

## Reviewed Actions integration

Root owns the workflow and production migration script. Keep the integration small:

1. Use the existing `NEON_API_KEY` Actions secret only in the authorized production job. Restrict the job to the intended repository, reviewed revision and explicit production action; use minimum GitHub permissions and pinned Actions. Avoid pull-request code execution with production secrets, shell tracing, environment dumps, raw API bodies and raw driver errors.
2. Before production operations, validate the public key with `credentialRecipientFingerprint(publicKey)` and match the authorized recipient fingerprint. Verify the intended project, production branch, database, actual endpoint and schema/migration proof. Provision the restricted runtime role through the reviewed owner-maintenance utility. It preserves an existing password unless explicit rotation is authorized. A newly generated password is therefore not automatically valid on an idempotent rerun.
3. Authenticate an actual restricted-role connection and verify permissions before packaging its URL. Do not transport an owner URL or the API key. Fail rather than encrypt a newly invented password when the role kept an older one.
4. Build the exact public context below from verified project/endpoint metadata and trusted Actions identity. Import `encryptCredentialEnvelope` in the production script, passing the runtime URL in memory. Write the envelope and its ciphertext-file SHA-256 receipt; neither contains the plaintext URL or password. Alternatively, the CLI reads `ATLAS_RUNTIME_DATABASE_URL` from a private environment binding, never a command-line argument.
5. Upload only the encrypted envelope and sanitized verification receipt. Keep artifact access and retention appropriate to the handoff. The private key and unencrypted URL must not enter Actions artifacts, Git, chat or logs.

Required context keys are exact; adding or omitting a key fails:

```json
{
  "purpose": "worldatlas-runtime-database-url",
  "repository": "ChengshuLi/WorldAtlas",
  "workflow_path": ".github/workflows/neon-production-cutover.yml",
  "commit_sha": "40 lowercase hexadecimal characters from the authorized commit",
  "run_id": "positive numeric Actions run ID",
  "run_attempt": "positive numeric Actions attempt",
  "project_id": "weathered-lab-37571695",
  "branch_id": "br-summer-butterfly-ar8qikk5",
  "endpoint_host": "the verified ep-...neon.tech endpoint host",
  "database_name": "neondb",
  "role_name": "worldatlas_app",
  "source_manifest_sha256": "64 lowercase hexadecimal characters from the verified source manifest",
  "schema_sha256": "64 lowercase hexadecimal characters from the reviewed schema",
  "runtime_role_sql_sha256": "64 lowercase hexadecimal characters from the reviewed runtime-role SQL",
  "issued_at_utc": "canonical ISO UTC timestamp with milliseconds",
  "expires_at_utc": "canonical ISO UTC timestamp with milliseconds, at most 24 hours later"
}
```

The explanatory placeholders above are not executable context values. Root must supply the actual authorized workflow path, commit, run, endpoint and times. The credential host must exactly match the verified endpoint or its corresponding `-pooler` host; its username and database must match the context, and `sslmode=require` must be present once.

CLI encryption, when needed:

```sh
node scripts/credential-envelope.mjs encrypt \
  --public-key recipient-public.pem \
  --context authorized-context.json \
  --output runtime-credential-envelope.json
```

Only the runtime URL belongs in `ATLAS_RUNTIME_DATABASE_URL`; the CLI prints ciphertext hash and recipient fingerprint. Never place the URL in shell arguments or display the environment binding.

## Local delivery and the Site boundary

After authenticating the run and artifact, create the expected-context file from those trusted facts, check the recipient fingerprint and use the authenticated ciphertext hash:

```sh
node scripts/credential-envelope.mjs decrypt \
  --private-key /workspace/private/worldatlas-handoff/recipient-private.pem \
  --context authorized-context.json \
  --envelope runtime-credential-envelope.json \
  --expected-sha256 CIPHERTEXT_SHA256_FROM_AUTHENTICATED_RECEIPT \
  --output /workspace/private/worldatlas-handoff/runtime-database-url
```

Decryption writes the URL only to a new owner-only `0600` file outside Git and prints metadata. It refuses weak key permissions, symlinked key files, hardlinked private keys, existing output files, a wrong digest, a wrong key, an expired interval and an unexpected context. It does not print a usable connection string. Preserve the ciphertext receipt as needed; keep the private files local and temporary.

The native Site environment setter accepts a plaintext value with `is_secret: true`, not a filesystem path. Delivering an authorized database credential to that server-side secret store is the necessary final boundary. Root can orchestrate the local file read and secret-aware setter internally, without printing the intermediate result, putting the URL literally into model-generated arguments, or forwarding it through `text`/`notify`. The request still carries plaintext to the authorized secret API over its protected connection. Encryption transport is not a claim that the Site can consume ciphertext as its `DATABASE_URL` or that platform internals never handle the secret.

Set only the intended `DATABASE_URL` secret and backend selector, preserve other runtime settings and audience, deploy the reviewed version to apply the environment revision, and verify the live API's restricted identity and retained data. Keep the original D1 database and archived source bytes until root accepts the read-back proof. Delete the temporary local credential and private key after successful delivery; filesystem deletion is not guaranteed physical erasure on snapshots or SSDs. A lost recipient key requires a new authorized handoff and, where needed, explicit password rotation.

## Verification

```sh
node --test test/credential-envelope.test.mjs
```

The tests cover roundtrip/randomness, authenticated metadata, wrong keys, component tampering, malformed encodings, unsupported suites, expiry/size bounds, restricted-role/endpoint/TLS validation, owner-only outside-Git delivery, wrong hashes, overwrite protection and metadata-only CLI output. They do not prove production workflow authorization, actual Neon authentication or successful Site secret installation; those are root's separately recorded cutover checks.
