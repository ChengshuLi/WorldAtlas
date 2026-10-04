# ENG 0 checkpoint — 2026-10-04 06:24 UTC

Claim 6280f87c-c2be-425b-b0ae-e1ba35e73c46 remains active, live_work=false, on engineering/sql-recovery-20261004-7e91. First partial PR711 actually merged as 16da778105250d33b749ed6e0a9d0141dc1f6f1a. One final PR remains in issue51's two-PR budget.

Local implementation now includes a trusted-main manual native pg_dump/isolated restore workflow, exact current source/window/canonical-claim checks, full factual raw-row hashes, private owner registry and table permissions/sequence comparison. Existing owner credentials are obtained inside the trusted workflow, passed through hidden stdin, and never written to Git or public artifacts.

The repository is now public: plaintext backups and raw private inventories stay in the ignored private runner directory; retained artifact delivery is AES-256-GCM with a pinned RSA-OAEP-SHA256 public recipient. The recipient's private key stays outside Git. No actual recipient credentials have been generated or rotated. ENG main selects the authorized recipient and coordinates the actual live read/owner window on714.

58 unit controls pass, including ciphertext/tag/key tampering, recipient and run/window replay binding, source/target drift, mismatched live claims, bounded owner API responses and failure before provider access in untrusted contexts. These are local synthetic controls, NOT evidence of actual current production SQL recovery. Native fixture integration, operational documentation, independent exact-head review and package/CI validation remain before final PR/queue. Production SQL recovery remains unverified until an actual current coherent backup is restored and checked.

Actions now have fresh successful executions after the user's billing fix. No production capture, deployment, DDL, credential rotation or shared live operation was performed by this checkpoint. ENG main remains sole publisher. Preserve previous object caches and receipts.
