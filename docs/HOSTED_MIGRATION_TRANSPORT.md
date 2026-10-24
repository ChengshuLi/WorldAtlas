# Historical Site migration transport

The Site-only latest-main build and its transport/budget commands are retired.
Their historical procedure and implementation remain in Git at
`e0a3e2a447394175fd23c7097e0e4498fa7a4175` and in the frozen private Site recovery
copy. This retirement does not alter immutable `drizzle/` migrations, dated
receipts, Neon backup/restore, archives or provider resources.

Current publication uses [Cloudflare](CLOUDFLARE_RECOVERY_HANDOFF.md) and the
[publication handoff](PUBLICATION_HANDOFF.md), not a Site recovery build.
