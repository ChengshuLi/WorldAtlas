# Historical presentation release research

This prototype stores only the structured presentation records and a release manifest in Neon. The manifest binds the existing catalog entries and read-back bytes for the historical proposal, water presentation and reference index, as well as the reviewed code revision and hashes. It creates no new R2 manifest object and does not change or deploy the historical UI.

`presentation_release_schema.sql` creates a separately named table so an earlier empty research table with a mandatory manifest-asset foreign key is not silently altered. The table has foreign keys to the three existing source assets and guards ordinary update, delete and truncate operations. A privileged database owner can alter schema or disable guards. The table does not itself authenticate the manifest or source bytes.

`presentation_manifest_fk_upgrade.sql` is a legacy migration for the earlier, empty research table; it is not used by this Neon-only schema and must not be used for a new installation.

`export_presentation_release.sql` reads a release through an authenticated Neon connection. The caller must independently authenticate the connection and snapshot, compute or obtain the expected manifest digest from trusted evidence, read back and hash the existing R2 objects, and verify the code revision. The verifier checks all those supplied pins, the Neon JSON against the separately pinned manifest, and canonical string-only records before running full historical index parity. The origin fields are assertions, not authentication; Neon-only storage is not an independent signature. On-disk code hashes do not authenticate already executing Python or Node code.

The verifier requires Linux sealed memfds and trusted Python and Node environments. Matching an index does not prove browser rendering, cache behavior, deployment correctness or historical source-creation provenance. Before any UI change, independently verify source rights, test the actual browser and staging deployment, establish a rollback path, and retain the current UI until full parity is demonstrated.
