# Compact membership compatibility profile

This second part of #783 installs an explicitly versioned PostgreSQL compatibility profile. Original scientific identities, all retained release rows, seven membership fields and raw evidence TEXT remain unchanged. Private integer keys and a collision-checked exact-byte evidence dictionary reduce repetition; public inserts still run the original immutable/geography guard functions.

Storage V4 exports either the complete original V2 or V3 factual inventory under separately pinned public and private compact catalogs. Original V2/V3 catalogs remain strict. Restricted runtime roles cannot read the private dictionaries, execute owner copy helpers or use identity sequences. Metadata verification rejects other-owner functions/sequences, private grants (including column grants), changed projection definitions and disabled internal foreign-key triggers.

The copier reads bounded pages inside PostgreSQL and returns only its cursor and row count. Offline full-size rehearsal loads the whole reviewed prepared inventory, checks exact row parity and pinned public lookups, proves no-new-writes rollback and measures the compact-only fixture. The fixture uses synthetic shared registry descriptions and empty unrelated factual collections; it is not a production backup, Neon capacity measurement, release approval or delivered Site.

V4 durable export retains part hashes and resumable cursors, limits request deadlines and adapts to oversized pages. Logical restoration creates the original base schema and preserves every original factual field; it explicitly excludes native private tables, owner migration registry, ACLs and private sequences. Native production backup, restore rehearsal and a reviewed owner maintenance runner are the remaining implementation part. Do not retire a production original heap based on these offline results alone.

To reproduce, use Node24 with locked dependencies. Run the commands in the owned evidence manifest, supply fresh absolute full-size output/target directories and retain failures. Generate catalog pins into a fresh output directory; do not overwrite historical pins.
