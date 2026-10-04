# Registered immutable object recovery

Issue #51 measures a current backup and isolated restore. SQL V2 preserves 23 factual tables and raw JSON TEXT, but explicitly excludes binary object bytes and the owner-only migration registry. This tool supplies one bounded registered-object part. It does not complete the PostgreSQL or provider recovery acceptance criteria.

```sh
NODE_USE_ENV_PROXY=1 node scripts/verify-retained-object-recovery.mjs https://worldatlas-explorer.chengshu-li-2013.chatgpt.site/ /durable/private/new-isolated-directory
```

Use the configured proxy and CA when required by the runtime. Enter the existing Site bypass token as hidden terminal JSON stdin; never put it in arguments, Git, output or files. The designated publisher coordinates production reads on #39 and retains the normal reservation/live-operation receipts.

The command only sends GETs to the confirmed Site: a V2 marker, bounded registered-media pages, complete `/api/media/{id}` responses, and a final marker. Both markers must describe the same complete known PostgreSQL V2 snapshot. A later installed V3 schema requires separate reviewed complete-schema recovery; a V2 legacy projection is rejected. Nonempty footprint-object references require a separate coverage implementation and are rejected rather than silently omitted.

Every registered media row retains its original ID, object key, source ID, status, byte count and SHA-256. Shared keys may have multiple retained IDs only with identical byte pins. The default ceilings are 1,000 rows, 512 MiB total and 32 MiB per object. The tool requires complete HTTP200 bytes, rejects range responses and conflicting content lengths, streams into a new private isolated directory, checks the original full hash/length and then reopens the recovered bytes to check local readback. Only after an unchanged final marker does the receipt say `verified`.

The request deadline covers fetch and body transfer; an external abort also stops capture. No automatic overwrite or blind retry exists. Failures preserve categorized receipts and any partial bytes. A new attempt uses a new directory; an existing recovery directory is rejected. The receipt contains relative object paths and actual durations, not credentials. This local copy is recoverable while its bytes remain retained; it is not an offsite disaster-retention policy or a provider-managed backup.

Unregistered R2 objects, billable account storage, access configuration and provider retention are outside this registered inventory. Source/SQL/claim/interval/correction/identity/owner-schema recovery remain separate requirements. Do not call marker stability an authoritative SQL capture: the service may remain writable during this immutable-object read, and the existing complete SQL exporter still requires the documented maintenance protocol.

Validation uses positive full-byte/local-readback controls and negative corruption, truncation, oversized/partial transfer, repeated identity, incomplete schema, omitted footprint coverage, marker change, deadline and abort controls:

```sh
node --test test/retained-object-recovery.test.mjs
```

Synthetic controls validate the tool only. Actual source receipts must explicitly identify the tested Site/revision/marker, complete registered inventory, full per-object byte/hash results, local retention and unavailable SQL/provider recovery.
