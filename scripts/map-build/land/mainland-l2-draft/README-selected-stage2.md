# Mainland decision export

`query-stage2-selected.sql` reads a single Neon decision revision using the
bound `revision` parameter. It exports the registry bindings, raw source
references, boundaries, closure routes, seed regions, witnesses and mainland
rules that belong to the selected revision.

The query reads the schema defined by
[the initial database schema](../../../../migrations/001_initial_schema.sql).
For the full rebuild command and runtime dependencies, see
[the V8 pipeline guide](../../pipeline/README.md).
