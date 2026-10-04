# Full-size native archive transport

Production run37244242006 reached database ACL replay but failed with unchanged source and confirmed lock/target cleanup. A 22,510,251-byte stdin buffer produces spawnSync EPIPE when a successful child stops reading early. The small native fixture did not exercise production-sized TOC input.

Keep original archive bytes in isolated writable tmpfs, verify their SHA256, and give pg_restore a seekable filename for TOC and selected ACL rendering. SQL ACL selection/extraction and source contracts remain unchanged. Each native helper command has a sanitized fixed diagnostic stage; raw stderr/commands/secrets are never published.

The exact helper native fixture now includes at least22MiB of synthetic incompressible archive data, exercises and records the legacy TOC stdin result, and verifies identical source/restored/after inventories, database/default/table ACLs, raw bytes and isolated cleanup. Local early-input-close controls supplement the native fixture; actual production recovery remains required before any Neon compaction. No source SQL or factual edits.
